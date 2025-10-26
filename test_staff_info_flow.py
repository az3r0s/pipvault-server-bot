#!/usr/bin/env python3
"""
Test Script for Staff Information Flow
======================================

This script tests the new staff information feature that sends 
staff details to the VA when a user sends their first message.
"""

import asyncio
import json
from typing import Dict, Optional

# Mock classes for testing
class MockThread:
    def __init__(self, thread_id: int):
        self.id = thread_id

class MockUser:
    def __init__(self, user_id: int, name: str):
        self.id = user_id
        self.name = name

class MockTelegramManager:
    def __init__(self):
        self.sent_messages = []
    
    async def send_message(self, user_id: str, username: str, message: str):
        self.sent_messages.append({
            'user_id': user_id,
            'username': username,
            'message': message
        })
        print(f"📤 TELEGRAM: From {user_id} to @{username}: {message}")
        return True

class MockVIPSessionManager:
    def __init__(self):
        self.active_threads = {}
        self.thread_sessions = {}
        self.threads_awaiting_first_message = set()
        self.TELEGRAM_VA_USERNAME = "test_va"
        self.telegram_manager = MockTelegramManager()
        
        # Load staff config for testing
        with open('config/staff_config.json', 'r') as f:
            self.staff_config = json.load(f)
    
    def create_session(self, user_id: str, thread_id: int):
        """Simulate creating a VIP session"""
        thread = MockThread(thread_id)
        self.active_threads[user_id] = thread
        self.thread_sessions[thread_id] = user_id
        self.threads_awaiting_first_message.add(thread_id)
        print(f"✅ Created session: User {user_id} -> Thread {thread_id}")
        print(f"📝 Threads awaiting first message: {self.threads_awaiting_first_message}")
    
    async def _get_referring_staff(self, user_id: int) -> Optional[Dict]:
        """Mock referring staff lookup - simulates database lookup"""
        # For testing, we'll simulate different users having different staff
        staff_mapping = {
            123456789: "Aidan",
            987654321: "Travis", 
            555666777: "Cyril",
            111222333: "Fin G",
            444555666: "Luca"
        }
        
        staff_key = staff_mapping.get(user_id)
        if not staff_key:
            print(f"⚠️ No staff mapping found for user {user_id}")
            return None
        
        staff_member = self.staff_config['staff_members'].get(staff_key)
        if not staff_member:
            print(f"⚠️ Staff member '{staff_key}' not found in config")
            return None
        
        return {
            'staff_id': staff_member['discord_id'],
            'staff_name': staff_member['username'],
            'full_name': staff_member['full_name'],
            'vantage_email': staff_member['vantage_email'],
            'vantage_referral_link': staff_member['vantage_referral_link'],
            'vantage_ib_code': staff_member['vantage_ib_code']
        }
    
    async def _send_staff_info_to_va(self, user_id: str, referring_staff: Optional[Dict], thread):
        """Send staff information to VA when user sends their first message"""
        if not referring_staff:
            print(f"⚠️ No referring staff found for user {user_id}")
            return
        
        # Extract full name and vantage email from staff config
        full_name = referring_staff.get('full_name', 'Unknown')
        vantage_email = referring_staff.get('vantage_email', 'unknown@email.com')
        
        # Create the staff information message in the requested format
        staff_info_message = f"THIS USER IS UPGRADING FOR: {full_name}\nWITH EMAIL: {vantage_email}"
        
        # Send to VA via Telegram
        await self.telegram_manager.send_message(
            user_id,
            self.TELEGRAM_VA_USERNAME,
            staff_info_message
        )
        print(f"✅ Sent staff info to VA for user {user_id}")
    
    async def simulate_user_message(self, user_id: int, thread_id: int, message: str):
        """Simulate a user sending a message in a thread"""
        print(f"\n🔵 USER MESSAGE: User {user_id} in thread {thread_id}: {message}")
        
        # Check if this is the user's first message in the thread
        is_first_message = thread_id in self.threads_awaiting_first_message
        if is_first_message:
            print(f"🆕 This is the user's FIRST message in thread {thread_id}")
            
            # Remove from awaiting set
            self.threads_awaiting_first_message.discard(thread_id)
            
            # Get referring staff info and send to VA before user's message
            referring_staff = await self._get_referring_staff(user_id)
            await self._send_staff_info_to_va(str(user_id), referring_staff, MockThread(thread_id))
            
            # Small delay to ensure staff info arrives before user message
            await asyncio.sleep(0.1)  # Shorter for testing
        else:
            print(f"📝 This is a follow-up message in thread {thread_id}")
        
        # Forward user's message to Telegram
        await self.telegram_manager.send_message(
            str(user_id),
            self.TELEGRAM_VA_USERNAME,
            message
        )
        print(f"📤 Forwarded user message to VA")

async def test_staff_info_flow():
    """Test the complete staff information flow"""
    print("🧪 Testing Staff Information Flow")
    print("=" * 50)
    
    manager = MockVIPSessionManager()
    
    # Test Case 1: User with Aidan as referring staff
    print("\n📋 TEST CASE 1: User referred by Aidan")
    print("-" * 30)
    user_id_1 = 123456789
    thread_id_1 = 1001
    
    manager.create_session(str(user_id_1), thread_id_1)
    await manager.simulate_user_message(user_id_1, thread_id_1, "Hi, I want to upgrade to VIP")
    await manager.simulate_user_message(user_id_1, thread_id_1, "What's the next step?")
    
    # Test Case 2: User with Travis as referring staff  
    print("\n📋 TEST CASE 2: User referred by Travis")
    print("-" * 30)
    user_id_2 = 987654321
    thread_id_2 = 1002
    
    manager.create_session(str(user_id_2), thread_id_2)
    await manager.simulate_user_message(user_id_2, thread_id_2, "Hello!")
    await manager.simulate_user_message(user_id_2, thread_id_2, "Can you help me with my account?")
    
    # Test Case 3: User with no referring staff
    print("\n📋 TEST CASE 3: User with no referring staff")  
    print("-" * 30)
    user_id_3 = 999888777
    thread_id_3 = 1003
    
    manager.create_session(str(user_id_3), thread_id_3)
    await manager.simulate_user_message(user_id_3, thread_id_3, "Hi there")
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total messages sent to Telegram: {len(manager.telegram_manager.sent_messages)}")
    
    for i, msg in enumerate(manager.telegram_manager.sent_messages, 1):
        print(f"{i}. User {msg['user_id']} -> @{msg['username']}: {msg['message'][:50]}{'...' if len(msg['message']) > 50 else ''}")
    
    print("\n✅ Staff information should appear BEFORE user messages!")
    print("🔍 Expected flow: Staff info -> User: Hi -> User: Follow-up")

if __name__ == "__main__":
    print("🔐 Staff Information Flow Test")
    print("=" * 50)
    
    try:
        asyncio.run(test_staff_info_flow())
        print("\n✅ Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()