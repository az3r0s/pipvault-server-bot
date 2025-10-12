"""
VIP Session Management Cog
==========================

Handles VIP chat sessions including:
- Thread creation and management
- Session lifecycle management
- Message routing between Discord and Telegram
- Integration with existing VIP upgrade system
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

# Import the Telegram manager
import sys
from pathlib import Path
import asyncio

sys.path.append(str(Path(__file__).parent.parent))

try:
    from src.telegram import telegram_manager
except ImportError:
    telegram_manager = None

logger = logging.getLogger(__name__)

class VIPSessionManager(commands.Cog):
    """Manages VIP chat sessions with Telegram integration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_threads: Dict[str, discord.Thread] = {}  # discord_user_id -> thread
        self.thread_sessions: Dict[int, str] = {}  # thread_id -> discord_user_id
        
        # Configuration
        self.VIP_UPGRADE_CHANNEL_ID = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '0'))
        self.VIP_ROLE_ID = os.getenv('VIP_ROLE_ID', '0')
        self.TELEGRAM_VA_USERNAME = os.getenv('TELEGRAM_VA_USERNAME', '')
        self.VA_DISCORD_USER_ID = int(os.getenv('VA_DISCORD_USER_ID', '0'))  # Your Discord user ID
        
        # Start cleanup task
        self.cleanup_expired_sessions.start()
    
    async def cog_load(self):
        """Called when cog is loaded"""
        logger.info("💬 VIP Session Manager loaded")
        
        # Set up Telegram callback for VA replies
        if telegram_manager:
            telegram_manager.set_discord_callback(self.handle_va_reply)
    
    async def cog_unload(self):
        """Called when cog is unloaded"""
        self.cleanup_expired_sessions.cancel()
    
    async def create_vip_session(self, interaction: discord.Interaction) -> bool:
        """Create a new VIP chat session for a user"""
        user_id = str(interaction.user.id)
        
        try:
            # Check if user already has VIP role
            if self.VIP_ROLE_ID in [str(role.id) for role in interaction.user.roles]:
                await interaction.response.send_message(
                    "❌ **VIP users cannot use this system.** This feature is for regular users only.\n"
                    "As a VIP member, you already have access to premium channels and support.",
                    ephemeral=True
                )
                return False
            
            # Check if user already has an active session  
            if user_id in self.active_threads:
                await interaction.response.send_message(
                    "ℹ️ You already have an active VIP chat session. Please complete your current session first.",
                    ephemeral=True
                )
                return False
            
            # Get available Telegram account
            if not telegram_manager:
                await interaction.response.send_message(
                    "❌ VIP chat system is currently unavailable. Please try again later.",
                    ephemeral=True
                )
                return False
            
            telegram_account = await telegram_manager.assign_account(user_id)
            if not telegram_account:
                await interaction.response.send_message(
                    "⏳ All VIP chat slots are currently busy. Please try again in a few minutes.",
                    ephemeral=True
                )
                return False
            
            # Create private thread for the user
            channel = self.bot.get_channel(self.VIP_UPGRADE_CHANNEL_ID)
            if not channel:
                await interaction.response.send_message(
                    "❌ VIP upgrade channel not found. Please contact support.",
                    ephemeral=True
                )
                await telegram_manager.release_account(user_id)
                return False
            
            # Create thread
            thread_name = f"VIP Chat - {interaction.user.display_name}"
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                reason=f"VIP chat session for {interaction.user.name}"
            )
            
            # Add user to thread
            await thread.add_user(interaction.user)
            
            # Store session info
            self.active_threads[user_id] = thread
            self.thread_sessions[thread.id] = user_id
            
            # Send welcome message to thread
            embed = discord.Embed(
                title="🎯 VIP Chat Session Started",
                description=f"Welcome {interaction.user.mention}! Your private VIP chat session is now active.",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📱 How It Works",
                value=(
                    "• Messages you send here will be forwarded to our VA on Telegram\n"
                    "• VA replies will appear in this thread\n"
                    "• This session will remain active for 24 hours\n"
                    "• Type `!end` to complete your session early"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔄 Connection Status",
                value=f"✅ Connected via account: `{telegram_account.phone[-4:]}`",
                inline=False
            )
            
            # Get referring staff member (from existing invite tracking)
            referring_staff = await self._get_referring_staff(interaction.user.id)
            if referring_staff:
                embed.add_field(
                    name="👨‍💼 Your Referral Agent",
                    value=f"**{referring_staff['staff_name']}** (`{referring_staff['staff_username']}`)",
                    inline=False
                )
            
            await thread.send(embed=embed)
            
            # Respond with message in vip-upgrade channel (ephemeral to user only)
            embed_response = discord.Embed(
                title="🎯 VIP Upgrade Session Started",
                description=f"Your private VIP chat thread has been created!\n\n**Thread:** {thread.mention}\n\nClick the link above to access your private chat with our VAs.",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            embed_response.add_field(
                name="💬 How to Use",
                value=(
                    "• Click the thread link above to enter your chat\n"
                    "• Messages you send will be forwarded to our VA team\n"
                    "• Get personalized VIP upgrade assistance\n"
                    "• Session active for 24 hours"
                ),
                inline=False
            )
            
            if referring_staff:
                embed_response.add_field(
                    name="👨‍💼 Your Agent",
                    value=f"**{referring_staff['staff_name']}**",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed_response, ephemeral=True)
            
            # Log the session creation
            await self._log_session_creation(interaction.user, thread, telegram_account, referring_staff)
            
            logger.info(f"✅ Created VIP session for {interaction.user.name} in thread {thread.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create VIP session for {interaction.user.name}: {e}")
            await interaction.response.send_message(
                "❌ Failed to create VIP chat session. Please try again or contact support.",
                ephemeral=True
            )
            
            # Cleanup on error
            if user_id in self.active_threads:
                del self.active_threads[user_id]
            if telegram_manager:
                await telegram_manager.release_account(user_id)
            
            return False
    
    async def _get_referring_staff(self, user_id: int) -> Optional[Dict]:
        """Get the staff member who referred this user (existing functionality)"""
        try:
            # This would integrate with the existing invite tracking system
            # For now, return None - will be implemented when we integrate with existing DB
            return None
        except Exception as e:
            logger.error(f"Error getting referring staff for user {user_id}: {e}")
            return None
    
    async def _log_session_creation(self, user: discord.User, thread: discord.Thread, 
                                  telegram_account, referring_staff: Optional[Dict]):
        """Log VIP session creation for analytics"""
        try:
            # This would log to the database for analytics
            # Integrate with existing VIP upgrade tracking system
            logger.info(f"📊 VIP session logged: User {user.name}, Thread {thread.id}, Account {telegram_account.phone}")
        except Exception as e:
            logger.error(f"Error logging session creation: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages in VIP chat threads"""
        # Only process messages in active VIP threads
        if (message.channel.type != discord.ChannelType.private_thread or 
            message.author.bot or
            message.channel.id not in self.thread_sessions):
            return
        
        user_id = self.thread_sessions[message.channel.id]
        
        # Handle end session command
        if message.content.lower().strip() == "!end":
            await self._end_session(message.channel, user_id)
            return
        
        # Forward message to Telegram
        if telegram_manager:
            success = await telegram_manager.send_message(
                user_id, 
                self.TELEGRAM_VA_USERNAME, 
                f"**{message.author.display_name}**: {message.content}"
            )
            
            if success:
                # Add reaction to confirm message was sent
                await message.add_reaction("📤")
            else:
                await message.reply("❌ Failed to send message to VA. Please try again.")
    
    async def handle_va_reply(self, user_id: str, message_content: str):
        """Handle VA reply from Telegram - send as your actual Discord account"""
        try:
            if user_id not in self.active_threads:
                logger.warning(f"No active thread found for user {user_id}")
                return False
            
            thread = self.active_threads[user_id]
            
            # Option 1: Use webhook on parent channel to send as your Discord account
            if self.VA_DISCORD_USER_ID:
                va_user = self.bot.get_user(self.VA_DISCORD_USER_ID)
                if va_user and thread.parent:
                    try:
                        # Get or create webhook on parent channel
                        webhooks = await thread.parent.webhooks()
                        webhook = None
                        
                        # Find existing webhook or create new one
                        for wh in webhooks:
                            if wh.name == "VIP_VA_Webhook":
                                webhook = wh
                                break
                        
                        if not webhook:
                            webhook = await thread.parent.create_webhook(name="VIP_VA_Webhook")
                        
                        # Send message as your Discord account in the thread
                        await webhook.send(
                            content=message_content,
                            username=va_user.display_name,
                            avatar_url=va_user.display_avatar.url,
                            thread=thread
                        )
                        
                        logger.info(f"✅ Sent VA reply as {va_user.display_name} to thread {thread.id}")
                        return True
                    except Exception as webhook_error:
                        logger.warning(f"Webhook failed, falling back to embed: {webhook_error}")
            
            # Option 2: Fallback to bot message with clear VA attribution
            embed = discord.Embed(
                description=message_content,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_author(name="VA Response", icon_url=self.bot.user.display_avatar.url)
            
            await thread.send(embed=embed)
            logger.info(f"✅ Sent VA reply as embed to thread {thread.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending VA reply: {e}")
            return False
    
    async def _end_session(self, thread: discord.Thread, user_id: str):
        """End a VIP chat session"""
        try:
            # Release Telegram account
            if telegram_manager:
                await telegram_manager.release_account(user_id)
            
            # Clean up session tracking
            if user_id in self.active_threads:
                del self.active_threads[user_id]
            if thread.id in self.thread_sessions:
                del self.thread_sessions[thread.id]
            
            # Send completion message
            embed = discord.Embed(
                title="✅ VIP Chat Session Completed",
                description="Your VIP chat session has been completed successfully.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value=(
                    "• This thread will be archived shortly\n"
                    "• You can create a new session anytime using the VIP upgrade button\n"
                    "• Thank you for using our VIP chat system!"
                ),
                inline=False
            )
            
            await thread.send(embed=embed)
            
            # Archive thread after a delay
            await asyncio.sleep(30)
            await thread.edit(archived=True)
            
            logger.info(f"✅ Ended VIP session for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error ending VIP session for user {user_id}: {e}")
    
    @tasks.loop(minutes=30)
    async def cleanup_expired_sessions(self):
        """Clean up expired VIP sessions"""
        try:
            if telegram_manager:
                await telegram_manager.cleanup_expired_sessions()
            
            # Clean up orphaned thread sessions
            current_time = datetime.now()
            expired_threads = []
            
            for user_id, thread in self.active_threads.items():
                try:
                    # Check if thread still exists and get creation time
                    if thread.created_at:
                        age = current_time - thread.created_at.replace(tzinfo=None)
                        if age > timedelta(hours=24):  # 24 hour timeout
                            expired_threads.append(user_id)
                except:
                    # Thread no longer exists
                    expired_threads.append(user_id)
            
            for user_id in expired_threads:
                thread = self.active_threads.get(user_id)
                if thread:
                    await self._end_session(thread, user_id)
            
            if expired_threads:
                logger.info(f"🧹 Cleaned up {len(expired_threads)} expired VIP sessions")
                
        except Exception as e:
            logger.error(f"❌ Error in session cleanup: {e}")
    
    @cleanup_expired_sessions.before_loop
    async def before_cleanup(self):
        """Wait for bot to be ready before starting cleanup task"""
        await self.bot.wait_until_ready()
    
    # Admin commands for session management
    @app_commands.command(name="vip-status", description="Check VIP chat system status")
    @app_commands.default_permissions(administrator=True)
    async def vip_status(self, interaction: discord.Interaction):
        """Check status of VIP chat system"""
        try:
            if not telegram_manager:
                await interaction.response.send_message("❌ Telegram manager not initialized", ephemeral=True)
                return
            
            status = telegram_manager.get_status()
            
            embed = discord.Embed(
                title="📊 VIP Chat System Status",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🏢 Telegram Accounts",
                value=f"Connected: {status['connected_accounts']}/{status['total_accounts']}",
                inline=True
            )
            
            embed.add_field(
                name="💬 Active Sessions",
                value=f"{status['active_sessions']}/{status['max_sessions']}",
                inline=True
            )
            
            embed.add_field(
                name="🔄 Discord Threads",
                value=f"{len(self.active_threads)} active",
                inline=True
            )
            
            # Add account details
            account_info = []
            for acc in status['accounts']:
                status_emoji = "🟢" if acc['connected'] else "🔴"
                user_info = f" (User: {acc['assigned_user'][-4:]})" if acc['assigned_user'] else ""
                account_info.append(f"{status_emoji} {acc['phone'][-4:]}{user_info}")
            
            if account_info:
                embed.add_field(
                    name="📱 Account Status",
                    value="\n".join(account_info[:10]),  # Limit to 10 accounts
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error in vip_status command: {e}")
            await interaction.response.send_message(
                f"❌ Error retrieving status: {str(e)}", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(VIPSessionManager(bot))