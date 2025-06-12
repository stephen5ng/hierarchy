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
        b64_file = os.path.join(GEN_IMAGES_DIR, image_folder, filename)
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
        self.image_sets = [d for d in os.listdir(GEN_IMAGES_DIR) if os.path.isdir(os.path.join(GEN_IMAGES_DIR, d))]
        random.shuffle(self.image_sets)
        print(f"Available image sets: {self.image_sets}")
        self.previous_neighbors = {}
        self.current_image_set = None
        self.cube_to_filename = {}  # Maps cube_id to its real filename
    
    async def update_cubes(self, image_set):
        print(f"Updating cubes to {image_set}")
        self.current_image_set = image_set
        # Get all .b64 files and sort them
        b64_files = sorted(glob.glob(f'{GEN_IMAGES_DIR}/{image_set}/*.b64'))
        # Map each cube to its image file
        self.cube_to_filename = {}
        for i, b64_file in enumerate(b64_files):
            if i >= len(self.cube_order):
                break
            self.cube_to_filename[self.cube_order[i]] = os.path.basename(b64_file)
        await publish_images(self.client, self.cube_order, image_set, self.cube_to_filename)
        # Reset neighbor connections
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
        
        # Display images from the first set
        if cube_manager.image_sets:
            await cube_manager.update_cubes(cube_manager.image_sets[0])
        
        await client.subscribe("cube/nfc/#")
        
        async for message in client.messages:
            if await handle_nfc_message(cube_manager, message, victory_sound):
                # If victory achieved, move to next image set
                current_index = cube_manager.image_sets.index(cube_manager.current_image_set)
                next_index = (current_index + 1) % len(cube_manager.image_sets)
                await cube_manager.update_cubes(cube_manager.image_sets[next_index])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 