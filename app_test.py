import random
from io import StringIO
import unittest

import app

class TestCubeGame(unittest.TestCase):
    mock_open = lambda filename, mode: StringIO("\n".join([
        "5 fuzzbox",
        "8 pizzazz",
    ]))


    def test_index(self):
        app.my_open = TestCubeGame.mock_open
        app.init()
        template = app.index()
        self.assertIn("bfouxzz", template)

    def test_sort(self):
        self.assertEqual("abc", app.sort_word("cab"))

if __name__ == '__main__':
    random.seed(1)

    unittest.main()