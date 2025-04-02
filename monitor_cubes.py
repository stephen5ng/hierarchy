#! /usr/bin/env python

import aiomqtt
import asyncio
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
import cubes_to_game

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CubeState:
    letter: str = ''
    neighbor_tag: str = ''
    neighbor_cube: str = ''

class CubeMonitor:
    def __init__(self, mqtt_server: str = "localhost"):
        self.mqtt_server = mqtt_server
        self.cubes: List[str] = []
        self.tags: List[str] = []
        self.tags_to_cubes: Dict[str, str] = {}
        self.cube_states: Dict[str, CubeState] = {}
        
        # Load configuration
        self._load_cube_config()
        
    def _load_cube_config(self) -> None:
        """Load cube and tag IDs from configuration files."""
        try:
            self.cubes = self._read_file("cube_ids.txt")
            self.tags = self._read_file("tag_ids.txt")
            
            # Create tag to cube mapping
            for cube, tag in zip(self.cubes, self.tags):
                self.tags_to_cubes[tag] = cube
                self.cube_states[cube] = CubeState()
                
            logger.info(f"Loaded {len(self.cubes)} cubes and {len(self.tags)} tags")
        except Exception as e:
            logger.error(f"Failed to load cube configuration: {e}")
            raise

    @staticmethod
    def _read_file(filename: str) -> List[str]:
        """Read lines from a file and return them as a list of strings."""
        try:
            with open(filename, 'r') as f:
                return [line.strip() for line in f.readlines()]
        except Exception as e:
            logger.error(f"Failed to read file {filename}: {e}")
            raise

    async def _handle_letter_message(self, topic: str, payload: bytes) -> None:
        """Handle letter assignment messages."""
        cube_id = topic.split('/')[1]
        if cube_id in self.cube_states:
            self.cube_states[cube_id].letter = payload.decode()
            logger.info(f"Letter assigned to cube {cube_id}: {payload.decode()}")

    async def _handle_nfc_message(self, topic: str, payload: bytes) -> None:
        """Handle NFC tag detection messages."""
        cube_id = topic.split('/')[2]
        neighbor_tag = payload.decode()
        logger.info(f"process_tag(cube_id, neighbor_tag): {cubes_to_game.process_tag(cube_id, neighbor_tag)}")
        if cube_id in self.cube_states:
            self.cube_states[cube_id].neighbor_tag = neighbor_tag
            self.cube_states[cube_id].neighbor_cube = self.tags_to_cubes.get(neighbor_tag, '')
            logger.info(f"NFC tag detected for cube {cube_id}: {neighbor_tag}")

    def _print_cube_state(self) -> None:
        """Print the current state of all cubes."""
        for cube in self.cubes:
            state = self.cube_states[cube]
            print(f"{cube}[{state.letter}]", end="")
            
            if state.neighbor_tag:
                print(f"-> {state.neighbor_tag},{state.neighbor_cube}", end="")
                if state.neighbor_cube:
                    print(f"[{self.cube_states[state.neighbor_cube].letter}]", end="")
            print()

    async def _process_message(self, message: aiomqtt.Message) -> None:
        """Process incoming MQTT messages."""
        topic = str(message.topic)
        try:
            if "letter" in topic:
                await self._handle_letter_message(topic, message.payload)
            elif "nfc" in topic:
                await self._handle_nfc_message(topic, message.payload)
            
            self._print_cube_state()
            print()  # Add blank line for readability
        except Exception as e:
            logger.error(f"Error processing message {topic}: {e}")

    async def start(self) -> None:
        """Start the MQTT monitoring process."""
        try:
            async with aiomqtt.Client(self.mqtt_server) as client:
                await client.subscribe("cube/#")
                logger.info(f"Connected to MQTT server at {self.mqtt_server}")
                
                async for message in client.messages:
                    await self._process_message(message)
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            raise

def main():
    """Main entry point for the cube monitoring application."""
    mqtt_server = os.environ.get("MQTT_SERVER", "localhost")
    monitor = CubeMonitor(mqtt_server)
    
    try:
        asyncio.run(monitor.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    cubes_to_game.init("cube_ids.txt", "tag_ids.txt")
    main()
