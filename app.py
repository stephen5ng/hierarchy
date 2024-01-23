from bottle import route, run, template
import random

my_open = open

MAX_LETTERS = 7
words = []
tiles = ""

def read_dictionary(filename):
    words = []
    with my_open(filename, "r") as f:
        for line in f:
            line = line.strip()
            count, word = line.split(" ")
            if len(word) != MAX_LETTERS:
                continue
            words.append(word)
    return words

def sort_word(word):
    return "".join(sorted(word))

def get_tiles():
    return sort_word(random.choice(words))

@route('/')
def index():
    global tiles
    tiles = get_tiles()
    return template('index', tiles=tiles)

def init():
    global words
    words = read_dictionary("../sowpods.count.withzeros.sevenless.txt")

if __name__ == '__main__':
    init()
    run(host='localhost', port=8080)
