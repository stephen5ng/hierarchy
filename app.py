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
from paho.mqtt import client as mqtt_client
import paho.mqtt.subscribe as subscribe
import random
import serial
import sys
import time
import psutil
import signal

from dictionary import Dictionary
import tiles
from scorecard import ScoreCard

MQTT_BROKER = 'localhost'
MQTT_CLIENT_ID = 'game-server'
MQTT_CLIENT_PORT = 1883

my_open = open

logger = logging.getLogger("app:"+__name__)

UPDATE_TILES_REBROADCAST_S = 8

dictionary = None
game_mqtt_client = None
score_card = None
player_rack = None
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
        flag_set = update_event.wait(timeout=timeout)
        if flag_set:
            update_event.clear()
        else:
            logger.info("TIMED OUT! retransmitting...")

        # fn_name = str(fn_content)
        fn_name = str(fn_content).split()[1].split(".")[0]
        content = fn_content()
        logger.info(f"stream_content: {fn_name} {content}")
        yield f"data: {content}\n\n"

# app = Bottle()
# app.install(log_to_logger)

def mqtt_publish(topic, message):
    result = game_mqtt_client.publish(f"app/{topic}", json.dumps(message))
    if result[0] != 0:
        raise Exception(f"{str(result)}: failed to mqtt publish {topic}, {message}")

def index():
    global player_rack, score_card
    player_rack = tiles.Rack('?' * tiles.MAX_LETTERS)
    score_card = ScoreCard(player_rack, dictionary)

def start():
    global player_rack, running, score_card
    player_rack = dictionary.get_rack()
    mqtt_publish("next_tile", player_rack.next_letter())
    score_card = ScoreCard(player_rack, dictionary)
    mqtt_get_tiles()
    mqtt_update_rack()
    mqtt_update_score()
    mqtt_previous_guesses()
    mqtt_remaining_previous_guesses()
    score_card.start()
    running = True
    print("starting game...")

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

def mqtt_previous_guesses():
    mqtt_publish("get_previous_guesses", score_card.get_previous_guesses())

def mqtt_remaining_previous_guesses():
    mqtt_publish("get_remaining_previous_guesses", score_card.get_remaining_previous_guesses())

def mqtt_update_rack():
    mqtt_publish("get_rack_letters", score_card.player_rack.letters())

@route("/last_play")
def get_last_play():
    return player_rack.last_guess()

def get_tiles_with_letters_json():
    return json.dumps(player_rack.get_tiles_with_letters())

# for the cubes
def mqtt_get_tiles():
    mqtt_publish("get_tiles", player_rack.get_tiles_with_letters())

def accept_new_letter(next_letter, position):
    changed_tile = player_rack.replace_letter(next_letter, position)
    score_card.update_previous_guesses()
    mqtt_previous_guesses()
    mqtt_remaining_previous_guesses()
    mqtt_get_tiles()
    mqtt_update_rack()
    mqtt_publish("next_tile", player_rack.next_letter())

def mqtt_update_score():
    mqtt_publish("score", [score_card.current_score, score_card.last_guess])

@route('/guess_tiles')
def guess_tiles_route():
    if not running:
        return str(0)
    word_tile_ids = request.query.get('tiles')
    guess = ""
    for word_tile_id in word_tile_ids:
        for rack_tile in player_rack._tiles:
            if rack_tile.id == word_tile_id:
                guess += rack_tile.letter
                break
    print(f"guess: {guess}")
    score = guess_word(guess)
    logger.info(f"guess_tiles_route: {score}")
    return str(score)

def guess_word(guess):
    score = score_card.guess_word(guess)

    mqtt_previous_guesses()
    mqtt_update_score()
    mqtt_update_rack()
    # print(f"guess_word: {score}")
    return score

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

def connect_mqtt():
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            raise Exception(f"Can't connect to MQTT broker {rc}")

    def on_disconnect(client, userdata, rc):
        logging.info("Disconnected with result code: %s", rc)
        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            logging.info("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                logging.info("Reconnected successfully!")
                return
            except Exception as err:
                logging.error("%s. Reconnect failed. Retrying...", err)

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1
        logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

    client = mqtt_client.Client(client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_CLIENT_PORT)
    return client

def handle_mqtt_message(client, userdata, message):
    payload = json.loads(message.payload) if message.payload else None
    logging.info(f"app.py handle message: {message} {payload}")
    if message.topic == "pygame/accept_new_letter":
        accept_new_letter(*payload)
    if message.topic == "pygame/guess_word":
        guess_word(payload)
    elif message.topic == "pygame/start":
        start()
    elif message.topic == "pygame/stop":
        stop()

def init():
    global dictionary, player_rack, score_card, game_mqtt_client
    # For Equinox Word Games Radio theme:
    # equinox_filter = lambda w: "K" in w or "W" in w
    dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open=my_open)
    dictionary.read(f"{BUNDLE_TEMP_DIR}/sowpods.txt")
    index()
    game_mqtt_client = connect_mqtt()
    print(f"mqtt client {game_mqtt_client}")
    game_mqtt_client.subscribe("pygame/#")
    game_mqtt_client.on_message = handle_mqtt_message
    game_mqtt_client.loop_start()


if __name__ == '__main__':
    # logger.setLevel(logging.DEBUG)

    init()
    if len(sys.argv) > 1:
        random.seed(0)
    run(host='0.0.0.0', port=8080, server='gevent', debug=True, quiet=True)
