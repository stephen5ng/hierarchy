#!/usr/bin/env python3

# From https://python-forum.io/thread-23029.html

import aiohttp
from aiohttp_sse import sse_response
import argparse
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
ANTIALIAS = 1

class Rack():
    LETTER_SIZE = 25
    LETTER_COUNT = 6
    COLOR = "green"

    def __init__(self):
        self.font = pygame.font.SysFont(FONT, Rack.LETTER_SIZE)
        self.letters = ""
        self.running = False
        events.on(f"rack.change_rack")(self.change_rack)
        self.draw()

    def draw(self):
        letters = self.letters
        if not self.running:
            letters = "GAME OVER"
        self.surface = self.font.render(letters, ANTIALIAS, Color(Rack.COLOR))
        width, height = self.surface.get_size()
        self.height = height
        self.pos = ((SCREEN_WIDTH/2 - width/2), (SCREEN_HEIGHT - height))

    def start(self):
        self.running = True
        self.draw()

    def stop(self):
        self.running = False
        self.draw()

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
        print(f"score: {score}")
        self.speed = -math.log(1+score) / 10
        self.color = Shield.COLOR
        self.score = score
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

            # Get the tightest rectangle around the content for collision detection.
            self.rect = self.surface.get_bounding_rect().move(self.pos[0], self.pos[1])

    def letter_collision(self):
        self.letters = None
        self.pos[1] = SCREEN_HEIGHT

class InProgressShield(Shield):
    X_OFFSET = 10
    COLOR = "grey"

    def __init__(self, y):
        super().__init__("", 10)
        self.font = pygame.font.SysFont("Arial", 12)
        self.draw()

        self.y_midpoint = y
        self.speed = 0
        self.pos[0] = InProgressShield.X_OFFSET
        self.pos[1] = self.y_midpoint - self.surface.get_height()/2
        self.color = InProgressShield.COLOR

    def draw(self):
        self.surface = self.font.render(
            self.letters, Letter.ANTIALIAS, Color(self.color))
        self.pos[0] = InProgressShield.X_OFFSET

    def update_letters(self, letters):
        self.letters = letters
        self.draw()

    async def update(self, window):
        window.blit(self.surface, self.pos)

class Score():
    def __init__(self):
        self.font = pygame.font.SysFont(FONT, Rack.LETTER_SIZE)
        self.pos = [0, 0]
        self.start()
        self.draw()

    def start(self):
        self.score = 0
        self.draw()

    def draw(self):
        self.surface = self.font.render(str(self.score), Letter.ANTIALIAS, (255, 255, 255))
        self.pos[0] = SCREEN_WIDTH/2 - self.surface.get_width()/2

    def update_score(self, score):
        self.score += score
        self.draw()

    async def update(self, window):
        window.blit(self.surface, self.pos)

class PreviousGuesses():
    COLOR = "skyblue"
    FONT = "Arial"
    FONT_SIZE = 12
    POSITION_TOP = 20

    def __init__(self):
        self.fontsize = PreviousGuesses.FONT_SIZE
        self.color = PreviousGuesses.COLOR
        self.font = pygame.font.SysFont(PreviousGuesses.FONT, self.fontsize)
        self.previous_guesses = ""
        events.on(f"input.previous_guesses")(self.update_previous_guesses)
        self.draw()

    async def update_previous_guesses(self, previous_guesses):
        self.previous_guesses = previous_guesses
        self.draw()

    def draw(self):
        try:
            self.surface = textrect.render_textrect(self.previous_guesses, self.font,
                pygame.Rect(0,0, SCREEN_WIDTH, SCREEN_HEIGHT),
                Color(self.color), Color("black"), 0)
            return
        except textrect.TextRectException:
            print("Too many guesses to display!")

    async def update(self, window):
        window.blit(self.surface, [0, PreviousGuesses.POSITION_TOP])


class RemainingPreviousGuesses(PreviousGuesses):
    COLOR = "white"
    FONT = "Arial"
    FONT_SIZE = 10
    TOP_GAP = 3

    def __init__(self):
        self.fontsize = RemainingPreviousGuesses.FONT_SIZE
        self.font = pygame.font.SysFont(RemainingPreviousGuesses.FONT, self.fontsize)
        self.color = RemainingPreviousGuesses.COLOR
        self.previous_guesses = ""
        events.on(f"input.remaining_previous_guesses")(self.update_previous_guesses)
        self.draw()

    async def update(self, window, height):
        # print(f"RPG blitting: {height}")
        window.blit(self.surface, 
            [0, height + PreviousGuesses.POSITION_TOP + RemainingPreviousGuesses.TOP_GAP])

logfile = open("letter.log", "w")
class Letter():
    LETTER_SIZE = 25
    ANTIALIAS = 1
    COLOR = "yellow"
    ACCELERATION = 1.01
    INITIAL_SPEED = 0.005
    INITIAL_HEIGHT = 20
    HEIGHT_INCREMENT = 10
    COLUMN_SHIFT_INTERVAL_MS = 2000

    def __init__(self, session):
        self._session = session
        self.font = pygame.font.SysFont(FONT, Letter.LETTER_SIZE)
        self.width = self.font.size(tiles.MAX_LETTERS*" ")[0]
        self.start()

        self.speed = 0
        self.draw()

    def start(self):
        self.letter = ""
        self.letter_ix = 0
        self.height = Letter.INITIAL_HEIGHT
        self.column_move_direction = 1
        self.next_column_move_time_ms = time.time() * 1000
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.pos = [0, self.height]
        self.speed = Letter.INITIAL_SPEED

    def stop(self):
        self.speed = 0
        self.letter = ""

    def draw(self):
        self.surface = self.font.render(self.letter_ix*" " + self.letter, Letter.ANTIALIAS, Color(Letter.COLOR))
        # w = self.surface.get_width()+1
        self.pos[0] = SCREEN_WIDTH/2 - self.width/2

    def shield_collision(self):
        new_pos = self.height + (self.pos[1] - self.height)/2
        # print(f"---------- {self.height}, {self.pos[1]}, {new_pos}, {self.pos[1] - new_pos}", file=logfile)
        logfile.flush()

        self.pos[1] = self.height + (self.pos[1] - self.height)/2
        self.speed = Letter.INITIAL_SPEED
        self.next_column_move_time_ms = 0

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
        now = time.time() * 1000
        if now > self.next_column_move_time_ms:
            self.letter_ix = self.letter_ix + self.column_move_direction
            if self.letter_ix < 0 or self.letter_ix >= tiles.MAX_LETTERS:
                self.column_move_direction *= -1
                self.letter_ix = self.letter_ix + self.column_move_direction*2

            percent_complete = ((self.pos[1] - Letter.INITIAL_HEIGHT) /
                (SCREEN_HEIGHT - (Letter.INITIAL_HEIGHT + 25)))
            next_interval = 100 + 10000*percent_complete
            self.next_column_move_time_ms = now + next_interval

    def reset(self):
        self.height += Letter.HEIGHT_INCREMENT
        self.pos[1] = self.height
        self.speed = Letter.INITIAL_SPEED

async def safeget(session, url):
    async with session.get(url) as response:
        if response.status != 200:
            c = (await response.content.read()).decode()
            print(c)
            raise Exception(f"bad response: {c}")
        return response

class SafeSession:
    def __init__(self, original_context_manager):
        self.original_context_manager = original_context_manager

    async def __aenter__(self):
        response = await self.original_context_manager.__aenter__()
        if response.status != 200:
            c = (await response.content.read()).decode()
            print(c)
            raise Exception(f"Bad response: {c}")
        return response

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self.original_context_manager.__aexit__(exc_type, exc_value, traceback)

class Game:
    def __init__(self, session):
        self._session = session
        self.letter = Letter(session)
        self.rack = Rack()
        self.previous_guesses = PreviousGuesses()
        self.remaining_previous_guesses = RemainingPreviousGuesses()
        self.score = Score()
        self.shields = []
        self.in_progress_shield = InProgressShield(self.rack.get_midpoint())
        self.running = False
        events.on(f"game.current_score")(self.score_points)

    async def start(self):
        self.letter.start()
        self.score.start()
        self.rack.start()
        self.running = True
        async with SafeSession(self._session.get(
                "http://localhost:8080/start")) as _:
                pass
        os.system('python3 -c "import beepy; beepy.beep(1)"&')

    async def score_points(self, score):
        print(f"SCORING POINTS: {score}")
        #TODO: centralize http error handling
        async with SafeSession(self._session.get("http://localhost:8080/last_play")) as response:
            new_word = (await response.content.read()).decode()
            self.in_progress_shield.update_letters(new_word)

            if score <= 0:
                return
            # self.score.update_score(score)
            # print(f"creating shield with word {new_word}")
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
                self.score.update_score(shield.score)
                os.system("python3 ./beep.py&")
        self.shields[:] = [s for s in self.shields if s.letters]
        await self.score.update(window)

        if self.letter.height + Letter.LETTER_SIZE > self.rack.pos[1] and self.running:
            os.system('python3 -c "import beepy; beepy.beep(7)"')
            print("GAME OVER")
            self.rack.stop()
            self.running = False
            async with SafeSession(self._session.get("http://localhost:8080/stop")) as _:
                pass
            print("GAME OVER OVER")


        if self.running and self.letter.pos[1] + Letter.LETTER_SIZE/2 >= self.rack.pos[1]:
            async with SafeSession(self._session.get(
                "http://localhost:8080/accept_new_letter",
                params={
                    "next_letter": self.letter.letter,
                    "position": self.letter.letter_ix
                })) as _:
                pass

            await self.letter.change_letter(await get_next_tile(self._session))
            self.letter.reset()
            os.system('python3 -c "import beepy; beepy.beep(1)"&')

async def trigger_events_from_sse(session, event, url, parser):
    async for message in get_sse_messages(session, url):
        events.trigger(event, parser(message))

async def get_next_tile(session):
    async with SafeSession(session.get("http://localhost:8080/next_tile")) as response:
        return (await response.content.read()).decode()

async def guess_word_keyboard(session, guess):
    async with SafeSession(session.get("http://localhost:8080/guess_word", params={"guess": guess})) as _:
        pass

async def main(start):
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
                    if key == "SPACE":
                        await game.start()
                    elif key == "BACKSPACE":
                        keyboard_guess = keyboard_guess[:-1]
                    elif key == "RETURN":
                        await guess_word_keyboard(session, keyboard_guess)
                        print("RETURN CASE DONE")
                        keyboard_guess = ""
                    elif len(key) == 1:
                        keyboard_guess += key
                        print(f"key: {str(key)} {keyboard_guess}")
                    game.in_progress_shield.update_letters(keyboard_guess)

            screen.fill((0, 0, 0))
            await game.update(screen)
            window.blit(pygame.transform.scale(screen, window.get_rect().size), (0, 0))
            pygame.display.flip()
            await clock.tick(30)

        for t in tasks:
            t.cancel()

if __name__ == "__main__":

    # For some reason, pygame doesn't like argparse.
    print(sys.argv)
    auto_start = False
    if len(sys.argv) > 1:
        auto_start = True
    sys.argv[:] = sys.argv[0:]


    pygame.init()
    asyncio.run(main(auto_start))
    pygame.quit()
