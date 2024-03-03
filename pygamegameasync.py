#!/usr/bin/env python3

from aiohttp import web
from aiohttp_sse import sse_response
import asyncio
from datetime import datetime
import json
import pygame


class Clock:
    def __init__(self, time_func=pygame.time.get_ticks):
        self.time_func = time_func
        self.last_tick = time_func() or 0

    async def tick(self, fps=0):
        if 0 >= fps:
            return

        end_time = (1.0 / fps) * 1000
        current = self.time_func()
        time_diff = current - self.last_tick
        delay = (end_time - time_diff) / 1000

        self.last_tick = current
        if delay < 0:
            delay = 0

        await asyncio.sleep(delay)

class EventEngine:
    def __init__(self):
        self.listeners = {}

    def on(self, event):
        if event not in self.listeners:
            self.listeners[event] = []

        def wrapper(func, *args):
            self.listeners[event].append(func)
            return func

        return wrapper

    # this function is purposefully not async
    # code calling this will do so in a "fire-and-forget" manner, and shouldn't be slowed down by needing to await a result
    def trigger(self, event, *args, **kwargs):
        asyncio.create_task(self.async_trigger(event, *args, **kwargs))

    # whatever gets triggered is just added to the current asyncio event loop, which we then trust to run eventually
    async def async_trigger(self, event, *args, **kwargs):
        if event in self.listeners:
            handlers = [func(*args, **kwargs) for func in self.listeners[event]]

            # schedule all listeners to run
            return await asyncio.gather(*handlers)


events = EventEngine()


class Player:
    player_count = 0

    def __init__(self, color):
        Player.player_count += 1
        self.player_id = Player.player_count

        self.surface = self.original_surface = self.create_surface(color)
        self.pos = [10, 10]
        self.movement_intensity = 10
        self.register_handlers()

    def create_surface(self, color):
        surf = pygame.Surface((25, 25), pygame.SRCALPHA)
        surf.fill(color)
        return surf

    def register_handlers(self):
        events.on(f"input.move_up.{self.player_id}")(self.move_up)
        events.on(f"input.move_right.{self.player_id}")(self.move_right)

    async def move_right(self, amount):
        self.pos[0] += amount * self.movement_intensity

    async def move_up(self, amount):
        # 0 == top of screen, so 'up' is negative
        self.pos[1] -= amount * self.movement_intensity

    async def update(self, window):
        window.blit(self.surface, self.pos)


class Game:
    player_colors = [(155, 155, 0), (0, 155, 155), (155, 0, 155)]

    def __init__(self):
        self.players = []
        events.on("player.add")(self.create_player)

    async def create_player(self):
        color = self.player_colors[len(self.players) % len(self.player_colors)]
        new_player = Player(color)
        self.players.append(new_player)
        return new_player

    async def update(self, window):
        for player in self.players:
            await player.update(window)


class WebFrontend:
    def __init__(self, port=8081):
        self.port = port
        self.runner = None
        self.app = web.Application()

        self.app.add_routes(
            [
                web.get("/hello", self.serve_sse)
            ]
        )

    async def serve_sse(self, request: web.Request) -> web.StreamResponse:
        async with sse_response(request) as resp:
            while resp.is_connected():
                time_dict = {"time": f"Server Time : {datetime.now()}"}
                data = json.dumps(time_dict, indent=2)
                print(data)
                await resp.send(data)
                await asyncio.sleep(1)
        return resp

    async def startup(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "localhost", self.port)
        await site.start()

    async def shutdown(self):
        if self.runner:
            await self.runner.cleanup()


async def main():
    window = pygame.display.set_mode((500, 500))
    web_server = WebFrontend()
    await web_server.startup()

    game = Game()
    local_player = (await events.async_trigger("player.add"))[0]
    local_player_id = local_player.player_id

    clock = Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    events.trigger(f"input.move_right.{local_player_id}", -1)
                elif ev.key == pygame.K_RIGHT:
                    events.trigger(f"input.move_right.{local_player_id}", +1)
                elif ev.key == pygame.K_UP:
                    events.trigger(f"input.move_up.{local_player_id}", +1)
                elif ev.key == pygame.K_DOWN:
                    events.trigger(f"input.move_up.{local_player_id}", -1)

        window.fill((0, 0, 0))
        await game.update(window)
        pygame.display.flip()

        await clock.tick(30)

if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()