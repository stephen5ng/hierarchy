#!/usr/bin/env python3

import unittest
import app
import json
import cubes_to_game
import io
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
        rack = tiles.Rack("ABCD")
        cubes_to_game.cubes_to_tiles["BLOCK_0"] = str(rack._tiles[0].id)
        cubes_to_game.cubes_to_tiles["BLOCK_1"] = str(rack._tiles[1].id)
        cubes_to_game.cubes_to_tiles["BLOCK_2"] = str(rack._tiles[2].id)
        cubes_to_game.cubes_to_tiles["BLOCK_3"] = str(rack._tiles[3].id)
        cubes_to_game.TAGS_TO_CUBES = {
            "TAG_0": "BLOCK_0",
            "TAG_1": "BLOCK_1",
            "TAG_2": "BLOCK_2",
            "TAG_3": "BLOCK_3"
        }
        cubes_to_game.cube_chain = {}
        cubes_to_game.cubes_to_letters = {}
        tiles.MAX_LETTERS = 5

    def test_two_chain(self):
        self.assertEqual(["01"], cubes_to_game.process_tag("BLOCK_0", "TAG_1"))

    def test_multiple_chains(self):
        cubes_to_game.cube_chain["BLOCK_0"] = "BLOCK_1"
        self.assertEqual(['01', '23'], cubes_to_game.process_tag("BLOCK_2", "TAG_3"))

    def test_existing_chain(self):
        cubes_to_game.cube_chain["BLOCK_0"] = "BLOCK_1"
        self.assertEqual(["012"], cubes_to_game.process_tag("BLOCK_1", "TAG_2"))

    def test_remove_back_pointer(self):
        cubes_to_game.cube_chain["BLOCK_0"] = "BLOCK_1"
        cubes_to_game.initialize_arrays()
        self.assertEqual(["21"], cubes_to_game.process_tag("BLOCK_2", "TAG_1"))

    def test_break_2_chain(self):
        cubes_to_game.cube_chain["BLOCK_0"] = "BLOCK_1"
        self.assertEqual(["10"], cubes_to_game.process_tag("BLOCK_1", "TAG_0"))

    def test_break_3_chain(self):
        cubes_to_game.cube_chain["BLOCK_0"] = "BLOCK_1"
        cubes_to_game.cube_chain["BLOCK_1"] = "BLOCK_2"
        self.assertEqual(["201"], cubes_to_game.process_tag("BLOCK_2", "TAG_0"))

    def test_delete_link(self):
        cubes_to_game.cube_chain["BLOCK_0"] = "BLOCK_1"
        cubes_to_game.cube_chain["BLOCK_1"] = "BLOCK_2"
        self.assertEqual(["12"], cubes_to_game.process_tag("BLOCK_0", None))

    def test_delete_link_nothing_left(self):
        self.assertEqual([], cubes_to_game.process_tag("BLOCK_0", None))

    def test_bad_tag(self):
        self.assertEqual([], cubes_to_game.process_tag("BLOCK_0", "TAG_Z"))

    def test_sender_is_target(self):
        self.assertEqual([], cubes_to_game.process_tag("BLOCK_0", "TAG_0"))

    def test_get_tags_to_cubes(self):
        cubes_file = io.StringIO("CUBE_0000000\nCUBE_0000001\nCUBE_0000002")
        tags_file = io.StringIO("TAG_0000000\nTAG_0000001\nTAG_0000002")
        result = cubes_to_game.get_tags_to_cubes_f(cubes_file, tags_file)
        expected = {
            'TAG_0000000': 'CUBE_0000000',
            'TAG_0000001': 'CUBE_0000001',
            'TAG_0000002': 'CUBE_0000002'}
        print(f"{result}")
        self.assertEqual(expected, result)

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
        cubes_to_game.initialize_arrays()
        await cubes_to_game.load_rack_only(
            {"0": "A", "1": "B", "2": "C", "3": "D", "4": "E", "5": "F"}, writer)
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