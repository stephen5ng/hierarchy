#!/usr/bin/env python3

import aiohttp
import json
import serial_asyncio

async def process_serial_messages(url, serial_handler):
    reader, _ = await serial_asyncio.open_serial_connection(
        url=url, baudrate=115200)
    while True:
        msg = await reader.readuntil(b'\n')
        if not serial_handler(msg.rstrip().decode()):
            return

async def process_sse_messages(url, sse_handler):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            while True:
                chunk = await response.content.readuntil(b"\n\n")
                if not sse_handler(json.loads(chunk.strip())):
                    return
