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

class TestCubeGame(unittest.TestCase):
    def setUp(self):
        tiles.MAX_LETTERS = 7
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