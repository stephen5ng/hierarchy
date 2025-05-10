#! /usr/bin/env python

import aiomqtt
import asyncio
import os
import logging
import cubes_to_game
import re
import json
import argparse
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_cube_ids() -> List[str]:
    """Read cube IDs from cube_ids.txt into an array."""
    try:
        with open("cube_ids.txt", 'r') as f:
            return [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        logger.error("cube_ids.txt not found")
        raise
    except Exception as e:
        logger.error(f"Error reading cube_ids.txt: {e}")
        raise

def read_content(content_file: str) -> List[str]:
    """
    Read content from a JSON file into an array.
    The file should be in JSON format, e.g.:
    [
        "GENE\\nRAL",
        "COLONEL",
        "MAJOR",
        "CAPTAIN",
        "LIEUTENANT",
        "PRIVATE"
    ]
    """
    try:
        with open(content_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Content file not found: {content_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing {content_file} as JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading {content_file}: {e}")
        raise

def find_consecutive_indexes(s: str) -> list[list[int]]:
    """Find all consecutive sequences of digits in the string."""
    # Find all digits in the string
    numbers = [int(d) for d in re.findall(r'\d', s)]
    print(f"numbers: {numbers}")
    if len(numbers) < 2:
        print(f"No consecutive integers found in: {s}")
        return []
    
    # Find consecutive sequences in the original order
    sequences = []
    current_sequence = []
    
    for i in range(len(numbers) - 1):
        if numbers[i + 1] - numbers[i] == 1:
            if not current_sequence:
                current_sequence.append(numbers[i])
            current_sequence.append(numbers[i + 1])
        else:
            if current_sequence:
                sequences.append(current_sequence)
                current_sequence = []
    
    # Add the last sequence if it exists
    if current_sequence:
        sequences.append(current_sequence)
    
    print(f"Found consecutive sequences: {sequences}")
    return sequences

async def _handle_nfc_message(topic: str, payload: bytes, client: aiomqtt.Client, cube_ids: list[str]) -> None:
    """Handle NFC tag detection messages."""
    cube_id = topic.split('/')[2]
    neighbor_tag = payload.decode()
    results = cubes_to_game.process_tag(cube_id, neighbor_tag)
    print(f"process_tag(cube_id, neighbor_tag): {results}")
    
    # Track which indexes we've handled
    handled_indexes = set()
    
    # Find consecutive digits and publish border lines
    for result in results:
        sequences = find_consecutive_indexes(result)
        for sequence in sequences:
            for i, idx in enumerate(sequence):
                if 0 <= idx < len(cube_ids):
                    topic = f"cube/{cube_ids[idx]}/border_line"
                    if i == 0:
                        message = "["
                    elif i == len(sequence) - 1:
                        message = "]"
                    else:
                        message = "-"
                    await client.publish(topic, message, retain=True)
                    logger.info(f"Published {message} to {topic}")
                    handled_indexes.add(idx)
    
    # Publish spaces to cubes not in sequences
    print(f"handled_numbers: {handled_indexes}")
    for idx in range(6):  # Numbers 1-6
        if idx not in handled_indexes:
            if 0 <= idx < len(cube_ids):
                topic = f"cube/{cube_ids[idx]}/border_line"
                await client.publish(topic, " ", retain=True)
                logger.info(f"Published space to {topic}")

async def _process_message(message: aiomqtt.Message, client: aiomqtt.Client, cube_ids: list[str]) -> None:
    """Process incoming MQTT messages."""
    topic = str(message.topic)
    try:
        if "nfc" in topic:
            await _handle_nfc_message(topic, message.payload, client, cube_ids)
    except Exception as e:
        logger.error(f"Error processing message {topic}: {e}")

async def publish_initial_messages(client: aiomqtt.Client, cube_ids: List[str], content_file: str) -> None:
    """
    Publish initial messages for each cube.
    
    Args:
        client: MQTT client
        cube_ids: List of cube IDs
        content_file: Path to the content file
    """
    content = read_content(content_file)
    for cube_id, content_line in zip(cube_ids, content):
        topic = f"cube/{cube_id}/string"
        await client.publish(topic, content_line, retain=True)
        logger.info(f"Published '{content_line}' to {topic}")

async def start(mqtt_server: str = "localhost", cube_ids: Optional[List[str]] = None, content_file: str = "content.txt") -> None:
    """
    Start the MQTT monitoring process.
    
    Args:
        mqtt_server: MQTT server address
        cube_ids: List of cube IDs, or None to read from file
        content_file: Path to the content file
    """
    if cube_ids is None:
        cube_ids = read_cube_ids()
    
    try:
        async with aiomqtt.Client(mqtt_server) as client:
            # Publish initial messages for each cube
            await publish_initial_messages(client, cube_ids, content_file)
            
            await client.subscribe("cube/#")
            logger.info(f"Connected to MQTT server at {mqtt_server}")
            
            async for message in client.messages:
                await _process_message(message, client, cube_ids)
    except Exception as e:
        logger.error(f"MQTT connection error: {e}")
        raise

def main() -> None:
    """Main entry point for the cube monitoring application."""
    parser = argparse.ArgumentParser(description='Cube monitoring application')
    parser.add_argument('--content', default='content.txt', help='Path to the content file (default: content.txt)')
    parser.add_argument('--mqtt', default='localhost', help='MQTT server address (default: localhost)')
    args = parser.parse_args()
    
    mqtt_server = os.environ.get("MQTT_SERVER", args.mqtt)
    cube_ids = read_cube_ids()
    logger.info(f"Loaded {len(cube_ids)} cube IDs")
    
    try:
        asyncio.run(start(mqtt_server, cube_ids, args.content))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    cubes_to_game.init("cube_ids.txt", "tag_ids.txt")
    main()
