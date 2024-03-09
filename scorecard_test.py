#!/usr/bin/env python3

import unittest
from io import StringIO

from dictionary import Dictionary
import random
from scorecard import ScoreCard
import tiles

class TestScoreCard(unittest.TestCase):
    def setUp(self):
        my_open = lambda filename, mode: StringIO("\n".join([
            "fuzz",
            "fuzzbox",
            "pizzazz",
        ]))
        random.seed(1)
        dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open = my_open)
        dictionary.read("fake_dictionary")
        player_rack = dictionary.get_rack()
        self.score_card = ScoreCard(player_rack, dictionary)

    def test_guess(self):
        self.score_card.guess_word("FUZZ", False)
        self.assertEqual("<span class='word'>FUZZ</span> BOX",
            self.score_card.get_rack_html())
        self.assertEqual(25, self.score_card.current_score)
        self.assertEqual(25, self.score_card.total_score)

    def test_guess_bingo(self):
        self.score_card.guess_word("FUZZBOX", False)
        self.assertEqual("<span class='word'>FUZZBOX</span> ",
            self.score_card.get_rack_html())
        self.assertEqual(87, self.score_card.current_score)
        self.assertEqual(87, self.score_card.total_score)

    def test_dupe_word(self):
        self.score_card.guess_word("FUZZBOX", False)
        self.score_card.guess_word("FUZZBOX", False)

        self.assertEqual(0, self.score_card.current_score)
        self.assertEqual(87, self.score_card.total_score)
        self.assertEqual("<span class='already-played'>FUZZBOX</span> </span>",
            self.score_card.get_rack_html())

    def test_cant_make_word(self):
        self.score_card.guess_word("PIZZAZZ", False)

        self.assertEqual(0, self.score_card.current_score)
        self.assertEqual(" BFOUXZZ <span class='missing'>PIZA</span>",
            self.score_card.get_rack_html())

    def test_score(self):
        self.assertEqual(4, self.score_card.calculate_score("TAIL", False))
        self.assertEqual(12, self.score_card.calculate_score("QAT", False))
        self.assertEqual(24, self.score_card.calculate_score("QAT", True))
        self.assertEqual(61, self.score_card.calculate_score("FRIENDS", False))

    def test_update_previous_guesses(self):
        self.score_card.previous_guesses = set(["CAT", "DOG"])
        self.score_card.player_rack = tiles.Rack("ABCDEFT")
        self.score_card.update_previous_guesses()
        self.assertEqual(set(["CAT"]), self.score_card.possible_guessed_words)

    def test_get_previous_guesses(self):
        self.score_card.possible_guessed_words = set(["CAT", "DOG"])
        self.assertEqual("CAT DOG", self.score_card.get_previous_guesses())

if __name__ == '__main__':
    unittest.main()
