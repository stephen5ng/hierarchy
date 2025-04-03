#! /usr/bin/env python

import pytest
import asyncio
import aiomqtt
import hierarchy
from unittest.mock import AsyncMock, patch, MagicMock

def test_find_consecutive_numbers():
    # Test cases
    test_cases = [
        # Basic consecutive numbers
        ("12", [[1, 2]]),
        ("234", [[2, 3, 4]]),
        ("123", [[1, 2, 3]]),

        # Incorrect order
        ("21", []),
        
        # Non-consecutive numbers
        ("13", []),
        ("135", []),

        # Single number
        ("1", []),

        # Multiple consecutive sequences
        ("1245", [[1, 2], [4, 5]]),
        
    ]
    
    for input_str, expected in test_cases:
        result = hierarchy.find_consecutive_numbers(input_str)
        assert result == expected, f"Failed for input '{input_str}': expected {expected}, got {result}"

if __name__ == "__main__":
    pytest.main([__file__]) 