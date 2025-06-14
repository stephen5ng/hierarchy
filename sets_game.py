#!/usr/bin/env python3

import asyncio
import aiomqtt
import glob
import os
import random
import pygame

GEN_IMAGES_DIR = 'gen_images_sets'

def load_cube_order():
    """Load the first 6 cube IDs from cube_ids.txt."""
    with open('cube_ids.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()][:6]

def load_tag_order():
    """Load the first 6 tag IDs from tag_ids.txt."""
    with open('tag_ids.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()][:6]

def get_image_prefix(b64_file):
    """Extract the prefix from a .b64 filename."""
    return os.path.basename(b64_file).split('.')[0]

async def publish_images(client, cube_order, cube_to_file):
    """Publish images to their corresponding cubes via MQTT.
    
    Args:
        client: MQTT client
        cube_order: List of cube IDs in order
        cube_to_file: Dict mapping cube_id to (set_name, filename) tuple
    """
    print("Publishing images")
    # Publish each image to its corresponding cube
    for cube_id in cube_order:
        if cube_id not in cube_to_file:
            continue
        set_name, filename = cube_to_file[cube_id]
        b64_file = os.path.join(GEN_IMAGES_DIR, set_name, filename)
        with open(b64_file, 'r') as f:
            image_data = f.read().strip()
        topic = f"cube/{cube_id}/image"
        await client.publish(topic, image_data, retain=True)
        print(f"Published image from {set_name}/{filename} to {topic}")

def calculate_neighbors(cube_order, previous_neighbors, cube_to_set):
    """Calculate which cubes are connected and in the same set.
    
    Args:
        cube_order: List of cube IDs in order
        previous_neighbors: Dict mapping cube_id to its neighbor
        cube_to_set: Dict mapping cube_id to its set name
        
    Returns:
        A list where each element corresponds to a cube in cube_order and is a tuple (left_connected, right_connected):
        - left_connected is True if the cube is connected to its left neighbor (i-1) and both are in the same set, otherwise None.
        - right_connected is True if the cube is connected to its right neighbor (i+1) and both are in the same set, otherwise None.
    """
    result = [(None, None) for _ in cube_order]
    
    # For each cube in order
    for i, cube_id in enumerate(cube_order):
        # Check right side
        right_neighbor = previous_neighbors.get(cube_id)
        if right_neighbor:
            # Check if cubes are in the same set
            same_set = cube_to_set.get(cube_id) == cube_to_set.get(right_neighbor)
            result[i] = (result[i][0], same_set)
            
            # Update left side of the right neighbor
            right_neighbor_index = cube_order.index(right_neighbor)
            result[right_neighbor_index] = (same_set, result[right_neighbor_index][1])
    
    return result

def get_symbol(connected, is_three_chain, all_same_set, is_left):
    """Get the border symbol for a cube's side.
    
    Args:
        connected: Whether this side is connected to a neighbor
        is_three_chain: Whether this cube is part of a chain of 3
        all_same_set: Whether all cubes in the chain are in the same set
        is_left: Whether this is the left side of the cube
        
    Returns:
        A single character symbol: '{', '}', '(', ')', '<', '>', '[', or ']'
    """
    if not connected:
        return "<" if is_left else ">"
    symbol_map = {
        (True, True, True): ("{", "}"),
        (True, True, False): ("(", ")"),
        (True, False, False): ("(", ")"),
    }
    left_right = symbol_map.get((connected, is_three_chain, all_same_set), ("<", ">"))
    return left_right[0] if is_left else left_right[1]

def get_neighbor_symbols(neighbor_statuses, cube_order, previous_neighbors, cube_to_set):
    """Calculate border symbols for all cubes.
    
    A cube is part of a chain of 3 if it's in a set that has exactly 3 connected cubes.
    Border symbols indicate whether cubes are connected and if they form a chain of 3.
    
    Args:
        neighbor_statuses: List of (left_connected, right_connected) tuples from calculate_neighbors
        cube_order: List of cube IDs in order
        previous_neighbors: Dict mapping cube_id to its neighbor
        cube_to_set: Dict mapping cube_id to its set name
        
    Returns:
        List of (left_symbol, right_symbol) tuples for each cube
    """
    # Track cubes in each set that have neighbors in the same set
    set1_cubes = set()
    set2_cubes = set()
    
    # One pass through neighbors to find connected cubes in same set
    for cube, neighbor in previous_neighbors.items():
        if cube not in cube_to_set or neighbor not in cube_to_set:
            continue
        if cube_to_set[cube] == cube_to_set[neighbor]:
            if cube_to_set[cube] == 'set1':
                set1_cubes.add(cube)
                set1_cubes.add(neighbor)
            else:
                set2_cubes.add(cube)
                set2_cubes.add(neighbor)
    
    # Compute symbols
    result = []
    for i, (left, right) in enumerate(neighbor_statuses):
        cube_id = cube_order[i]
        left_connected = (cube_id in previous_neighbors.values())
        right_connected = (cube_id in previous_neighbors)
        
        # A cube is in a chain of 3 if its set has exactly 3 cubes
        is_three_chain = (cube_id in set1_cubes and len(set1_cubes) == 3) or (cube_id in set2_cubes and len(set2_cubes) == 3)
        all_same_set = is_three_chain  # If it's in a chain of 3, we know it's all the same set
        left_symbol = get_symbol(left_connected, is_three_chain, all_same_set, True)
        right_symbol = get_symbol(right_connected, is_three_chain, all_same_set, False)
        result.append((left_symbol, right_symbol))
    print(f"Result: {result}")
    return result

async def publish_neighbor_symbols(client, cube_order, previous_neighbors, cube_to_set):
    """Publish border symbols to cubes via MQTT based on current connections and sets.
    
    Args:
        client: MQTT client
        cube_order: List of cube IDs in order
        previous_neighbors: Dict mapping cube_id to its neighbor
        cube_to_set: Dict mapping cube_id to its set name
    """
    neighbor_bools = calculate_neighbors(cube_order, previous_neighbors, cube_to_set)
    neighbor_symbols = get_neighbor_symbols(neighbor_bools, cube_order, previous_neighbors, cube_to_set)
    
    for cube_id, (left_symbol, right_symbol) in zip(cube_order, neighbor_symbols):
        border_topic = f"cube/{cube_id}/border_side"
        await client.publish(border_topic, left_symbol, retain=False)
        await client.publish(border_topic, right_symbol, retain=False)
        print(f"Published border symbols '{left_symbol}{right_symbol}' to {border_topic}")

def check_connected_cubes_in_same_set(previous_neighbors, cube_to_set):
    """Check if all connected cubes are in the same set.
    
    Args:
        previous_neighbors: Dict mapping cube_id to its neighbor
        cube_to_set: Dict mapping cube_id to its set name
        
    Returns:
        True if all connected cubes are in the same set as their neighbors, False otherwise
    """
    for cube_id, neighbor_id in previous_neighbors.items():
        if cube_to_set.get(cube_id) != cube_to_set.get(neighbor_id):
            print(f"Cube {cube_id} is in set {cube_to_set.get(cube_id)} but its neighbor {neighbor_id} is in set {cube_to_set.get(neighbor_id)}")
            return False
    print("All connected cubes are in the same set")
    return True

class CubeManager:
    """Manages the state and updates of cubes in the game.
    
    Handles:
    - Loading cube and tag IDs
    - Tracking cube sets and neighbors
    - Publishing images and border symbols
    - Updating cube states
    """
    
    def __init__(self, client):
        """Initialize with MQTT client and load initial state."""
        self.client = client
        self.cube_order = load_cube_order()
        self.tag_order = load_tag_order()
        self.tag_to_cube = dict(zip(self.tag_order, self.cube_order))
        self.set_names = [d for d in os.listdir(GEN_IMAGES_DIR) if os.path.isdir(os.path.join(GEN_IMAGES_DIR, d))]
        print(f"Available sets: {self.set_names}")
        self.previous_neighbors = {}
        self.current_image_set = None
        self.cube_to_set = {}
    
    def _get_files_in_set(self, set_name):
        """Get all .b64 files in the given set's directory."""
        set_dir = os.path.join(GEN_IMAGES_DIR, set_name)
        return [f for f in os.listdir(set_dir) if f.endswith('.b64')]
    
    async def update_cubes(self):
        """Update cubes with new random sets and images.
        
        Selects 2 random sets and assigns 3 cubes to each set.
        Publishes new images and preserves neighbor connections.
        """
        print("Updating cubes with new random sets")
        if len(self.set_names) < 2:
            raise ValueError("Need at least 2 sets")
        selected_sets = random.sample(self.set_names, 2)
        print(f"Selected sets: {selected_sets}")
        
        set1_files = random.sample(self._get_files_in_set(selected_sets[0]), 3)
        set2_files = random.sample(self._get_files_in_set(selected_sets[1]), 3)
        print(f"Selected files from {selected_sets[0]}: {set1_files}")
        print(f"Selected files from {selected_sets[1]}: {set2_files}")
        
        all_cubes = self.cube_order.copy()
        random.shuffle(all_cubes)
        
        self.cube_to_set = {}
        for i, cube_id in enumerate(all_cubes):
            self.cube_to_set[cube_id] = selected_sets[0] if i < 3 else selected_sets[1]
        
        self.current_image_set = f"{selected_sets[0]}+{selected_sets[1]}"
        
        cube_to_file = {}
        for i, cube_id in enumerate(all_cubes):
            if i < 3:
                cube_to_file[cube_id] = (selected_sets[0], set1_files[i])
            else:
                cube_to_file[cube_id] = (selected_sets[1], set2_files[i - 3])
        
        await publish_images(self.client, self.cube_order, cube_to_file)
        await publish_neighbor_symbols(self.client, self.cube_order, 
                                     self.previous_neighbors, self.cube_to_set)
        print("Done updating cubes")

async def handle_nfc_message(cube_manager, message, victory_sound):
    """Handle NFC tag detection messages.
    
    Updates neighbor connections and checks for victory condition.
    Plays victory sound if all connected cubes are in the same set.
    
    Args:
        cube_manager: CubeManager instance
        message: MQTT message containing tag ID
        victory_sound: Pygame sound to play on victory
        
    Returns:
        True if victory achieved, False otherwise
    """
    payload = message.payload.decode()
    print(f"Received message on topic {message.topic}: {payload}")
    
    current_cube_id = str(message.topic).split('/')[-1]
    
    if not payload:
        if current_cube_id in cube_manager.previous_neighbors:
            del cube_manager.previous_neighbors[current_cube_id]
            await publish_neighbor_symbols(cube_manager.client, cube_manager.cube_order, 
                                         cube_manager.previous_neighbors, cube_manager.cube_to_set)
        return False
    
    right_side_cube_id = cube_manager.tag_to_cube.get(payload)
    if not right_side_cube_id:
        print(f"Unknown tag ID: {payload}")
        return False
    cube_manager.previous_neighbors[current_cube_id] = right_side_cube_id
    
    await publish_neighbor_symbols(cube_manager.client, cube_manager.cube_order, 
                                 cube_manager.previous_neighbors, cube_manager.cube_to_set)

    if len(cube_manager.previous_neighbors) == 4:  # Exactly 4 connections for two sets of 3 cubes
        if check_connected_cubes_in_same_set(cube_manager.previous_neighbors, cube_manager.cube_to_set):
            print("Victory! All connected cubes are in the same set!")
            victory_sound.play()
            return True
    return False

async def main():
    """Main game loop.
    
    Initializes pygame mixer, connects to MQTT broker, and handles NFC messages.
    Updates cubes with new sets when victory is achieved.
    """
    random.seed(1)
    # Initialize pygame mixer for audio
    pygame.mixer.init()
    victory_sound = pygame.mixer.Sound("victory.mp3")
    
    async with aiomqtt.Client("192.168.8.247") as client:
        cube_manager = CubeManager(client)
        
        # Display initial random sets
        await cube_manager.update_cubes()
        
        await client.subscribe("cube/nfc/#")
        
        async for message in client.messages:
            if await handle_nfc_message(cube_manager, message, victory_sound):
                # If victory achieved, load new random sets
                await cube_manager.update_cubes()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 