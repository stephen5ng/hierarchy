from collections import Counter
from dataclasses import dataclass
import logging
import random

MIN_LETTERS = 3
MAX_LETTERS = 6

SCRABBLE_LETTER_FREQUENCIES = Counter({
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2, 'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2,
    'N': 6, 'O': 8, 'P': 2, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1, 'Y': 2, 'Z': 1
})

ENGLISH_LETTER_FREQUENCIES = Counter({
    'A': 16, 'B': 4, 'C': 9, 'D': 6, 'E': 22, 'F': 4, 'G': 5, 'H': 6, 'I': 15, 'J': 1, 'K': 2, 'L': 11, 'M': 6,
    'N': 13, 'O': 14, 'P': 6, 'R': 15, 'S': 12, 'T': 14, 'U': 7, 'V': 2, 'W': 2, 'X': 1, 'Y': 4, 'Z': 1
})
FREQUENCIES = ENGLISH_LETTER_FREQUENCIES

BAG_SIZE = sum(FREQUENCIES.values())

def remove_letters(source_string, letters_to_remove):
    for char in letters_to_remove:
        source_string = source_string.replace(char, '', 1)
    return source_string

@dataclass(unsafe_hash=True)
class Tile:
    # Class to track the cubes. Unlike Scrabble, a "tile"'s letter is mutable.

    letter: str
    id: str


def _tiles_to_letters(tiles):
    return ''.join([t.letter for t in tiles])

class Rack:
    def __init__(self, letters: str):
        self._tiles = []
        for count, letter in enumerate(letters):
            self._tiles.append(Tile(letter, str(count)))
        self._last_guess = []
        self._unused_tiles = self._tiles
        self._next_letter = self.gen_next_letter()

    def __repr__(self):
        return (f"TILES: {self._tiles}\n" +
            f"LAST_GUESS: {self._last_guess}\n" +
            f"UNUSED_TILES: {self._unused_tiles}")

    def get_tiles(self):
        return self._tiles

    def last_guess(self):
        return _tiles_to_letters(self._last_guess)

    def unused_letters(self):
        return _tiles_to_letters(self._unused_tiles)

    def display(self):
        return f"{_tiles_to_letters(self._last_guess)} {_tiles_to_letters(self._unused_tiles)}"

    def letters_to_ids(self, letters: str):
        ids = []
        tiles = self._tiles.copy()
        for letter in letters:
            for tile in tiles:
                if tile.letter == letter:
                    tiles.remove(tile)
                    ids += tile.id
                    break
        return ids

    def ids_to_tiles(self, ids: str):
        tiles = []
        for an_id in ids:
            tiles.append(next(t for t in self._tiles if t.id == an_id))
        return tiles

    def ids_to_letters(self, ids: str):
        return ''.join([t.letter for t in self.ids_to_tiles(ids)])

    def guess(self, guess):
        # Assumes all the letters of guess are in the rack.

        guess_letters = list(guess)
        self._last_guess = []
        unused_tiles = list(self._tiles)
        for guess_letter in guess_letters:
            for tile in unused_tiles:
                if guess_letter == tile.letter:
                    self._last_guess.append(tile)
                    unused_tiles.remove(tile)
                    break

        self._unused_letters = remove_letters(_tiles_to_letters(self._tiles), guess)
        self._unused_tiles = unused_tiles
        logging.info(f"guess({guess})")

    def missing_letters(self, word):
        rack_hash = Counter(_tiles_to_letters(self._tiles))
        word_hash = Counter(word)
        if all(word_hash[letter] <= rack_hash[letter] for letter in word):
            return ""
        else:
            return "".join([l for l in word_hash if word_hash[l] > rack_hash[l]])

    def letters(self):
        return ''.join([l.letter for l in self._tiles])

    def next_letter(self):
        return self._next_letter

    def gen_next_letter(self):
        c = Counter(''.join([l.letter for l in self._tiles]))
        for k in c.keys():
            c[k] *= int(BAG_SIZE / MAX_LETTERS)
        frequencies = Counter(FREQUENCIES) # make a copy
        frequencies.subtract(c)

        bag = [letter for letter, frequency in frequencies.items() for _ in range(frequency)]
        return random.choice(bag)

    def replace_letter(self, new_letter, position):
        logging.info(f"\nreplace_letter() {new_letter} -> {str(self)}, new_letter: {new_letter}")
        remove_tile = self._tiles[position]

        remove_tile.letter = new_letter
        self._next_letter = self.gen_next_letter()
        logging.info(f"final: {str(self)}")
        return self
