from bottle import request, route, run, static_file, template
from collections import Counter
import random

my_open = open

MAX_LETTERS = 7
dictionary = None
tiles = None

scrabble_letter_frequencies = {
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2, 'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2,
    'N': 6, 'O': 8, 'P': 2, 'Q': 1, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1, 'Y': 2, 'Z': 1
}
letters = [letter for letter, frequency in scrabble_letter_frequencies.items() for _ in range(frequency)]

class Tiles:
    def __init__(self, tiles):
        self._tiles = tiles

    def tiles(self):
        return self._tiles

    def is_word(self, word):
        tiles_hash = Counter(self._tiles)
        word_hash = Counter(word)
        return all(word_hash[letter] <= tiles_hash[letter] for letter in word)


class Dictionary:

    def __init__(self, open=open):
        self._open = open
        self._words = []
        self._word_frequencies = {}

    def read(self, filename):
        with self._open(filename, "r") as f:
            for line in f:
                line = line.strip()
                count, word = line.split(" ")
                word = word.upper()
                self._word_frequencies[word] = int(count)
                if len(word) != MAX_LETTERS:
                    continue
                self._words.append(word)

    def get_tiles(self):
        return Tiles(sort_word(random.choice(self._words)))

    def is_word(self, word):
        return word in self._word_frequencies

def sort_word(word):
    return "".join(sorted(word))

@route('/')
def index():
    global tiles
    return template('index', tiles=tiles.tiles(), next_tile=next_tile())

@route('/get_tiles')
def get_tiles():
    global tiles
    next_tile = request.query.get('next_tile')

    old_letters = tiles.tiles()
    remove_tile = random.randint(0, MAX_LETTERS-1)

    new_letters = old_letters[:remove_tile] + old_letters[remove_tile+1:] + next_tile
    new_letters = sort_word(new_letters)
    tiles = Tiles(new_letters)
    return new_letters

@route('/guess_word')
def guess_word():
    global tiles
    guess = request.query.get('guess').upper()
    if not dictionary.is_word(guess):
        return(f"{guess} is not a word")

    if not tiles.is_word(guess):
        return f"can't make {guess} from {tiles.tiles()}"
    return(f"guess: {guess}")

@route('/next_tile')
def next_tile():
    next_tile = random.choice(letters)
    return next_tile

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='.')

def init():
    global dictionary, tiles
    dictionary = Dictionary(open = my_open)
    dictionary.read("../sowpods.count.withzeros.sevenless.txt")
    tiles = dictionary.get_tiles()

if __name__ == '__main__':
    init()
    run(host='localhost', port=8080)
