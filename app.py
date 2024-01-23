from bottle import route, run, template
import random

MAX_LETTERS = 7

def read_dictionary():
    words = []
    with open("../sowpods.count.withzeros.sevenless.txt", "r") as f:
        for line in f:
            line = line.strip()
            count, word = line.split(" ")
            if len(word) != MAX_LETTERS:
                continue
            words.append(word)
    return words

tiles = ""

@route('/')
def index():
    global tiles
    words = read_dictionary()
    tiles = random.choice(words)
    return template('index', tiles=tiles)

def init():
    pass

if __name__ == '__main__':
    init()
    run(host='localhost', port=8080)
