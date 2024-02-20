#!/usr/bin/env python3

from gevent import monkey; monkey.patch_all()  # Enable asynchronous behavior
from gevent import event
from bottle import request, response, route, run, static_file, template
import bottle
from collections import Counter
import json
import serial
import sys
import time
import gevent

from dictionary import Dictionary
import tiles

my_open = open

dictionary = None
score_cord = None
player_rack = None
guessed_words_updated = event.Event()
total_score_updated = event.Event()

SCRABBLE_LETTER_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3,
    'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

BUNDLE_TEMP_DIR = "."

if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    BUNDLE_TEMP_DIR = sys._MEIPASS
    bottle.TEMPLATE_PATH.insert(0, BUNDLE_TEMP_DIR)
    print(f"tempdir: {BUNDLE_TEMP_DIR}")

class ScoreCard:
    def __init__(self):
        self.total_score = 0
        self.current_score = 0
        self.possible_guessed_words = set()
        self.previous_guesses = set()

    def calculate_score(self, word, bonus):
        return (sum(SCRABBLE_LETTER_SCORES.get(letter, 0) for letter in word)
            * (2 if bonus else 1)
            + (50 if len(word) == tiles.MAX_LETTERS else 0))

    def guess_word(self, guess, bonus):
        global player_rack
        print(f"guessing {guess}, {bonus}")

        response = {}
        missing_letters = player_rack.missing_letters(guess)
        if missing_letters:
            print(f"fail: {guess} from {player_rack.letters()}")
            return { 'current_score': 0,
                     'tiles': f"{player_rack.display()} <span class='missing'>{missing_letters}</span>"
                    }

        player_rack.guess(guess)
        if not dictionary.is_word(guess):
            return { 'current_score': 0,
                     'tiles': f"<span class='not-word'>{player_rack.last_guess()}</span> {player_rack.unused_letters()}</span>"
                   }

        if guess in self.previous_guesses:
            return { 'current_score': 0,
                     'tiles': f"<span class='already-played'>{player_rack.last_guess()}</span> {player_rack.unused_letters()}</span>"
                    }

        self.previous_guesses.add(guess)
        self.possible_guessed_words.add(guess)
        print(f"guess_word: previous_guesses: {self.previous_guesses}")

        self.current_score = self.calculate_score(guess, bonus)
        self.total_score += self.current_score
        return {'current_score': self.current_score,
                'score': self.total_score,
                'tiles': (f"<span class='word{' bonus' if bonus else ''}'>" +
                    player_rack.last_guess() + f"</span> {player_rack.unused_letters()}")}

    def update_previous_guesses(self):
        self.possible_guessed_words = set([word for word in self.previous_guesses if not player_rack.missing_letters(word)])

    def get_previous_guesses(self):
        return " ".join(sorted(list(self.possible_guessed_words)))

@route('/')
def index():
    global player_rack
    player_rack = dictionary.get_rack()
    print("calling index...")
    return template('index', tiles=player_rack.letters(), next_tile=next_tile())

@route('/previous_guesses')
def previous_guesses():
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    while True:
        print(f"previous_guesses yielding")
        yield f"data: {score_card.get_previous_guesses()}\n\n"
        print(f"previous_guesses yielding done")
        guessed_words_updated.wait()
        guessed_words_updated.clear()

@route('/get_current_rack')
def get_current_rack():
    return json.dumps(player_rack.get_tiles_with_letters())

@route('/get_rack')
def get_rack():
    next_letter = request.query.get('next_letter')
    if len(next_letter) != 1:
        print(f"****************")

    print(f"get_rack {next_letter}")
    new_rack = player_rack.replace_letter(next_letter)
    score_card.update_previous_guesses()
    guessed_words_updated.set()
    return new_rack

@route('/get_current_score')
def get_current_score():
    return str(score_card.current_score)

@route('/total_score')
def get_total_score():
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    while True:
        total_score_updated.wait()
        total_score_updated.clear()
        yield f"data: {total_score}\n\n"

    return str(total_score)

@route('/guess_word')
def guess_word_route():
    guess = request.query.get('guess').upper()
    bonus = request.query.get('bonus') == "true"
    r = score_card.guess_word(guess, bonus)
    guessed_words_updated.set()
    return r


@route('/next_tile')
def next_tile():
    # TODO: Don't create a rack that has no possible words.
    l = player_rack.next_letter()
    print(f"next_tile: {l}")
    return l

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root=BUNDLE_TEMP_DIR)

def init():
    global dictionary, player_rack, score_card
    dictionary = Dictionary(tiles.MAX_LETTERS, open = my_open)
    score_card = ScoreCard()
    dictionary.read(f"{BUNDLE_TEMP_DIR}/words.txt")

if __name__ == '__main__':
    init()
    run(host='0.0.0.0', port=8080, server='gevent', debug=True)
