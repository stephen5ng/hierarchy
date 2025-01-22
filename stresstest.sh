#!/bin/bash -ex
. cube_env/bin/activate

trap "kill 0" EXIT

python fake_tile_sequences.py &

./runpygame.sh
