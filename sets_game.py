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

async def publish_images(client, cube_order, cube_to_file):
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
    # Initialize result array with None for both sides of each cube
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

def find_chain_of_three(cube_id, previous_neighbors, checked_cubes=None):
    """Find a chain of 3 cubes starting from cube_id. Returns set of cubes in chain if found, None otherwise."""
    if checked_cubes is None:
        checked_cubes = set()
    
    if cube_id in checked_cubes:
        return None
        
    checked_cubes.add(cube_id)
    
    # Get direct neighbors of this cube
    neighbors = []
    for other_cube, neighbor in previous_neighbors.items():
        if other_cube == cube_id:
            neighbors.append(neighbor)
        elif neighbor == cube_id:
            neighbors.append(other_cube)
    
    # If this cube has 2 neighbors, it's the middle of a chain
    if len(neighbors) == 2:
        # Start from this cube and follow both directions
        visited = {cube_id}  # Track visited cubes to avoid cycles
        
        # Follow first direction
        current = neighbors[0]
        visited.add(current)
        while True:
            next_neighbors = []
            for other_cube, neighbor in previous_neighbors.items():
                if other_cube == current and neighbor not in visited:
                    next_neighbors.append(neighbor)
                elif neighbor == current and other_cube not in visited:
                    next_neighbors.append(other_cube)
            
            if not next_neighbors:  # Dead end
                break
            if len(next_neighbors) > 1:  # Branch - not a chain
                return None
                
            current = next_neighbors[0]
            if current in visited:  # Cycle
                return None
            visited.add(current)
            
            if len(visited) > 3:  # Chain too long
                return None
        
        # Follow second direction
        current = neighbors[1]
        if current in visited:  # Already visited - not a chain
            return None
        visited.add(current)
        while True:
            next_neighbors = []
            for other_cube, neighbor in previous_neighbors.items():
                if other_cube == current and neighbor not in visited:
                    next_neighbors.append(neighbor)
                elif neighbor == current and other_cube not in visited:
                    next_neighbors.append(other_cube)
            
            if not next_neighbors:  # Dead end
                break
            if len(next_neighbors) > 1:  # Branch - not a chain
                return None
                
            current = next_neighbors[0]
            if current in visited:  # Cycle
                return None
            visited.add(current)
            
            if len(visited) > 3:  # Chain too long
                return None
        
        return visited if len(visited) == 3 else None
    
    # If this cube has 1 neighbor, check if that neighbor is in a chain of 3
    elif len(neighbors) == 1:
        # Check if the neighbor is in a chain of 3
        return find_chain_of_three(neighbors[0], previous_neighbors, checked_cubes)
    
    # If this cube has 0 or >2 neighbors, it's not in a chain
    return None

def get_symbol(connected, is_chain, all_same_set, is_left):
    if not connected:
        return "<" if is_left else ">"
    if is_chain:
        if all_same_set:
            return "{" if is_left else "}"
        else:
            return "(" if is_left else ")"
    else:
        return "(" if is_left else ")"
    
def get_neighbor_symbols(neighbor_statuses, cube_order, previous_neighbors, cube_to_set):
    # First find all chains of 3
    chains = {}
    checked_cubes = set()
    for i, cube_id in enumerate(cube_order):
        if cube_id not in checked_cubes:
            chain = find_chain_of_three(cube_id, previous_neighbors, checked_cubes)
            if chain:
                for c in chain:
                    chains[c] = chain
    result = []
    for i, (left, right) in enumerate(neighbor_statuses):
        cube_id = cube_order[i]
        left_connected = (cube_id in previous_neighbors.values())
        right_connected = (cube_id in previous_neighbors and previous_neighbors[cube_id] in cube_order)
        is_chain = cube_id in chains
        all_same_set = (is_chain and all(cube_to_set.get(c) == cube_to_set.get(cube_id) for c in chains[cube_id]))
        left_symbol = get_symbol(left_connected, is_chain, all_same_set, True)
        right_symbol = get_symbol(right_connected, is_chain, all_same_set, False)
        result.append((left_symbol, right_symbol))
    print(f"Result: {result}")
    return result

async def publish_neighbor_symbols(client, cube_order, neighbor_symbols):
    for cube_id, (left_symbol, right_symbol) in zip(cube_order, neighbor_symbols):
        border_topic = f"cube/{cube_id}/border_side"
        await client.publish(border_topic, right_symbol, retain=False)
        print(f"Published border line message '{right_symbol}' to {border_topic}")
        await client.publish(border_topic, left_symbol, retain=False)
        print(f"Published border line message '{left_symbol}' to {border_topic}")

def check_prefix_matches(previous_neighbors, cube_to_set):
    # Check each connection using the set names
    for cube_id, neighbor_id in previous_neighbors.items():
        if cube_id not in cube_to_set or neighbor_id not in cube_to_set:
            return False
        if cube_to_set[cube_id] != cube_to_set[neighbor_id]:
            return False
    return True

class CubeManager:
    def __init__(self, client):
        self.client = client
        self.cube_order = load_cube_order()
        self.tag_order = load_tag_order()
        self.tag_to_cube = dict(zip(self.tag_order, self.cube_order))
        # Each set is a subdirectory in gen_images_sets
        self.set_names = [d for d in os.listdir(GEN_IMAGES_DIR) if os.path.isdir(os.path.join(GEN_IMAGES_DIR, d))]
        print(f"Available sets: {self.set_names}")
        self.previous_neighbors = {}
        self.current_image_set = None
        self.cube_to_set = {}  # Maps cube_id to its set name
    
    def _get_files_in_set(self, set_name):
        """Get all .b64 files in the given set's directory."""
        set_dir = os.path.join(GEN_IMAGES_DIR, set_name)
        return [f for f in os.listdir(set_dir) if f.endswith('.b64')]
    
    async def update_cubes(self):
        print("Updating cubes with new random sets")
        # Select 2 different random sets
        if len(self.set_names) < 2:
            raise ValueError("Need at least 2 sets")
        selected_sets = random.sample(self.set_names, 2)
        print(f"Selected sets: {selected_sets}")
        
        # Select 3 random files from each set
        set1_files = random.sample(self._get_files_in_set(selected_sets[0]), 3)
        set2_files = random.sample(self._get_files_in_set(selected_sets[1]), 3)
        print(f"Selected files from {selected_sets[0]}: {set1_files}")
        print(f"Selected files from {selected_sets[1]}: {set2_files}")
        
        # Randomly assign sets to cubes
        all_cubes = self.cube_order.copy()
        random.shuffle(all_cubes)
        
        # Map cubes to their sets
        self.cube_to_set = {}
        for i, cube_id in enumerate(all_cubes):
            if i < 3:
                self.cube_to_set[cube_id] = selected_sets[0]
            else:
                self.cube_to_set[cube_id] = selected_sets[1]
        
        # Store the current image sets (for logging/debugging)
        self.current_image_set = f"{selected_sets[0]}+{selected_sets[1]}"
        
        # Create mapping of cube order to files for publishing
        cube_to_file = {}
        for i, cube_id in enumerate(all_cubes):
            if i < 3:
                cube_to_file[cube_id] = (selected_sets[0], set1_files[i])
            else:
                cube_to_file[cube_id] = (selected_sets[1], set2_files[i - 3])
        
        # Publish images and reset neighbors
        await publish_images(self.client, self.cube_order, cube_to_file)
        self.previous_neighbors = {}
        await publish_neighbor_symbols(self.client, self.cube_order, get_neighbor_symbols(calculate_neighbors(self.cube_order, self.previous_neighbors, self.cube_to_set), self.cube_order, self.previous_neighbors, self.cube_to_set))
        print("Done updating cubes")

async def handle_nfc_message(cube_manager, message, victory_sound):
    payload = message.payload.decode()
    print(f"Received message on topic {message.topic}: {payload}")
    
    # Extract CUBE_ID from the topic (cube/nfc/CUBE_ID)
    current_cube_id = str(message.topic).split('/')[-1]
    
    if not payload:
        if current_cube_id in cube_manager.previous_neighbors:
            del cube_manager.previous_neighbors[current_cube_id]
            # Update border symbols after removing neighbor
            neighbor_bools = calculate_neighbors(cube_manager.cube_order, cube_manager.previous_neighbors, cube_manager.cube_to_set)
            neighbor_symbols = get_neighbor_symbols(neighbor_bools, cube_manager.cube_order, cube_manager.previous_neighbors, cube_manager.cube_to_set)
            print(f"No payload neighbor symbols: {neighbor_symbols}")
            await publish_neighbor_symbols(cube_manager.client, cube_manager.cube_order, neighbor_symbols)
        print("didn't have a payload or previous neighbor")
        return False
    
    print("--------------------------------handle_nfc_message 0")
    # Map tag ID (payload) to cube ID
    right_side_cube_id = cube_manager.tag_to_cube.get(payload)
    if not right_side_cube_id:
        print(f"Unknown tag ID: {payload}")
        return False
    cube_manager.previous_neighbors[current_cube_id] = right_side_cube_id
    print("--------------------------------handle_nfc_message 1")
    
    neighbor_bools = calculate_neighbors(cube_manager.cube_order, cube_manager.previous_neighbors, cube_manager.cube_to_set)
    print("--------------------------------handle_nfc_message 1a")
    neighbor_symbols = get_neighbor_symbols(neighbor_bools, cube_manager.cube_order, cube_manager.previous_neighbors, cube_manager.cube_to_set)
    print("--------------------------------handle_nfc_message 1b")
    print(f"Neighbor symbols: {neighbor_symbols}")
    await publish_neighbor_symbols(cube_manager.client, cube_manager.cube_order, neighbor_symbols)
    print("--------------------------------handle_nfc_message 2")

    # Check if all neighbors are connected and have matching prefixes
    if len(cube_manager.previous_neighbors) >= len(cube_manager.cube_order) - 1:
        if check_prefix_matches(cube_manager.previous_neighbors, cube_manager.cube_to_set):
            print("Victory! All neighbors have matching prefixes!")
            victory_sound.play()
            return True
    print("--------------------------------handle_nfc_message 3")
    return False

async def main():
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