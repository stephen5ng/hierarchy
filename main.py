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
from pygameasync import events
import pygamegameasync
if platform.system() != "Darwin":
    from rgbmatrix import graphics
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    from runtext import RunText


logger = logging.getLogger(__name__)

async def trigger_events_from_mqtt(client):
    try:
        async for message in client.messages:
            logger.info(f"trigger_events_from_mqtt incoming message topic: {message.topic} {message.payload}")
            await cubes_to_game.handle_mqtt_message(client, message)
    except Exception as e:
        events.trigger("game.abort")
        raise e

async def main(args):
    async with aiomqtt.Client("localhost") as mqtt_client:
        app.init()
        await cubes_to_game.init(mqtt_client, args.cubes, args.tags)

        t = asyncio.create_task(trigger_events_from_mqtt(mqtt_client))

        await pygamegameasync.main(mqtt_client, args.start, args)
        t.cancel()

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
        pygamegameasync.offscreen_canvas = matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("7x13.bdf")
        textColor = graphics.Color(255, 255, 0)
        pos = offscreen_canvas.width - 40
        my_text = "HELLO"
        graphics.DrawText(offscreen_canvas, font, pos, 10, textColor, my_text)
        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

    pygame.init()
    asyncio.run(main(args))
    pygame.quit()