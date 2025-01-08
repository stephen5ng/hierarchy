#!/bin/bash -ex
trap "kill 0" EXIT

./fake_tile_sequences.sh &

./pygamegameasync.py --no-start
