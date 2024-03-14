#!/bin/bash -ex
trap "kill 0" EXIT

FAKE_SERIAL_SLEEP=0.5

./app.py &

./speak.sh &
rm -f /tmp/socat.log
socat -lf /tmp/socat.log pty,rawer,echo=0,link=./CUBES_TO_GAME_READER pty,rawer,echo=0,link=./CUBES_TO_GAME_WRITER &
socat -lf /tmp/socat2.log pty,rawer,echo=0,link=./GAME_TO_CUBES_READER pty,rawer,echo=0,link=./GAME_TO_CUBES_WRITER &
sleep 1
cat < ./GAME_TO_CUBES_READER &
./fake_serial.py --sleep $FAKE_SERIAL_SLEEP --tags tag_ids.fake.txt --cubes cube_ids.fake.txt > ./CUBES_TO_GAME_WRITER &
sleep 2
./cubes_to_game.py --tags tag_ids.fake.txt --cubes cube_ids.fake.txt --serial_reader "./CUBES_TO_GAME_READER" --serial_writer "./GAME_TO_CUBES_WRITER"
