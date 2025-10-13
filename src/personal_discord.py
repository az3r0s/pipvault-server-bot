#!/usr/bin/env python3
"""
Personal Discord Account Bot for VIP Chat System
===============================================

This bot runs with your personal Discord account token to send messages
naturally in VIP chat threads without the "APP" tag.

IMPORTANT: This uses a user token, which is against Discord's ToS if used
for automated behavior. Use at your own risk and keep this private.
"""

import asyncio
import json
import logging
import os
import aiohttp
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class PersonalDiscordBot:
    """Handles sending messages as your personal Discord account"""
    
    def __init__(self, token: str):
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_id: Optional[str] = None
        self.running = False
        
        # Discord API endpoints
        self.base_url = "https://discord.com/api/v10"
        
    async def start(self):
        """Start the personal Discord bot"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": self.token,
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot (VIP Chat System, 1.0)"
            }
        )
        
        # Get current user info
        try:
            async with self.session.get(f"{self.base_url}/users/@me") as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    self.user_id = user_data['id']
                    username = user_data.get('username', 'Unknown')
                    logger.info(f"✅ Personal Discord bot started as {username} ({self.user_id})")
                    self.running = True
                    return True
                else:
                    logger.error(f"❌ Failed to authenticate personal Discord account: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error starting personal Discord bot: {e}")
            return False
    
    async def stop(self):
        """Stop the personal Discord bot"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("🛑 Personal Discord bot stopped")
    
    async def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a Discord channel as your personal account"""
        if not self.running or not self.session:
            logger.error("❌ Personal Discord bot not running")
            return False
        
        try:
            payload = {
                "content": content,
                "tts": False
            }
            
            async with self.session.post(
                f"{self.base_url}/channels/{channel_id}/messages",
                json=payload
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Sent message as personal account to channel {channel_id}")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Failed to send message: {resp.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending message as personal account: {e}")
            return False
    
    async def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """Get information about a Discord channel"""
        if not self.running or not self.session:
            return None
        
        try:
            async with self.session.get(f"{self.base_url}/channels/{channel_id}") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"❌ Failed to get channel info: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ Error getting channel info: {e}")
            return None

# Global instance
personal_bot: Optional[PersonalDiscordBot] = None

async def initialize_personal_bot() -> bool:
    """Initialize the personal Discord bot"""
    global personal_bot
    
    token = os.getenv('PERSONAL_DISCORD_TOKEN')
    if not token:
        logger.warning("⚠️ PERSONAL_DISCORD_TOKEN not found - personal account messaging disabled")
        return False
    
    personal_bot = PersonalDiscordBot(token)
    success = await personal_bot.start()
    
    if success:
        logger.info("✅ Personal Discord bot initialized")
    else:
        logger.error("❌ Failed to initialize personal Discord bot")
        personal_bot = None
    
    return success

async def cleanup_personal_bot():
    """Cleanup the personal Discord bot"""
    global personal_bot
    if personal_bot:
        await personal_bot.stop()
        personal_bot = None

def get_personal_bot() -> Optional[PersonalDiscordBot]:
    """Get the global personal bot instance"""
    return personal_bot