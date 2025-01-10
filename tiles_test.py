#!/usr/bin/env python3

import random
import unittest

import tiles

class TestRack(unittest.TestCase):
    def setUp(self):
        tiles.MAX_LETTERS = 7
        random.seed(1)

    def test_replace_letter(self):
        t = tiles.Rack("FRIENDS")
        self.assertEqual(" FRIZNDS", t.replace_letter("Z", 3).display())

    def testRemoveLetters(self):
        self.assertEqual("TTER", tiles.remove_letters("LETTER", "LE"))


if __name__ == '__main__':
    unittest.main()