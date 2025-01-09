#!/bin/bash
while true
do
    mosquitto_pub -h localhost -t "cube/nfc" -m "$(shuf -n 1 cube_ids.txt):$(shuf -n 1 tag_ids.txt)"
    # sleep 2
done
