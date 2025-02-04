#!/usr/bin/env python3

import asyncio
from io import StringIO
import random
import unittest
from unittest import IsolatedAsyncioTestCase

import app
import dictionary
from pygameasync import events
import cubes_to_game
import tiles

class TestCubeGame(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async def nop(*a):
            pass

        self.publish_queue = asyncio.Queue()
        my_open = lambda filename, mode: StringIO("\n".join([
            "arch",
            "fuzz",
            "line",
            "search",
            "online" # eilnno
        ])) if filename == "sowpods.txt" else StringIO("\n".join([
            "search", # ACEHRS
            "online"
        ]))
        cubes_to_game.TAGS_TO_CUBES = {
            "TAG_0": "BLOCK_0",
            "TAG_1": "BLOCK_1",
            "TAG_2": "BLOCK_2",
            "TAG_3": "BLOCK_3",
            "TAG_4": "BLOCK_4",
            "TAG_5": "BLOCK_5",
        }
        random.seed(1)
        events.on("game.bad_guess")(nop)
        events.on("game.next_tile")(nop)
        events.on("game.stage_guess")(nop)
        events.on("rack.update_letter")(nop)
        events.on("rack.update_rack")(nop)
        events.on("input.remaining_previous_guesses")(nop)
        events.on("input.update_previous_guesses")(nop)
        a_dictionary = dictionary.Dictionary(3, 6, my_open)
        a_dictionary.read("sowpods.txt", "bingos.txt")
        self.app = app.App(self.publish_queue, a_dictionary)
        cubes_to_game.initialize_arrays()
        await self.app.start()

    async def test_accept_new_letter_bingo(self):
        await self.app.guess_tiles(list("520413"), True)
        await self.app.accept_new_letter("M", 0)
        self.assertEqual("MEARCH", ''.join([t.letter for t in self.app._player_rack._tiles]))

    def test_sort(self):
        self.assertEqual("abc", dictionary._sort_word("cab"))

    async def test_guess_tiles(self):
        await self.app.guess_tiles("0413", True)

        published = list(self.publish_queue._queue)
        self.assertIn(('cube/BLOCK_0/flash', None, True), published)
        self.assertIn(('cube/BLOCK_4/flash', None, True), published)
        self.assertIn(('cube/BLOCK_1/flash', None, True), published)
        self.assertIn(('cube/BLOCK_3/flash', None, True), published)

    async def test_guess_tiles_not_word(self):
        await self.app.guess_tiles("04132", True)
        published = list(self.publish_queue._queue)
        self.assertNotIn(('cube/BLOCK_0/flash', None, True), published)

if __name__ == '__main__':
    unittest.main()
