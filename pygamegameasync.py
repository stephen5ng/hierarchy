#!/usr/bin/env python3

from aiohttp import web
from aiohttp_sse import sse_response
import asyncio
from datetime import datetime
import json
import pygame

from pygameasync import Clock, EventEngine, WebFrontend

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


class CubeWebFrontend(WebFrontend):
    def __init__(self, port=8081):
        super().__init__(port)

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