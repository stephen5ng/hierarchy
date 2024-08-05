#!/usr/bin/env python3

from gevent import monkey; monkey.patch_all()  # Enable asynchronous behavior
from gevent import event
from bottle import Bottle, request, response, route, run, static_file, template
import bottle
from collections import Counter
from datetime import datetime
from functools import wraps
import gevent
import json
import logging
import os
import random
import serial
import sys
import time
import psutil
import signal

from dictionary import Dictionary
import tiles
from scorecard import ScoreCard

my_open = open

logger = logging.getLogger("app:"+__name__)

UPDATE_TILES_REBROADCAST_S = 8

dictionary = None
score_card = None
player_rack = None
guessed_words_updated = event.Event()
remaining_guessed_words_updated = event.Event()
current_score_updated = event.Event()
total_score_updated = event.Event()
rack_updated = event.Event()
tiles_updated = event.Event()
running = False

SCRABBLE_LETTER_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4,
    'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1,
    'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1,
    'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8,
    'Y': 4, 'Z': 10
}

BUNDLE_TEMP_DIR = "."

# mypy: disable-error-code = attr-defined
if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    BUNDLE_TEMP_DIR = sys._MEIPASS
    bottle.TEMPLATE_PATH.insert(0, BUNDLE_TEMP_DIR)
    logger.info(f"tempdir: {BUNDLE_TEMP_DIR}")

# Sends the result of fn_content when update_event is set, or every "timeout" seconds.
def stream_content(update_event, fn_content, timeout=None):
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    while True:
        fn_name = str(fn_content).split()[1].split(".")[0]
        # fn_name = str(fn_content)
        content = fn_content()
        logger.info(f"stream_content: {fn_name} {content}")
        yield f"data: {content}\n\n"
        while True:
            flag_set = update_event.wait(timeout=timeout)
            if flag_set:
                update_event.clear()
                break
            logger.info("TIMED OUT! retransmitting...")
            yield f"data: {content}\n\n"

# app = Bottle()
# app.install(log_to_logger)

@route("/") #TODO: remove
def index():
    global player_rack, score_card
    player_rack = tiles.Rack('?' * tiles.MAX_LETTERS)
    score_card = ScoreCard(player_rack, dictionary)

@route("/start")
def start():
    global player_rack, running, score_card
    player_rack = dictionary.get_rack()
    score_card = ScoreCard(player_rack, dictionary)
    rack_updated.set()
    tiles_updated.set()
    current_score_updated.set()
    total_score_updated.set()
    guessed_words_updated.set()
    remaining_guessed_words_updated.set()
    score_card.start()
    running = True
    print("starting game...")

@route("/stop")
def stop():
    global running
    player_rack = tiles.Rack('?' * tiles.MAX_LETTERS)
    score_card.stop()
    running = False


@route('/shutdown')
def shutdown():
    # https://stackoverflow.com/a/60888399
    print("SHUTTING DOWN")
    sys.stderr.close()

    # current_process = psutil.Process()
    # current_process.send_signal(signal.SIGKILL)

    # server.stop()


@route("/get_previous_guesses")
def previous_guesses():
    yield from stream_content(
        guessed_words_updated, lambda: score_card.get_previous_guesses())

@route("/get_remaining_previous_guesses")
def remaining_previous_guesses():
    yield from stream_content(
        remaining_guessed_words_updated, lambda: score_card.get_remaining_previous_guesses())

@route("/get_rack_letters")
def get_rack():
    yield from stream_content(rack_updated, lambda: json.dumps(score_card.player_rack.letters()))

@route("/last_play")
def get_last_play():
    return player_rack.last_guess()

def get_tiles_with_letters_json():
    return json.dumps(player_rack.get_tiles_with_letters())

@route("/get_tiles")
def get_tiles():
    yield from stream_content(tiles_updated, get_tiles_with_letters_json, UPDATE_TILES_REBROADCAST_S)

@route("/accept_new_letter")
def accept_new_letter():
    next_letter = request.query.get('next_letter')
    position = int(request.query.get('position'))

    # print(f"get_rack {next_letter}, {position}")
    changed_tile = player_rack.replace_letter(next_letter, position)
    score_card.update_previous_guesses()
    guessed_words_updated.set()
    remaining_guessed_words_updated.set()
    tiles_updated.set()
    rack_updated.set()

def get_score_and_play():
    return json.dumps([score_card.current_score, score_card.last_guess])

@route('/get_current_score')
def get_current_score():
    yield from stream_content(current_score_updated, get_score_and_play)

@route('/get_total_score')
def get_total_score():
    yield from stream_content(total_score_updated, lambda: score_card.total_score)

started_updated = event.Event()
@route('/started')
def started():
    yield from stream_content(started_updated, lambda: None)

@route('/guess_tiles')
def guess_tiles_route():
    if not running:
        return str(0)
    word_tile_ids = request.query.get('tiles')
    guess = ""
    for word_tile_id in word_tile_ids:
        for rack_tile in player_rack._tiles:
            if rack_tile.id == int(word_tile_id):
                guess += rack_tile.letter
                break
    score = guess_word(guess)
    logger.info(f"guess_tiles_route s {score}")
    return str(score)

# For keyboard UI
@route('/guess_word')
def guess_word_route():
    guess = request.query.get('guess').upper()
    guess_word(guess)

def guess_word(guess):
    score = score_card.guess_word(guess)

    guessed_words_updated.set()
    current_score_updated.set()
    total_score_updated.set()
    rack_updated.set()
    # print(f"guess_word: {score}")
    return score

@route('/next_tile')
def next_tile():
    # TODO: Don't create a rack that has no possible words.
    l = player_rack.next_letter()
    # print(f"next_tile: {l}")
    return l

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root=BUNDLE_TEMP_DIR)

def init():
    global dictionary, player_rack, score_card
    # For Equinox Word Games Radio theme:
    # equinox_filter = lambda w: "K" in w or "W" in w
    dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open=my_open)
    dictionary.read(f"{BUNDLE_TEMP_DIR}/sowpods.txt")
    index()

if __name__ == '__main__':
    # logger.setLevel(logging.DEBUG)

    init()
    if len(sys.argv) > 1:
        random.seed(0)
    run(host='0.0.0.0', port=8080, server='gevent', debug=True, quiet=True)
