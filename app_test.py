import unittest
import app
import random

class TestCubeGame(unittest.TestCase):

    def test_index(self):
        app.init()
        template = app.index()
        self.assertIn("carven", template)

if __name__ == '__main__':
    random.seed(1)

    unittest.main()