#!/usr/bin/env python3

import asyncio
import aiomqtt
import json

async def main():
    async with aiomqtt.Client("localhost") as client:
        # Subscribe to all cube NFC messages
        await client.subscribe("cube/nfc/#")
        
        print("Monitoring cube NFC messages...")
        async for message in client.messages:
            try:
                # Decode the message payload
                payload = message.payload.decode()
                print(f"Received message on topic {message.topic}: {payload}")
                
                # Extract CUBE_ID from the topic (cube/nfc/CUBE_ID)
                cube_id = str(message.topic).split('/')[-1]
                border_topic = f"cube/{cube_id}/border_line"
                
                # Publish "-" for non-empty payload, " " for empty payload
                border_message = "-" if payload else " "
                await client.publish(border_topic, border_message)
                print(f"Published border line message '{border_message}' to {border_topic}")
                    
            except Exception as e:
                print(f"Error processing message: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped.") 