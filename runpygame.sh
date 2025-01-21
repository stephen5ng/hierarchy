#!/bin/bash -e

. cube_env/bin/activate

trap "kill 0" EXIT
if ! nc -zv localhost 1883 > /dev/null 2>&1; then
  /opt/homebrew/opt/mosquitto/sbin/mosquitto -c /opt/homebrew/etc/mosquitto/mosquitto.conf &
fi

has_esp_32() {
  local pattern="$2"
  if [[ $(find "/dev" -maxdepth 1 \( -name "ttyUSB*" -o -name "cu.usb*" \) -print -quit) ]]; then
    return 0  # True if a matching file is found
  fi
  return 1  # False if no matching files are found
}

python -X dev -X tracemalloc=5 ./main.py
# python ./main.py
