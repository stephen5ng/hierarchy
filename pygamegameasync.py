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


class Letter(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1

    def __init__(self):
        self.letter = " "

        self.surface = pygame.Surface((Letter.LETTER_SIZE, Letter.LETTER_SIZE), pygame.SRCALPHA)
        self.surface.fill((0,0,0))

        self.pos = [10, 10]
        self.movement_intensity = 0.1
        self.register_handlers()

    def draw_letter(self):
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
        self.draw_letter()

    async def move_up(self, amount):
        self.pos[1] -= amount
        print(f"move up: {self.pos[1]}")

    async def update(self, window):
        await self.move_up(-0.1)
        window.blit(self.surface, self.pos)


class Game:
    def __init__(self):
        self.letters = []
        events.on("letter.add")(self.create_letter)

    async def create_letter(self):
        new_letter = Letter()
        self.letters.append(new_letter)
        return new_letter

    async def update(self, window):
        for letter in self.letters:
            await letter.update(window)

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
    local_letter = (await events.async_trigger("letter.add"))[0]

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