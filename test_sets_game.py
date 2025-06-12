import unittest
import os
import tempfile
import shutil
from sets_game import (
    load_cube_order,
    load_tag_order,
    calculate_neighbors,
    get_neighbor_symbols,
    check_prefix_matches,
    get_image_prefix,
    CubeManager
)

class TestSetsGame(unittest.TestCase):
    def setUp(self):
        # Create temporary test files
        self.test_dir = tempfile.mkdtemp()
        self.gen_images_dir = os.path.join(self.test_dir, 'gen_images_sets')
        os.makedirs(self.gen_images_dir)
        
        # Create test cube_ids.txt
        with open(os.path.join(self.test_dir, 'cube_ids.txt'), 'w') as f:
            f.write('cube1\ncube2\ncube3\ncube4\ncube5\ncube6\ncube7\ncube8\n')
            
        # Create test tag_ids.txt
        with open(os.path.join(self.test_dir, 'tag_ids.txt'), 'w') as f:
            f.write('tag1\ntag2\ntag3\ntag4\ntag5\ntag6\ntag7\ntag8\n')
            
        # Create test image sets with files
        self.test_sets = ['fruits', 'vegetables']
        for set_name in self.test_sets:
            set_dir = os.path.join(self.gen_images_dir, set_name)
            os.makedirs(set_dir)
            # Create some test files in each set
            for item in ['apple', 'orange', 'banana', 'pear', 'grape', 'melon'] if set_name == 'fruits' else ['carrot', 'peas', 'corn', 'potato', 'celery', 'lettuce']:
                with open(os.path.join(set_dir, f'{set_name}.{item}.b64'), 'w') as f:
                    pass  # Empty file is fine for testing
        
        # Change to test directory
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        # Clean up
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_load_cube_order(self):
        cubes = load_cube_order()
        self.assertEqual(len(cubes), 6)
        self.assertEqual(cubes, ['cube1', 'cube2', 'cube3', 'cube4', 'cube5', 'cube6'])

    def test_load_tag_order(self):
        tags = load_tag_order()
        self.assertEqual(len(tags), 6)
        self.assertEqual(tags, ['tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6'])

    def test_calculate_neighbors(self):
        cube_order = ['cube1', 'cube2', 'cube3', 'cube4', 'cube5', 'cube6']
        previous_neighbors = {
            'cube1': 'cube2',
            'cube2': 'cube3',
            'cube3': 'cube4',
            'cube4': 'cube5',
            'cube5': 'cube6'
        }
        result = calculate_neighbors(cube_order, previous_neighbors)
        expected = [(None, True), (True, True), (True, True), (True, True), (True, True), (True, None)]
        self.assertEqual(result, expected)

    def test_get_neighbor_symbols(self):
        neighbor_statuses = [
            (None, True),
            (True, True),
            (True, None)
        ]
        result = get_neighbor_symbols(neighbor_statuses)
        expected = [('<', '}'), ('{', '}'), ('{', '>')]
        self.assertEqual(result, expected)

    def test_get_image_prefix(self):
        prefix = get_image_prefix('test/prefix123.b64')
        self.assertEqual(prefix, 'prefix123')

    def test_check_prefix_matches(self):
        cube_order = ['cube1', 'cube2', 'cube3', 'cube4', 'cube5', 'cube6']
        previous_neighbors = {
            'cube1': 'cube2',
            'cube2': 'cube3',
            'cube3': 'cube4',
            'cube4': 'cube5',
            'cube5': 'cube6'
        }
        
        # Test with matching prefixes (all from same set)
        cube_to_filename = {
            'cube1': 'fruits.apple.b64',
            'cube2': 'fruits.orange.b64',
            'cube3': 'fruits.banana.b64',
            'cube4': 'fruits.pear.b64',
            'cube5': 'fruits.grape.b64',
            'cube6': 'fruits.melon.b64'
        }
        self.assertTrue(check_prefix_matches(cube_order, previous_neighbors, 'fruits', cube_to_filename))
        
        # Test with non-matching prefixes (mixed sets)
        cube_to_filename['cube1'] = 'vegetables.carrot.b64'
        self.assertFalse(check_prefix_matches(cube_order, previous_neighbors, 'fruits', cube_to_filename))

    def test_select_random_files(self):
        cube_manager = CubeManager(None)  # Client not needed for this test
        # Test selecting 3 files from a set
        files = cube_manager._select_random_files('fruits', 3)
        self.assertEqual(len(files), 3)
        self.assertTrue(all(f.startswith('fruits.') for f in files))
        
        # Test error when not enough files
        with self.assertRaises(ValueError):
            cube_manager._select_random_files('fruits', 10)

if __name__ == '__main__':
    unittest.main() 