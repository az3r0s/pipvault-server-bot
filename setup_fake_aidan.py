#!/usr/bin/env python3
"""
Fake Aidan Account Setup Script
===============================

This script helps you set up the webhook for the fake Aidan account system.
Run this once to create the webhook in your VIP channel.
"""

import asyncio
import os
import discord
from discord.ext import commands
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_fake_aidan_webhook():
    """Set up the fake Aidan webhook in the VIP channel"""
    
    # Bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        logger.info(f"✅ Logged in as {bot.user}")
        
        # Get VIP channel
        vip_channel_id = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '0'))
        if not vip_channel_id:
            logger.error("❌ VIP_UPGRADE_CHANNEL_ID not set in environment variables")
            await bot.close()
            return
        
        vip_channel = bot.get_channel(vip_channel_id)
        if not vip_channel:
            logger.error(f"❌ VIP channel {vip_channel_id} not found")
            await bot.close()
            return
        
        logger.info(f"📍 Found VIP channel: {vip_channel.name}")
        
        # Check for existing webhook
        webhooks = await vip_channel.webhooks()
        fake_aidan_webhook = None
        
        for webhook in webhooks:
            if webhook.name == "Fake Aidan VIP":
                fake_aidan_webhook = webhook
                logger.info(f"✅ Found existing webhook: {webhook.url}")
                break
        
        # Create webhook if it doesn't exist
        if not fake_aidan_webhook:
            try:
                # Your actual Discord avatar URL - replace with your real one
                avatar_url = "https://cdn.discordapp.com/avatars/243819020040536065/f47ac10b58cc4372a567c0e02b2c3d479378d6563d58850d46e86909e08c8b9a.png"
                
                # Download avatar for webhook
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url) as resp:
                        if resp.status == 200:
                            avatar_bytes = await resp.read()
                        else:
                            avatar_bytes = None
                            logger.warning("⚠️ Could not download avatar, using default")
                
                # Create webhook
                fake_aidan_webhook = await vip_channel.create_webhook(
                    name="Fake Aidan VIP",
                    avatar=avatar_bytes,
                    reason="Fake Aidan account for safe VIP messaging"
                )
                
                logger.info(f"🎉 Created new webhook!")
                logger.info(f"🔗 Webhook URL: {fake_aidan_webhook.url}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create webhook: {e}")
                await bot.close()
                return
        
        # Test the webhook
        try:
            from src.fake_personal_account import initialize_fake_aidan
            success = await initialize_fake_aidan(fake_aidan_webhook.url)
            
            if success:
                logger.info("🎯 Fake Aidan account system ready!")
                logger.info("✅ Setup complete - your bot will now use safe fake account messaging")
            else:
                logger.error("❌ Failed to initialize fake Aidan account")
                
        except Exception as e:
            logger.error(f"❌ Error testing fake account: {e}")
        
        await bot.close()
    
    # Run the bot
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("❌ DISCORD_BOT_TOKEN not found in environment variables")
        return
    
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"❌ Failed to run setup bot: {e}")

if __name__ == "__main__":
    print("🔧 Setting up Fake Aidan Account Webhook...")
    print("⚠️ Make sure your environment variables are set:")
    print("   - DISCORD_BOT_TOKEN")
    print("   - VIP_UPGRADE_CHANNEL_ID")
    print()
    
    try:
        asyncio.run(setup_fake_aidan_webhook())
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled by user")
    except Exception as e:
        print(f"❌ Setup failed: {e}")