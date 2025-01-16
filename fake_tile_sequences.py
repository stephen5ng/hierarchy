#! /usr/bin/env python

import aiomqtt
import asyncio
import random

def get_lines(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
        return [line.strip() for line in lines]

    return random.choice(lines).strip()

async def pub():
    cube_ids = get_lines("cube_ids.txt")
    tag_ids = get_lines("tag_ids.txt")
    tag_ids.append("")

    async with aiomqtt.Client("localhost") as client:
        while True:
            await client.publish(f"cube/nfc/{random.choice(cube_ids)}", payload=random.choice(tag_ids))
            await asyncio.sleep(0.05)

asyncio.run(pub())
