#!/usr/bin/env python3
"""
Telegram Session Generator
Generate StringSession for Railway deployment
"""

from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

# Telegram API credentials (get from https://my.telegram.org)
API_ID = '26361462'  # Replace with your actual API ID
API_HASH = '204bc1ecf02dbf8c3dae2eff9523fcab'  # Replace with your actual API hash

async def generate_session():
    """Generate StringSession for a phone number"""
    
    phone = input("Enter phone number (with country code, e.g., +447449766009): ")
    
    # Create client with StringSession
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    print(f"Connecting to Telegram...")
    await client.start(phone=phone)
    
    # Get the StringSession
    session_string = client.session.save()
    
    print(f"\n✅ Session generated successfully!")
    print(f"📱 Phone: {phone}")
    print(f"🔑 StringSession:")
    print(f"{session_string}")
    print(f"\n📋 Copy this StringSession to your Railway environment variable:")
    print(f"TELEGRAM_ACCOUNT_1_SESSION={session_string}")
    
    await client.disconnect()

if __name__ == "__main__":
    print("🔐 Telegram StringSession Generator")
    print("=" * 50)
    
    if API_ID == 'YOUR_API_ID' or API_HASH == 'YOUR_API_HASH':
        print("❌ Please set your API_ID and API_HASH first!")
        print("Get them from: https://my.telegram.org")
        exit(1)
    
    asyncio.run(generate_session())