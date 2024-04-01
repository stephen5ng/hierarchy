#!/usr/bin/env python3

import bottle
from io import StringIO
import random
import unittest

import app
import dictionary
import tiles

def bapi(method, args):
    bottle.request.query.update(args)
    return method()

class TestCubeGame(unittest.TestCase):
    def setUp(self):
        tiles.MAX_LETTERS = 7
        app.my_open = lambda filename, mode: StringIO("\n".join([
            "fuzz",
            "fuzzbox",
            "pizzazz",
        ]))
        random.seed(1)
        app.init()
        app.index()
        app.start()

    def test_accept_new_letter(self):
        bapi(app.accept_new_letter, {'next_letter': "M", "position": 0})
        self.assertEqual(" MFOUXZZ", app.player_rack.display())

    def test_accept_new_letter_bingo(self):
        bapi(app.guess_tiles_route, {"tiles": "1356024"})
        bapi(app.accept_new_letter, {"next_letter" : "M", "position": 0})
        self.assertEqual("FUZZMOX ", app.player_rack.display())

    def test_next_tile(self):
        print("next_tile...")
        self.assertEqual("T", app.next_tile())
        print("next_tile done")

    def test_sort(self):
        self.assertEqual("abc", dictionary._sort_word("cab"))

if __name__ == '__main__':
    unittest.main()