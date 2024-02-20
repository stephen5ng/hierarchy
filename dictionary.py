import random

import tiles
from tiles import Rack

def _sort_word(word):
    return "".join(sorted(word))

class Dictionary:
    def __init__(self, max_letters, open=open):
        self._open = open
        self._words = []
        self._word_frequencies = {}
        self._max_letters = max_letters

    def read(self, filename):
        with self._open(filename, "r") as f:
            for line in f:
                line = line.strip()
                count, word = line.split(" ")
                word = word.upper()
                self._word_frequencies[word] = int(count)
                if len(word) != self._max_letters:
                    continue
                self._words.append(word)

    def get_rack(self):
        bingo = random.choice(self._words)
        print(f"initial bingo: {bingo}")
        return Rack(_sort_word(bingo))

    def is_word(self, word):
        return word in self._word_frequencies
