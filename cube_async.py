#!/usr/bin/env python3

import aiohttp
import asyncio
import json
import serial_asyncio


async def process_serial_messages(reader, serial_handler):
    while True:
        msg = await reader.readuntil(b'\n')
        if not await serial_handler(msg.rstrip().decode()):
            return

async def process_sse_messages(url, sse_handler, arg):
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60*60*24*7)) as session:

        print(f"process sse {url}")
        while True:
            async with session.get(url) as response:
                while True:
                    chunk = await response.content.readuntil(b"\n\n")
                    some_data = chunk.strip().decode().lstrip("data: ")
                    # print(f"data: {chunk}")
                    if not await sse_handler(json.loads(some_data), arg):
                        return
