#! /usr/bin/env python

import pytest
import asyncio
import aiomqtt
import hierarchy
from unittest.mock import AsyncMock, patch, MagicMock

def test_find_consecutive_numbers():
    """
    Test the find_consecutive_numbers function with various input patterns.
    The function should:
    - Return empty list for no sequences
    - Return sorted sequences by first number
    - Handle single and multiple sequences
    - Handle non-consecutive numbers
    """
    test_cases = [
        # Single consecutive sequence
        ("12", [[1, 2]]),
        ("234", [[2, 3, 4]]),
        ("123", [[1, 2, 3]]),

        # Multiple consecutive sequences
        ("1245", [[1, 2], [4, 5]]),
        ("123567", [[1, 2, 3], [5, 6, 7]]),
        
        # Non-consecutive numbers
        ("13", []),
        ("135", []),
        ("246", []),

        # Single number
        ("1", []),
        ("9", []),

        # No numbers
        ("abc", []),
        ("", []),
        
        # Numbers in wrong order
        ("21", []),
        ("321", []),
        ("54321", []),
    ]
    
    for input_str, expected in test_cases:
        result = hierarchy.find_consecutive_numbers(input_str)
        assert result == expected, f"Failed for input '{input_str}': expected {expected}, got {result}"

if __name__ == "__main__":
    pytest.main([__file__]) 