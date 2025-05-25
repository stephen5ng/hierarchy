#!/usr/bin/env python3

import asyncio
import aiomqtt
import json
import glob
import os
import random
import time

IMAGE_SETS = ["start", "math", "military", "scrabble", "starbucks", "planets", "succession"]
START_TAG = "4342D303530104E0"
TIMEOUT_SECONDS = 120

def load_cube_order():
    with open('cube_ids.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

def load_tag_order():
    with open('tag_ids.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

def load_orders():
    cube_order = load_cube_order()
    tag_order = load_tag_order()
    # Create pairs of cube and tag IDs
    pairs = list(zip(cube_order, tag_order))
    # Shuffle the pairs
    random.shuffle(pairs)
    # Unzip back into separate lists
    cube_order, tag_order = zip(*pairs)
    return list(cube_order), list(tag_order)

async def publish_images(client, cube_order, image_folder):
    # Get all .b64 files and sort them
    b64_files = sorted(glob.glob(f'gen_images/{image_folder}/*.b64'))
    print(f"Publishing {len(b64_files)} images for {image_folder}")
    # Publish each image to its corresponding cube
    for i, b64_file in enumerate(b64_files):
        if i >= len(cube_order):
            break
            
        cube_id = cube_order[i]
        with open(b64_file, 'r') as f:
            image_data = f.read().strip()
            
        topic = f"cube/{cube_id}/image"
        await client.publish(topic, image_data, retain=True)
        print(f"Published image from {b64_file} to {topic}")

async def clear_previous_neighbor(client, current_cube_id, previous_neighbors):
    if current_cube_id in previous_neighbors:
        old_neighbor_topic = f"cube/{previous_neighbors[current_cube_id]}/border_side"
        await client.publish(old_neighbor_topic, "<")
        print(f"Cleared border line < for previous neighbor {previous_neighbors[current_cube_id]}")
        del previous_neighbors[current_cube_id]

def calculate_neighbors(cube_order, previous_neighbors):
    # Initialize result array with None for both sides of each cube
    result = [(None, None) for _ in cube_order]
    
    # For each cube in order
    for i, cube_id in enumerate(cube_order):
        # Check right side
        right_neighbor = previous_neighbors.get(cube_id)
        if right_neighbor:
            # print(f"right_neighbor: {right_neighbor}, expected: {cube_order[i + 1]}")
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
        await client.publish(border_topic, right_symbol)
        print(f"Published border line message '{right_symbol}' to {border_topic}")
        await client.publish(border_topic, left_symbol)
        print(f"Published border line message '{left_symbol}' to {border_topic}")

def check_cube_order_correctness(cube_order, previous_neighbors):
    for i in range(len(cube_order) - 1):
        current = cube_order[i]
        if current not in previous_neighbors or previous_neighbors[current] != cube_order[i + 1]:
            if current in previous_neighbors:
                print(f"failed: current: {current}, expected: {cube_order[i + 1]}, neighbor: {previous_neighbors[current]}")
            else:
                print(f"failed: current: {current} missing neighbor")
            return False
    return True

async def handle_nfc_message(client, message, cube_order, tag_to_cube, previous_neighbors, current_index):
    payload = message.payload.decode()
    print(f"Received message on topic {message.topic}: {payload}")
    
    # Special case for start set
    if current_index == 0:
        return payload == START_TAG
    
    # Ignore if payload is an unknown tag ID
    if payload and payload not in tag_to_cube:
        return False
    
    # Extract CUBE_ID from the topic (cube/nfc/CUBE_ID)
    current_cube_id = str(message.topic).split('/')[-1]

    if not payload:
        if current_cube_id in previous_neighbors:
            del previous_neighbors[current_cube_id]
    
    right_side_cube_id = tag_to_cube.get(payload)
        
    previous_neighbors[current_cube_id] = right_side_cube_id
    neighbor_bools = calculate_neighbors(cube_order, previous_neighbors)
    neighbor_symbols = get_neighbor_symbols(neighbor_bools)
    print(f"neighbors: {neighbor_symbols}")
    await publish_neighbor_symbols(client, cube_order, neighbor_symbols)
    
    # Check if all five neighbors are correctly connected
    print(f"previous_neighbors: {previous_neighbors}")
    if len(previous_neighbors) >= 5:
        return check_cube_order_correctness(cube_order, previous_neighbors)
    return False

class GameState:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.current_index = 0
        self.start_time = float('inf')

async def update_cubes(client, cube_order, previous_neighbors, image_set):
    print(f"Updating cubes to {image_set}")
    await publish_images(client, cube_order, image_set)
    await publish_neighbor_symbols(client, cube_order, get_neighbor_symbols(calculate_neighbors(cube_order, previous_neighbors)))
    print("done updating cubes")

async def check_timer(state, client, cube_order, previous_neighbors):
    while True:
        if time.time() - state.start_time > TIMEOUT_SECONDS:
            print("\nTime's up! Resetting to start...")
            state.reset()
            print(f"updating cubes to {IMAGE_SETS[state.current_index]}")
            await update_cubes(client, cube_order, previous_neighbors, IMAGE_SETS[state.current_index])
            print("\nTime's up! Resetting to start done...")
            return
        await asyncio.sleep(0.5)

async def main():
    cube_order, tag_order = load_orders()
    
    # Create mapping from tag ID to cube ID
    tag_to_cube = dict(zip(tag_order, cube_order))
    
    # Track previous right neighbors for each cube
    previous_neighbors = {}
    
    state = GameState()
    timer_task = None
    
    async with aiomqtt.Client("192.168.8.247") as client:
        print(f"Publishing {IMAGE_SETS[state.current_index]} images...")
        await update_cubes(client, cube_order, previous_neighbors, IMAGE_SETS[state.current_index])
        print("done publishing start images")
        await client.subscribe("cube/nfc/#")
        
        async for message in client.messages:
            if await handle_nfc_message(client, message, cube_order, tag_to_cube, previous_neighbors, state.current_index):
                print(f"Finished {IMAGE_SETS[state.current_index]}")
     
                state.current_index = (state.current_index + 1) % len(IMAGE_SETS)
                print(f"\nSwitching to {IMAGE_SETS[state.current_index]} images...")
                
                if state.current_index == 1:
                    if timer_task:
                        timer_task.cancel()
                    state.start_time = time.time()
                    timer_task = asyncio.create_task(check_timer(state, client, cube_order, previous_neighbors))
                
                cube_order, tag_order = load_orders()
                await update_cubes(client, cube_order, previous_neighbors, IMAGE_SETS[state.current_index])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 
