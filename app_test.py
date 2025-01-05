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

class Client:
    def subscribe(self, topic):
        pass
    def loop_start(self):
        pass
    def publish(self, topic, payload):
        return 0, None

def stub_connect():
    return Client()

class TestCubeGame(unittest.TestCase):
    def setUp(self):
        tiles.MAX_LETTERS = 7
        app.my_open = lambda filename, mode: StringIO("\n".join([
            "fuzz",
            "fuzzbox",
            "pizzazz",
        ]))
        app.connect_mqtt = stub_connect
        random.seed(1)
        app.init()
        app.index()
        app.start()

    def test_accept_new_letter(self):
        app.accept_new_letter("M", 0)
        self.assertEqual(" MFOUXZZ", app.player_rack.display())

    def test_accept_new_letter_bingo(self):
        bapi(app.guess_tiles_route, {"tiles": "1356024"})
        app.accept_new_letter("M", 0)
        self.assertEqual("FUZZMOX ", app.player_rack.display())

    def test_sort(self):
        self.assertEqual("abc", dictionary._sort_word("cab"))

if __name__ == '__main__':
    unittest.main()