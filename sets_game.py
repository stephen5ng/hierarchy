#!/usr/bin/env python3

import asyncio
import aiomqtt
import glob
import os
import random
import pygame

GEN_IMAGES_DIR = 'gen_images_sets'

def load_cube_order():
    with open('cube_ids.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()][:6]

def load_tag_order():
    with open('tag_ids.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()][:6]

def get_image_prefix(b64_file):
    return os.path.basename(b64_file).split('.')[0]

async def publish_images(client, cube_order, image_folder, cube_to_filename):
    print(f"Publishing images for {image_folder}")
    # Publish each image to its corresponding cube using the mapping
    for cube_id in cube_order:
        if cube_id not in cube_to_filename:
            continue
        filename = cube_to_filename[cube_id]
        b64_file = os.path.join(GEN_IMAGES_DIR, filename)
        with open(b64_file, 'r') as f:
            image_data = f.read().strip()
        topic = f"cube/{cube_id}/image"
        await client.publish(topic, image_data, retain=True)
        print(f"Published image from {filename} to {topic}")

def calculate_neighbors(cube_order, previous_neighbors):
    # Initialize result array with None for both sides of each cube
    result = [(None, None) for _ in cube_order]
    
    # For each cube in order
    for i, cube_id in enumerate(cube_order):
        # Check right side
        right_neighbor = previous_neighbors.get(cube_id)
        if right_neighbor:
            correct_right = i + 1 < len(cube_order) and cube_order[i + 1] == right_neighbor
            result[i] = (result[i][0], correct_right)
            
            # Update left side of the right neighbor
            right_neighbor_index = cube_order.index(right_neighbor)
            result[right_neighbor_index] = (correct_right, result[right_neighbor_index][1])
    
    return result

def get_neighbor_symbols(neighbor_statuses):
    result = []
    for left, right in neighbor_statuses:
        left_symbol = "<" if left is None else "{" if left else "("
        right_symbol = ">" if right is None else "}" if right else ")"
        result.append((left_symbol, right_symbol))
    return result

async def publish_neighbor_symbols(client, cube_order, neighbor_symbols):
    for cube_id, (left_symbol, right_symbol) in zip(cube_order, neighbor_symbols):
        border_topic = f"cube/{cube_id}/border_side"
        await client.publish(border_topic, right_symbol, retain=True)
        print(f"Published border line message '{right_symbol}' to {border_topic}")
        await client.publish(border_topic, left_symbol, retain=True)
        print(f"Published border line message '{left_symbol}' to {border_topic}")

def check_prefix_matches(cube_order, previous_neighbors, image_folder, cube_to_filename):
    # Check each connection using the real filenames
    for cube_id, neighbor_id in previous_neighbors.items():
        if cube_id not in cube_to_filename or neighbor_id not in cube_to_filename:
            return False
        cube_prefix = cube_to_filename[cube_id].split('.')[0]
        neighbor_prefix = cube_to_filename[neighbor_id].split('.')[0]
        if cube_prefix != neighbor_prefix:
            return False
    return True

class CubeManager:
    def __init__(self, client):
        self.client = client
        self.cube_order = load_cube_order()
        self.tag_order = load_tag_order()
        self.tag_to_cube = dict(zip(self.tag_order, self.cube_order))
        # All files are in a flat directory
        self.all_files = [f for f in os.listdir(GEN_IMAGES_DIR) if f.endswith('.b64')]
        # Group files by set prefix
        self.set_to_files = {}
        for f in self.all_files:
            prefix = f.split('.', 1)[0]
            self.set_to_files.setdefault(prefix, []).append(f)
        self.set_names = list(self.set_to_files.keys())
        print(f"Available sets: {self.set_names}")
        self.previous_neighbors = {}
        self.current_image_set = None
        self.cube_to_filename = {}  # Maps cube_id to its real filename
    
    async def update_cubes(self):
        print("Updating cubes with new random sets")
        # Select 2 different random sets
        if len(self.set_names) < 2:
            raise ValueError("Need at least 2 sets")
        selected_sets = random.sample(self.set_names, 2)
        print(f"Selected sets: {selected_sets}")
        
        # Select 3 random files from each set
        set1_files = random.sample(self.set_to_files[selected_sets[0]], 3)
        set2_files = random.sample(self.set_to_files[selected_sets[1]], 3)
        print(f"Selected files from {selected_sets[0]}: {set1_files}")
        print(f"Selected files from {selected_sets[1]}: {set2_files}")
        
        # Map files to cubes
        self.cube_to_filename = {}
        for i, cube_id in enumerate(self.cube_order):
            if i < 3:
                self.cube_to_filename[cube_id] = set1_files[i]
            else:
                self.cube_to_filename[cube_id] = set2_files[i - 3]
        
        # Store the current image set (for logging/debugging)
        self.current_image_set = f"{selected_sets[0]}+{selected_sets[1]}"
        
        # Publish images and reset neighbors
        await publish_images(self.client, self.cube_order, None, self.cube_to_filename)
        self.previous_neighbors = {}
        await publish_neighbor_symbols(self.client, self.cube_order, [('<', '>')]*len(self.cube_order))
        print("Done updating cubes")

async def handle_nfc_message(cube_manager, message, victory_sound):
    payload = message.payload.decode()
    print(f"Received message on topic {message.topic}: {payload}")
    
    if not payload:
        return False
    
    # Extract CUBE_ID from the topic (cube/nfc/CUBE_ID)
    current_cube_id = str(message.topic).split('/')[-1]
    
    if not payload:
        if current_cube_id in cube_manager.previous_neighbors:
            del cube_manager.previous_neighbors[current_cube_id]
        return False
    
    # Map tag ID (payload) to cube ID
    right_side_cube_id = cube_manager.tag_to_cube.get(payload)
    if not right_side_cube_id:
        print(f"Unknown tag ID: {payload}")
        return False
    cube_manager.previous_neighbors[current_cube_id] = right_side_cube_id
    
    neighbor_bools = calculate_neighbors(cube_manager.cube_order, cube_manager.previous_neighbors)
    neighbor_symbols = get_neighbor_symbols(neighbor_bools)
    await publish_neighbor_symbols(cube_manager.client, cube_manager.cube_order, neighbor_symbols)
    
    # Check if all neighbors are connected and have matching prefixes
    if len(cube_manager.previous_neighbors) >= len(cube_manager.cube_order) - 1:
        if check_prefix_matches(cube_manager.cube_order, cube_manager.previous_neighbors, cube_manager.current_image_set, cube_manager.cube_to_filename):
            print("Victory! All neighbors have matching prefixes!")
            victory_sound.play()
            return True
    return False

async def main():
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