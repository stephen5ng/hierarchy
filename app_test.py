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
        self.assertEqual("BFOUXZZ", self.d.get_tiles().tiles())

    def testIsWord(self):
        self.assertTrue(self.d.is_word("FUZZBOX"))
        self.assertFalse(self.d.is_word("FUXBOX"))


class TestCubeGame(unittest.TestCase):

    def setUp(self):
        app.my_open = lambda filename, mode: StringIO("\n".join([
            "5 fuzzbox",
            "8 pizzazz",
        ]))
        random.seed(1)
        app.init()
        app.index()

    def test_get_tiles(self):
        bottle.request.query['next_tile'] = "M"
        self.assertEqual("BFMOUXZ", app.get_tiles())

    def test_guess(self):
        bottle.request.query['guess'] = "fuzzbox"
        self.assertEqual({
            "status": "guess: FUZZBOX",
            "score": 37,
            "current_score": 37}, app.guess_word())

    def test_dupe_word(self):
        bottle.request.query['guess'] = "fuzzbox"
        app.guess_word()
        self.assertEqual({
            "status": "already played FUZZBOX",
            "current_score": 0}, app.guess_word())

    def test_not_a_word(self):
        bottle.request.query['guess'] = "ffz"
        self.assertEqual({
            "status": "FFZ is not a word",
            "current_score": 0}, app.guess_word())

    def test_cant_make_word(self):
        bottle.request.query['guess'] = "pizzazz"
        self.assertEqual(
            { "status": "can't make PIZZAZZ from BFOUXZZ",
            "current_score": 0}, app.guess_word())

    def test_score(self):
        self.assertEqual(4, app.calculate_score("TAIL"))
        self.assertEqual(12, app.calculate_score("QAT"))

    def test_index(self):
        template = app.index()

        self.assertIn("BFOUXZZ", template)

    def test_next_tile(self):
        self.assertEqual("Z", app.next_tile())

    def test_sort(self):
        self.assertEqual("abc", app.sort_word("cab"))



if __name__ == '__main__':
    unittest.main()