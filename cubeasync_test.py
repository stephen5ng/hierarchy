#!/usr/bin/env python3

import aiohttp
import argparse
import asyncio
import re
import serial_asyncio
from collections import Counter
from cube_async import get_sse_messages, get_serial_messages
import cubes_to_game

# Ensure that messages are handled asynchronously and correctly.

all_messages = []
NUMBER_OF_TASKS = 10

update_count = 0
async def process_cube_guess(message):
    global update_count
    print(f"<-- SERIAL {update_count}: {message}")
    match = int(re.search(r"(\d+)", message).group(1))
    if match != update_count % len(cubes_to_game.TAGS_TO_CUBES):
        raise Exception(
            f"incorrect serial message: {message}. Expected {update_count}, got: {match}")
    all_messages.append("SERIAL")
    update_count += 1
    return False if update_count >= NUMBER_OF_TASKS else True

async def handle_cube_guess_from_serial(reader):
    async for data in get_serial_messages(reader):
        if not await process_cube_guess(data):
            return

response_count = 0
async def load_rack(tiles_with_letters, writer):
    global response_count
    all_messages.append("HTTP")
    print(f"<-- HTTP: {response_count} {tiles_with_letters}")
    first_letter = tiles_with_letters["0"]
    expected_first_letter = chr(ord("A") + response_count)
    if first_letter != expected_first_letter:
        raise Exception(f"incorrect http message: {first_letter}, expected: {expected_first_letter} ")
    response_count += 1
    await cubes_to_game.load_rack(tiles_with_letters, writer)
    return False if response_count >= NUMBER_OF_TASKS else True

async def load_rack_from_sse(session, url, writer):
    async for rack in get_sse_messages(session, url):
        if not await load_rack(rack, writer):
            return

async def load_tiles(session):
    for i in range(10):
        async with session.get("http://localhost:8080/next_tile") as response:
            t = (await response.content.read()).decode()
            print(f"next tile: {t}")
            all_messages.append("GET")
            await asyncio.sleep(1)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial_reader", help="Serial port reader", type=str)
    parser.add_argument("--serial_writer", help="Serial port writer", type=str)
    parser.add_argument("--sse_host", help="Hostname from which to read SSE updates", type=str)
    parser.add_argument("--tags", default="tag_ids.txt", type=str)
    parser.add_argument("--cubes", default="cube_ids.txt", type=str)
    args = parser.parse_args()

    cubes_to_game.get_tags_to_cubes(args.cubes, args.tags)

    http_url = f"{args.sse_host}/get_tiles"
    fake_serial_reader, _ = await serial_asyncio.open_serial_connection(
        url=args.serial_reader, baudrate=115200)
    _, fake_serial_writer2 = await serial_asyncio.open_serial_connection(
        url=args.serial_writer, baudrate=115200)
    wrapped_serial_writer = lambda s: cubes_to_game.write_to_serial(fake_serial_writer2, s)
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60*60*24*7)) as session:
        tasks = []
        tasks.append(asyncio.create_task(
            load_rack_from_sse(session, http_url, wrapped_serial_writer)))
        tasks.append(asyncio.create_task(handle_cube_guess_from_serial(
            fake_serial_reader)))
        tasks.append(asyncio.create_task(load_tiles(session)))

        await asyncio.wait(tasks)
    print(all_messages)
    counts = Counter(all_messages[:10])
    print(f"counter: {counts}")
    if counts["GET"] < 3 or counts["HTTP"] < 3 or counts["SERIAL"] < 3:
        raise Exception("Error: tasks not async enough.")


if __name__ == "__main__":
    asyncio.run(main())
