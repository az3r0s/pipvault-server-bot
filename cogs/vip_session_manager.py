"""
VIP Session Management
=====================

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

# We'll get telegram_manager dynamically to avoid import issues
def get_telegram_manager():
    """Get the global telegram manager instance"""
    try:
        import src.telegram.manager as telegram_module
        print(f"🔍 DEBUG get_telegram_manager: Successfully imported, telegram_manager = {telegram_module.telegram_manager}")
        print(f"🔍 DEBUG get_telegram_manager: Type = {type(telegram_module.telegram_manager)}")
        return telegram_module.telegram_manager
    except ImportError as e:
        print(f"🔍 DEBUG get_telegram_manager: ImportError = {e}")
        return None

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
        telegram_manager = get_telegram_manager()
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
            telegram_manager = get_telegram_manager()
            print(f"🔍 DEBUG VIPSessionManager: telegram_manager = {telegram_manager}")
            print(f"🔍 DEBUG VIPSessionManager: telegram_manager type = {type(telegram_manager)}")
            if telegram_manager is None:
                print("🔍 DEBUG VIPSessionManager: telegram_manager is None")
            if not telegram_manager:
                print(f"🔍 DEBUG VIPSessionManager: telegram_manager failed boolean check")
                await interaction.response.send_message(
                    "❌ VIP chat system is currently unavailable (session manager - no telegram_manager). Please try again later.",
                    ephemeral=True
                )
                return False
            else:
                print(f"🔍 DEBUG VIPSessionManager: telegram_manager is available, proceeding")
            
            telegram_account = await telegram_manager.assign_account(user_id)
            if not telegram_account:
                await interaction.response.send_message(
                    "⏳ All VIP chat slots are currently busy. Please try again in a few minutes.",
                    ephemeral=True
                )
                return False
            
            # Update dummy account display name to match Discord user
            display_name_updated = await telegram_manager.update_account_display_name(
                user_id, 
                interaction.user.display_name
            )
            if display_name_updated:
                logger.info(f"✅ Updated Telegram display name to '{interaction.user.display_name}' for user {interaction.user.name}")
            else:
                logger.warning(f"⚠️ Failed to update Telegram display name for user {interaction.user.name}")
            
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
            
            # Add VA (your Discord account) to thread so you can see and respond
            if self.VA_DISCORD_USER_ID:
                try:
                    va_user = self.bot.get_user(self.VA_DISCORD_USER_ID)
                    if va_user:
                        await thread.add_user(va_user)
                        logger.info(f"✅ Added VA {va_user.name} to thread {thread.id}")
                    else:
                        logger.warning(f"⚠️ Could not find VA user with ID {self.VA_DISCORD_USER_ID}")
                except Exception as e:
                    logger.error(f"❌ Failed to add VA to thread: {e}")
            
            # Store session info
            self.active_threads[user_id] = thread
            self.thread_sessions[thread.id] = user_id
            
            # Send welcome message to thread
            embed = discord.Embed(
                title="🎯 VIP Chat Session Started",
                description=f"Welcome {interaction.user.mention}! Your private VIP chat session is now active.",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="📋 Getting Started",
                value=(
                    "• Send a message in this chat to begin your VIP upgrade consultation\n"
                    "• Our staff team will respond to you shortly\n"
                    "• This session will remain active for 24 hours\n"
                    "• Type `!end` to complete your session early"
                ),
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
                description=f"Your private VIP chat thread has been created!\n\n**Thread:** {thread.mention}\n\nClick the link above to access your private chat with our staff team.",
                color=discord.Color.gold()
            )
            
            embed_response.add_field(
                name="💬 How to Use",
                value=(
                    "• Click the thread link above to enter your chat\n"
                    "• Messages you send will be handled by our staff team\n"
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
            telegram_manager = get_telegram_manager()
            if telegram_manager:
                await telegram_manager.release_account(user_id)
            
            return False
    
    async def _get_referring_staff(self, user_id: int) -> Optional[Dict]:
        """Get the staff member who referred this user (existing functionality)"""
        try:
            logger.info(f"🔍 DEBUG: Looking up referring staff for user {user_id}")
            
            # Get user's invite information
            try:
                invite_info = self.bot.db.get_user_invite_info(user_id)
                logger.info(f"🔍 DEBUG: Invite info for user {user_id}: {invite_info}")
            except Exception as db_error:
                logger.error(f"Database error getting invite info for user {user_id}: {db_error}")
                return None
                
            if not invite_info:
                logger.info(f"No invite info found for user {user_id}")
                return None
            
            # Get staff configuration based on the invite
            try:
                staff_config = self.bot.db.get_staff_config_by_invite(invite_info['invite_code'])
                logger.info(f"🔍 DEBUG: Staff config for invite {invite_info['invite_code']}: {staff_config}")
            except Exception as db_error:
                logger.error(f"Database error getting staff config for invite {invite_info['invite_code']}: {db_error}")
                return None
                
            if not staff_config:
                logger.info(f"No staff config found for invite {invite_info['invite_code']}")
                return None
            
            # Debug the staff_config structure
            logger.info(f"🔍 DEBUG: Staff config keys: {list(staff_config.keys()) if isinstance(staff_config, dict) else 'Not a dict'}")
            
            return {
                'staff_id': staff_config.get('staff_id') or staff_config.get('staff_user_id') or staff_config.get('discord_id'),
                'staff_name': staff_config.get('staff_name') or staff_config.get('username', 'Unknown'),
                'staff_username': staff_config.get('staff_username') or staff_config.get('username', 'Unknown'),
                'vantage_referral_link': staff_config.get('ib_link', '') or staff_config.get('vantage_referral_link', ''),
                'vantage_referral_code': self._extract_referral_code(staff_config.get('ib_link', '') or staff_config.get('vantage_referral_link', ''))
            }
            
        except Exception as e:
            logger.error(f"Error getting referring staff for user {user_id}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def _extract_referral_code(self, referral_link: str) -> str:
        """Extract referral code from Vantage referral link"""
        try:
            import base64
            import urllib.parse
            
            # Parse the URL to get the affid parameter
            parsed = urllib.parse.urlparse(referral_link)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            if 'affid' in query_params:
                # Decode the base64 encoded affiliate ID
                encoded_affid = query_params['affid'][0]
                decoded_code = base64.b64decode(encoded_affid + '==').decode('utf-8')  # Add padding if needed
                return decoded_code
            
            return ""
        except Exception as e:
            logger.error(f"Error extracting referral code from {referral_link}: {e}")
            return ""
    
    def _replace_referral_info(self, message: str, referring_staff: Optional[Dict]) -> str:
        """Replace generic referral links/codes with personalized ones"""
        if not referring_staff:
            logger.info("No referring staff found, keeping original referral info")
            return message
        
        try:
            # Define the generic referral info to replace
            generic_link = 'https://www.vantagemarkets.com/open-live-account/?affid=NzQ3MDMyMA=='
            generic_code = '7470320'
            
            # Get personalized referral info
            personal_link = referring_staff.get('vantage_referral_link', '')
            personal_code = referring_staff.get('vantage_referral_code', '')
            
            if not personal_link or not personal_code:
                logger.warning(f"Missing referral info for staff {referring_staff.get('staff_name', 'Unknown')}")
                return message
            
            # Replace in message
            replaced_message = message
            
            # Replace generic link with personal link
            if generic_link in replaced_message:
                replaced_message = replaced_message.replace(generic_link, personal_link)
                logger.info(f"Replaced generic referral link with {referring_staff.get('staff_name', 'Unknown')}'s link")
            
            # Replace generic code with personal code  
            if generic_code in replaced_message:
                replaced_message = replaced_message.replace(generic_code, personal_code)
                logger.info(f"Replaced generic referral code with {referring_staff.get('staff_name', 'Unknown')}'s code: {personal_code}")
            
            return replaced_message
            
        except Exception as e:
            logger.error(f"Error replacing referral info: {e}")
            return message
    
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
        
        # CRITICAL: Prevent echo loop - don't forward messages from personal Discord account
        personal_discord_id = 243819020040536065  # thegoldtradingresults
        if message.author.id == personal_discord_id:
            logger.info(f"🔍 DEBUG: Ignoring message from personal Discord account to prevent echo loop")
            return
        
        user_id = self.thread_sessions[message.channel.id]
        
        # Handle end session command
        if message.content.lower().strip() == "!end":
            await self._end_session(message.channel, user_id)
            return
        
        # Forward message to Telegram - send as natural conversation
        telegram_manager = get_telegram_manager()
        if telegram_manager:
            # Format as natural message (VA sees this as coming from the dummy account)
            natural_message = f"{message.content}"
            
            success = await telegram_manager.send_message(
                user_id, 
                self.TELEGRAM_VA_USERNAME, 
                natural_message
            )
            
            if not success:
                await message.reply("❌ Failed to send message to VA. Please try again.")
    
    async def handle_va_reply(self, user_id: str, message_content: str):
        """Handle VA reply from Telegram - send as your actual Discord account"""
        try:
            logger.info(f"🔍 DEBUG: Handling VA reply for user {user_id}: {message_content[:50]}...")
            logger.info(f"🔍 DEBUG: Active threads: {list(self.active_threads.keys())}")
            
            if user_id not in self.active_threads:
                logger.warning(f"No active thread found for user {user_id}")
                return False
            
            thread = self.active_threads[user_id]
            logger.info(f"🔍 DEBUG: Found thread {thread.id} for user {user_id}")
            
            # Get referring staff info for this user and replace referral links/codes
            referring_staff = await self._get_referring_staff(int(user_id))
            processed_message = self._replace_referral_info(message_content, referring_staff)
            
            if processed_message != message_content:
                logger.info(f"📋 Processed referral replacements for user {user_id}")
            else:
                logger.info(f"ℹ️ No referral replacements needed for user {user_id}")
            
            # Option 1: Use personal Discord bot to send as your actual account (no APP tag)
            try:
                from src.personal_discord import get_personal_bot
                personal_bot = get_personal_bot()
                
                if personal_bot and personal_bot.running:
                    logger.info(f"🔍 DEBUG: Sending message via personal Discord bot...")
                    success = await personal_bot.send_message(str(thread.id), processed_message)
                    
                    if success:
                        logger.info(f"✅ Sent VA reply as personal account to thread {thread.id}")
                        return True
                    else:
                        logger.warning(f"⚠️ Personal bot message failed, trying fallback...")
                else:
                    logger.warning(f"⚠️ Personal Discord bot not available, using fallback...")
                    
            except Exception as personal_error:
                logger.error(f"❌ Personal bot failed: {personal_error}")
            
            # Option 2: Fallback to regular bot message (clean, no embed)
            logger.info(f"🔍 DEBUG: Using fallback bot message...")
            await thread.send(processed_message)
            logger.info(f"✅ Sent VA reply as bot message to thread {thread.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending VA reply: {e}")
            return False
    
    async def _end_session(self, thread: discord.Thread, user_id: str):
        """End a VIP chat session"""
        try:
            # Clear chat history and release Telegram account
            telegram_manager = get_telegram_manager()
            if telegram_manager:
                # Clear chat history between dummy account and VA
                history_cleared = await telegram_manager.clear_chat_history(user_id, self.TELEGRAM_VA_USERNAME)
                if history_cleared:
                    logger.info(f"✅ Cleared chat history for user {user_id}")
                else:
                    logger.warning(f"⚠️ Failed to clear chat history for user {user_id}")
                
                # Release the account
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
                color=discord.Color.green()
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
            telegram_manager = get_telegram_manager()
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
            telegram_manager = get_telegram_manager()
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