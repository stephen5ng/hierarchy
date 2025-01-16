#!/bin/bash
while true
do
    mosquitto_pub -h localhost -t "cube/nfc/$(shuf -n 1 cube_ids.txt)" -m "$(shuf -n 1 <(./fake_tags.sh))"
    sleep 0.05
done
