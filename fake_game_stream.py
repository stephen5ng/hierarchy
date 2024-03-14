#!/usr/bin/env python3

# Serve SSE data that looks like rack updates from the game to the frontend (cubes or web).

import argparse
from bottle import response, route, run
import json
import random
import time

import tiles

def num_to_letter(i):
    return chr(ord("A") + (i % 26))

@route("/get_tiles")
def get_tiles():
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    request_number = 0
    while True:
        rack = {}
        for id in range(tiles.MAX_LETTERS):
            rack[str(id)] = num_to_letter(request_number + id)

        request_number = (request_number+1) % 26
        print(f"GET TILES --> {json.dumps(rack)}")
        time.sleep(random.randrange(0, 20) / 100.0)
        yield f"{json.dumps(rack)}\n\n"


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str)
    parser.add_argument("--port", type=int)
    args = parser.parse_args()

    run(host=args.host, port=args.port)
