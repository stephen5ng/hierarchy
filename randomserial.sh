#!/bin/bash
# Emit output that look like updates from the cubes.

sleep 3
for num in {0..9}
do
    sleep $((RANDOM % 3))
    CONTENT="CUBE_${num}: TAG_$((num+1))"
    echo "--> $CONTENT"
    echo $CONTENT > ./writer
done
