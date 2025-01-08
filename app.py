#!/usr/bin/env python3

import aiomqtt
import asyncio
from gevent import monkey; monkey.patch_all()  # Enable asynchronous behavior
from gevent import event
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

async def mqtt_publish(client, topic, *message):
    await client.publish(f"app/{topic}", json.dumps(message))

def index():
    global player_rack, score_card
    player_rack = tiles.Rack('?' * tiles.MAX_LETTERS)
    score_card = ScoreCard(player_rack, dictionary)

async def start(client):
    global player_rack, running, score_card
    player_rack = dictionary.get_rack()
    await mqtt_publish(client, "next_tile", player_rack.next_letter())
    score_card = ScoreCard(player_rack, dictionary)
    await mqtt_tiles(client)
    await mqtt_update_rack(client)
    await mqtt_update_score(client)
    await mqtt_previous_guesses(client)
    await mqtt_remaining_previous_guesses(client)
    score_card.start()
    running = True
    print("starting game...")

async def stop(client):
    global running
    player_rack = tiles.Rack('?' * tiles.MAX_LETTERS)
    score_card.stop()
    running = False

async def mqtt_previous_guesses(client):
    await mqtt_publish(client, "previous_guesses", score_card.get_previous_guesses())

async def mqtt_remaining_previous_guesses(client):
    await mqtt_publish(client, "remaining_previous_guesses", score_card.get_remaining_previous_guesses())

async def mqtt_update_rack(client):
    await mqtt_publish(client, "rack_letters", score_card.player_rack.letters())

async def mqtt_tiles(client):
    await mqtt_publish(client, "tiles", player_rack.get_tiles_with_letters())

async def accept_new_letter(client, next_letter, position):
    changed_tile = player_rack.replace_letter(next_letter, position)
    score_card.update_previous_guesses(client)
    await mqtt_previous_guesses(client)
    await mqtt_remaining_previous_guesses(client)
    await mqtt_update_rack(client)
    await mqtt_publish(client, "next_tile", player_rack.next_letter())

async def mqtt_update_score(client):
    await mqtt_publish(client, "score", score_card.current_score, score_card.last_guess)

async def guess_tiles(client, word_tile_ids):
    if not running:
        return str(0)
    guess = ""
    for word_tile_id in word_tile_ids:
        for rack_tile in player_rack._tiles:
            if rack_tile.id == word_tile_id:
                guess += rack_tile.letter
                break
    score = score_card.guess_word(guess)
    await mqtt_update_score(client)
    if score:
        await mqtt_previous_guesses(client)
        await mqtt_update_rack(client)
        await mqtt_publish(client, "good_word", word_tile_ids)

    logger.info(f"guess_tiles_route: {score}")

async def guess_word_keyboard(client, guess):
    word_tile_ids = ""
    rack_tiles = player_rack._tiles.copy()
    for letter in guess:
        for rack_tile in rack_tiles:
            if rack_tile.letter == letter:
                rack_tiles.remove(rack_tile)
                word_tile_ids += rack_tile.id
                continue
    await guess_tiles(client, word_tile_ids)

HANDLERS = [
    ("pygame/new_letter", accept_new_letter),
    ("pygame/guess_word", guess_word_keyboard),
    ("pygame/start", start),
    ("pygame/stop", stop),
    ("cubes/guess_tiles", guess_tiles)]

async def handle_mqtt_message(client, message):
    try:
        payload = json.loads(message.payload) if message.payload else []
    except json.JSONDecodeError:
        logging.error(f"handle_mqtt_message can't decode {message.topic}: '{message.payload}'")
        return

    for topic, handler in HANDLERS:
        if message.topic.matches(topic):
            await handler(client, *payload)
            return

async def handle_mqtt_messages(client):
    for topic, _ in HANDLERS:
        await client.subscribe(topic)

    async for message in client.messages:
        logging.info(f"trigger_events_from_mqtt incoming message topic: {message.topic} {message.payload}")
        await handle_mqtt_message(client, message)

async def main():
    init()
    async with aiomqtt.Client("localhost") as client:
        await handle_mqtt_messages(client)

def init():
    global dictionary
    dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open=my_open)
    dictionary.read(f"{BUNDLE_TEMP_DIR}/sowpods.txt")
    index()


if __name__ == '__main__':
    asyncio.run(main())
