from io import StringIO
import bottle
import random
import unittest

import app
app.MAX_LETTERS = 7

class TestDictionary(unittest.TestCase):
    mock_open = lambda filename, mode: StringIO("\n".join([
        "1 fuzzbox",
        "1 pizzazz",
    ]))

    def setUp(self):
        random.seed(1)
        self.d = app.Dictionary(open = TestDictionary.mock_open)
        self.d.read("foo")

    def testGetTiles(self):
        self.assertEqual("BFOUXZZ", self.d.get_tiles().letters())

    def testIsWord(self):
        self.assertTrue(self.d.is_word("FUZZBOX"))
        self.assertFalse(self.d.is_word("FUXBOX"))

    def testRemoveLetters(self):
        self.assertEqual("TTER", app.remove_letters("LETTER", "LE"))

class TestTiles(unittest.TestCase):
    def setUp(self):
        app.MAX_LETTERS = 7        
        random.seed(1)

    def test_replace_letter_all_unused(self):
        self.assertEqual(" ZINTANG", app.Tiles("GINTANG").replace_letter("Z"))
        random.seed(5)
        self.assertEqual(" GINZANG", app.Tiles("GINTANG").replace_letter("Z"))

    def test_replace_letter_some_used_least_used_is_in_guess(self):
        t = app.Tiles("FRIENDS")
        t.guess("FIND")
        t.guess("FIND")
        t.guess("ERS")
        self.assertEqual("RS FINDZ", t.replace_letter("Z"))

    def test_replace_letter_some_used(self):
        t = app.Tiles("GINTANG")
        t.guess("GIN")
        self.assertEqual("GIN TZNG", t.replace_letter("Z"))

    def test_replace_letter_all_used(self):
        t = app.Tiles("GINTANG")
        t.guess("GINTANG")
        self.assertEqual("GNTANG Z", t.replace_letter("Z"))
        random.seed(2)
        t = app.Tiles("GINTANG")
        t.guess("GINTANG")
        self.assertEqual("GINTAN Z", t.replace_letter("Z"))

class TestCubeGame(unittest.TestCase):

    def setUp(self):
        app.my_open = lambda filename, mode: StringIO("\n".join([
            "1 fuzz",
            "1 fuzzbox",
            "1 pizzazz",
        ]))
        random.seed(1)
        app.init()
        app.index()

    def test_get_rack(self):
        bottle.request.query['next_letter'] = "M"
        self.assertEqual(" MFOUXZZ", app.get_rack())

    def test_get_rack_bingo(self):
        bottle.request.query['guess'] = "fuzzbox"
        app.guess_word()
        bottle.request.query['next_letter'] = "M"
        self.assertEqual("FUZZBO M", app.get_rack())

    def test_guess(self):
        bottle.request.query['guess'] = "fuzz"
        self.assertEqual({
            "score": 25,
            "current_score": 25,
            "tiles": "<span class='word'>FUZZ</span> BOX"
            }, app.guess_word())

    def test_guess_bingo(self):
        bottle.request.query['guess'] = "fuzzbox"
        self.assertEqual({
            "score": 87,
            "current_score": 87,
            'tiles': "<span class='word'>FUZZBOX</span> "}, app.guess_word())

    def test_dupe_word(self):
        bottle.request.query['guess'] = "fuzzbox"
        app.guess_word()
        self.assertEqual({
             "tiles": "<span class='already-played'>FUZZBOX</span> </span>",
             "current_score": 0}, app.guess_word())

    def test_not_a_word(self):
        bottle.request.query['guess'] = "fzz"
        self.assertEqual(
             {'current_score': 0, 'tiles': "<span class='not-word'>FZZ</span> BOUX</span>"},
             app.guess_word())

    def test_cant_make_word(self):
        bottle.request.query['guess'] = "pizzazz"
        self.assertEqual(
            { "tiles": " BFOUXZZ <span class='missing'>PIZA</span>",
              "current_score": 0}, app.guess_word())

    def test_score(self):
        self.assertEqual(4, app.calculate_score("TAIL", False))
        self.assertEqual(12, app.calculate_score("QAT", False))
        self.assertEqual(24, app.calculate_score("QAT", True))
        self.assertEqual(61, app.calculate_score("FRIENDS", False))

    def test_index(self):
        template = app.index()

        self.assertIn("BFOUXZZ", template)

    def test_next_tile(self):
        self.assertEqual("A", app.next_tile())

    def test_sort(self):
        self.assertEqual("abc", app.sort_word("cab"))



if __name__ == '__main__':
    unittest.main()