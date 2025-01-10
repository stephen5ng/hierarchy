#!/usr/bin/env python3

import aiomqtt
import asyncio
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

import cubes_to_game
from dictionary import Dictionary
from pygameasync import events
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

class App:
    def __init__(self, client):
        def make_guess_tiles_callback(the_app):
            async def guess_tiles_callback(guess):
                await the_app.guess_tiles(guess)
            return guess_tiles_callback

        self._client = client
        global dictionary, score_card, player_rack
        dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open=my_open)
        dictionary.read(f"{BUNDLE_TEMP_DIR}/sowpods.txt")

        score_card = ScoreCard(player_rack, dictionary)
        self._index()
        cubes_to_game.set_guess_tiles_callback(make_guess_tiles_callback(self))

    def _index(self):
        global player_rack, score_card
        player_rack = tiles.Rack('?' * tiles.MAX_LETTERS)
        score_card = ScoreCard(player_rack, dictionary)

    async def start(self):
        global player_rack, running, score_card
        player_rack = dictionary.get_rack()
        self._update_next_tile(player_rack.next_letter())
        score_card = ScoreCard(player_rack, dictionary)
        await self.load_rack()
        self._update_rack()
        await self._update_score()
        await self._update_previous_guesses()
        await self._update_remaining_previous_guesses()
        score_card.start()
        running = True

    def stop(self):
        global running
        player_rack = tiles.Rack('?' * tiles.MAX_LETTERS)
        score_card.stop()
        running = False

    async def load_rack(self, ):
        await cubes_to_game.load_rack(self._client, player_rack.get_tiles_with_letters())

    async def accept_new_letter(self, next_letter, position):
        changed_tile = player_rack.replace_letter(next_letter, position)
        score_card.update_previous_guesses()
        await cubes_to_game.accept_new_letter(self._client, next_letter, position)

        await self._update_previous_guesses()
        await self._update_remaining_previous_guesses()
        self._update_rack()
        self._update_next_tile(player_rack.next_letter())

    async def guess_tiles(self, word_tile_ids):
        logger.info(f"guess_tiles: {word_tile_ids}")
        if not running:
            logger.info(f"not running, bailing")
            return
        guess = ""
        for word_tile_id in word_tile_ids:
            for rack_tile in player_rack._tiles:
                if rack_tile.id == word_tile_id:
                    guess += rack_tile.letter
                    break
        score = score_card.guess_word(guess)
        await self._update_score()
        if score:
            await self._update_previous_guesses()
            self._update_rack()
            await cubes_to_game.flash_good_words(self._client, word_tile_ids)

        logger.info(f"guess_tiles: {score}")

    async def guess_word_keyboard(self, guess):
        word_tile_ids = ""
        rack_tiles = player_rack._tiles.copy()
        for letter in guess:
            for rack_tile in rack_tiles:
                if rack_tile.letter == letter:
                    rack_tiles.remove(rack_tile)
                    word_tile_ids += rack_tile.id
                    break

        await self.guess_tiles(word_tile_ids)

    def _update_next_tile(self, next_tile):
        events.trigger("game.next_tile", next_tile)

    async def _update_previous_guesses(self):
        events.trigger("input.previous_guesses", score_card.get_previous_guesses())

    async def _update_remaining_previous_guesses(self):
        events.trigger("input.remaining_previous_guesses", score_card.get_remaining_previous_guesses())

    def _update_rack(self):
        events.trigger("rack.change_rack", score_card.player_rack.letters())

    async def _update_score(self):
        events.trigger("game.current_score", score_card.current_score, score_card.last_guess)

