#!/bin/bash -ex
trap "kill 0" EXIT

./app.py 1 &

LETTERS=$(grep "MAX_LETTERS =" tiles.py | cut -d ' ' -f 3)
head -$LETTERS cube_ids.fake.txt > /tmp/cube_ids.txt
head -$LETTERS tag_ids.fake.txt > /tmp/tag_ids.txt

sleep 1
./cubes_to_game.py --tags /tmp/tag_ids.txt --cubes /tmp/cube_ids.txt &
sleep 2
./fake_tile_sequences.sh &

./pygamegameasync.py --start True
