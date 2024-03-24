#!/usr/bin/env python3

import aiohttp
import argparse
import asyncio
import json
import os
import re
import requests
import serial
import serial_asyncio
import sys
import time
from typing import Dict

from cube_async import get_sse_messages, get_serial_messages
import tiles


# "Tags" are nfc ids
# "Cubes" are the MAC address of the ESP32
# "Tiles" are the tile number assigned by the app (usually 0-6)

TAGS_TO_CUBES : Dict[str, str] = {}

# Linked list of cubes which are adjacent to each other, left-to-right
cube_chain : Dict[str, str] = {}

cubes_to_letters : Dict[str, str] = {}
tiles_to_cubes : Dict[str, str] = {}
cubes_to_tiles : Dict[str, str] = {}

def find_unmatched_cubes():
    sources = set(cube_chain.keys())
    targets = set(cube_chain.values())
    return list(sources - targets)

def remove_back_pointer(target_cube: str):
    for source in cube_chain:
        if cube_chain[source] == target_cube:
            # print(f"removing {source}: {cubes_to_letters[source]}")
            del cube_chain[source]
            break

def print_cube_chain():
    s = ""
    for source in cube_chain:
        target = cube_chain[source]
        s += f"{source} [{cubes_to_letters[source]}] -> {target} [{cubes_to_letters[target]}]; "
    return s

def process_tag(sender_cube, tag):
    # print(f"cubes_to_letters: {cubes_to_letters}")
    if not tag:
        # print(f"process_tag: no tag, deleting target of {sender_cube}")
        if sender_cube in cube_chain:
            del cube_chain[sender_cube]
    else:
        if tag not in TAGS_TO_CUBES:
            print(f"bad tag: {tag}")
            return None
        target_cube = TAGS_TO_CUBES[tag]
        if sender_cube == target_cube:
            # print(f"cube can't point to itself")
            return None

        # print(f"process_tag: {sender_cube} -> {target_cube}")
        if target_cube in cube_chain.values():
            # sender overrides existing chain--must have missed a remove message, process it now.
            # print(f"override: remove back pointer for {target_cube}")
            remove_back_pointer(target_cube)

        cube_chain[sender_cube] = TAGS_TO_CUBES[tag]

    # search for and remove any new loops
    source_cube = sender_cube
    while source_cube:
        if not source_cube in cube_chain:
            break
        next_cube = cube_chain[source_cube]
        if next_cube == sender_cube:
            # print(f"breaking chain {print_cube_chain()}")
            del cube_chain[source_cube]
            # print(f"breaking chain done {print_cube_chain()}")
            break
        source_cube = next_cube

    # print(f"process_tag final cube_chain: {print_cube_chain()}")
    if not cube_chain:
        # No links at all, quit.
        return None

    word_tiles = []
    source_cube = find_unmatched_cubes()[0]
    while source_cube:
        # print(f"source_cube: {source_cube}")
        word_tiles.append(cubes_to_tiles[source_cube])
        if len(word_tiles) > tiles.MAX_LETTERS:
            raise Exception("infinite loop")
        if source_cube not in cube_chain:
            break
        source_cube = cube_chain[source_cube]
    print(f"word is {word_tiles}")
    return "".join(word_tiles)

async def current_score(score, writer):
    if score == 0 or not last_guess_tiles or len(last_guess_tiles) < 3:
        return True
    if score > 0:
        print(f"SCORE: {score}")
    return True

async def write_to_serial(serial_writer, str):
    # print(f"--------WRITING TO SERIAL {str}")
    serial_writer.write(str.encode('utf-8'))
    await serial_writer.drain()

def initialize_arrays():
    tiles_to_cubes.clear()
    cubes_to_tiles.clear()

    cubes = list(TAGS_TO_CUBES.values())
    for ix in range(tiles.MAX_LETTERS+1):
        if ix >= len(cubes):
            break
        tile_id = str(ix)
        tiles_to_cubes[tile_id] = cubes[ix]
        cubes_to_tiles[cubes[ix]] = tile_id

    # print(f"tiles_to_cubes: {tiles_to_cubes}")

async def load_rack_only(tiles_with_letters, writer):
    print(f"LOAD RACK tiles_with_letters: {tiles_with_letters}")

    for tile_id in tiles_with_letters:
        if True or tile_id in tiles_to_cubes:
            cube_id = tiles_to_cubes[tile_id]
            letter = tiles_with_letters[tile_id]
            cubes_to_letters[cube_id] = letter
            await writer(f"{cube_id}:{letter}\n")
    print(f"LOAD RACK tiles_with_letters done: {cubes_to_letters}")

last_tiles_with_letters : Dict[str, str] = {}
async def load_rack(tiles_with_letters, writer, session, serial_writer):
    global last_tiles_with_letters

    print(f"LOAD RACK tiles_with_letters: {tiles_with_letters}")

    for tile_id in tiles_with_letters:
        cube_id = tiles_to_cubes[tile_id]
        letter = tiles_with_letters[tile_id]
        cubes_to_letters[cube_id] = letter
        await writer(f"{cube_id}:{letter}\n")
    print(f"LOAD RACK tiles_with_letters done: {cubes_to_letters}")

    # Some of the tiles changed. Make a guess, just in case one of them was in
    # our last guess (which is overkill).
    if last_tiles_with_letters != tiles_with_letters:
        print(f"LOAD RACK guessing")
        await guess_last_tiles(session, serial_writer)
        last_tiles_with_letters = tiles_with_letters

    return True

async def apply_f_from_sse(session, f, url, *args):
    async for data in get_sse_messages(session, url):
        print(f"data: {data}")
        if not await f(json.loads(data), *args):
            return

last_guess_time = time.time()
last_guess_tiles = ""
DEBOUNCE_TIME = 10
async def guess_word_based_on_cubes(session, sender, tag, serial_writer):
    global last_guess_time, last_guess_tiles

    now = time.time()
    word_tiles = process_tag(sender, tag)
    if not word_tiles:
        return
    if word_tiles == last_guess_tiles and now - last_guess_time < DEBOUNCE_TIME:
        # print("debounce ignoring guess")
        last_guess_time = now
        return

    last_guess_time = now
    last_guess_tiles = word_tiles
    await guess_last_tiles(session, serial_writer)

async def guess_last_tiles(session, serial_writer):
    global last_guess_tiles
    async with session.get(
        "http://localhost:8080/guess_tiles",
        params={"tiles": last_guess_tiles}) as response:
        score = (await response.content.read()).decode()

        print(f"WORD_TILES: {last_guess_tiles}, {score}")
        # flash correct tiles
        if int(score):
            for t in last_guess_tiles:
                await write_to_serial(serial_writer, f"{tiles_to_cubes[t]}:_\n")

async def process_cube_guess(session, data, serial_writer):
    # A serial message "CUBE_ID : TAG_ID" is received whenever a cube is placed
    # next to a tag.
    print(f"process_cube_guess: {data}")
    if data[12] != ":":
        print(f"process_cube_guess ignoring: {data[12]}")
        return True
    sender, tag = data.split(":")
    await guess_word_based_on_cubes(session, sender, tag, serial_writer)
    return True

async def process_cube_guess_from_serial(session, reader, writer):
    async for data in get_serial_messages(reader):
        if not await process_cube_guess(session, data, writer):
            return

def read_data(f):
    data = f.readlines()
    data = [l.strip() for l in data]
    return data

def get_tags_to_cubes(cubes_file, tags_file):
    with open(cubes_file) as cubes_f:
        with open(tags_file) as tags_f:
            return get_tags_to_cubes_f(cubes_f, tags_f)

def get_tags_to_cubes_f(cubes_f, tags_f):
    cubes = read_data(cubes_f)
    tags = read_data(tags_f)

    tags_to_cubes = {}
    for cube, tag in zip(cubes, tags):
        tags_to_cubes[tag] = cube
    return tags_to_cubes

async def main():
    global TAGS_TO_CUBES
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial_reader", required=True, help="Serial port reader", type=str)
    parser.add_argument("--serial_writer", help="Serial port writer", type=str)
    parser.add_argument("--tags", default="tag_ids.txt", type=str)
    parser.add_argument("--cubes", default="cube_ids.txt", type=str)
    args = parser.parse_args()

    TAGS_TO_CUBES = get_tags_to_cubes(args.cubes, args.tags)
    print(f"ttc: {TAGS_TO_CUBES}")

    if args.serial_writer:
        reader, _ = await serial_asyncio.open_serial_connection(
            url=args.serial_reader, baudrate=115200)
        _, writer = await serial_asyncio.open_serial_connection(
            url=args.serial_writer, baudrate=115200)
    else:
        print(f"serial port: {serial}")
        reader, writer = await serial_asyncio.open_serial_connection(
            url=args.serial_reader, baudrate=115200)

    initialize_arrays()
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60*60*24*7)) as session:

        await asyncio.gather(
            process_cube_guess_from_serial(session, reader, writer),
            apply_f_from_sse(session, load_rack, "http://localhost:8080/get_tiles",
                lambda s: write_to_serial(writer, s), session, writer),
            apply_f_from_sse(session, current_score, "http://localhost:8080/get_current_score", writer),
            )

if __name__ == "__main__":
    asyncio.run(main())
