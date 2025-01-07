#!/bin/bash
while true
do
    mosquitto_pub -h localhost -t "cubes/guess_tiles" -m "[\"$(./fake_tile_sequences.py)\"]"
    sleep 20
done