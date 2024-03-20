from enum import Enum
import os
import tiles
from pathlib import Path

SCRABBLE_LETTER_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3,
    'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

Play = Enum("PLAY", ["BONUS", "GOOD", "MISSING_LETTERS", "DUPE_WORD", "BAD_WORD"])

class ScoreCard:
    def __init__(self, player_rack, dictionary):
        self.total_score = 0
        self.current_score = 0
        self.possible_guessed_words = set()
        self.previous_guesses = set()
        self.player_rack = player_rack
        self.dictionary = dictionary
        self.missing_letters = ""
        self.last_play = Play.GOOD

    def calculate_score(self, word, bonus):
        return (sum(SCRABBLE_LETTER_SCORES.get(letter, 0) for letter in word)
            * (2 if bonus else 1)
            + (50 if len(word) == tiles.MAX_LETTERS else 0))

    def get_rack_html(self):
        rack = self.player_rack

        if self.last_play == Play.MISSING_LETTERS:
            return f"{rack.last_guess()} {rack.unused_letters()} <span class='missing'>{self.missing_letters}</span>"
        if self.last_play == Play.BAD_WORD:
            return f"<span class='not-word'>{rack.last_guess()}</span> {rack.unused_letters()}</span>"
        if self.last_play == Play.DUPE_WORD:
            return f"<span class='already-played'>{self.player_rack.last_guess()}</span> {self.player_rack.unused_letters()}</span>"

        return (f"<span class='word{' bonus' if self.last_play == Play.BONUS else ''}'>" +
                    rack.last_guess() + f"</span> {rack.unused_letters()}")

    def guess_word(self, guess, bonus):
        print(f"guessing {guess}, {bonus}")
        self.current_score = 0
        response = {}
        self.missing_letters = self.player_rack.missing_letters(guess)
        if self.missing_letters:
            self.last_play = Play.MISSING_LETTERS
            print(f"fail: {guess} from {self.player_rack.letters()}")
            return

        self.player_rack.guess(guess)
        if not self.dictionary.is_word(guess):
            self.last_play = Play.BAD_WORD
            return

        if guess in self.previous_guesses:
            self.last_play = Play.DUPE_WORD
            return

        self.last_play = Play.BONUS if bonus else Play.GOOD
        self.previous_guesses.add(guess)
        self.possible_guessed_words.add(guess)
        print(f"guess_word: previous_guesses: {self.previous_guesses}")

        self.current_score = self.calculate_score(guess, bonus)
        self.total_score += self.current_score
        print(f"--------------GUESS SAYING {guess}")
        Path(f"/tmp/sayfiles/{guess.lower()}").touch()

    def update_previous_guesses(self):
        self.possible_guessed_words = set([word for word in self.previous_guesses if not self.player_rack.missing_letters(word)])

    def get_previous_guesses(self):
        return " ".join(sorted(list(self.possible_guessed_words)))

