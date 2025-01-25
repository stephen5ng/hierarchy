#! /usr/bin/env python

import aiomqtt
import argparse
import asyncio
import os
import random

MQTT_SERVER = os.environ.get("MQTT_SERVER", "localhost")

def get_lines(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
        return [line.strip() for line in lines]

    return random.choice(lines).strip()

async def pub(sleep_duration_s):
    cube_ids = get_lines("cube_ids.txt")
    tag_ids = get_lines("tag_ids.txt")
    tag_ids.append("")

    async with aiomqtt.Client(MQTT_SERVER) as client:
        while True:
            await client.publish(f"cube/nfc/{random.choice(cube_ids)}",
                payload=random.choice(tag_ids))
            await asyncio.sleep(sleep_duration_s)

parser = argparse.ArgumentParser(description="Generate random cube sequences")
parser.add_argument("--duration", type=float, default=0.01,
                    help="Sleep duration in seconds (default: 0.01)")
args = parser.parse_args()

asyncio.run(pub(args.duration))
