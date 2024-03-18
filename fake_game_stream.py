#!/usr/bin/env python3

# Serve SSE data that looks like rack updates from the game to the frontend (cubes or web).
from gevent import monkey; monkey.patch_all()  # Enable asynchronous behavior

import argparse
from bottle import response, route, run
import json
import random
import time

import tiles

def num_to_letter(i):
    return chr(ord("A") + (i % 26))

tile_number = -1
@route('/next_tile')
def next_tile():
    global tile_number
    tile_number = (tile_number + 1) % 26
    return chr(ord("A") + tile_number)


@route("/get_tiles")
def get_tiles():
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    request_number = 0
    while True:
        time.sleep(sleep_time) # TODO: support random sleep times
        rack = {}
        for id in range(tiles.MAX_LETTERS):
            rack[str(id)] = num_to_letter(request_number + id)

        request_number = (request_number+1) % 26
        print(f"GET TILES --> {json.dumps(rack)}")
        yield f"{json.dumps(rack)}\n\n"


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str)
    parser.add_argument("--port", type=int)
    parser.add_argument("--sleep", type=int, default=1)
    args = parser.parse_args()

    sleep_time = args.sleep
    run(host=args.host, port=args.port, server='gevent')
