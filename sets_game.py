#!/usr/bin/env python3

import asyncio
import aiomqtt
import glob
import os
import random

GEN_IMAGES_DIR = 'gen_images_sets'

def load_cube_order():
    with open('cube_ids.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

async def publish_images(client, cube_order, image_folder):
    # Get all .b64 files and sort them
    b64_files = sorted(glob.glob(f'{GEN_IMAGES_DIR}/{image_folder}/*.b64'))
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

class CubeManager:
    def __init__(self, client):
        self.client = client
        self.cube_order = load_cube_order()
        self.image_sets = [d for d in os.listdir(GEN_IMAGES_DIR) if os.path.isdir(os.path.join(GEN_IMAGES_DIR, d))]
        random.shuffle(self.image_sets)
        print(f"Available image sets: {self.image_sets}")
    
    async def update_cubes(self, image_set):
        print(f"Updating cubes to {image_set}")
        await publish_images(self.client, self.cube_order, image_set)
        print("Done updating cubes")

async def main():
    async with aiomqtt.Client("192.168.8.247") as client:
        cube_manager = CubeManager(client)
        
        # Display images from the first set
        if cube_manager.image_sets:
            await cube_manager.update_cubes(cube_manager.image_sets[0])
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 