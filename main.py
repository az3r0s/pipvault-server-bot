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
        
        # Fake Aidan account will be initialized in on_ready event
        logger.info("⏳ Fake Aidan account initialization deferred to on_ready event")
        
        # Load cogs
        cogs_to_load = [
            'cogs.vip_upgrade',
            'cogs.invite_tracker',
            'cogs.embed_management',
            'cogs.vip_session_manager',
            'cogs.database_export',
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
        
        # Initialize fake Aidan account system
        await self.setup_fake_aidan_account()
    
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
    
    async def setup_fake_aidan_account(self):
        """Set up fake Aidan account system for safe VIP messaging"""
        try:
            from src.fake_personal_account import initialize_fake_aidan
            
            logger.info("🔧 Setting up fake Aidan account system...")
            
            # Get VIP channel (now that bot is ready and channel cache is populated)
            vip_channel_id = self.VIP_UPGRADE_CHANNEL_ID
            if not vip_channel_id:
                logger.warning("⚠️ VIP_UPGRADE_CHANNEL_ID not set - fake account system disabled")
                return
            
            vip_channel = self.get_channel(vip_channel_id)
            if not vip_channel:
                logger.error(f"❌ VIP channel {vip_channel_id} not found - fake account system disabled")
                return
            
            if not hasattr(vip_channel, 'webhooks'):
                logger.error("❌ VIP channel doesn't support webhooks - fake account system disabled")
                return
            
            # Look for existing webhook
            webhooks = await vip_channel.webhooks()
            fake_aidan_webhook = None
            
            for webhook in webhooks:
                if webhook.name == "Fake Aidan VIP":
                    fake_aidan_webhook = webhook
                    logger.info(f"✅ Found existing Fake Aidan webhook")
                    break
            
            # Download avatar for webhook (needed for both create and update)
            import aiohttp
            avatar_bytes = None
            
            # Try to get the user's avatar directly from Discord API first
            try:
                # Get the user object to access their avatar
                user = await self.fetch_user(243819020040536065)
                logger.info(f"🔍 DEBUG: Found user: {user.display_name} ({user.id})")
                if user and user.avatar:
                    # Use Discord.py's built-in method to get avatar bytes
                    avatar_bytes = await user.avatar.read()
                    logger.info(f"✅ Downloaded avatar directly from Discord API")
                    logger.info(f"🔍 DEBUG: Avatar hash: {user.avatar.key}")
                    logger.info(f"🔍 DEBUG: Avatar URL: {user.avatar.url}")
                else:
                    logger.info("ℹ️ User has no custom avatar, trying fallback URLs...")
            except Exception as api_error:
                logger.warning(f"⚠️ Discord API avatar fetch failed: {api_error}")
            
            # Fallback to manual download if Discord API failed
            if not avatar_bytes:
                # Your Discord avatar URL - try multiple formats
                avatar_urls = [
                    "https://cdn.discordapp.com/avatars/243819020040536065/f47ac10b58cc4372a567c0e02b2c3d479378d6563d58850d46e86909e08c8b9a.png",
                    "https://cdn.discordapp.com/avatars/243819020040536065/f47ac10b58cc4372a567c0e02b2c3d479378d6563d58850d46e86909e08c8b9a.webp",
                    "https://cdn.discordapp.com/avatars/243819020040536065/f47ac10b58cc4372a567c0e02b2c3d479378d6563d58850d46e86909e08c8b9a.jpg"
                ]
                
                for avatar_url in avatar_urls:
                    try:
                        timeout = aiohttp.ClientTimeout(total=15)
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
                        }
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(avatar_url, headers=headers) as resp:
                                logger.info(f"🔍 Avatar URL {avatar_url} returned status {resp.status}")
                                if resp.status == 200:
                                    avatar_bytes = await resp.read()
                                    logger.info(f"✅ Downloaded avatar from {avatar_url} ({len(avatar_bytes)} bytes)")
                                    break
                                else:
                                    logger.warning(f"Avatar URL {avatar_url} returned {resp.status}: {resp.reason}")
                    except Exception as avatar_error:
                        logger.warning(f"Avatar download attempt failed for {avatar_url}: {avatar_error}")
                        continue
            
            if not avatar_bytes:
                logger.warning("⚠️ Could not download avatar from any source, using default Discord avatar")
            else:
                logger.info(f"✅ Avatar ready for webhook ({len(avatar_bytes)} bytes)")
            
            # Force refresh webhook avatar by recreating it (Discord caching workaround)
            if fake_aidan_webhook:
                try:
                    # Delete existing webhook to force Discord cache refresh
                    logger.info("🔄 Deleting existing webhook to refresh avatar cache...")
                    await fake_aidan_webhook.delete(reason="Refreshing avatar cache")
                    fake_aidan_webhook = None
                    logger.info("✅ Deleted old webhook - will create fresh one")
                    
                    # Small delay to ensure Discord processes the deletion
                    await asyncio.sleep(2)
                    logger.info("⏳ Waited for Discord to process webhook deletion")
                except Exception as delete_error:
                    logger.warning(f"⚠️ Failed to delete old webhook: {delete_error}")
            
                try:
                    logger.info("🔧 Creating fresh Fake Aidan VIP webhook with updated avatar...")
                    
                    # Create webhook with timeout protection
                    fake_aidan_webhook = await asyncio.wait_for(
                        vip_channel.create_webhook(
                            name="Fake Aidan VIP",
                            avatar=avatar_bytes,
                            reason="Fresh fake Aidan account with updated avatar"
                        ),
                        timeout=15.0  # 15 second timeout
                    )
                    logger.info("🎉 Created fresh Fake Aidan VIP webhook with correct avatar!")
                    
                except asyncio.TimeoutError:
                    logger.error("❌ Webhook creation timed out")
                    return
                except Exception as webhook_error:
                    logger.error(f"❌ Failed to create webhook: {webhook_error}")
                    return
            
            # Initialize fake account system
            if fake_aidan_webhook:
                try:
                    fake_success = await asyncio.wait_for(
                        initialize_fake_aidan(fake_aidan_webhook.url),
                        timeout=10.0  # 10 second timeout
                    )
                    if fake_success:
                        logger.info("✅ Fake Aidan account initialized - 100% safe messaging!")
                    else:
                        logger.error("❌ Fake Aidan account initialization failed")
                except asyncio.TimeoutError:
                    logger.error("❌ Fake Aidan initialization timed out")
                except Exception as init_error:
                    logger.error(f"❌ Fake Aidan initialization error: {init_error}")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup fake Aidan account: {e}")
            logger.info("🔄 VIP system will use regular bot messages as fallback")
    
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
            # Cleanup fake Aidan account system
            from src.fake_personal_account import cleanup_fake_accounts
            await cleanup_fake_accounts()
            logger.info("✅ Cleaned up fake Aidan account system")
        except Exception as e:
            logger.error(f"❌ Error cleaning up fake Aidan account system: {e}")
        
        # Call parent close
        await super().close()
    
    def get_env_var(self, key: str, default: str = '') -> str:
        """Get environment variable with default fallback"""
        return os.getenv(key, default)

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