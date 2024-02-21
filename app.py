#!/usr/bin/env python3

from gevent import monkey; monkey.patch_all()  # Enable asynchronous behavior
from gevent import event
from bottle import request, response, route, run, static_file, template
import bottle
from collections import Counter
import json
import serial
import sys
import time
import gevent

from dictionary import Dictionary
import tiles
from scorecard import ScoreCard

my_open = open

dictionary = None
score_card = None
player_rack = None
guessed_words_updated = event.Event()
current_score_updated = event.Event()
total_score_updated = event.Event()
rack_updated = event.Event()

SCRABBLE_LETTER_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3,
    'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

BUNDLE_TEMP_DIR = "."

if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    BUNDLE_TEMP_DIR = sys._MEIPASS
    bottle.TEMPLATE_PATH.insert(0, BUNDLE_TEMP_DIR)
    print(f"tempdir: {BUNDLE_TEMP_DIR}")


def stream_content(update_event, fn_content):
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    while True:
        content = fn_content()
        print(f"stream_content: {content}")
        yield f"data: {content}\n\n"
        update_event.wait()
        update_event.clear()


@route("/")
def index():
    global player_rack, score_card
    player_rack = dictionary.get_rack()
    score_card = ScoreCard(player_rack, dictionary)
    print("calling index...")
    return template('index', tiles=player_rack.letters(), next_tile=next_tile())

@route("/get_previous_guesses")
def previous_guesses():
    yield from stream_content(guessed_words_updated, score_card.get_previous_guesses)

@route("/get_rack")
def get_rack():
    yield from stream_content(rack_updated, score_card.get_rack_html)

@route('/accept_new_letter')
def accept_new_letter():
    next_letter = request.query.get('next_letter')
    if len(next_letter) != 1:
        print(f"****************")

    print(f"get_rack {next_letter}")
    new_rack = player_rack.replace_letter(next_letter)
    score_card.update_previous_guesses()
    guessed_words_updated.set()
    rack_updated.set()
    return new_rack

@route('/get_current_score')
def get_current_score():
    yield from stream_content(current_score_updated, lambda: score_card.current_score)

@route('/get_total_score')
def get_total_score():
    yield from stream_content(total_score_updated, lambda: score_card.total_score)


started_updated = event.Event()
@route('/started')
def started():
    yield from stream_content(started_updated, lambda: None)

@route('/guess_word')
def guess_word_route():
    guess = request.query.get('guess').upper()
    bonus = request.query.get('bonus') == "true"
    score_card.guess_word(guess, bonus)
    guessed_words_updated.set()
    current_score_updated.set()
    total_score_updated.set()
    rack_updated.set()

@route('/next_tile')
def next_tile():
    # TODO: Don't create a rack that has no possible words.
    l = player_rack.next_letter()
    print(f"next_tile: {l}")
    return l

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root=BUNDLE_TEMP_DIR)

def init():
    global dictionary, player_rack, score_card
    dictionary = Dictionary(tiles.MAX_LETTERS, open = my_open)
    dictionary.read(f"{BUNDLE_TEMP_DIR}/words.txt")

if __name__ == '__main__':
    init()
    run(host='0.0.0.0', port=8080, server='gevent', debug=True)
