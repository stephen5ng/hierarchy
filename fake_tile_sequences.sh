#!/bin/bash
while true
do
    mosquitto_pub -h localhost -t "cube/nfc" -m "$(shuf -n 1 cube_ids.txt):$(shuf -n 1 <(./fake_tags.sh))"
    # sleep 2
done
