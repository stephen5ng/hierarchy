#!/usr/bin/env python3

import unittest
import app
import json
import cubes_to_game
import tiles

class FakeResponse:
    def __init__(self, value):
        self.__value = value

    def json(self):
        return self.__value


written = []
async def writer(s):
    global written
    written.append(s)

class TestCubesToGame(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        global written
        written = []

    def test_existing_chain(self):
        rack = tiles.Rack("ABC")
        cubes_to_game.TAGS_TO_CUBES = {
            "TAG_0": "BLOCK_0",
            "TAG_1": "BLOCK_1",
            "TAG_2": "BLOCK_2"
        }
        cubes_to_game.cubes_to_letters = {
            "BLOCK_0": "A",
            "BLOCK_1": "B",
            "BLOCK_2": "C"
        }
        cubes_to_game.cubes_to_tiles["BLOCK_0"] = str(rack._tiles[0].id)
        cubes_to_game.cubes_to_tiles["BLOCK_1"] = str(rack._tiles[1].id)
        cubes_to_game.cubes_to_tiles["BLOCK_2"] = str(rack._tiles[2].id)
        cubes_to_game.cube_chain["BLOCK_0"] = "BLOCK_1"
        result = cubes_to_game.process_tag("BLOCK_1", "TAG_2")
        self.assertEqual(("ABC", "0,1,2"), result)

    def test_two_chain(self):
        cubes_to_game.cube_chain = {}
        cubes_to_game.TAGS_TO_CUBES = {
            "TAG_0": "BLOCK_0",
            "TAG_1": "BLOCK_1"
        }
        cubes_to_game.cubes_to_letters = {
            "BLOCK_0": "A",
            "BLOCK_1": "B"
        }
        result = cubes_to_game.process_tag("BLOCK_0", "TAG_1")
        self.assertEqual(("AB", "0,1"), result)

    async def test_load_rack(self):
        cubes_to_game.cubes_to_letters = {}
        cubes_to_game.TAGS_TO_CUBES = {
            "tag_0": "cube_0",
            "tag_1": "cube_1",
            "tag_2": "cube_2",
            "tag_3": "cube_3",
            "tag_4": "cube_4",
            "tag_5": "cube_5",
            "tag_6": "cube_6",
            }
        app.player_rack = tiles.Rack("ABCDEFG")
        await cubes_to_game.load_rack({"0": "A", "1": "B", "2": "C", "3": "D", "4": "E", "5": "F"}, writer)
        self.assertEqual(
             {'cube_0': 'A', 'cube_1': 'B', 'cube_2': 'C', 'cube_3': 'D', 'cube_4': 'E', 'cube_5': 'F'},
            cubes_to_game.cubes_to_letters)
        self.assertEqual(
             {'0': 'cube_0', '1': 'cube_1', '2': 'cube_2', '3': 'cube_3', '4': 'cube_4', '5': 'cube_5'},
            cubes_to_game.tiles_to_cubes)
        self.assertEqual(
            ['cube_0:A\n',
             'cube_1:B\n',
             'cube_2:C\n',
             'cube_3:D\n',
             'cube_4:E\n',
             'cube_5:F\n'],
            written)

if __name__ == '__main__':
    unittest.main()