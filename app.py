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

my_open = open

MAX_LETTERS = 6
dictionary = None
previous_guesses = set()
score = 0
tiles = None
guessed_words_updated = event.Event()

SCRABBLE_LETTER_FREQUENCIES = Counter({
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2, 'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2,
    'N': 6, 'O': 8, 'P': 2, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1, 'Y': 2, 'Z': 1
})
BAG_SIZE = sum(SCRABBLE_LETTER_FREQUENCIES.values())
SCRABBLE_LETTER_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3,
    'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

BUNDLE_TEMP_DIR = "."

if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    BUNDLE_TEMP_DIR = sys._MEIPASS
    bottle.TEMPLATE_PATH.insert(0, BUNDLE_TEMP_DIR)
    print(f"tempdir: {BUNDLE_TEMP_DIR}")

class Tiles:
    def __init__(self, letters):
        self._letters = letters
        self._last_guess = ""
        self._unused_letters = letters
        self._used_counter = Counter(set(self._letters))

    def last_guess(self):
        return self._last_guess

    def unused_letters(self):
        return self._unused_letters

    def display(self):
        return f"{self._last_guess} {self._unused_letters}"

    def guess(self, guess):
        self._last_guess = guess
        self._unused_letters = remove_letters(self._letters, guess)
        self._used_counter.update(guess)
        print(f"guess({guess}): Counter: {self._used_counter}")

    def missing_letters(self, word):
        rack_hash = Counter(self._letters)
        word_hash = Counter(word)
        if all(word_hash[letter] <= rack_hash[letter] for letter in word):
            return ""
        else:
            return "".join([l for l in word_hash if word_hash[l] > rack_hash[l]])

    def letters(self):
        return self._letters

    def next_letter(self):
        c = Counter(self._letters)
        for k in c.keys():
            c[k] *= int(BAG_SIZE / MAX_LETTERS)
        frequencies = Counter(SCRABBLE_LETTER_FREQUENCIES) # make a copy
        frequencies.subtract(c)

        bag = [letter for letter, frequency in frequencies.items() for _ in range(frequency)]
        return random.choice(bag)

    def replace_letter(self, new_letter):
        # new_letter_html = f"<span style='blue'><bold>{new_letter}</bold></span>"
        print(f"replace_letter() new_letter: {new_letter}, last_guess: {self._last_guess}, unused: {self._unused_letters}, used_counter: {self._used_counter}")
        if self._unused_letters:
            lowest_count = self._used_counter.most_common()[-1][1]
            # Counter ordering is non-deterministic; sort so that tests will be consistent.
            least_used_letters = sorted([c[0] for c in self._used_counter if self._used_counter[c] == lowest_count])
            remove_letter = random.choice(least_used_letters)
            print(f"removing: {remove_letter} from {least_used_letters}")
            if remove_letter in self._unused_letters:
                remove_ix = self._unused_letters.index(remove_letter)
                self._unused_letters = "".join(self._unused_letters[:remove_ix] + new_letter +
                    self._unused_letters[remove_ix+1:])
            else:
                remove_ix = self._last_guess.index(remove_letter)
                self._last_guess = (self._last_guess[:remove_ix] + self._last_guess[remove_ix+1:])
                self._unused_letters = "".join(self._unused_letters + new_letter)
            print(f"least_used_letters: {least_used_letters}, remove_letter: {remove_letter}, last_guess: {self._last_guess}, unused: {self._unused_letters}")
        else:
            print(f"no unused letters")
            remove_ix = random.randint(0, len(self._last_guess)-1)
            self._last_guess = self._last_guess[:remove_ix] + self._last_guess[remove_ix+1:]
            self._unused_letters = new_letter

        self._letters = self._last_guess + self._unused_letters

        # Initialize so that each letter appears at least once.
        self._used_counter = Counter(set(self._letters))
        print(f"replace_letter() done used: {self._used_counter}, last guess: {self._last_guess}, unused: {self._unused_letters}")
        return self.display()

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
        bingo = random.choice(self._words)
        print(f"initial: {bingo}")
        return Tiles(sort_word(bingo))

    def is_word(self, word):
        return word in self._word_frequencies

def remove_letters(source_string, letters_to_remove):
    for char in letters_to_remove:
        source_string = source_string.replace(char, '', 1)
    return source_string

def sort_word(word):
    return "".join(sorted(word))

def calculate_score(word, bonus):
    return (sum(SCRABBLE_LETTER_SCORES.get(letter, 0) for letter in word)
        * (2 if bonus else 1)
        + (50 if len(word) == MAX_LETTERS else 0))

def get_previous_guesses():
    possible_guessed_words = set([word for word in previous_guesses if not tiles.missing_letters(word)])
    return " ".join(sorted(list(possible_guessed_words)))

def guess_word(guess, bonus):
    global score, tiles
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
    score += current_score
    return {'current_score': current_score,
            'score': score,
            'tiles': (f"<span class='word{' bonus' if bonus else ''}'>" +
                tiles.last_guess() + f"</span> {tiles.unused_letters()}")}

@route('/')
def index():
    global previous_guesses, score, tiles
    previous_guesses = set()
    tiles = dictionary.get_tiles()
    score = 0
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
    return str(score)

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
