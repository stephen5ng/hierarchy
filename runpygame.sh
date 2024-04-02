#!/bin/bash -e

. cube_env/bin/activate

trap 'kill $(jobs -p)' EXIT

rm -f /tmp/sayfiles/*

./app.py &

has_esp_32() {
  local pattern="$2"
  if [[ $(find "/dev" -name "cu.usb*" -maxdepth 1 -print -quit) ]]; then
    return 0  # True if a matching file is found
  fi
  return 1  # False if no matching files are found
}

if has_esp_32; then
    sleep 4
    python -X dev -X tracemalloc=5 ./cubes_to_game.py --tags tag_ids.txt --cubes cube_ids.txt --serial_reader $(ls /dev/cu.usb*) &
fi

# python -X dev -X tracemalloc=5 ./fake_game_stream.py --host localhost --port 8080 2> fake_game_stream.log &
sleep 2
python -X dev -X tracemalloc=5 ./pygamegameasync.py
