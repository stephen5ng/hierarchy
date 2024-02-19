#!/usr/bin/env python3

from gevent import monkey; monkey.patch_all()  # Enable asynchronous behavior
from gevent import event
from bottle import request, response, route, run, static_file, template
import bottle
from collections import Counter
import random
import serial
import sys
import time
import gevent

from tiles import Tiles
import tiles as tiles_mod

my_open = open

dictionary = None
previous_guesses = set()
total_score = 0
tiles = None
guessed_words_updated = event.Event()

SCRABBLE_LETTER_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3,
    'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

BUNDLE_TEMP_DIR = "."

if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    BUNDLE_TEMP_DIR = sys._MEIPASS
    bottle.TEMPLATE_PATH.insert(0, BUNDLE_TEMP_DIR)
    print(f"tempdir: {BUNDLE_TEMP_DIR}")

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
                if len(word) != tiles_mod.MAX_LETTERS:
                    continue
                self._words.append(word)

    def get_tiles(self):
        print(f"words: {self._words}")
        bingo = random.choice(self._words)
        print(f"initial: {bingo}")
        return Tiles(sort_word(bingo))

    def is_word(self, word):
        return word in self._word_frequencies

def sort_word(word):
    return "".join(sorted(word))

def calculate_score(word, bonus):
    return (sum(SCRABBLE_LETTER_SCORES.get(letter, 0) for letter in word)
        * (2 if bonus else 1)
        + (50 if len(word) == tiles_mod.MAX_LETTERS else 0))

def get_previous_guesses():
    possible_guessed_words = set([word for word in previous_guesses if not tiles.missing_letters(word)])
    return " ".join(sorted(list(possible_guessed_words)))

def guess_word(guess, bonus):
    global total_score, tiles
    response = {}

    missing_letters = tiles.missing_letters(guess)
    if missing_letters:
        print(f"fail: {guess} from {tiles.letters()}")
        return { 'current_score': 0,
                 'tiles': f"{tiles.display()} <span class='missing'>{missing_letters}</span>"
                }

    tiles.guess(guess)
    if not dictionary.is_word(guess):
        return { 'current_score': 0,
                 'tiles': f"<span class='not-word'>{tiles.last_guess()}</span> {tiles.unused_letters()}</span>"
               }

    if guess in previous_guesses:
        return { 'current_score': 0,
                 'tiles': f"<span class='already-played'>{tiles.last_guess()}</span> {tiles.unused_letters()}</span>"
                }

    previous_guesses.add(guess)
    guessed_words_updated.set()
    current_score = calculate_score(guess, bonus)
    total_score += current_score
    return {'current_score': current_score,
            'score': total_score,
            'tiles': (f"<span class='word{' bonus' if bonus else ''}'>" +
                tiles.last_guess() + f"</span> {tiles.unused_letters()}")}

@route('/')
def index():
    global previous_guesses, total_score, tiles
    previous_guesses = set()
    tiles = dictionary.get_tiles()
    total_score = 0
    return template('index', tiles=tiles.letters(), next_tile=next_tile())

@route('/previous-guesses')
def previous_guesses():
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    while True:
        guessed_words_updated.wait()
        guessed_words_updated.clear()
        yield f"data: {get_previous_guesses()}\n\n"

@route('/get_rack')
def get_rack():
    next_letter = request.query.get('next_letter')
    if len(next_letter) != 1:
        print(f"****************")

    print(f"get_rack {next_letter}")
    return tiles.replace_letter(next_letter)

@route('/get_score')
def get_score():
    return str(total_score)

@route('/guess_word')
def guess_word_route():
    guess = request.query.get('guess').upper()
    bonus = request.query.get('bonus') == "true"
    return guess_word(guess, bonus)

@route('/next_tile')
def next_tile():
    # TODO: Don't create a rack that has no possible words.
    l = tiles.next_letter()
    print(f"next_tile: {l}")
    return l

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root=BUNDLE_TEMP_DIR)

def init():
    global dictionary
    dictionary = Dictionary(open = my_open)
    dictionary.read(f"{BUNDLE_TEMP_DIR}/words.txt")

if __name__ == '__main__':
    init()
    run(host='0.0.0.0', port=8080, server='gevent', debug=True)
