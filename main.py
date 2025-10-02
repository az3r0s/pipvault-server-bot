#!/usr/bin/env python3
"""
Zinrai Discord Server Management Bot
====================================

This bot handles all Discord server management features including:
- VIP upgrade system with invite tracking
- Ticket system
- Admin commands
- Welcome system
- Community features

Separated from the trading bot for better reliability and maintainability.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import discord
from discord.ext import commands
from discord.ext.commands import Bot

# Import shared utilities from parent trading bot
from shared.constants import Colors, Emojis
from server_bot.utils.database import ServerDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ZinraiServerBot(commands.Bot):
    """Main server management bot class"""
    
    def __init__(self):
        # Bot configuration
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.invites = True  # Required for invite tracking
        
        super().__init__(
            command_prefix='!server ',
            intents=intents,
            description="Zinrai Discord Server Management Bot",
            help_command=None
        )
        
        # Initialize database
        self.db = ServerDatabase()
        
        # Configuration
        self.GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', '0'))
        self.VIP_UPGRADE_CHANNEL_ID = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '0'))
        
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        logger.info("🚀 Setting up Zinrai Server Bot...")
        
        # Load cogs
        cogs_to_load = [
            'server_bot.cogs.vip_upgrade',
            'server_bot.cogs.invite_tracker',
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"❌ Failed to load cog {cog}: {e}")
        
        # Sync slash commands
        try:
            if self.GUILD_ID:
                guild = discord.Object(id=self.GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"✅ Synced slash commands to guild {self.GUILD_ID}")
            else:
                await self.tree.sync()
                logger.info("✅ Synced slash commands globally")
        except Exception as e:
            logger.error(f"❌ Failed to sync slash commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🎯 {self.user} is ready!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"👥 Serving {sum(guild.member_count for guild in self.guilds)} members")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Zinrai Community 👑"
            )
        )
        
        # Initialize VIP upgrade channel
        if self.VIP_UPGRADE_CHANNEL_ID:
            await self.setup_vip_upgrade_channel()
    
    async def setup_vip_upgrade_channel(self):
        """Set up the sticky embed in VIP upgrade channel"""
        try:
            channel = self.get_channel(self.VIP_UPGRADE_CHANNEL_ID)
            if channel:
                # Get VIP upgrade cog and set up sticky embed
                vip_cog = self.get_cog('VIPUpgrade')
                if vip_cog:
                    await vip_cog.setup_sticky_embed(channel)
                    logger.info(f"✅ Set up VIP upgrade channel: {channel.name}")
        except Exception as e:
            logger.error(f"❌ Failed to setup VIP upgrade channel: {e}")
    
    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        logger.error(f"Command error in {ctx.command}: {error}")
        
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=Colors.ERROR
        )
        
        try:
            await ctx.send(embed=embed, ephemeral=True)
        except:
            pass

async def main():
    """Main entry point"""
    # Check for required environment variables
    token = os.getenv('SERVER_BOT_TOKEN')
    if not token:
        logger.error("❌ SERVER_BOT_TOKEN environment variable not set!")
        return
    
    guild_id = os.getenv('DISCORD_GUILD_ID')
    if not guild_id:
        logger.error("❌ DISCORD_GUILD_ID environment variable not set!")
        return
    
    vip_channel_id = os.getenv('VIP_UPGRADE_CHANNEL_ID') 
    if not vip_channel_id:
        logger.warning("⚠️ VIP_UPGRADE_CHANNEL_ID not set - VIP upgrade system will be disabled")
    
    # Create and run bot
    bot = ZinraiServerBot()
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())