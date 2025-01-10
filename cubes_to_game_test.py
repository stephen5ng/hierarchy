#!/usr/bin/env python3

import aiomqtt
import io
import json
import unittest

import app
import cubes_to_game
from pygameasync import events
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
        async def nop(*a):
            pass

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
            "TAG_3": "BLOCK_3",
            "TAG_4": "BLOCK_4",
            "TAG_5": "BLOCK_5",
            "TAG_6": "BLOCK_6",
        }
        cubes_to_game.cube_chain = {}
        cubes_to_game.cubes_to_letters = {}
        cubes_to_game.last_guess_tiles: List[str] = []
        events.on("game.current_score")(nop)
        tiles.MAX_LETTERS = 5
        self.client = Client([])
        the_app = app.App(self.client)
        # the_app.init()
        # app.index()
        cubes_to_game.initialize_arrays()

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
        self.assertEqual(expected, result)

    async def test_process_cube_guess(self):
        await cubes_to_game.process_cube_guess(self.client, "BLOCK_0:TAG_1")
        self.assertEqual([], self.client.published)

    async def test_load_rack(self):
        cubes_to_game.cubes_to_letters = {}
        app.player_rack = tiles.Rack("ABCDEFG")
        cubes_to_game.initialize_arrays()
        cubes_to_game.last_guess_tiles = ['01']
        await cubes_to_game.load_rack(self.client,
            {"0": "A", "1": "B", "2": "C", "3": "D", "4": "E", "5": "F"})
        self.assertEqual(
            [('cube/BLOCK_0', 'A'),
             ('cube/BLOCK_1', 'B'),
             ('cube/BLOCK_2', 'C'),
             ('cube/BLOCK_3', 'D'),
             ('cube/BLOCK_4', 'E'),
             ('cube/BLOCK_5', 'F')],
            self.client.published)

    async def test_load_rack_only(self):
        cubes_to_game.cubes_to_letters = {}
        app.player_rack = tiles.Rack("ABCDEFG")
        cubes_to_game.initialize_arrays()

        await cubes_to_game.load_rack_only(self.client,
            {"0": "A", "1": "B", "2": "C", "3": "D", "4": "E", "5": "F"})

        self.assertEqual(
             {'BLOCK_0': 'A', 'BLOCK_1': 'B', 'BLOCK_2': 'C', 'BLOCK_3': 'D', 'BLOCK_4': 'E', 'BLOCK_5': 'F'},
            cubes_to_game.cubes_to_letters)
        self.assertEqual(
             {'0': 'BLOCK_0', '1': 'BLOCK_1', '2': 'BLOCK_2', '3': 'BLOCK_3', '4': 'BLOCK_4', '5': 'BLOCK_5'},
            cubes_to_game.tiles_to_cubes)
        self.assertEqual(
            [('cube/BLOCK_0', 'A'),
             ('cube/BLOCK_1', 'B'),
             ('cube/BLOCK_2', 'C'),
             ('cube/BLOCK_3', 'D'),
             ('cube/BLOCK_4', 'E'),
             ('cube/BLOCK_5', 'F')],
            self.client.published)

    async def test_guess_word_based_on_cubes(self):
        client = Client([])
        await cubes_to_game.guess_word_based_on_cubes("BLOCK_0", "TAG_1", client)
        self.assertEqual([], client.published)

    async def test_guess_last_tiles(self):
        serial_output = []
        async def write_to_serial(writer, content):
            serial_output.append(content)
        cubes_to_game.tiles_to_cubes = {
            "1" : "cube_1",
            "2" : "cube_2",
            "3" : "cube_3"
        }
        cubes_to_game.write_to_serial = write_to_serial
        cubes_to_game.last_guess_tiles = ["123"]
        client = Client(None)
        await cubes_to_game.guess_last_tiles()
        self.assertEqual([], client.published)

    async def test_flash_good_words(self):
        cubes_to_game.tiles_to_cubes = {
            "1" : "cube_1",
            "2" : "cube_2",
            "3" : "cube_3"
        }
        client = Client([Message(aiomqtt.Topic("app/good_word"))])
        await cubes_to_game.flash_good_words(client, "123")
        self.assertEqual([('cube/cube_1/flash',), ('cube/cube_2/flash',), ('cube/cube_3/flash',)],
            client.published)

class Message:
    def __init__(self, topic):
        self.topic = topic
        self.topic_ix = 0

class Client:
    def __init__(self, messages):
        self.published = []
        self.messages = self._messages_iter(messages)

    async def _messages_iter(self, messages):
        for message in messages:
            yield message

    async def publish(self, topic, *payload):
        self.published.append((topic, *payload))

if __name__ == '__main__':
    unittest.main()
