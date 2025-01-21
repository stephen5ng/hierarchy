#!/usr/bin/env python3

import platform
import aiomqtt
import argparse
import asyncio
import logging
import pygame
import traceback

import app
import cubes_to_game
from dictionary import Dictionary
from pygameasync import events
import pygamegameasync
import tiles
if platform.system() != "Darwin":
    from rgbmatrix import graphics
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    from runtext import RunText

MQTT_SERVER = "192.168.0.211"

my_open = open

logger = logging.getLogger(__name__)

async def publish_tasks_in_queue(publish_client, queue):
    while True:
        topic, message, retain = await queue.get()
        await publish_client.publish(topic, message, retain=retain)

async def trigger_events_from_mqtt(subscribe_client, publish_queue):
    try:
        async for message in subscribe_client.messages:
            logger.info(f"trigger_events_from_mqtt incoming message topic: {message.topic} {message.payload}")
            await cubes_to_game.handle_mqtt_message(publish_queue, message)
    except Exception as e:
        print(f"fatal error: {e}")
        traceback.print_tb(e.__traceback__)
        events.trigger("game.abort")
        raise e

async def main(args, dictionary, block_words):
    async with aiomqtt.Client(MQTT_SERVER) as subscribe_client:
        async with aiomqtt.Client(MQTT_SERVER) as publish_client:
            publish_queue = asyncio.Queue()
            the_app = app.App(publish_client, publish_queue, dictionary)
            await cubes_to_game.init(subscribe_client, args.cubes, args.tags)

            subscribe_task = asyncio.create_task(trigger_events_from_mqtt(subscribe_client, publish_queue),
                name="mqtt subscribe handler")
            publish_task = asyncio.create_task(publish_tasks_in_queue(publish_client, publish_queue),
                name="mqtt publish handler")

            await block_words.main(the_app, subscribe_client, args.start, args)

            subscribe_task.cancel()
            publish_queue.shutdown() #?
            publish_task.cancel()

BUNDLE_TEMP_DIR = "."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", default="tag_ids.txt", type=str)
    parser.add_argument("--cubes", default="cube_ids.txt", type=str)
    parser.add_argument('--start', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    # logger.setLevel(logging.DEBUG)
    pygame.mixer.init(11025 if platform.system() != "Darwin" else 22050)

    if platform.system() != "Darwin":
        run_text = RunText()
        run_text.process()

        pygamegameasync.matrix = run_text.matrix
        pygamegameasync.offscreen_canvas = pygamegameasync.matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("7x13.bdf")
        textColor = graphics.Color(255, 255, 0)
        pos = pygamegameasync.offscreen_canvas.width - 40
        my_text = "HELLO"
        graphics.DrawText(pygamegameasync.offscreen_canvas, font, pos, 10, textColor, my_text)
        offscreen_canvas = pygamegameasync.matrix.SwapOnVSync(pygamegameasync.offscreen_canvas)

    dictionary = Dictionary(tiles.MIN_LETTERS, tiles.MAX_LETTERS, open=my_open)
    dictionary.read(f"{BUNDLE_TEMP_DIR}/sowpods.txt")
    pygame.init()
    block_words = pygamegameasync.BlockWordsPygame()
    asyncio.run(main(args, dictionary, block_words))
    pygame.quit()