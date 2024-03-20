#!/bin/bash -e
trap "kill 0" EXIT

python -X dev -X tracemalloc=5 ./fake_game_stream.py --host localhost --port 8080 2> fake_game_stream.log &
sleep 2
python -X dev -X tracemalloc=5 ./pygamegameasync.py
