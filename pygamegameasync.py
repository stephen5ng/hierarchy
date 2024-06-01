#!/usr/bin/env python3

# From https://python-forum.io/thread-23029.html

import aiohttp
from aiohttp_sse import sse_response
import argparse
import asyncio
import beepy
from datetime import datetime
import json
import logging
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

logger = logging.getLogger(__name__)

events = EventEngine()

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
SCALING_FACTOR = 4

TICKS_PER_SECOND = 45

FONT = "Courier"
ANTIALIAS = 1

FREE_SCORE = 8

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
        self.rect = self.surface.get_bounding_rect().move(self.pos[0], self.pos[1])

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
        # pygame.draw.rect(window, Color("orange"), self.rect)
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
            logger.warning("Too many guesses to display!")

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

class LetterSource():
    def __init__(self, letter):
        self.letter = letter

    async def update(self, window):
        bounding_rect = self.letter.surface.get_bounding_rect()
        self.pos = [SCREEN_WIDTH/2 - self.letter.all_letters_width()/2,
            self.letter.height + bounding_rect.y]
        size = [self.letter.all_letters_width(), 1]
        surf = pygame.Surface(size, pygame.SRCALPHA)
        color = pygame.Color("yellow")
        color.a = 128
        surf.fill(color)
        window.blit(surf, self.pos)

class Letter():
    LETTER_SIZE = 25
    ANTIALIAS = 1
    COLOR = "yellow"
    # ACCELERATION = 1.01
    ACCELERATION = 1.01
    # acc: 1.1, robot score: 100
    # acc: 1.005, robot score: 544

    # ACCELERATION = 1.005
    INITIAL_SPEED = 0.020
    INITIAL_HEIGHT = 20
    ROUNDS = 15
    HEIGHT_INCREMENT = SCREEN_HEIGHT // ROUNDS
    COLUMN_SHIFT_INTERVAL_MS = 10000

    def __init__(self, session):
        self._session = session
        self.font = pygame.font.SysFont(FONT, Letter.LETTER_SIZE)
        self.width = self.font.size(" ")[0]
        self.next_interval_ms = 1
        self.fraction_complete = 0
        self.start()
        self.start_fall_time_ms = pygame.time.get_ticks()
        self.draw()

    def start(self):
        self.letter = ""
        self.letter_ix = 0
        self.height = Letter.INITIAL_HEIGHT
        self.column_move_direction = 1
        self.next_column_move_time_ms = pygame.time.get_ticks()
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.pos = [0, self.height]
        self.start_fall_time_ms = pygame.time.get_ticks()

    def stop(self):
        self.letter = ""

    def all_letters_width(self):
        return tiles.MAX_LETTERS*self.width

    def letter_index(self):
        if self.fraction_complete >= 0.5:
            return self.letter_ix
        return self.letter_ix - self.column_move_direction

    def draw(self):
        self.surface = self.font.render(self.letter, Letter.ANTIALIAS, Color(Letter.COLOR))

        now_ms = pygame.time.get_ticks()
        remaining_ms = max(0, self.next_column_move_time_ms - now_ms)
        self.fraction_complete = 1.0 - remaining_ms/self.next_interval_ms
        boost_x = self.column_move_direction*(self.width*self.fraction_complete - self.width)
        self.pos[0] = ((SCREEN_WIDTH/2 - self.all_letters_width()/2) +
            self.width*self.letter_ix + boost_x)
        self.rect = self.surface.get_bounding_rect().move(
            self.pos[0], self.pos[1]).inflate(SCREEN_WIDTH, 0)

    def shield_collision(self):
        new_pos = self.height + (self.pos[1] - self.height)/2
        logger.debug(f"---------- {self.height}, {self.pos[1]}, {new_pos}, {self.pos[1] - new_pos}")

        self.pos[1] = self.height + (self.pos[1] - self.height)/2
        self.start_fall_time_ms = pygame.time.get_ticks()

    async def change_letter(self, new_letter):
        self.letter = new_letter
        self.draw()

    async def update(self, window, score):
        if not self.letter:
            self.letter = await get_next_tile(self._session)
        now_ms = pygame.time.get_ticks()
        time_since_last_fall_s = (now_ms - self.start_fall_time_ms)/1000.0
        dy = 0 if score < FREE_SCORE else Letter.INITIAL_SPEED * math.pow(Letter.ACCELERATION,
            time_since_last_fall_s*TICKS_PER_SECOND)
        self.pos[1] += dy

        self.draw()
        # pygame.draw.rect(window, Color("orange"), self.rect)

        window.blit(self.surface, self.pos)

        if now_ms > self.next_column_move_time_ms:
            self.letter_ix = self.letter_ix + self.column_move_direction
            if self.letter_ix < 0 or self.letter_ix >= tiles.MAX_LETTERS:
                self.column_move_direction *= -1
                self.letter_ix = self.letter_ix + self.column_move_direction*2

            percent_complete = ((self.pos[1] - Letter.INITIAL_HEIGHT) /
                (SCREEN_HEIGHT - (Letter.INITIAL_HEIGHT + 25)))
            self.next_interval_ms = 100 + Letter.COLUMN_SHIFT_INTERVAL_MS*percent_complete
            self.next_column_move_time_ms = now_ms + self.next_interval_ms

    def reset(self):
        self.height += Letter.HEIGHT_INCREMENT
        self.pos[1] = self.height
        self.start_fall_time_ms = pygame.time.get_ticks()

async def safeget(session, url):
    async with session.get(url) as response:
        if response.status != 200:
            c = (await response.content.read()).decode()
            logger.error(c)
            raise Exception(f"bad response: {c}")
        return response

class SafeSession:
    def __init__(self, original_context_manager):
        self.original_context_manager = original_context_manager

    async def __aenter__(self):
        response = await self.original_context_manager.__aenter__()
        if response.status != 200:
            c = (await response.content.read()).decode()
            logger.error(c)
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
        self.letter_source = LetterSource(self.letter)
        self.shields = []
        self.in_progress_shield = InProgressShield(self.rack.get_midpoint())
        self.running = False
        self.game_log_f = open("gamelog.csv", "a")
        self.duration_log_f = open("durationlog.csv", "a")
        events.on(f"game.current_score")(self.score_points)

    async def start(self):
        self.letter.start()
        self.score.start()
        self.rack.start()
        self.running = True
        now_s = pygame.time.get_ticks() / 1000
        self.last_letter_time_s = now_s
        self.start_time_s = now_s
        async with SafeSession(self._session.get(
                "http://localhost:8080/start")) as _:
                pass
        os.system('python3 -c "import beepy; beepy.beep(1)"&')

    async def score_points(self, score_and_last_guess):
        score = score_and_last_guess[0]
        last_guess = score_and_last_guess[1]
        self.in_progress_shield.update_letters(last_guess)

        if score <= 0:
            return
        logger.info(f"SCORING POINTS: {score_and_last_guess}")
        now_s = pygame.time.get_ticks()/1000
        self.game_log_f.write(
            f"{now_s-self.start_time_s},{now_s-self.last_letter_time_s},{self.score.score}\n")
        self.game_log_f.flush()
        # print(f"creating shield with word {last_guess}")
        self.shields.append(Shield(last_guess, score))

    async def accept_letter(self):
        async with SafeSession(self._session.get(
            "http://localhost:8080/accept_new_letter",
            params={
                "next_letter": self.letter.letter,
                "position": self.letter.letter_index()
            })) as _:
            self.last_letter_time_s = pygame.time.get_ticks()/1000

    async def stop(self):
        os.system('python3 -c "import beepy; beepy.beep(7)"')
        os.system('say -v "Bad News" "GAME OVER"')

        logger.info("GAME OVER")
        self.rack.stop()
        self.running = False
        now_s = pygame.time.get_ticks() / 1000
        self.duration_log_f.write(
            f"{Letter.ACCELERATION},{Letter.INITIAL_SPEED},{self.score.score},{now_s-self.start_time_s}\n")
        self.duration_log_f.flush()
        async with SafeSession(self._session.get("http://localhost:8080/stop")) as _:
            pass
        logger.info("GAME OVER OVER")

    async def update(self, window):
        await self.letter_source.update(window)
        await self.previous_guesses.update(window)
        await self.remaining_previous_guesses.update(
            window, self.previous_guesses.surface.get_bounding_rect().height)

        if self.running:
            await self.letter.update(window, self.score.score)

        await self.rack.update(window)
        if self.running:
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

        # letter collide with rack
        if self.running and self.letter.rect.y + self.letter.rect.height >= self.rack.rect.y:
            if self.letter.letter == "!":
                await self.stop()

            else:
                await self.accept_letter()

                # logger.info(f"-->{self.letter.height}. {self.letter.rect.height}, {Letter.HEIGHT_INCREMENT}, {self.rack.pos[1]}")
                if self.letter.height + self.letter.rect.height + Letter.HEIGHT_INCREMENT*3 > self.rack.rect.y:
                    logger.info("Switching to !")
                    next_letter = "!"
                else:
                    next_letter = await get_next_tile(self._session)
                await self.letter.change_letter(next_letter)
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
                "http://localhost:8080/get_current_score", lambda s: json.loads(s))))
        tasks.append(asyncio.create_task(
            trigger_events_from_sse(session, "input.previous_guesses",
                "http://localhost:8080/get_previous_guesses", lambda s: s)))
        tasks.append(asyncio.create_task(
            trigger_events_from_sse(session, "input.remaining_previous_guesses",
                "http://localhost:8080/get_remaining_previous_guesses", lambda s: s)))
        while True:
            if start and not game.running:
                await game.start()
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
                        logger.info("RETURN CASE DONE")
                        keyboard_guess = ""
                    elif len(key) == 1:
                        keyboard_guess += key
                        logger.info(f"key: {str(key)} {keyboard_guess}")
                    game.in_progress_shield.update_letters(keyboard_guess)

            screen.fill((0, 0, 0))
            await game.update(screen)
            window.blit(pygame.transform.scale(screen, window.get_rect().size), (0, 0))
            pygame.display.flip()
            await clock.tick(TICKS_PER_SECOND)

        for t in tasks:
            t.cancel()

if __name__ == "__main__":

    # For some reason, pygame doesn't like argparse.
    logger.info(sys.argv)
    auto_start = False
    if len(sys.argv) > 1:
        auto_start = True
    sys.argv[:] = sys.argv[0:]

    # logger.setLevel(logging.DEBUG)

    pygame.init()
    asyncio.run(main(auto_start))
    pygame.quit()
