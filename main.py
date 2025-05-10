#!/usr/bin/env python3

import platform
import aiomqtt
import argparse
import asyncio
import datetime
import logging
import os
import pygame
import traceback

import app
import cubes_to_game
from dictionary import Dictionary
from pygameasync import events
import pygamegameasync
import tiles
import hub75

MQTT_SERVER = os.environ.get("MQTT_SERVER", "localhost")
my_open = open

logger = logging.getLogger(__name__)

last_cube_id = None
last_cube_time = None

async def publish_tasks_in_queue(publish_client: aiomqtt.Client, queue: asyncio.Queue) -> None:
    while True:
        topic, message, retain = await queue.get()
        await publish_client.publish(topic, message, retain=retain)
        logger.info(f"publishing: {topic}, {message}")
        if "cube" in str(topic):
            cube_id = str(topic).split('/')[1]
            if cube_id == last_cube_id:
                # print(f"{topic}  delta: {datetime.datetime.now() - last_cube_time}")
                pass

async def trigger_events_from_mqtt(
    subscribe_client: aiomqtt.Client, publish_queue: asyncio.Queue, block_words: pygamegameasync.BlockWordsPygame) -> None:

    global last_cube_id, last_cube_time
    try:
        async for message in subscribe_client.messages:
            logger.info(f"trigger_events_from_mqtt incoming message topic: {message.topic} {message.payload!r}")
            if message.topic.matches("cube/nfc/#"):
                now = datetime.datetime.now()
                cube_id = str(message.topic).split('/')[2]
                last_cube_time = now
                last_cube_id = cube_id
                await cubes_to_game.handle_mqtt_message(publish_queue, message)
            else:
                await block_words.handle_mqtt_message(message.topic)

    except Exception as e:
        print(f"fatal error: {e}")
        traceback.print_tb(e.__traceback__)
        events.trigger("game.abort")
        raise e

async def main(args: argparse.Namespace, dictionary: Dictionary, block_words: pygamegameasync.BlockWordsPygame) -> None:
    async with aiomqtt.Client(MQTT_SERVER) as subscribe_client:
        async with aiomqtt.Client(MQTT_SERVER) as publish_client:
            publish_queue: asyncio.Queue = asyncio.Queue()
            the_app = app.App(publish_queue, dictionary)
            
            cubes_to_game.init(args.cubes, args.tags)
            await cubes_to_game.subscribe(subscribe_client)

            subscribe_task = asyncio.create_task(
                trigger_events_from_mqtt(subscribe_client, publish_queue, block_words),
                name="mqtt subscribe handler")
            publish_task = asyncio.create_task(publish_tasks_in_queue(publish_client, publish_queue),
                name="mqtt publish handler")

            await block_words.main(the_app, subscribe_client, args.start, args)

            subscribe_task.cancel()
            publish_queue.shutdown()
            publish_task.cancel()

BUNDLE_TEMP_DIR = "."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", default="tag_ids.txt", type=str)
    parser.add_argument("--cubes", default="cube_ids.txt", type=str)
    parser.add_argument('--start', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    # logger.setLevel(logging.DEBUG)
    pygame.mixer.init(frequency=48000, size=-16, channels=2)
    hub75.init()
    dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open=my_open)
    dictionary.read(f"{BUNDLE_TEMP_DIR}/sowpods.txt", f"{BUNDLE_TEMP_DIR}/bingos.txt")
    pygame.init()
    block_words = pygamegameasync.BlockWordsPygame()
    asyncio.run(main(args, dictionary, block_words))
    pygame.quit()