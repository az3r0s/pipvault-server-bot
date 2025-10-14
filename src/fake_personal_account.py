"""
Fake Personal Account Webhook System
===================================

Creates a webhook that mimics your personal Discord account appearance
and messaging style, but uses Discord's official webhook API instead
of your personal token. This is 100% safe and Discord ToS compliant.
"""

import discord
from discord import Webhook
import aiohttp
import asyncio
import random
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class FakePersonalAccount:
    """
    Creates a webhook-based fake version of your personal Discord account
    that looks identical but doesn't risk your real account
    """
    
    def __init__(self, webhook_url: str, profile_config: Dict[str, Any]):
        self.webhook_url = webhook_url
        self.profile_config = profile_config
        self.session: Optional[aiohttp.ClientSession] = None
        self.webhook: Optional[Webhook] = None
        
        # Your real account details for mimicking
        self.fake_username = profile_config.get('username', 'Aidan')
        self.fake_avatar_url = profile_config.get('avatar_url', '')
        self.fake_display_name = profile_config.get('display_name', 'Aidan')
        
    async def initialize(self):
        """Initialize the fake account webhook system"""
        try:
            self.session = aiohttp.ClientSession()
            self.webhook = Webhook.from_url(self.webhook_url, session=self.session)
            
            logger.info(f"✅ Fake Aidan account initialized with webhook")
            logger.info(f"👤 Fake Profile: {self.fake_username} ({self.fake_display_name})")
            logger.info(f"🖼️ Avatar URL: {self.fake_avatar_url}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize fake account: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup webhook session"""
        if self.session:
            await self.session.close()
        logger.info("🛑 Fake account webhook cleaned up")
    
    async def send_message(self, content: str, thread: Optional[discord.Thread] = None) -> bool:
        """
        Send a message as the fake Aidan account using webhook
        This looks exactly like your real account but is 100% safe
        """
        if not self.webhook:
            logger.error("❌ Fake account not initialized")
            return False
        
        try:
            # Add human-like delay before sending
            delay = random.uniform(1.5, 4.0)  # 1.5-4 second delay
            await asyncio.sleep(delay)
            
            # Send message with fake profile
            send_kwargs = {
                "content": content,
                "username": self.fake_display_name,  # Shows as "Aidan" 
                "avatar_url": self.fake_avatar_url,  # Your exact profile picture
                "wait": True  # Wait for message to be sent
            }
            
            # Add thread if provided
            if thread:
                send_kwargs["thread"] = thread
            
            webhook_message = await self.webhook.send(**send_kwargs)
            
            logger.info(f"✅ Fake Aidan sent message: {content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send fake account message: {e}")
            return False
    
    async def send_with_typing(self, content: str, thread: Optional[discord.Thread] = None) -> bool:
        """
        Send message with realistic typing simulation
        Makes it look like you're actually typing the response
        """
        if not thread:
            logger.warning("⚠️ Cannot simulate typing without thread reference")
            return await self.send_message(content, thread)
        
        try:
            # Calculate realistic typing time based on message length
            words = len(content.split())
            typing_seconds = max(2, min(8, words / 15))  # 15 WPM typing speed
            
            # Start typing indicator (this requires the actual bot, not webhook)
            # We'll add a delay instead to simulate thinking/typing time
            logger.info(f"⌨️ Fake Aidan is 'typing' for {typing_seconds:.1f} seconds...")
            await asyncio.sleep(typing_seconds)
            
            # Send the message as fake account
            return await self.send_message(content, thread)
            
        except Exception as e:
            logger.error(f"❌ Error in typing simulation: {e}")
            return False
    
    async def send_realistic_response(self, content: str, thread: Optional[discord.Thread] = None) -> bool:
        """
        Send a response with realistic human behavior patterns
        - Random delay before responding
        - Typing simulation
        - Natural message sending
        """
        try:
            # Random thinking delay (like you reading the message first)
            thinking_delay = random.uniform(3, 12)  # 3-12 seconds to "read" message
            logger.info(f"🤔 Fake Aidan is 'reading' message for {thinking_delay:.1f} seconds...")
            await asyncio.sleep(thinking_delay)
            
            # Send with typing simulation
            return await self.send_with_typing(content, thread)
            
        except Exception as e:
            logger.error(f"❌ Error in realistic response: {e}")
            return False

class FakeAccountManager:
    """
    Manages the fake account system for VIP communications
    """
    
    def __init__(self):
        self.fake_accounts: Dict[str, FakePersonalAccount] = {}
        self.active = False
    
    async def setup_fake_aidan_account(self, webhook_url: str) -> bool:
        """
        Set up the fake Aidan account with your exact profile details
        """
        try:
            # Your real profile configuration - can be set via environment variables
            aidan_profile = {
                'username': os.getenv('FAKE_AIDAN_USERNAME', 'Aidan'),
                'display_name': os.getenv('FAKE_AIDAN_DISPLAY_NAME', 'Aidan'),
                'avatar_url': os.getenv('FAKE_AIDAN_AVATAR_URL', 'https://cdn.discordapp.com/avatars/243819020040536065/f47ac10b58cc4372a567c0e02b2c3d479378d6563d58850d46e86909e08c8b9a.png')
            }
            
            fake_aidan = FakePersonalAccount(webhook_url, aidan_profile)
            
            if await fake_aidan.initialize():
                self.fake_accounts['aidan'] = fake_aidan
                self.active = True
                logger.info("✅ Fake Aidan account ready for VIP communications")
                return True
            else:
                logger.error("❌ Failed to setup fake Aidan account")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error setting up fake Aidan account: {e}")
            return False
    
    async def send_as_aidan(self, content: str, thread: Optional[discord.Thread] = None) -> bool:
        """
        Send a message as fake Aidan - looks exactly like your real account
        """
        if not self.active or 'aidan' not in self.fake_accounts:
            logger.error("❌ Fake Aidan account not available")
            return False
        
        fake_aidan = self.fake_accounts['aidan']
        return await fake_aidan.send_realistic_response(content, thread)
    
    async def cleanup_all(self):
        """Cleanup all fake accounts"""
        for fake_account in self.fake_accounts.values():
            await fake_account.cleanup()
        
        self.fake_accounts.clear()
        self.active = False
        logger.info("🛑 All fake accounts cleaned up")
    
    def get_status(self) -> dict:
        """Get status of fake account system for debugging"""
        return {
            "active": self.active,
            "fake_accounts": list(self.fake_accounts.keys()),
            "aidan_account_available": 'aidan' in self.fake_accounts,
            "aidan_account_initialized": ('aidan' in self.fake_accounts and 
                                        self.fake_accounts['aidan'].webhook is not None)
        }

# Global instance for easy access
fake_account_manager = FakeAccountManager()

async def initialize_fake_aidan(webhook_url: str) -> bool:
    """Initialize the fake Aidan account system"""
    return await fake_account_manager.setup_fake_aidan_account(webhook_url)

async def send_as_fake_aidan(content: str, thread: Optional[discord.Thread] = None) -> bool:
    """Send message as fake Aidan account"""
    logger.info(f"🔍 DEBUG: send_as_fake_aidan called - Manager active: {fake_account_manager.active}")
    logger.info(f"🔍 DEBUG: Available fake accounts: {list(fake_account_manager.fake_accounts.keys())}")
    
    if not fake_account_manager.active:
        logger.error("❌ Fake account manager not active")
        return False
    
    if 'aidan' not in fake_account_manager.fake_accounts:
        logger.error("❌ Fake Aidan account not found in manager")
        return False
    
    logger.info(f"🔍 DEBUG: Calling fake_account_manager.send_as_aidan...")
    return await fake_account_manager.send_as_aidan(content, thread)

def get_fake_account_manager() -> FakeAccountManager:
    """Get the global fake account manager"""
    return fake_account_manager

async def cleanup_fake_accounts():
    """Cleanup all fake accounts"""
    await fake_account_manager.cleanup_all()