#!/bin/bash -ex
. cube_env/bin/activate

trap "kill 0" EXIT

./fake_tile_sequences.sh &

./main.py --start
