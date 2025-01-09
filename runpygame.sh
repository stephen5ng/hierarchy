#!/bin/bash -ex

. cube_env/bin/activate

trap 'kill $(jobs -p)' EXIT
/opt/homebrew/opt/mosquitto/sbin/mosquitto -c /opt/homebrew/etc/mosquitto/mosquitto.conf &

has_esp_32() {
  local pattern="$2"
  if [[ $(find "/dev" -maxdepth 1 \( -name "ttyUSB*" -o -name "cu.usb*" \) -print -quit) ]]; then
    return 0  # True if a matching file is found
  fi
  return 1  # False if no matching files are found
}

# python -X dev -X tracemalloc=5 ./fake_game_stream.py --host localhost --port 8080 2> fake_game_stream.log &
python -X dev -X tracemalloc=5 ./main.py
