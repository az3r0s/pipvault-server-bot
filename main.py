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

# Import local utilities
from constants import Colors, Emojis
from utils.database import ServerDatabase
from utils.cloud_database import CloudAPIServerDatabase

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
        
        # Initialize database (use Cloud API if available, else SQLite only)
        try:
            cloud_url = os.getenv('CLOUD_API_URL', 'https://web-production-1299f.up.railway.app')
            if cloud_url:
                self.db = CloudAPIServerDatabase(cloud_url)
                logger.info("✅ Using Cloud API database for persistence")
            else:
                self.db = ServerDatabase("server_management.db")
                logger.info("⚠️ Using SQLite database (not persistent on Railway)")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            # Fallback to SQLite
            self.db = ServerDatabase("server_management.db")
            logger.info("📦 Fallback to SQLite database")
        
        # Configuration
        self.GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', '0'))
        self.VIP_UPGRADE_CHANNEL_ID = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '0'))
        
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        logger.info("🚀 Setting up Zinrai Server Bot...")
        
        # Initialize Telegram manager
        try:
            import src.telegram.manager as telegram_module
            
            # Initialize the manager if credentials are available
            api_id = os.getenv('TELEGRAM_API_ID')
            api_hash = os.getenv('TELEGRAM_API_HASH')
            
            if api_id and api_hash:
                manager = await telegram_module.initialize_telegram_manager()
                print(f"🔍 DEBUG main.py: initialize_telegram_manager returned: {manager}")
                print(f"🔍 DEBUG main.py: manager type: {type(manager)}")
                
                # Verify the global manager is set directly from the module
                print(f"🔍 DEBUG main.py: telegram_module.telegram_manager after init: {telegram_module.telegram_manager}")
                print(f"🔍 DEBUG main.py: telegram_module.telegram_manager type: {type(telegram_module.telegram_manager)}")
                
                logger.info("✅ Telegram manager initialized")
            else:
                print(f"🔍 DEBUG main.py: Missing credentials - api_id={api_id}, api_hash={'***' if api_hash else None}")
                logger.warning("⚠️ Telegram credentials not found - VIP chat system will be limited")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram manager: {e}")
        
        # Initialize personal Discord bot for natural messaging
        try:
            from src.personal_discord import initialize_personal_bot
            personal_success = await initialize_personal_bot()
            if personal_success:
                logger.info("✅ Personal Discord bot initialized")
            else:
                logger.warning("⚠️ Personal Discord bot not available - will use fallback methods")
        except Exception as e:
            logger.error(f"❌ Failed to initialize personal Discord bot: {e}")
        
        # Load cogs
        cogs_to_load = [
            'cogs.vip_upgrade',
            'cogs.invite_tracker',
            'cogs.embed_management',
            'cogs.vip_session_manager',
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"❌ Failed to load cog {cog}: {e}")
        
        # Initialize cloud database if using CloudAPIServerDatabase
        if hasattr(self.db, 'restore_from_cloud'):
            try:
                await self.db.restore_from_cloud()
                logger.info("✅ Restored data from cloud API")
                # Start periodic backup task
                self.loop.create_task(self.db.periodic_backup())
                logger.info("✅ Started periodic cloud backup")
            except Exception as e:
                logger.error(f"❌ Cloud database setup failed: {e}")
        
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
    
    async def close(self):
        """Cleanup when bot is shutting down"""
        try:
            # Cleanup personal Discord bot
            from src.personal_discord import cleanup_personal_bot
            await cleanup_personal_bot()
            logger.info("✅ Cleaned up personal Discord bot")
        except Exception as e:
            logger.error(f"❌ Error cleaning up personal Discord bot: {e}")
        
        # Call parent close
        await super().close()

async def main():
    """Main entry point"""
    # Check for required environment variables
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("❌ DISCORD_BOT_TOKEN environment variable not set!")
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