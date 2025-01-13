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
        tiles.MAX_LETTERS = 7
        random.seed(1)
        dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open = my_open)
        dictionary.read("fake_dictionary")
        player_rack = dictionary.get_rack()
        self.score_card = ScoreCard(player_rack, dictionary)
        self.score_card.start()

    def test_guess(self):
        self.score_card.guess_word("FUZZ")
        self.assertEqual(4, self.score_card.current_score)
        self.assertEqual(4, self.score_card.total_score)

    def test_guess_bingo(self):
        self.score_card.guess_word("FUZZBOX")
        self.assertEqual(17, self.score_card.current_score)
        self.assertEqual(17, self.score_card.total_score)

    def test_score(self):
        self.assertEqual(4, self.score_card.calculate_score("TAIL"))
        self.assertEqual(3, self.score_card.calculate_score("QAT"))
        self.assertEqual(17, self.score_card.calculate_score("FRIENDS"))

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
