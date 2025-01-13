#!/usr/bin/env python3

import random
import unittest

import tiles

class TestRack(unittest.TestCase):
    def setUp(self):
        tiles.MAX_LETTERS = 7
        random.seed(1)

    def test_replace_letter(self):
        rack = tiles.Rack("FRIENDS")
        self.assertEqual(" FRIZNDS", rack.replace_letter("Z", 3).display())

    def test_letters_to_ids(self):
        rack = tiles.Rack("FRIENDS")
        self.assertEqual(['3', '4', '5'], rack.letters_to_ids("END"))
        self.assertEqual(['3', '4', '5'], rack.letters_to_ids("EEND"))
        self.assertEqual(['3', '4', '5'], rack.letters_to_ids("ENZD"))

    def test_ids_to_letters(self):
        rack = tiles.Rack("FRIENDS")
        self.assertEqual('END', rack.ids_to_letters("345"))

if __name__ == '__main__':
    unittest.main()