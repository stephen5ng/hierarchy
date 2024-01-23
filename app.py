from bottle import route, run, template
import random

def read_dictionary():
    words = []
    with open("../sowpods.count.withzeros.sevenless.txt", "r") as f:
        for line in f:
            line = line.strip()
            count, word = line.split(" ")
            words.append(word)
    return words

tiles = ""

@route('/')
def index():
    return template('index', tiles=tiles)

def init():
    global tiles
    words = read_dictionary()
    tiles = random.choice(words)


if __name__ == '__main__':
    init()
    run(host='localhost', port=8080)
