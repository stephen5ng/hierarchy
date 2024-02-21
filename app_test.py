import bottle
from io import StringIO
import random
import unittest

import app
import dictionary
import tiles
tiles.MAX_LETTERS = 7

def bapi(method, args):
    bottle.request.query.update(args)
    return method()

class TestRack(unittest.TestCase):
    def setUp(self):
        tiles.MAX_LETTERS = 7
        random.seed(1)

    def test_get_rack(self):
        t = tiles.Rack("FRIENDS")
        self.assertEqual({0: 'F', 1: 'R', 2: 'I', 3: 'E', 4: 'N', 5: 'D', 6: 'S'},
            t.get_tiles_with_letters())

    def test_replace_letter_all_unused(self):
        self.assertEqual(" ZINTANG", tiles.Rack("GINTANG").replace_letter("Z"))
        random.seed(5)
        self.assertEqual(" GIZTANG", tiles.Rack("GINTANG").replace_letter("Z"))

    def test_replace_letter_some_used_least_used_is_in_guess(self):
        t = tiles.Rack("FRIENDS")
        t.guess("FIND")
        t.guess("FIND")
        t.guess("ERS")
        self.assertEqual("RS FINDZ", t.replace_letter("Z"))

    def test_replace_letter_some_used_no_dupe(self):
        t = tiles.Rack("GINTANE")
        t.guess("GIN")
        self.assertEqual("GIN TANZ", t.replace_letter("Z"))

    def test_replace_letter_some_used(self):
        t = tiles.Rack("GINTANG")
        t.guess("GIN")
        self.assertEqual("GIN TANZ", t.replace_letter("Z"))

    def test_replace_letter_all_used(self):
        t = tiles.Rack("GINTANG")
        t.guess("GINTANG")
        self.assertEqual("GNTANG Z", t.replace_letter("Z"))
        random.seed(2)
        t = tiles.Rack("GINTANG")
        t.guess("GINTANG")
        self.assertEqual("GINTAN Z", t.replace_letter("Z"))

    def testRemoveLetters(self):
        self.assertEqual("TTER", tiles.remove_letters("LETTER", "LE"))


class TestScoreCard(unittest.TestCase):
    def setUp(self):
        app.my_open = lambda filename, mode: StringIO("\n".join([
            "1 fuzz",
            "1 fuzzbox",
            "1 pizzazz",
        ]))
        random.seed(1)
        app.init()
        app.index()

    def test_guess(self):
        self.assertEqual({
            "score": 25,
            "current_score": 25,
            "tiles": "<span class='word'>FUZZ</span> BOX"
            }, app.score_card.guess_word("FUZZ", False))
        self.assertEqual(25, app.score_card.current_score)
        self.assertEqual(25, app.score_card.total_score)

    def test_guess_bingo(self):
        self.assertEqual({
            "score": 87,
            "current_score": 87,
            'tiles': "<span class='word'>FUZZBOX</span> "},
            app.score_card.guess_word("FUZZBOX", False))

    def test_dupe_word(self):
        app.score_card.guess_word("FUZZBOX", False)
        self.assertEqual({
             "tiles": "<span class='already-played'>FUZZBOX</span> </span>",
             "current_score": 0},
             app.score_card.guess_word("FUZZBOX", False))

    def test_cant_make_word(self):
        self.assertEqual(
            { "tiles": " BFOUXZZ <span class='missing'>PIZA</span>",
              "current_score": 0},
              app.score_card.guess_word("PIZZAZZ", False))

    def test_score(self):
        self.assertEqual(4, app.score_card.calculate_score("TAIL", False))
        self.assertEqual(12, app.score_card.calculate_score("QAT", False))
        self.assertEqual(24, app.score_card.calculate_score("QAT", True))
        self.assertEqual(61, app.score_card.calculate_score("FRIENDS", False))

    def test_update_previous_guesses(self):
        app.score_card.previous_guesses = set(["CAT", "DOG"])
        app.score_card.player_rack = tiles.Rack("ABCDEFT")
        app.score_card.update_previous_guesses()
        self.assertEqual(set(["CAT"]), app.score_card.possible_guessed_words)

    def test_get_previous_guesses(self):
        app.score_card.possible_guessed_words = set(["CAT", "DOG"])
        self.assertEqual("CAT DOG", app.score_card.get_previous_guesses())


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
        self.assertEqual(" BFOUXZM",
            bapi(app.get_rack, {'next_letter': "M"}))

    def test_get_rack_bingo(self):
        bapi(app.guess_word_route, {"guess": "fuzzbox"})
        self.assertEqual("FUZBOX M",
            bapi(app.get_rack, {"next_letter" : "M"}))

    def test_not_a_word(self):
        self.assertEqual(
             {'current_score': 0, 'tiles': "<span class='not-word'>FZZ</span> BOUX</span>"},
             bapi(app.guess_word_route, {"guess": "fzz"}))

    def test_index(self):
        template = bapi(app.index, {"guess": "fuzzbox"})

        self.assertIn("BFOUXZZ", template)
        self.assertEquals(0, app.score_card.current_score)
        self.assertEquals(0, app.score_card.total_score)

    def test_next_tile(self):
        print("next_tile...")
        self.assertEqual("A", app.next_tile())
        print("next_tile done")

    def test_sort(self):
        self.assertEqual("abc", dictionary._sort_word("cab"))

if __name__ == '__main__':
    unittest.main()