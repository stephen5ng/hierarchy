from bottle import request, route, run, static_file, template
import random

my_open = open

MAX_LETTERS = 7
tiles = ""
dictionary = None

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
        return sort_word(random.choice(self._words))

    def is_word(self, word):
        return word in self._word_frequencies


def sort_word(word):
    return "".join(sorted(word))


@route('/guess_word')
def guess_word():
    guess = request.query.get('guess').upper()
    if not dictionary.is_word(guess):
        return(f"{guess} is not a word")
    return(f"guess: {guess}")

@route('/')
def index():
    global dictionary
    tiles = dictionary.get_tiles()
    return template('index', tiles=tiles)

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='.')

def init():
    global dictionary
    dictionary = Dictionary(open = my_open)
    dictionary.read("../sowpods.count.withzeros.sevenless.txt")

if __name__ == '__main__':
    init()
    run(host='localhost', port=8080)
