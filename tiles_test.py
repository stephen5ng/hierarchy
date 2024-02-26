#!/usr/bin/env python3

import random
import unittest

import tiles

class TestRack(unittest.TestCase):
    def setUp(self):
        tiles.MAX_LETTERS = 7
        random.seed(1)

    def test_get_rack(self):
        t = tiles.Rack("FRIENDS")
        self.assertEqual({0: 'F', 1: 'R', 2: 'I', 3: 'E', 4: 'N', 5: 'D', 6: 'S'},
            t.get_tiles_with_letters())

    def test_replace_letter_all_unused(self):
        self.assertEqual(" ZINTANG", tiles.Rack("GINTANG")
            .replace_letter("Z").display())
        random.seed(5)
        self.assertEqual(" GIZTANG", tiles.Rack("GINTANG")
            .replace_letter("Z").display())

    def test_replace_letter_some_used_least_used_is_in_guess(self):
        t = tiles.Rack("FRIENDS")
        t.guess("FIND")
        t.guess("FIND")
        t.guess("ERS")
        self.assertEqual("RS FINDZ", t.replace_letter("Z").display())

    def test_replace_letter_some_used_no_dupe(self):
        t = tiles.Rack("GINTANE")
        t.guess("GIN")
        self.assertEqual("GIN TANZ", t.replace_letter("Z").display())

    def test_replace_letter_some_used(self):
        t = tiles.Rack("GINTANG")
        t.guess("GIN")
        self.assertEqual("GIN TANZ", t.replace_letter("Z").display())

    def test_replace_letter_all_used(self):
        t = tiles.Rack("GINTANG")
        t.guess("GINTANG")
        self.assertEqual("GNTANG Z", t.replace_letter("Z").display())
        random.seed(2)
        t = tiles.Rack("GINTANG")
        t.guess("GINTANG")
        self.assertEqual("GINTAN Z", t.replace_letter("Z").display())

    def testRemoveLetters(self):
        self.assertEqual("TTER", tiles.remove_letters("LETTER", "LE"))


if __name__ == '__main__':
    unittest.main()