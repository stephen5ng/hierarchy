#! /usr/bin/env python

import aiomqtt
import asyncio
import os
import logging
import cubes_to_game

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_cube_ids() -> list[str]:
    """Read cube IDs from cube_ids.txt into an array."""
    with open("cube_ids.txt", 'r') as f:
        return [line.strip() for line in f.readlines()]

async def _handle_nfc_message(topic: str, payload: bytes) -> None:
    """Handle NFC tag detection messages."""
    cube_id = topic.split('/')[2]
    neighbor_tag = payload.decode()
    print(f"process_tag(cube_id, neighbor_tag): {cubes_to_game.process_tag(cube_id, neighbor_tag)}")

async def _process_message(message: aiomqtt.Message) -> None:
    """Process incoming MQTT messages."""
    topic = str(message.topic)
    try:
        if "nfc" in topic:
            await _handle_nfc_message(topic, message.payload)
    except Exception as e:
        logger.error(f"Error processing message {topic}: {e}")

async def start(mqtt_server: str = "localhost") -> None:
    """Start the MQTT monitoring process."""
    try:
        async with aiomqtt.Client(mqtt_server) as client:
            await client.subscribe("cube/#")
            logger.info(f"Connected to MQTT server at {mqtt_server}")
            
            async for message in client.messages:
                await _process_message(message)
    except Exception as e:
        logger.error(f"MQTT connection error: {e}")
        raise

def main():
    """Main entry point for the cube monitoring application."""
    mqtt_server = os.environ.get("MQTT_SERVER", "localhost")
    cube_ids = read_cube_ids()
    logger.info(f"Loaded {len(cube_ids)} cube IDs")
    
    try:
        asyncio.run(start(mqtt_server))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    cubes_to_game.init("cube_ids.txt", "tag_ids.txt")
    main()
