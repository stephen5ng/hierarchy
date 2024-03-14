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

from cube_async import process_serial_messages, process_sse_messages
import tiles


# "Tags" are nfc ids
# "Cubes" are the MAC address of the ESP32
# "Tiles" are the tile number assigned by the app (usually 0-6)

TAGS_TO_CUBES = {}

# Linked list of cubes which are adjacent to each other, left-to-right
cube_chain = {}

cubes_to_letters = {}
tiles_to_cubes = {}
cubes_to_tiles = {}

def find_first_matching_file(directory, pattern):
    compiled_pattern = re.compile(pattern)
    for filename in os.listdir(directory):
        if compiled_pattern.match(filename):
            print(f"dev: {filename}")
            return filename
    return None

def find_unmatched_cubes():
    sources = set(cube_chain.keys())
    targets = set(cube_chain.values())
    return list(sources - targets)

def remove_back_pointer(target_cube):
    for source in cube_chain:
        if cube_chain[source] == target_cube:
            print(f"removing {source}: {cubes_to_letters[source]}")
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
        print(f"process_tag: no tag, deleting target of {sender_cube}")
        if sender_cube in cube_chain:
            del cube_chain[sender_cube]
    else:
        if tag not in TAGS_TO_CUBES:
            print(f"bad tag: {tag}")
            return None, None
        target_cube = TAGS_TO_CUBES[tag]
        if sender_cube == target_cube:
            # print(f"cube can't point to itself")
            return None, None

        print(f"process_tag: {sender_cube} -> {target_cube}")
        if target_cube in cube_chain.values():
            # sender overrides existing chain--nust have missed a remove message, process it now.
            print(f"override: remove back pointer for {target_cube}")
            remove_back_pointer(target_cube)

        cube_chain[sender_cube] = TAGS_TO_CUBES[tag]

    # search for and remove any new loops
    source_cube = sender_cube
    while source_cube:
        if not source_cube in cube_chain:
            break
        next_cube = cube_chain[source_cube]
        if next_cube == sender_cube:
            print(f"breaking chain {print_cube_chain()}")
            del cube_chain[source_cube]
            print(f"breaking chain done {print_cube_chain()}")
            break
        source_cube = next_cube

    print(f"process_tag final cube_chain: {print_cube_chain()}")
    if not cube_chain:
        # No links at all, quit.
        return None, None

    word = ""
    word_tiles = []
    source_cube = find_unmatched_cubes()[0]
    while source_cube:
        print(f"source_cube: {source_cube}")
        word += cubes_to_letters[source_cube]
        word_tiles.append(cubes_to_tiles[source_cube])
        if len(word) > tiles.MAX_LETTERS:
            raise Exception("infinite loop")
        if source_cube not in cube_chain:
            break
        source_cube = cube_chain[source_cube]
    print(f"word is {word} / {word_tiles}")
    return word, ",".join(word_tiles)

async def current_score(score, writer):
    if score == 0 or not last_guess_word or len(last_guess_word) < 3:
        return True
    if score > 0:
        print(f"SCORE: {score}")
    return True

async def write_to_serial(serial_writer, str):
    serial_writer.write(str.encode('utf-8'))
    await serial_writer.drain()

async def load_rack(tiles_with_letters, writer):
    print(f"LOAD RACK tiles_with_letters: {tiles_with_letters}")
    cubes = list(TAGS_TO_CUBES.values())
    if not tiles_to_cubes:
        for ix, tile_id in enumerate(tiles_with_letters):
            # Assign the tiles to the cubes in order
            if ix >= len(cubes):
                break
            tiles_to_cubes[tile_id] = cubes[ix]
            cubes_to_tiles[cubes[ix]] = tile_id

    print(f"tiles_to_cubes: {tiles_to_cubes}")
    for tile_id in tiles_with_letters:
        # print(f"tile_id: {tile_id}")
        if tile_id in tiles_to_cubes:
            cube_id = tiles_to_cubes[tile_id]
            letter = tiles_with_letters[tile_id]
            cubes_to_letters[cube_id] = letter
            await writer(f"{cube_id}:{letter}\n")
    print(f"LOAD RACK tiles_with_letters done: {cubes_to_letters}")

    return True

last_guess_time = time.time()
last_guess_word = None
DEBOUNCE_TIME = 10
async def guess_word_based_on_cubes(sender, tag):
    global last_guess_time, last_guess_word

    now = time.time()
    # TODO(sng): remove word
    word, word_tiles = process_tag(sender, tag)
    if not word:
        return
    if word == last_guess_word and now - last_guess_time < DEBOUNCE_TIME:
        # print("debounce ignoring guess")
        last_guess_time = now
        return

    last_guess_time = now
    last_guess_word = word
    query_params = {
        "guess": word,
        "tiles": word_tiles,
        "bonus": "false" }
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8080/guess_word", params=query_params) as response:
            print(f"response: {response}")

async def process_cube_guess(data):
    # A serial message "CUBE_ID : TAG_ID" is received whenever a cube is placed
    # next to a tag.
    print(f"process_cube_guess: {data}")
    if data[12] != ":":
        print(f"process_cube_guess ignoring: {data[12]}")
        return True
    sender, tag = data.split(":")
    await guess_word_based_on_cubes(sender, tag)
    return True

def find_esp_serial_port():
    serial_port = find_first_matching_file("/dev", r"cu.usbserial-.*")
    print(f"serial port: {serial_port}")
    if not serial_port:
        raise Exception("Error: no ESP32 detected on serial port.")
    return f"/dev/{serial_port}"

def read_data(filename):
    with open(filename) as f:
        data = f.readlines()
    data = [l.strip() for l in data]
    return data

def get_tags_to_cubes(cubes_file, tags_file):
    global TAGS_TO_CUBES
    cubes = read_data(cubes_file)
    tags = read_data(tags_file)

    tags_to_cubes = {}
    for cube, tag in zip(cubes, tags):
        tags_to_cubes[tag] = cube
    TAGS_TO_CUBES = tags_to_cubes

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial_reader", help="Serial port reader", type=str)
    parser.add_argument("--serial_writer", help="Serial port writer", type=str)
    parser.add_argument("--tags", default="tag_ids.txt", type=str)
    parser.add_argument("--cubes", default="cube_ids.txt", type=str)
    args = parser.parse_args()

    get_tags_to_cubes(args.cubes, args.tags)
    print(f"ttc: {TAGS_TO_CUBES}")

    if args.serial_reader and args.serial_writer:
        reader, _ = await serial_asyncio.open_serial_connection(
            url=args.serial_reader, baudrate=115200)
        _, writer = await serial_asyncio.open_serial_connection(
            url=args.serial_writer, baudrate=115200)
    else:
        serial = find_esp_serial_port()
        print(f"serial port: {serial}")
        reader, writer = await serial_asyncio.open_serial_connection(url=serial, baudrate=115200)

    await asyncio.gather(
        process_serial_messages(reader, process_cube_guess),
        process_sse_messages("http://localhost:8080/get_tiles", load_rack, lambda s: write_to_serial(writer, s)),
        process_sse_messages("http://localhost:8080/get_current_score", current_score, writer),
        )

if __name__ == "__main__":
    asyncio.run(main())
