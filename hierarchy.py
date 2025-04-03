#! /usr/bin/env python

import aiomqtt
import asyncio
import os
import logging
import cubes_to_game
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONTENT = [
    "GENERAL",
    "COLONEL",
    "MAJOR",
    "CAPTAIN",
    "LIEUTENANT",
    "PRIVATE"
]

def read_cube_ids() -> list[str]:
    """Read cube IDs from cube_ids.txt into an array."""
    with open("cube_ids.txt", 'r') as f:
        return [line.strip() for line in f.readlines()]

def find_consecutive_numbers(s: str) -> list[list[int]]:
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
    
    # Track which numbers we've handled
    handled_numbers = set()
    
    # Find consecutive digits and publish border lines
    for result in results:
        sequences = find_consecutive_numbers(result)
        for sequence in sequences:
            for i, number in enumerate(sequence):
                idx = number  # Convert to index
                if 0 <= idx < len(cube_ids):
                    topic = f"cube/{cube_ids[idx]}/border_line"
                    if i == 0:
                        message = "["
                    elif i == len(sequence) - 1:
                        message = "]"
                    else:
                        message = "-"
                    await client.publish(topic, message)
                    logger.info(f"Published {message} to {topic}")
                    handled_numbers.add(number)
    
    # Publish spaces to cubes not in sequences
    for number in range(1, 7):  # Numbers 1-6
        if number not in handled_numbers:
            idx = number - 1
            if 0 <= idx < len(cube_ids):
                topic = f"cube/{cube_ids[idx]}/border_line"
                await client.publish(topic, " ")
                logger.info(f"Published space to {topic}")

async def _process_message(message: aiomqtt.Message, client: aiomqtt.Client, cube_ids: list[str]) -> None:
    """Process incoming MQTT messages."""
    topic = str(message.topic)
    try:
        if "nfc" in topic:
            await _handle_nfc_message(topic, message.payload, client, cube_ids)
    except Exception as e:
        logger.error(f"Error processing message {topic}: {e}")

async def publish_initial_messages(client: aiomqtt.Client, cube_ids: list[str]) -> None:
    """Publish initial messages for each cube."""
    for cube_id, content in zip(cube_ids, CONTENT):
        topic = f"cube/{cube_id}/string"
        await client.publish(topic, content)
        logger.info(f"Published '{content}' to {topic}")

async def start(mqtt_server: str = "localhost", cube_ids: list[str] = None) -> None:
    """Start the MQTT monitoring process."""
    try:
        async with aiomqtt.Client(mqtt_server) as client:
            # Publish initial messages for each cube
            await publish_initial_messages(client, cube_ids)
            
            await client.subscribe("cube/#")
            logger.info(f"Connected to MQTT server at {mqtt_server}")
            
            async for message in client.messages:
                await _process_message(message, client, cube_ids)
    except Exception as e:
        logger.error(f"MQTT connection error: {e}")
        raise

def main():
    """Main entry point for the cube monitoring application."""
    mqtt_server = os.environ.get("MQTT_SERVER", "localhost")
    cube_ids = read_cube_ids()
    logger.info(f"Loaded {len(cube_ids)} cube IDs")
    
    try:
        asyncio.run(start(mqtt_server, cube_ids))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    cubes_to_game.init("cube_ids.txt", "tag_ids.txt")
    main()
