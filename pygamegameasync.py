#!/usr/bin/env python3

# From https://python-forum.io/thread-23029.html

from aiohttp import web
from aiohttp_sse import sse_response
import asyncio
from datetime import datetime
import json
import pygame
from pygameasync import Clock, EventEngine, WebFrontend
from cube_async import process_serial_messages, process_sse_messages

events = EventEngine()

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
scaling_factor = 4

class Rack(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1
    LETTER_COUNT = 6

    def __init__(self):
        self.letters = "ABCDEF"

        self.surface = pygame.Surface((Rack.LETTER_SIZE*Rack.LETTER_COUNT,
            Rack.LETTER_SIZE), pygame.SRCALPHA)
        self.surface.fill((100, 100, 0))

        events.on(f"input.change_rack")(self.change_rack)
        self.pos = [0, 0]
        self.draw()

    def draw(self):
        width = height = Rack.LETTER_SIZE
        self.font = pygame.font.SysFont("Arial", Rack.LETTER_SIZE)
        self.textSurf = self.font.render(self.letters, Rack.ANTIALIAS, (128, 128, 0))
        W = self.textSurf.get_width()
        H = self.textSurf.get_height()

        # self.rect = self.textSurf.get_rect()
        self.pos[0] += (SCREEN_WIDTH - W/2)
        self.pos[1] += (SCREEN_HEIGHT - H)

        self.surface.fill((0,0,0))
        self.surface.blit(self.textSurf, [width/2 - W/2, height/2 - H/2])
        # self.pos

    def change_rack(self, letters):
        self.letters = letters
        self.draw()

    async def update(self, window):
        print(f"update: {self.pos}")
        window.blit(self.surface, self.pos)


class Letter(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1

    def __init__(self):
        self.letter = " "

        self.surface = pygame.Surface((Letter.LETTER_SIZE, Letter.LETTER_SIZE), pygame.SRCALPHA)
        self.surface.fill((0,0,0))

        self.pos = [10, 10]
        self.register_handlers()

    def draw(self):
        width = height = Letter.LETTER_SIZE
        self.font = pygame.font.SysFont("Arial", Letter.LETTER_SIZE)
        self.textSurf = self.font.render(self.letter, Letter.ANTIALIAS, (255, 0, 0))
        W = self.textSurf.get_width()
        H = self.textSurf.get_height()
        self.rect = self.textSurf.get_rect()
        self.surface.fill((0,0,0))
        self.surface.blit(self.textSurf, [width/2 - W/2, height/2 - H/2])

    def register_handlers(self):
        events.on(f"input.change_letter")(self.change_letter)
        events.on(f"input.move_up")(self.move_up)

    async def change_letter(self, new_letter):
        self.letter = new_letter
        self.draw()

    async def move_up(self, amount):
        self.pos[1] -= amount

    async def update(self, window):
        await self.move_up(-0.1)
        window.blit(self.surface, self.pos)


class Game:
    def __init__(self):
        self.letter = None
        self.letter = Letter()
        self.rack = Rack()

    async def update(self, window):
        await self.letter.update(window)
        await self.rack.update(window)

def load_rack(arg1):
    print(f"!!!!!!! load_rack: {arg1}")
    events.trigger(f"input.change_letter", arg1["0"])
    return True


async def main():
    window = pygame.display.set_mode((SCREEN_WIDTH*scaling_factor, SCREEN_HEIGHT*scaling_factor))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    clock = Clock()
    game = Game()

    asyncio.create_task(process_sse_messages("http://localhost:8080/get_tiles", load_rack))

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return

        screen.fill((0, 0, 0))
        await game.update(screen)
        window.blit(pygame.transform.scale(screen, window.get_rect().size), (0, 0))
        pygame.display.flip()

        await clock.tick(30)


if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()