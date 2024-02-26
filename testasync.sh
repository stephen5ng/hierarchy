#!/bin/bash -ex
trap "kill 0" EXIT

socat -d -d -lf socat.log pty,rawer,echo=0,link=./reader pty,rawer,echo=0,link=./writer &
sleep 1
./fake_game_stream.py 2> fake_game_stream.log &
./randomserial.sh &
sleep 2
./cubeasync_test.py
