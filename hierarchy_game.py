#!/usr/bin/env python3

import asyncio
import aiomqtt
import json
import glob
import os
import random

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

async def handle_nfc_message(client, message, cube_order, tag_to_cube, previous_neighbors, current_image_set):
    # Decode the message payload
    payload = message.payload.decode()
    print(f"Received message on topic {message.topic}: {payload}")
    
    # Extract CUBE_ID from the topic (cube/nfc/CUBE_ID)
    current_cube_id = str(message.topic).split('/')[-1]
    border_topic = f"cube/{current_cube_id}/border_side"
    
    border_message = ">"
    if not payload:
        await clear_previous_neighbor(client, current_cube_id, previous_neighbors)
        await client.publish(border_topic, border_message)
        print(f"Published border line message '{border_message}' to {border_topic}")
        return

    current_index = cube_order.index(current_cube_id)
    correct_neighbor = cube_order[current_index + 1] if current_index + 1 < len(cube_order) else None
    print(f"current_cube_id: {current_cube_id}, correct_neighbor: {correct_neighbor}")
    
    right_side_cube_id = tag_to_cube.get(payload)
    
    if current_cube_id in previous_neighbors and previous_neighbors[current_cube_id] != right_side_cube_id:
        await clear_previous_neighbor(client, current_cube_id, previous_neighbors)
    
    previous_neighbors[current_cube_id] = right_side_cube_id
    
    border_message = "}" if correct_neighbor == right_side_cube_id else ")"
    
    if correct_neighbor:
        neighbor_border_topic = f"cube/{right_side_cube_id}/border_side"
        neighbor_message = "{" if correct_neighbor == right_side_cube_id else "("
        await client.publish(neighbor_border_topic, neighbor_message)
        print(f"Published {neighbor_message} to {neighbor_border_topic}")

    # Check if all five neighbors are correctly connected
    if len(previous_neighbors) == 5:
        all_correct = True
        for i in range(len(cube_order) - 1):
            current = cube_order[i]
            if current not in previous_neighbors or previous_neighbors[current] != cube_order[i + 1]:
                all_correct = False
                break
        if all_correct:
            print("\n🎉 CONGRATULATIONS! 🎉")
            print("You have successfully connected all five cubes in the correct order!")
            # Rotate through all image sets
            image_sets = ["military", "math", "scrabble", "starbucks", "planets", "succession"]
            current_index = image_sets.index(current_image_set)
            next_index = (current_index + 1) % len(image_sets)
            next_image_set = image_sets[next_index]
            print(f"\nSwitching to {next_image_set} images...")
            await publish_images(client, cube_order, next_image_set)
            return next_image_set
    
    await client.publish(border_topic, border_message)
    print(f"Published border line message '{border_message}' to {border_topic}")
    return current_image_set

async def main():
    random.seed(0)

    cube_order, tag_order = load_orders()
    
    # Create mapping from tag ID to cube ID
    tag_to_cube = dict(zip(tag_order, cube_order))
    
    # Track previous right neighbors for each cube
    previous_neighbors = {}
    
    current_image_set = "military"
    
    async with aiomqtt.Client("localhost") as client:
        # Publish planet images on startup
        print(f"Publishing {current_image_set} images...")
        await publish_images(client, cube_order, current_image_set)
        
        # Subscribe to all cube NFC messages
        await client.subscribe("cube/nfc/#")
        
        print("Monitoring cube NFC messages...")
        async for message in client.messages:
            try:
                current_image_set = await handle_nfc_message(client, message, cube_order, tag_to_cube, previous_neighbors, current_image_set)
            except Exception as e:
                print(f"Error processing message: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 