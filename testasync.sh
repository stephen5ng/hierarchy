#!/bin/bash -ex

# Test that python async code is actually handling serial and http requests in parallel.

trap "kill 0" EXIT

socat -d -d -lf socat.log pty,rawer,echo=0,link=./CUBES_TO_GAME_READER pty,rawer,echo=0,link=./CUBES_TO_GAME_WRITER &
socat -d -d -lf socat.log pty,rawer,echo=0,link=./GAME_TO_CUBES_READER pty,rawer,echo=0,link=./GAME_TO_CUBES_WRITER &
sleep 1
cat ./GAME_TO_CUBES_READER > reader2.out &
./fake_game_stream.py --host localhost --port 8080 2> fake_game_stream.log &
./fake_serial.py --sleep 0.5 --tags tag_ids.fake.txt --cubes cube_ids.fake.txt > ./CUBES_TO_GAME_WRITER &
sleep 2
./cubeasync_test.py --tags tag_ids.fake.txt --cubes cube_ids.fake.txt --serial_reader ./CUBES_TO_GAME_READER --serial_writer ./GAME_TO_CUBES_WRITER --sse_host http://localhost:8080
