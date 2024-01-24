from io import StringIO
import bottle
import random
import unittest

import app

class TestDictionary(unittest.TestCase):
    mock_open = lambda filename, mode: StringIO("\n".join([
        "5 fuzzbox",
        "8 pizzazz",
    ]))

    def setUp(self):
        random.seed(1)
        self.d = app.Dictionary(open = TestDictionary.mock_open)
        self.d.read("foo")

    def testGetTiles(self):
        self.assertEqual("BFOUXZZ", self.d.get_tiles())

    def testIsWord(self):
        self.assertTrue(self.d.is_word("FUZZBOX"))
        self.assertFalse(self.d.is_word("FUXBOX"))


class TestCubeGame(unittest.TestCase):
    mock_open = lambda filename, mode: StringIO("\n".join([
        "5 fuzzbox",
        "8 pizzazz",
    ]))

    def setUp(self):
        random.seed(1)
        app.my_open = TestCubeGame.mock_open
        app.init()

    def test_guess(self):
        bottle.request.query['guess'] = "fuzzbox"
        self.assertEqual("guess: FUZZBOX", app.guess_word())

    def test_index(self):
        template = app.index()

        self.assertIn("BFOUXZZ", template)

    def test_sort(self):
        self.assertEqual("abc", app.sort_word("cab"))

if __name__ == '__main__':
    unittest.main()