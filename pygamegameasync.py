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
import textrect


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

class PreviousGuesses():
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 16)
        self.previous_guesses = ""
        events.on(f"input.previous_guesses")(self.update_previous_guesses)
        self.draw()

    async def update_previous_guesses(self, previous_guesses):
        self.previous_guesses = previous_guesses
        self.draw()

    def draw(self):
        self.surface = textrect.render_textrect(self.previous_guesses, self.font,
            pygame.Rect(0,0, SCREEN_WIDTH, SCREEN_HEIGHT),
            (216, 216, 216), (48, 48, 48), 0)

    async def update(self, window):
        window.blit(self.surface, [0, 0])


class Letter(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1

    def __init__(self, session):
        super(Letter, self).__init__()
        self._session = session
        self.letter = None
        self.height = 10
        self.font = pygame.font.SysFont("Arial", Letter.LETTER_SIZE)
        self.pos = [SCREEN_WIDTH/2 - Letter.LETTER_SIZE/2, self.height]

        events.on(f"input.change_letter")(self.change_letter)
        events.on(f"input.move_up")(self.move_up)
        events.on(f"input.current_score")(self.current_score)

        self.draw()

    def draw(self):
        self.textSurf = self.font.render(self.letter, Letter.ANTIALIAS, (255, 0, 0))

    async def current_score(self, current_score):
        if int(current_score) > 0:
            self.pos[1] = max(self.height, self.pos[1] - 10)
            self.draw()

    async def change_letter(self, new_letter):
        self.letter = new_letter
        self.draw()

    async def move_up(self, amount):
        self.pos[1] -= amount

    async def update(self, window):
        if not self.letter:
            self.letter = await get_next_tile(self._session)

        self.draw()
        speed = 0 + 4*(1 - ((SCREEN_HEIGHT - self.height) / SCREEN_HEIGHT))
        # print(f"pos: {self.pos}")
        await self.move_up(-speed)
        window.blit(self.textSurf, self.pos)

    def reset(self):
        self.pos[1] = self.height

class Game:
    def __init__(self, session):
        self._session = session
        self.letter = None
        self.letter = Letter(session)
        self.rack = Rack()
        self.previous_guesses = PreviousGuesses()


    async def update(self, window):
        await self.previous_guesses.update(window)
        await self.letter.update(window)
        await self.rack.update(window)
        if self.letter.pos[1] + Letter.LETTER_SIZE/2 >= self.rack.pos[1]:
            await self._session.get(
                "http://localhost:8080/accept_new_letter",
                params={"next_letter": self.letter.letter})

            self.letter.reset()
            self.letter.letter = await get_next_tile(self._session)
            self.letter.height += 10


async def load_rack_with_generator(session, url):
    async for rack in get_sse_messages(session, url):
        events.trigger(f"input.change_rack", json.loads(rack))

async def current_score_with_generator(session, url):
    async for score in get_sse_messages(session, url):
        events.trigger(f"input.current_score", score)

async def previous_guesses_with_generator(session, url):
    async for previous_guesses in get_sse_messages(session, url):
        events.trigger(f"input.previous_guesses", previous_guesses)

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
        tasks.append(asyncio.create_task(
            previous_guesses_with_generator(session, "http://localhost:8080/get_previous_guesses")))
        tasks.append(asyncio.create_task(
            current_score_with_generator(session, "http://localhost:8080/get_current_score")))

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
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
