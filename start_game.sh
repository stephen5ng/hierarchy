#!/bin/bash -e

cd /home/dietpi/hierarchy
. env/bin/activate
trap "kill 0" EXIT
mqtt_server=${MQTT_SERVER:-localhost}
if ! nc -zv $mqtt_server 1883 > /dev/null 2>&1; then
  /opt/homebrew/opt/mosquitto/sbin/mosquitto -c /opt/homebrew/etc/mosquitto/mosquitto.conf &
fi


./hierarchy_game.py