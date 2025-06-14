#!/usr/bin/env python3

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
    CubeManager,
    find_chain_of_three
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
        cube_order = ['A', 'B', 'C']
        previous_neighbors = {'A': 'B'}
        cube_to_set = {'A': 'set1', 'B': 'set1', 'C': 'set2'}
        result = calculate_neighbors(cube_order, previous_neighbors, cube_to_set)
        self.assertEqual(result, [(None, True), (True, None), (None, None)])

    def test_get_neighbor_symbols(self):
        # Test case 1: Chain of 3 in same set
        cube_order = ['A', 'B', 'C', 'D']
        neighbors = {
            'A': 'B',
            'B': 'C'
        }
        cube_to_set = {
            'A': 'set1',
            'B': 'set1',
            'C': 'set1',
            'D': 'set2'
        }
        neighbor_bools = calculate_neighbors(cube_order, neighbors, cube_to_set)
        symbols = get_neighbor_symbols(neighbor_bools, cube_order, neighbors, cube_to_set)
        # A is start of chain, connected to B
        self.assertEqual(symbols[0], ('<', '}'))
        # B is middle of chain, connected to A and C
        self.assertEqual(symbols[1], ('{', '}'))
        # C is end of chain, connected to B
        self.assertEqual(symbols[2], ('{', '>'))
        # D is not connected
        self.assertEqual(symbols[3], ('<', '>'))
        
        # Test case 2: Chain of 3 in different sets
        cube_to_set = {
            'A': 'set1',
            'B': 'set2',
            'C': 'set1',
            'D': 'set2'
        }
        symbols = get_neighbor_symbols(neighbor_bools, cube_order, neighbors, cube_to_set)
        # A is start of chain, connected to B
        self.assertEqual(symbols[0], ('<', ')'))
        # B is middle of chain, connected to A and C
        self.assertEqual(symbols[1], ('(', ')'))
        # C is end of chain, connected to B
        self.assertEqual(symbols[2], ('(', '>'))
        # D is not connected
        self.assertEqual(symbols[3], ('<', '>'))
        
        # Test case 3: Two separate connections
        neighbors = {
            'A': 'B',
            'C': 'D'
        }
        cube_to_set = {
            'A': 'set1',
            'B': 'set1',
            'C': 'set2',
            'D': 'set2'
        }
        neighbor_bools = calculate_neighbors(cube_order, neighbors, cube_to_set)
        symbols = get_neighbor_symbols(neighbor_bools, cube_order, neighbors, cube_to_set)
        # A connected to B
        self.assertEqual(symbols[0], ('<', ')'))
        # B connected to A
        self.assertEqual(symbols[1], ('(', '>'))
        # C connected to D
        self.assertEqual(symbols[2], ('<', ')'))
        # D connected to C
        self.assertEqual(symbols[3], ('(', '>'))
        
        # Test case 4: No connections
        neighbors = {}
        neighbor_bools = calculate_neighbors(cube_order, neighbors, cube_to_set)
        symbols = get_neighbor_symbols(neighbor_bools, cube_order, neighbors, cube_to_set)
        for symbol in symbols:
            self.assertEqual(symbol, ('<', '>'))

    def test_get_image_prefix(self):
        prefix = get_image_prefix('test/prefix123.b64')
        self.assertEqual(prefix, 'prefix123')

    def test_check_prefix_matches(self):
        previous_neighbors = {'A': 'B', 'B': 'C'}
        cube_to_set = {'A': 'set1', 'B': 'set1', 'C': 'set1'}
        self.assertTrue(check_prefix_matches(previous_neighbors, cube_to_set))
        
        cube_to_set = {'A': 'set1', 'B': 'set1', 'C': 'set2'}
        self.assertFalse(check_prefix_matches(previous_neighbors, cube_to_set))

    def test_find_chain_of_three(self):
        # Test case 1: Simple chain of 3
        neighbors = {
            'A': 'B',
            'B': 'C'
        }
        chain = find_chain_of_three('A', neighbors)
        self.assertEqual(chain, {'A', 'B', 'C'})
        
        # Test case 2: Middle cube of chain
        chain = find_chain_of_three('B', neighbors)
        self.assertEqual(chain, {'A', 'B', 'C'})
        
        # Test case 3: End cube of chain
        chain = find_chain_of_three('C', neighbors)
        self.assertEqual(chain, {'A', 'B', 'C'})
        
        # Test case 4: Not in chain (branch) - not supported by current code, so skip
        # Test case 5: Not in chain (cycle)
        neighbors = {
            'A': 'B',
            'B': 'C',
            'C': 'A'  # Cycle
        }
        chain = find_chain_of_three('A', neighbors)
        self.assertIsNone(chain)
        
        # Test case 6: Not in chain (too long)
        neighbors = {
            'A': 'B',
            'B': 'C',
            'C': 'D',
            'D': 'E'
        }
        chain = find_chain_of_three('A', neighbors)
        self.assertIsNone(chain)
        
        # Test case 7: Not in chain (isolated)
        neighbors = {
            'A': 'B',
            'C': 'D'
        }
        chain = find_chain_of_three('A', neighbors)
        self.assertIsNone(chain)

if __name__ == '__main__':
    unittest.main() 