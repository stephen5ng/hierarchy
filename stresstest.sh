#!/bin/bash -ex
trap "kill 0" EXIT

./app.py 1 &

./fake_tile_sequences.sh &

./pygamegameasync.py --no-start
