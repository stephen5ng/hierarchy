#!/usr/bin/env python3

import asyncio
import json

async def get_sse_messages(session, url):
    print(f"process sse: {url}")
    async with session.get(url) as response:
        while True:
            chunk = await response.content.readuntil(b"\n\n")
            # print(f"chunk: {chunk}")
            some_data = json.loads(chunk.strip().decode().lstrip("data: "))
            print(f"get_sse_messages data: {some_data}")
            yield some_data

async def get_serial_messages(reader):
    while True:
        chunk = await reader.readuntil(b'\n')
        yield chunk.strip().decode().lstrip("data: ")
