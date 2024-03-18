#!/bin/bash -ex
trap "kill 0" EXIT

FAKE_SERIAL_SLEEP=.05

./app.py &

./speak.sh &

LETTERS=$(grep "MAX_LETTERS =" tiles.py | cut -d ' ' -f 3)
head -$LETTERS cube_ids.fake.txt > /tmp/cube_ids.txt
head -$LETTERS tag_ids.fake.txt > /tmp/tag_ids.txt

rm -f /tmp/socat.log
socat -lf /tmp/socat.log pty,rawer,echo=0,link=./CUBES_TO_GAME_READER pty,rawer,echo=0,link=./CUBES_TO_GAME_WRITER &
socat -lf /tmp/socat2.log pty,rawer,echo=0,link=./GAME_TO_CUBES_READER pty,rawer,echo=0,link=./GAME_TO_CUBES_WRITER &
sleep 1
cat < ./GAME_TO_CUBES_READER &
./fake_serial.py --sleep $FAKE_SERIAL_SLEEP --tags /tmp/tag_ids.txt --cubes /tmp/cube_ids.txt --random true > ./CUBES_TO_GAME_WRITER &
sleep 2
#./pygamegameasync.py
./cubes_to_game.py --tags /tmp/tag_ids.txt --cubes /tmp/cube_ids.txt --serial_reader "./CUBES_TO_GAME_READER" --serial_writer "./GAME_TO_CUBES_WRITER"
