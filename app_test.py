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