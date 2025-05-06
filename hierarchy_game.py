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

async def publish_planet_images(client, cube_order):
    # Get all .b64 files and sort them
    b64_files = sorted(glob.glob('images/planets/*.b64'))
    
    # Publish each image to its corresponding cube
    for i, b64_file in enumerate(b64_files):
        if i >= len(cube_order):
            break
            
        cube_id = cube_order[i]
        with open(b64_file, 'r') as f:
            image_data = f.read().strip()
            
        topic = f"cube/{cube_id}/image"
        await client.publish(topic, image_data)
        print(f"Published image from {b64_file} to {topic}")

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

async def main():
    cube_order, tag_order = load_orders()
    
    # Create mapping from tag ID to cube ID
    tag_to_cube = dict(zip(tag_order, cube_order))
    
    # Track previous right neighbors for each cube
    previous_neighbors = {}
    
    async with aiomqtt.Client("localhost") as client:
        # Publish planet images on startup
        await publish_planet_images(client, cube_order)
        
        # Subscribe to all cube NFC messages
        await client.subscribe("cube/nfc/#")
        
        print("Monitoring cube NFC messages...")
        async for message in client.messages:
            try:
                # Decode the message payload
                payload = message.payload.decode()
                print(f"Received message on topic {message.topic}: {payload}")
                
                # Extract CUBE_ID from the topic (cube/nfc/CUBE_ID)
                current_cube_id = str(message.topic).split('/')[-1]
                border_topic = f"cube/{current_cube_id}/border_side"
                
                border_message = ">"
                # Check if right neighbor is correct
                if payload:
                    try:
                        current_index = cube_order.index(current_cube_id)
                        correct_neighbor = cube_order[current_index + 1] if current_index + 1 < len(cube_order) else None
                        print(f"current_cube_id: {current_cube_id}, correct_neighbor: {correct_neighbor}")
                        # Convert tag ID to cube ID
                        right_side_cube_id = tag_to_cube.get(payload)
                        
                        # If previous neighbor exists and is different, clear its border line
                        if current_cube_id in previous_neighbors and previous_neighbors[current_cube_id] != right_side_cube_id:
                            old_neighbor_topic = f"cube/{previous_neighbors[current_cube_id]}/border_side"
                            await client.publish(old_neighbor_topic, "<")
                            print(f"Cleared border line < for previous neighbor {previous_neighbors[current_cube_id]}")
                        
                        # Update previous neighbor
                        previous_neighbors[current_cube_id] = right_side_cube_id
                        
                        border_message = "}" if correct_neighbor == right_side_cube_id else ")"
                        
                        # If there's a right neighbor, publish appropriate opening brace
                        if correct_neighbor:
                            neighbor_border_topic = f"cube/{right_side_cube_id}/border_side"
                            neighbor_message = "{" if correct_neighbor == right_side_cube_id else "("
                            await client.publish(neighbor_border_topic, neighbor_message)
                            print(f"Published {neighbor_message} to {neighbor_border_topic}")
                    except ValueError:
                        print(f"Current cube ID {current_cube_id} not found in cube order")
                else:
                    # If payload is empty, clear previous neighbor's border line if it exists
                    if current_cube_id in previous_neighbors:
                        old_neighbor_topic = f"cube/{previous_neighbors[current_cube_id]}/border_side"
                        await client.publish(old_neighbor_topic, "<")
                        print(f"Cleared border line for previous neighbor {previous_neighbors[current_cube_id]}")
                        del previous_neighbors[current_cube_id]
                    
                await client.publish(border_topic, border_message)
                print(f"Published border line message '{border_message}' to {border_topic}")
                
            except Exception as e:
                print(f"Error processing message: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 