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

    def test_accept_new_letter(self):
        bapi(app.accept_new_letter, {'next_letter': "M"})
        self.assertEqual(" MFOUXZZ", app.player_rack.display())

    def test_accept_new_letter_bingo(self):
        bapi(app.guess_word_route, {"guess": "fuzzbox"})
        bapi(app.accept_new_letter, {"next_letter" : "M"})
        self.assertEqual("FUZZOX M", app.player_rack.display())

    def test_index(self):
        template = bapi(app.index, {"guess": "fuzzbox"})

        self.assertIn("BFOUXZZ", template)
        self.assertEquals(0, app.score_card.current_score)
        self.assertEquals(0, app.score_card.total_score)

    def test_next_tile(self):
        print("next_tile...")
        self.assertEqual("E", app.next_tile())
        print("next_tile done")

    def test_sort(self):
        self.assertEqual("abc", dictionary._sort_word("cab"))

if __name__ == '__main__':
    unittest.main()