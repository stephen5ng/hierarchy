#!/usr/bin/env python3

from io import StringIO
import random
import unittest

import dictionary

class TestDictionary(unittest.TestCase):
    mock_open = lambda filename, mode: StringIO("\n".join([
        "fuzzbox",
        "pizzazz",
    ]))

    def setUp(self):
        random.seed(1)
        self.d = dictionary.Dictionary(3, 7, open = TestDictionary.mock_open)
        self.d.read("mock_file")

    def testGetRack(self):
        self.assertEqual("BFOUXZZ", self.d.get_rack().letters())

    def testIsWord(self):
        self.assertTrue(self.d.is_word("FUZZBOX"))
        self.assertFalse(self.d.is_word("FUXBOX"))


if __name__ == '__main__':
    unittest.main()