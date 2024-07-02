from enum import Enum
import logging
import os
import tiles
from pathlib import Path

SCRABBLE_LETTER_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3,
    'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

Play = Enum("PLAY", ["GOOD", "MISSING_LETTERS", "DUPE_WORD", "BAD_WORD"])

class ScoreCard:
    def __init__(self, player_rack, dictionary):
        self.total_score = 0
        self.current_score = 0
        self.possible_guessed_words = set()
        self.previous_guesses = set()
        self.remaining_previous_guesses = set() # After possible have been removed
        self.player_rack = player_rack
        self.dictionary = dictionary
        self.missing_letters = ""
        self.last_play = Play.GOOD
        self.running = False
        self.last_guess = ""

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def calculate_score(self, word):
        if not self.running:
            return 0
        return len(word) + (10 if len(word) == tiles.MAX_LETTERS else 0)
        return (sum(SCRABBLE_LETTER_SCORES.get(letter, 0) for letter in word)
            + (50 if len(word) == tiles.MAX_LETTERS else 0))
        #* (2 if "W" in word or "K" in word else 1)

    def get_rack(self):
        rack = self.player_rack

        if self.last_play == Play.MISSING_LETTERS:
            return {
                "last-play": self.last_play.name,
                "last-guess": rack.last_guess(),
                "unused": rack.unused_letters(),
                "missing": self.missing_letters
            }
        elif self.last_play == Play.BAD_WORD:
            return {
                "last-play": self.last_play.name,
                "not-word": rack.last_guess(),
                "unused": rack.unused_letters()
            }
        elif self.last_play == Play.DUPE_WORD:
            return {
                "last-play": self.last_play.name,
                "already-played": rack.last_guess(),
                "unused": rack.unused_letters()
            }
        return {
                "last-play": self.last_play.name,
                "word": rack.last_guess(),
                "unused": rack.unused_letters()
            }

    def guess_word(self, guess):
        logging.info(f"guessing {guess}")
        self.last_guess = guess
        self.current_score = 0
        response = {}
        self.missing_letters = self.player_rack.missing_letters(guess)
        if self.missing_letters:
            self.last_play = Play.MISSING_LETTERS
            # print(f"fail: {guess} from {self.player_rack.letters()}")
            return 0

        self.player_rack.guess(guess)
        if not self.dictionary.is_word(guess):
            self.last_play = Play.BAD_WORD
            return 0

        if guess in self.previous_guesses:
            self.last_play = Play.DUPE_WORD
            return 0

        self.last_play = Play.GOOD
        self.previous_guesses.add(guess)
        self.possible_guessed_words.add(guess)
        # print(f"guess_word: previous_guesses: {self.previous_guesses}")

        self.current_score = self.calculate_score(guess)
        self.total_score += self.current_score
        # os.system(f"say {guess.lower()} &")
        pygame.mixer.Sound.play(pygame.mixer.Sound(f"word_sounds/{guess.lower()}.wav"))
        logging.info(f"--------------GUESS SAYING {guess}")
        # Path(f"/tmp/sayfiles/{guess.lower()}").touch()
        return self.current_score

    def update_previous_guesses(self):
        self.possible_guessed_words = set([word for word in self.previous_guesses if not self.player_rack.missing_letters(word)])
        self.remaining_previous_guesses = self.previous_guesses - self.possible_guessed_words

    def get_previous_guesses(self):
        return " ".join(sorted(list(self.possible_guessed_words)))

    def get_remaining_previous_guesses(self):
        return " ".join(sorted(list(self.remaining_previous_guesses)))
