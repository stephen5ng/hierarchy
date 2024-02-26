#!/usr/bin/env python3

import aiohttp
import json
import serial_asyncio

async def wait_for_game_updates(update_handler):
    reader, _ = await serial_asyncio.open_serial_connection(
        url='./reader', baudrate=115200)
    while True:
        msg = await reader.readuntil(b'\n')
        if not update_handler(msg.rstrip().decode()):
            return

async def listen_for_new_tiles(url, tile_handler):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            while True:
                chunk = await response.content.readuntil(b"\n\n")
                if not tile_handler(json.loads(chunk.strip())):
                    return
