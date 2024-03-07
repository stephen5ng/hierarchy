import random

import tiles
from tiles import Rack

def _sort_word(word):
    return "".join(sorted(word))

class Dictionary:
    def __init__(self, min_letters, max_letters, open=open):
        self._open = open
        self._bingos = []
        self._all_words = {}
        self._min_letters = min_letters
        self._max_letters = max_letters

    def read(self, filename):
        with self._open(filename, "r") as f:
            for line in f:
                word = line.strip().upper()
                if len(word) < self._min_letters or len(word) > self._max_letters:
                    continue
                self._all_words[word] = 1
                if len(word) != self._max_letters:
                    continue
                self._bingos.append(word)

    def get_rack(self):
        bingo = random.choice(self._bingos)
        print(f"initial bingo: {bingo}")
        return Rack(_sort_word(bingo))

    def is_word(self, word):
        return word in self._all_words
