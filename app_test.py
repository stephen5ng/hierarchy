#!/usr/bin/env python3

import bottle
from io import StringIO
import random
import unittest
from unittest import IsolatedAsyncioTestCase

import app
import dictionary
from pygameasync import events
import cubes_to_game
import tiles

def bapi(method, args):
    bottle.request.query.update(args)
    return method()

published = []
class Client:
    def subscribe(self, topic):
        pass
    def loop_start(self):
        pass
    async def publish(self, topic, *payload):
        published.append((topic, payload))
        return 0, None

def stub_connect():
    return Client()

class TestCubeGame(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        print('setup')
        async def nop(*a):
            pass
        global published
        tiles.MAX_LETTERS = 7
        app.my_open = lambda filename, mode: StringIO("\n".join([
            "fuzz",
            "fuzzbox",
            "pizzazz",
        ]))
        cubes_to_game.TAGS_TO_CUBES = {
            "TAG_0": "BLOCK_0",
            "TAG_1": "BLOCK_1",
            "TAG_2": "BLOCK_2",
            "TAG_3": "BLOCK_3",
            "TAG_4": "BLOCK_4",
            "TAG_5": "BLOCK_5",
            "TAG_6": "BLOCK_6",
        }
        print("setup 1")
        published = []
        self.client = Client()
        app.connect_mqtt = stub_connect
        random.seed(1)
        events.on(f"game.next_tile")(nop)
        events.on("rack.change_rack")(nop)
        events.on("input.remaining_previous_guesses")(nop)
        events.on("input.previous_guesses")(nop)
        events.on("game.current_score")(nop)
        app.init()
        app.index()
        print("setup 3")
        cubes_to_game.initialize_arrays()
        await app.start(self.client)
        print("setup 4")
        print("done setup")

    async def test_accept_new_letter(self):
        print(f"initial rack: {app.player_rack.display()}")
        await app.accept_new_letter(self.client, "M", 0)
        self.assertEqual(" MFOUXZZ", app.player_rack.display())

    async def test_accept_new_letter_bingo(self):
        await app.guess_tiles(self.client, "1356024")
        await app.accept_new_letter(self.client, "M", 0)
        self.assertEqual("FUZZMOX ", app.player_rack.display())

    def test_sort(self):
        self.assertEqual("abc", dictionary._sort_word("cab"))

    async def test_guess_tiles(self):
        await app.guess_tiles(self.client, "1356")
        self.assertIn(('cube/BLOCK_1/flash', ()), published)
        self.assertIn(('cube/BLOCK_3/flash', ()), published)
        self.assertIn(('cube/BLOCK_5/flash', ()), published)
        self.assertIn(('cube/BLOCK_6/flash', ()), published)

    async def test_guess_tiles_not_word(self):
        await app.guess_tiles(self.client, "135602")
        self.assertNotIn(('cube/BLOCK_1/flash', ()), published)

if __name__ == '__main__':
    unittest.main()
