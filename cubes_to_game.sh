#!/bin/bash


while true
do
    python -X dev -X tracemalloc=5 ./cubes_to_game.py --tags tag_ids.txt --cubes cube_ids.txt --serial_reader $(ls /dev/cu.usb*)
    echo cubes_to_game died, restarting
done