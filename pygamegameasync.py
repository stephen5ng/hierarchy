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

LETTER_SIZE = 25
ANTIALIAS = 1

class Letter:
    letter_count = 0

    def __init__(self, color):
        Letter.letter_count += 1
        self.letter = "A"
        self.letter_id = Letter.letter_count

        self.surface = self.create_surface(color)
        self.pos = [10, 10]
        self.movement_intensity = 10
        self.draw_letter()
        self.register_handlers()

    def draw_letter(self):
        width = height = LETTER_SIZE
        self.font = pygame.font.SysFont("Arial", LETTER_SIZE)
        self.textSurf = self.font.render(self.letter, ANTIALIAS, (255, 0, 0))
        W = self.textSurf.get_width()
        H = self.textSurf.get_height()
        self.rect = self.textSurf.get_rect()
        self.surface.fill((0,0,0))
        self.surface.blit(self.textSurf, [width/2 - W/2, height/2 - H/2])

    def create_surface(self, color):
        surf = pygame.Surface((LETTER_SIZE, LETTER_SIZE), pygame.SRCALPHA)
        surf.fill(color)
        return surf

    def register_handlers(self):
        events.on(f"input.change_letter.{self.letter_id}")(self.change_letter)
        events.on(f"input.move_up.{self.letter_id}")(self.move_up)
        events.on(f"input.move_right.{self.letter_id}")(self.move_right)

    async def change_letter(self, new_letter):
        self.letter = new_letter
        self.draw_letter()

    async def move_right(self, amount):
        self.pos[0] += amount * self.movement_intensity

    async def move_up(self, amount):
        # 0 == top of screen, so 'up' is negative
        self.pos[1] -= amount * self.movement_intensity

    async def update(self, window):
        window.blit(self.surface, self.pos)


class Game:
    def __init__(self):
        self.letters = []
        events.on("letter.add")(self.create_letter)

    async def create_letter(self):
        color = (155, 155, 0)
        new_letter = Letter(color)
        self.letters.append(new_letter)
        return new_letter

    async def update(self, window):
        for letter in self.letters:
            await letter.update(window)

def load_rack(arg1):
    print(f"!!!!!!! load_rack: {arg1}")
    events.trigger(f"input.change_letter.1", arg1["0"])

    return True

async def main():
    window = pygame.display.set_mode((SCREEN_WIDTH*scaling_factor, SCREEN_HEIGHT*scaling_factor))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    asyncio.create_task(process_sse_messages("http://localhost:8080/get_tiles", load_rack))
    game = Game()
    local_letter = (await events.async_trigger("letter.add"))[0]
    local_letter_id = local_letter.letter_id

    clock = Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    events.trigger(f"input.move_right.{local_letter_id}", -1)
                elif ev.key == pygame.K_RIGHT:
                    events.trigger(f"input.move_right.{local_letter_id}", +1)
                elif ev.key == pygame.K_UP:
                    events.trigger(f"input.move_up.{local_letter_id}", +1)
                elif ev.key == pygame.K_DOWN:
                    events.trigger(f"input.move_up.{local_letter_id}", -1)

        screen.fill((0, 0, 0))
        await game.update(screen)

        window.blit(pygame.transform.scale(screen, window.get_rect().size), (0, 0))

        pygame.display.flip()

        await clock.tick(30)

if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()