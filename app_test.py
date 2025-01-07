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

published = []
class Client:
    def subscribe(self, topic):
        pass
    def loop_start(self):
        pass
    def publish(self, topic, payload):
        published.append((topic, payload))
        return 0, None

def stub_connect():
    return Client()

class TestCubeGame(unittest.TestCase):
    def setUp(self):
        global published
        tiles.MAX_LETTERS = 7
        app.my_open = lambda filename, mode: StringIO("\n".join([
            "fuzz",
            "fuzzbox",
            "pizzazz",
        ]))
        published = []
        app.connect_mqtt = stub_connect
        random.seed(1)
        app.init()
        app.index()
        app.start()

    def test_accept_new_letter(self):
        app.accept_new_letter("M", 0)
        self.assertEqual(" MFOUXZZ", app.player_rack.display())

    def test_accept_new_letter_bingo(self):
        app.guess_tiles("1356024")
        app.accept_new_letter("M", 0)
        self.assertEqual("FUZZMOX ", app.player_rack.display())

    def test_sort(self):
        self.assertEqual("abc", dictionary._sort_word("cab"))

    def test_guess_tiles(self):
        app.guess_tiles("1356024")
        self.assertEqual(('app/score', '[17, "FUZZBOX"]'), published[-3])
        print(f"published {published}")
        self.assertEqual(('app/good_word', '"1356024"'), published[-1])

    def test_guess_tiles_not_word(self):
        app.guess_tiles("135602")
        # self.assertEqual(('app/score', '[0, "FUZZBO"]'), published[-2])
        self.assertNotEqual('app/good_word', published[-1][0])

if __name__ == '__main__':
    unittest.main()
