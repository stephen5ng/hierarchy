#!/usr/bin/env python3

import aiomqtt
import asyncio
import json
import logging
import os
import re
import requests
import sys
import time
from typing import Dict, List, Optional

import tiles
# "Tags" are nfc ids
# "Cubes" are the MAC address of the ESP32
# "Tiles" are the tile number assigned by the app (usually 0-6)

TAGS_TO_CUBES : Dict[str, str] = {}

# Linked list of cubes which are adjacent to each other, left-to-right
cube_chain : Dict[str, str] = {}

cubes_to_letters : Dict[str, str] = {}
tiles_to_cubes : Dict[str, str] = {}
cubes_to_tileid : Dict[str, str] = {}
cubes_to_neighbortags : Dict[str, str] = {}
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)

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
    try:
        s = ""
        for source in cube_chain:
            target = cube_chain[source]
            s += f"{source} [{cubes_to_letters[source]}] -> {target} [{cubes_to_letters[target]}]; "
        return s
    except Exception as e:
        print(f"print_cube_chain ERROR: {e}")

def dump_cubes_to_neighbortags():
    for cube in TAGS_TO_CUBES.values():
        print(f"{cube}", end="")
        print(f"[{cubes_to_letters.get(cube, '')}]", end="")
        if cube in cubes_to_neighbortags:
            neighbor = cubes_to_neighbortags[cube]
            neighbor_cube = TAGS_TO_CUBES.get(neighbor, "")
            print(f"-> {neighbor},{neighbor_cube}", end="")
            print(f"[{cubes_to_letters.get(neighbor_cube, '')}]", end="")
        print(f"")
    print("")

def process_tag(sender_cube: str, tag: str) -> List[str]:
    # Returns lists of tileids
    # print(f"cubes_to_letters: {cubes_to_letters}")
    cubes_to_neighbortags[sender_cube] = tag
    dump_cubes_to_neighbortags()
    print(f"process_tag {sender_cube}: {tag}")
    print(f"process_tag0 cube_chain {cube_chain}")
    if not tag:
        # print(f"process_tag: no tag, deleting target of {sender_cube}")
        if sender_cube in cube_chain:
            del cube_chain[sender_cube]
    elif tag not in TAGS_TO_CUBES:
        print(f"bad tag: {tag}")
        if sender_cube in cube_chain:
            del cube_chain[sender_cube]
    else:
        target_cube = TAGS_TO_CUBES[tag]
        if sender_cube == target_cube:
            print(f"cube can't point to itself")
            return []

        # print(f"process_tag: {sender_cube} -> {target_cube}")
        if target_cube in cube_chain.values():
            # sender overrides existing chain--must have missed a remove message, process it now.
            print(f"IGNORED override: remove back pointer for {target_cube}")
            # remove_back_pointer(target_cube)

        cube_chain[sender_cube] = TAGS_TO_CUBES[tag]

    print(f"process_tag1 cube_chain {cube_chain}")

    # search for and remove any new loops
    source_cube = sender_cube
    iter_length = 0
    while source_cube:
        iter_length += 1
        if iter_length > tiles.MAX_LETTERS:
            print(f"forever loop, bailing")
            return []
            raise Exception("")
        if not source_cube in cube_chain:
            break
        next_cube = cube_chain[source_cube]
        if next_cube == sender_cube:
            print(f"breaking chain {print_cube_chain()}")
            return []
            del cube_chain[source_cube]
            print(f"breaking chain done {print_cube_chain()}")
            break
        source_cube = next_cube
    print(f"process_tag2 cube_chain {cube_chain}")

    # print(f"process_tag final cube_chain: {print_cube_chain()}")
    if not cube_chain:
        # No links at all, quit.
        return []

    all_words = []
    source_cubes = find_unmatched_cubes()
    for source_cube in sorted(source_cubes):
        word_tiles = []
        sc = source_cube
        while sc:
            print(".", end="")
            # print(f"source_cube: {source_cube}")
            word_tiles.append(cubes_to_tileid[sc])
            if len(word_tiles) > tiles.MAX_LETTERS:
                print("infinite loop")
                return []
                # raise Exception("infinite loop")
            if sc not in cube_chain:
                break
            sc = cube_chain[sc]
        all_words.append("".join(word_tiles))
    logging.info(f"all_words is {all_words}")
    all_elements = [item for lst in all_words for item in lst]
    if len(all_elements) != len(set(all_elements)):
        print(f"DUPES: {all_words}")
        return []

    return all_words

def initialize_arrays():
    tiles_to_cubes.clear()
    cubes_to_tileid.clear()

    cubes = list(TAGS_TO_CUBES.values())
    for ix in range(tiles.MAX_LETTERS+1):
        if ix >= len(cubes):
            break
        tile_id = str(ix)
        tiles_to_cubes[tile_id] = cubes[ix]
        cubes_to_tileid[cubes[ix]] = tile_id

async def load_rack_only(publish_queue, tiles_with_letters: Dict[str, str]):
    logging.info(f"LOAD RACK tiles_with_letters: {tiles_with_letters}")
    for tile in tiles_with_letters:
        tile_id = tile.id
        cube_id = tiles_to_cubes[tile_id]
        letter = tile.letter
        cubes_to_letters[cube_id] = letter
        await publish_letter(publish_queue, letter, cube_id)
    logging.info(f"LOAD RACK tiles_with_letters done: {cubes_to_letters}")

async def accept_new_letter(publish_queue, letter, tile_id):
    await publish_letter(publish_queue, letter, tiles_to_cubes[str(tile_id)])
    await guess_last_tiles(publish_queue)

async def publish_letter(publish_queue, letter, cube_id):
    await publish_queue.put((f"cube/{cube_id}/letter", letter, True))

last_tiles_with_letters : Dict[str, str] = {}
async def load_rack(publish_queue, tiles_with_letters: Dict[str, str]):
    global last_tiles_with_letters
    await load_rack_only(publish_queue, tiles_with_letters)

    if last_tiles_with_letters != tiles_with_letters:
        # Some of the tiles changed. Make a guess, just in case one of them
        # was in our last guess (which is overkill).
        logging.info(f"LOAD RACK guessing")
        await guess_last_tiles(publish_queue)
        last_tiles_with_letters = tiles_with_letters

last_guess_time = time.time()
last_guess_tiles: List[str] = []
DEBOUNCE_TIME = 10
async def guess_word_based_on_cubes(sender: str, tag: str, publish_queue):
    global last_guess_time, last_guess_tiles
    now = time.time()
    word_tiles = process_tag(sender, tag)
    logging.info(f"WORD_TILES: {word_tiles}")
    if word_tiles == last_guess_tiles and now - last_guess_time < DEBOUNCE_TIME:
        logging.info(f"debounce ignoring guess")
        last_guess_time = now
        return

    last_guess_time = now
    last_guess_tiles = word_tiles
    await guess_last_tiles(publish_queue)

guess_tiles_callback = None

def set_guess_tiles_callback(f):
    global guess_tiles_callback
    guess_tiles_callback = f

async def guess_last_tiles(publish_queue):
    if not last_guess_tiles:
        await guess_tiles_callback("")

    all_tiles = set((str(i) for i in range(tiles.MAX_LETTERS)))
    borders = []
    for guess in last_guess_tiles:
        logging.info(f"guess_last_tiles: {guess}")
        await publish_queue.put((f"cube/{tiles_to_cubes[guess[0]]}/border", "[", True))
        await publish_queue.put((f"cube/{tiles_to_cubes[guess[-1]]}/border", ']', True))
        all_tiles.remove(guess[0])
        all_tiles.remove(guess[-1])
        for g in guess[1:-1]:
            await publish_queue.put((f"cube/{tiles_to_cubes[g]}/border", '-', True))
            all_tiles.remove(g)
    for g in all_tiles:
        await publish_queue.put((f"cube/{tiles_to_cubes[g]}/border", ' ', True))

    for guess in last_guess_tiles:
        await guess_tiles_callback(guess)

async def blank_out(publish_queue, tiles: str):
    for t in tiles:
        await publish_queue.put((f"cube/{tiles_to_cubes[t]}/flash", None, True))

async def flash_good_words(publish_queue, tiles: str):
    for t in tiles:
        await publish_queue.put((f"cube/{tiles_to_cubes[t]}/flash", None, True))

async def process_cube_guess(publish_queue, topic: aiomqtt.Topic, data: str):
    logging.info(f"process_cube_guess: {topic} {data}")
    sender = topic.value.removeprefix("cube/nfc/")
    await publish_queue.put((f"game/nfc/{sender}", data, True))
    await guess_word_based_on_cubes(sender, data, publish_queue)

def read_data(f):
    data = f.readlines()
    data = [l.strip() for l in data]
    return data

def get_tags_to_cubes(cubes_file: str, tags_file: str):
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

async def init(subscribe_client, cubes_file, tags_file):
    global TAGS_TO_CUBES
    logging.info("cubes_to_game")
    TAGS_TO_CUBES = get_tags_to_cubes(cubes_file, tags_file)
    logging.info(f"ttc: {TAGS_TO_CUBES}")

    initialize_arrays()
    await subscribe_client.subscribe("cube/nfc/#")

async def handle_mqtt_message(publish_queue, message):
    await process_cube_guess(publish_queue, message.topic, message.payload.decode())
