#!/usr/bin/env python3

# From https://python-forum.io/thread-23029.html

import aiohttp
from aiohttp_sse import sse_response
import asyncio
import beepy
from datetime import datetime
import json
import math
import os
import pygame
from pygame import Color
from pygameasync import Clock, EventEngine
import sys
import textrect
import time

import tiles


from cube_async import get_serial_messages, get_sse_messages

events = EventEngine()

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
SCALING_FACTOR = 4

FONT = "Courier"

class Rack(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1
    LETTER_COUNT = 6
    COLOR = "green"

    def __init__(self):
        super().__init__()
        self.font = pygame.font.SysFont(FONT, Rack.LETTER_SIZE)
        self.letters = ""

        events.on(f"rack.change_rack")(self.change_rack)
        self.draw()

    def draw(self):
        self.surface = self.font.render(self.letters, Rack.ANTIALIAS, Color(Rack.COLOR))
        width, height = self.surface.get_size()
        self.height = height
        self.pos = ((SCREEN_WIDTH/2 - width/2), (SCREEN_HEIGHT - height))

    def get_midpoint(self):
        return self.pos[1] + self.height/2

    async def change_rack(self, rack):
        self.letters = rack
        self.draw()

    async def update(self, window):
        window.blit(self.surface, self.pos)


class Shield():
    COLOR = "red"
    ACCELERATION = 1.05
    def __init__(self, letters, score):
        self.font = pygame.font.SysFont("Arial", int(2+math.log(1+score)*8))
        self.letters = letters
        self.baseline = SCREEN_HEIGHT - Rack.LETTER_SIZE
        self.pos = [SCREEN_WIDTH/2, self.baseline]
        self.rect = pygame.Rect(0, 0, 0, 0)
        print(f"socre: {score}")
        self.speed = -math.log(1+score) / 10
        self.color = Shield.COLOR
        self.draw()

    def draw(self):
        self.surface = self.font.render(
            self.letters, Letter.ANTIALIAS, Color(self.color))
        self.pos[0] = SCREEN_WIDTH/2 - self.surface.get_width()/2

    async def update(self, window):
        if self.letters:
            self.pos[1] += self.speed
            self.speed *= 1.05
            window.blit(self.surface, self.pos)
            self.rect = self.surface.get_bounding_rect().move(self.pos[0], self.pos[1])

    def letter_collision(self):
        self.letters = None
        self.pos[1] = SCREEN_HEIGHT

class InProgressShield(Shield):
    def __init__(self, y):
        super().__init__("", 10)
        self.font = pygame.font.SysFont("Arial", 12)
        self.draw()

        self.y_midpoint = y
        self.speed = 0
        self.pos[0] = 10
        self.pos[1] = self.y_midpoint - self.surface.get_height()/2
        self.color = "grey"

    def draw(self):
        self.surface = self.font.render(
            self.letters, Letter.ANTIALIAS, Color(self.color))
        self.pos[0] = 10

    def update_letters(self, letters):
        print(f"ips: {letters}")
        self.letters = letters
        self.draw()

    async def update(self, window):
        # return
        window.blit(self.surface, self.pos)

class Score():
    def __init__(self):
        self.font = pygame.font.SysFont(FONT, Rack.LETTER_SIZE)
        self.score = 0
        self.pos = [0, 0]
        self.draw()

    def draw(self):
        self.surface = self.font.render(str(self.score), Letter.ANTIALIAS, (255, 255, 255))
        self.pos[0] = SCREEN_WIDTH/2 - self.surface.get_width()/2

    async def update(self, window):
        window.blit(self.surface, self.pos)


class PreviousGuesses():
    COLOR = "skyblue"
    FONT = "Arial"
    FONT_SIZE = 14
    POSITION_TOP = 25

    def __init__(self):
        self.fontsize = PreviousGuesses.FONT_SIZE
        self.font = pygame.font.SysFont(PreviousGuesses.FONT, self.fontsize)
        self.previous_guesses = "pg"
        events.on(f"input.previous_guesses")(self.update_previous_guesses)
        self.draw()

    async def update_previous_guesses(self, previous_guesses):
        self.previous_guesses = previous_guesses
        self.draw()

    def draw(self):
        while self.fontsize >= 1:
            try:
                self.surface = textrect.render_textrect(self.previous_guesses, self.font,
                    pygame.Rect(0,0, SCREEN_WIDTH, SCREEN_HEIGHT),
                    Color(PreviousGuesses.COLOR), Color("black"), 0)
                return
            except textrect.TextRectException:
                self.fontsize -= 1
                self.font = pygame.font.SysFont(PreviousGuesses.FONT, self.fontsize)

    async def update(self, window):
        window.blit(self.surface, [0, PreviousGuesses.POSITION_TOP])


class RemainingPreviousGuesses():
    COLOR = "white"
    FONT = "Arial"
    FONT_SIZE = 8
    def __init__(self):
        self.fontsize = RemainingPreviousGuesses.FONT_SIZE
        self.font = pygame.font.SysFont(RemainingPreviousGuesses.FONT, self.fontsize)
        self.previous_guesses = "repg"
        events.on(f"input.remaining_previous_guesses")(self.update_previous_guesses)
        self.draw()

    async def update_previous_guesses(self, previous_guesses):
        print(f"remaining_previous_guesses updating: {previous_guesses}")
        self.previous_guesses = previous_guesses
        self.draw()

    def draw(self):
        while self.fontsize >= 1:
            try:
                print(f"rpg drawing {self.previous_guesses}")
                self.surface = textrect.render_textrect(self.previous_guesses, self.font,
                    pygame.Rect(0,0, SCREEN_WIDTH, SCREEN_HEIGHT),
                    Color(RemainingPreviousGuesses.COLOR), Color("black"), 0)
                return
            except textrect.TextRectException:
                self.fontsize -= 1
                self.font = pygame.font.SysFont(RemainingPreviousGuesses.FONT, self.fontsize)

    async def update(self, window, height):
        # print(f"RPG blitting: {height}")
        window.blit(self.surface, [0, height + PreviousGuesses.POSITION_TOP + 5])


class Letter(pygame.sprite.Sprite):
    LETTER_SIZE = 25
    ANTIALIAS = 1
    COLOR = "yellow"
    ACCELERATION = 1.01
    INITIAL_SPEED = 0.01

    def __init__(self, session):
        super(Letter, self).__init__()
        self._session = session
        self.letter = None
        self.height = 10
        self.rotation = 0
        self.letter_ix = 0
        self.font = pygame.font.SysFont(FONT, Letter.LETTER_SIZE)
        letter_width = self.font.size("X")[0]
        self.pos = [0, self.height]
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.speed = Letter.INITIAL_SPEED
        events.on(f"input.change_letter")(self.change_letter)
        self.draw()

    def draw(self):
        self.surface = self.font.render(self.letter, Letter.ANTIALIAS, Color(Letter.COLOR))
        # self.pos[0] = SCREEN_WIDTH/2 - self.surface.get_width()/2
        w = self.surface.get_width()
        self.pos[0] = SCREEN_WIDTH/2 - w*(tiles.MAX_LETTERS/2) + w*self.letter_ix

    def shield_collision(self):
        self.pos[1] = self.height + (self.pos[1] - self.height)/2
        self.speed = Letter.INITIAL_SPEED

    async def change_letter(self, new_letter):
        self.letter = new_letter
        self.draw()

    async def update(self, window):
        if not self.letter:
            self.letter = await get_next_tile(self._session)

        self.speed *= Letter.ACCELERATION
        self.pos[1] += self.speed

        self.draw()
        # self.rotation += 2
        # self.surface = pygame.transform.rotate(self.surface, self.rotation)
        window.blit(self.surface, self.pos)

        self.rect = self.surface.get_bounding_rect().move(self.pos[0], self.pos[1]).inflate(SCREEN_WIDTH, 0)

    def reset(self):
        self.pos[1] = self.height
        self.letter_ix = (self.letter_ix + 1) % tiles.MAX_LETTERS
        self.speed = Letter.INITIAL_SPEED

class Game:
    def __init__(self, session):
        self._session = session
        self.letter = None
        self.letter = Letter(session)
        self.rack = Rack()
        self.previous_guesses = PreviousGuesses()
        self.remaining_previous_guesses = RemainingPreviousGuesses()
        self.score = Score()
        self.shields = []
        self.in_progress_shield = InProgressShield(self.rack.get_midpoint())
        self.running = True
        events.on(f"game.current_score")(self.score_points)

    async def score_points(self, score):
        print(f"SCORING POINTS: {score}")
        #TODO: centralize http error handling
        async with self._session.get("http://localhost:8080/last_play") as response:
            new_word = (await response.content.read()).decode()
            self.in_progress_shield.update_letters(new_word)

            if response.status != 200:
                c = (await response.content.read()).decode()
                print(c)
                raise Exception(f"bad response: {c}")
            if score <= 0:
                return
            self.score.score += score
            self.score.draw()
            print(f"creating shield with word {new_word}")
            self.shields.append(Shield(new_word, score))

    async def update(self, window):
        await self.previous_guesses.update(window)
        await self.remaining_previous_guesses.update(
            window, self.previous_guesses.surface.get_bounding_rect().height)

        if self.running:
            await self.letter.update(window)
        await self.rack.update(window)
        await self.in_progress_shield.update(window)
        for shield in self.shields:
            await shield.update(window)
            # print(f"checking collision: {shield.rect}, {self.letter.rect}")
            if shield.rect.colliderect(self.letter.rect):
                # print(f"collided: {shield.letters}")
                shield.letter_collision()
                self.letter.shield_collision()
                os.system("python3 ./beep.py&")
        self.shields[:] = [s for s in self.shields if s.letters]
        await self.score.update(window)

        # print(f"letterpos: {self.letter.pos[1]}")
        if self.letter.height + Letter.LETTER_SIZE > self.rack.pos[1]:
            self.rack.letters = "GAME OVER"
            self.rack.draw()
            self.running = False

        if self.running and self.letter.pos[1] + Letter.LETTER_SIZE/2 >= self.rack.pos[1]:
            await self._session.get(
                "http://localhost:8080/accept_new_letter",
                params={
                    "next_letter": self.letter.letter,
                    "position": self.letter.letter_ix
                })

            self.letter.reset()
            self.letter.letter = await get_next_tile(self._session)
            os.system('python3 -c "import beepy; beepy.beep(1)"&')
            self.letter.height += 10

async def trigger_events_from_sse(session, event, url, parser):
    async for message in get_sse_messages(session, url):
        events.trigger(event, parser(message))

async def get_next_tile(session):
    async with session.get("http://localhost:8080/next_tile") as response:
        return (await response.content.read()).decode()

async def guess_word_keyboard(session, guess):
    await session.get("http://localhost:8080/guess_word", params={"guess": guess})


async def main():
    window = pygame.display.set_mode(
        (SCREEN_WIDTH*SCALING_FACTOR, SCREEN_HEIGHT*SCALING_FACTOR))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    clock = Clock()
    keyboard_guess = ""
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60*60*24*7)) as session:
        game = Game(session)

        tasks = []
        tasks.append(asyncio.create_task(
            trigger_events_from_sse(session, "rack.change_rack",
                "http://localhost:8080/get_rack_letters", json.loads)))
        tasks.append(asyncio.create_task(
            trigger_events_from_sse(session, "game.current_score",
                "http://localhost:8080/get_current_score", lambda s: int(s))))
        tasks.append(asyncio.create_task(
            trigger_events_from_sse(session, "input.previous_guesses",
                "http://localhost:8080/get_previous_guesses", lambda s: s)))
        tasks.append(asyncio.create_task(
            trigger_events_from_sse(session, "input.remaining_previous_guesses",
                "http://localhost:8080/get_remaining_previous_guesses", lambda s: s)))

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    key = pygame.key.name(event.key).upper()
                    if key == "BACKSPACE":
                        keyboard_guess = keyboard_guess[:-1]
                    elif key == "RETURN":
                        # game.in_progress_shield.update_letters("")
                        await guess_word_keyboard(session, keyboard_guess)
                        print("RETURN CASE DONE")
                        keyboard_guess = ""
                    elif len(key) == 1:
                        keyboard_guess += key
                    game.in_progress_shield.update_letters(keyboard_guess)
                    print(f"key: {keyboard_guess}")

            screen.fill((0, 0, 0))
            await game.update(screen)
            window.blit(pygame.transform.scale(screen, window.get_rect().size), (0, 0))
            pygame.display.flip()
            await clock.tick(30)

        for t in tasks:
            t.cancel()

if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()
