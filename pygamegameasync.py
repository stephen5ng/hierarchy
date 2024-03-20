#!/usr/bin/env python3

# From https://python-forum.io/thread-23029.html

import aiohttp
from aiohttp_sse import sse_response
import asyncio
from datetime import datetime
import json
import pygame
from pygameasync import Clock, EventEngine
import sys

from cube_async import get_serial_messages, get_sse_messages

events = EventEngine()

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
scaling_factor = 4


class Rack(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1
    LETTER_COUNT = 6

    def __init__(self):
        super(Rack, self).__init__()
        self.font = pygame.font.SysFont("Arial", Rack.LETTER_SIZE)
        self.letters = "ABCDEF"

        events.on(f"input.change_rack")(self.change_rack)
        self.pos = [0, 0]
        self.draw()

    def draw(self):
        self.textSurf = self.font.render(self.letters, Rack.ANTIALIAS, (128, 128, 0))
        textWidth = self.textSurf.get_width()
        textHeight = self.textSurf.get_height()

        self.pos = ((SCREEN_WIDTH/2 - textWidth/2), (SCREEN_HEIGHT - textHeight))

    async def change_rack(self, rack):
        if rack["last-play"] == "BAD_WORD":
            self.letters = f"{rack['not-word']} {rack['unused']}"
        elif rack["last-play"] == "DUPE_WORD":
            self.letters = f"{rack['already-played']} {rack['unused']}"
        elif rack["last-play"] == "MISSING_LETTERS":
            self.letters = f"{rack['last-guess']} {rack['unused']} {rack['missing']}"
        else:
            self.letters = f"{rack['word']} {rack['unused']}"
        self.draw()

    async def update(self, window):
        window.blit(self.textSurf, self.pos)


class Letter(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1

    def __init__(self, session):
        super(Letter, self).__init__()
        self._session = session
        self.letter = None

        self.font = pygame.font.SysFont("Arial", Letter.LETTER_SIZE)
        self.surface = pygame.Surface((Letter.LETTER_SIZE, Letter.LETTER_SIZE),
            pygame.SRCALPHA)
        self.surface.fill((0, 0, 0))

        self.pos = [SCREEN_WIDTH/2 - self.surface.get_width()/2, 10]
        self.register_handlers()
        self.draw()

    def draw(self):
        self.textSurf = self.font.render(self.letter, Letter.ANTIALIAS, (255, 0, 0))

    def register_handlers(self):
        events.on(f"input.change_letter")(self.change_letter)
        events.on(f"input.move_up")(self.move_up)

    async def change_letter(self, new_letter):
        self.letter = new_letter
        self.draw()

    async def move_up(self, amount):
        self.pos[1] -= amount

    async def update(self, window):
        self.letter = await get_next_tile(self._session)

        self.draw()
        await self.move_up(-0.1)
        window.blit(self.textSurf, self.pos)


class Game:
    def __init__(self, session):
        self.letter = None
        self.letter = Letter(session)
        self.rack = Rack()

    async def update(self, window):
        await self.letter.update(window)
        await self.rack.update(window)


async def load_rack_with_generator(session, url):
    async for rack in get_sse_messages(session, url):
        events.trigger(f"input.change_rack", ''.join(rack.values()))

async def get_next_tile(session):
    async with session.get("http://localhost:8080/next_tile") as response:
        return (await response.content.read()).decode()

async def main():
    window = pygame.display.set_mode(
        (SCREEN_WIDTH*scaling_factor, SCREEN_HEIGHT*scaling_factor))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    clock = Clock()

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60*60*24*7)) as session:
        game = Game(session)

        tasks = []
        tasks.append(asyncio.create_task(
            load_rack_with_generator(session, "http://localhost:8080/get_rack_dict")))

        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return

            screen.fill((0, 0, 0))
            await game.update(screen)
            window.blit(pygame.transform.scale(screen, window.get_rect().size), (0, 0))
            pygame.display.flip()
            sys.stderr.write(".")
            sys.stderr.flush()
            await clock.tick(10)

        for t in tasks:
            t.cancel()

if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()
