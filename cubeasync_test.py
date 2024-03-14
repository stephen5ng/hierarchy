#!/usr/bin/env python3

import argparse
import asyncio
import re
import serial_asyncio

from cube_async import process_serial_messages, process_sse_messages
import cubes_to_game

# Ensure that messages are handled asynchronously and correctly.

all_messages = []
update_count = 0
async def handle_guess(message):
    global update_count
    print(f"<-- SERIAL {update_count}: {message}")
    match = int(re.search(r"(\d+)", message).group(1))
    if match != update_count % len(cubes_to_game.TAGS_TO_CUBES):
        raise Exception(
            f"incorrect serial message: {message}. Expected {update_count}, got: {match}")
    all_messages.append("SERIAL")
    update_count += 1
    if update_count >= 10:
        return False
    return True

response_count = 0
async def load_rack(tiles_with_letters, writer):
    global response_count
    print(f"<-- HTTP: {response_count} {tiles_with_letters}")
    first_letter = tiles_with_letters["0"]
    expected_first_letter = chr(ord("A") + response_count)
    if first_letter != expected_first_letter:
        raise Exception(f"incorrect http message: {first_letter}, expected: {expected_first_letter} ")
    all_messages.append("HTTP")
    response_count += 1
    await cubes_to_game.load_rack(tiles_with_letters, writer)
    await asyncio.sleep(1)
    if response_count >= 10:
        return False
    return True


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
    if True:  # Parallel
        await asyncio.gather(process_serial_messages(fake_serial_reader, handle_guess),
            process_sse_messages(http_url, load_rack, wrapped_serial_writer))
    else:     # Serial
        await asyncio.gather(process_serial_messages(fake_serial_reader, handle_guess))
        await asyncio.gather(process_sse_messages(http_url, load_rack, wrapped_serial_writer))
    print(all_messages)
    first_half = set(all_messages[:10])
    if len(first_half) != 2:
        raise Exception("Error: not async")

if __name__ == "__main__":
    asyncio.run(main())
