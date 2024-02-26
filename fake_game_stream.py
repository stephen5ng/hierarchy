#!/usr/bin/env python3

from bottle import response, route, run
import random
import time
import json

# Serve SSE data that looks like tile updates.

@route("/get_tiles")
def get_tiles():
    response.content_type = 'text/event-stream'
    response.cache_control = 'no-cache'
    request_number = 0
    while True:
        tiles = {}
        for id in range(7):
            tiles[str(id)] = chr(ord("A") + request_number + id)
        request_number += 1
        print(f"--> {json.dumps(tiles)}")
        time.sleep(random.randrange(0, 20) / 10.0)
        yield f"{json.dumps(tiles)}\n\n"


if __name__ == '__main__':
    run(host='0.0.0.0', port=8080, debug=True)
