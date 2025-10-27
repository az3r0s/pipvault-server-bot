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
from typing import Optional, Dict, Union

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
        self.threads_awaiting_first_message: set = set()  # thread_ids where user hasn't sent first message yet
        
        # Configuration
        self.GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', '0'))  # Discord server ID
        self.VIP_UPGRADE_CHANNEL_ID = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '0'))
        self.VIP_ROLE_ID = os.getenv('VIP_ROLE_ID', '0')
        self.TELEGRAM_VA_USERNAME = os.getenv('TELEGRAM_VA_USERNAME', '')
        self.VA_DISCORD_USER_ID = int(os.getenv('VA_DISCORD_USER_ID', '0'))  # Your Discord user ID
        self.ADMIN_USER_ID = 243819020040536065  # thegoldtradingresults - for private error notifications
        
        # VIP Group monitoring
        self.TELEGRAM_VIP_GROUP_ID = os.getenv('TELEGRAM_VIP_GROUP_ID', '')  # Chat ID of VIP group
        self.TELEGRAM_VIP_GROUP_USERNAME = os.getenv('TELEGRAM_VIP_GROUP_USERNAME', '')  # @vipgroup username
        
        # Track completed upgrades
        self.completed_upgrades: set = set()  # discord_user_ids that completed VIP upgrade
        
        # Remove session timeout - sessions only end manually or when completed
        # self.session_timeout_hours = int(os.getenv('VIP_SESSION_TIMEOUT_HOURS', '72'))  # REMOVED
        
        # Start monitoring task (replaces cleanup task)
        self.monitor_vip_completions.start()
    
    async def cog_load(self):
        """Called when cog is loaded"""
        logger.info("💬 VIP Session Manager loaded")
        
        # Set up Telegram callback for VA replies
        telegram_manager = get_telegram_manager()
        if telegram_manager:
            telegram_manager.set_discord_callback(self.handle_va_reply)
    
    async def cog_unload(self):
        """Called when cog is unloaded"""
        self.monitor_vip_completions.cancel()
    
    async def create_vip_session(self, interaction: discord.Interaction) -> bool:
        """Create a new VIP chat session for a user"""
        user_id = str(interaction.user.id)
        
        try:
            # Check if user already has VIP role (handle both User and Member types)
            user_roles = getattr(interaction.user, 'roles', [])
            if self.VIP_ROLE_ID in [str(role.id) for role in user_roles]:
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
            self.threads_awaiting_first_message.add(thread.id)  # Mark as awaiting first message
            
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
                    "• This session will remain active until your VIP upgrade is complete\n"
                    "• Type `!end` to close your session early if needed"
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
                    "• Session remains active until your VIP upgrade is complete"
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
            
            # Send automatic referral message to VA when session starts
            await self._send_va_referral_message(user_id, interaction.user, referring_staff)
            
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
                'full_name': staff_config.get('full_name', staff_config.get('staff_name') or staff_config.get('username', 'Unknown')),
                'vantage_email': staff_config.get('vantage_email', 'unknown@email.com'),
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
    
    async def _notify_staff_privately(self, thread: discord.Thread, error_message: str):
        """Send private notification to staff about technical issues in the thread without alerting the user"""
        try:
            # Send message in the thread but mention only the staff member
            staff_user = self.bot.get_user(self.ADMIN_USER_ID)
            
            if staff_user:
                # Create staff-only notification in the thread
                embed = discord.Embed(
                    title="🔧 Staff Alert - VA Communication Issue",
                    description=error_message,
                    color=0xff0000  # Red for errors
                )
                embed.add_field(
                    name="Technical Details", 
                    value="Telegram session disconnected or TELEGRAM_VA_USERNAME misconfigured", 
                    inline=False
                )
                embed.set_footer(text="This notification is only visible to staff")
                
                # Send in thread with staff mention but make it clear it's staff-only
                await thread.send(
                    content=f"{staff_user.mention} 🚨 **Staff Only**", 
                    embed=embed,
                    suppress_embeds=False
                )
                logger.info(f"📬 Sent staff notification in thread {thread.id} about VA communication issue")
            else:
                logger.error(f"❌ Could not find staff user {self.ADMIN_USER_ID} to notify about VIP issue")
                
        except Exception as notification_error:
            logger.error(f"❌ Failed to send staff notification in thread: {notification_error}")

    async def _send_va_referral_message(self, user_id: str, discord_user: Union[discord.User, discord.Member], referring_staff: Optional[Dict]):
        """Send automatic referral message to VA when a new chat session is created"""
        try:
            # Only send referral message if we have referring staff info
            if not referring_staff:
                logger.info(f"No referring staff found for user {discord_user.name}, skipping VA referral message")
                return
            
            # Check if TELEGRAM_VA_USERNAME is configured
            if not self.TELEGRAM_VA_USERNAME:
                logger.warning(f"⚠️ TELEGRAM_VA_USERNAME not configured, skipping VA referral message for {discord_user.name}")
                return
            
            # Extract full name and vantage email from staff config
            full_name = referring_staff.get('full_name', referring_staff.get('staff_name', 'Unknown'))
            vantage_email = referring_staff.get('vantage_email', 'unknown@email.com')
            
            # Create the referral message
            referral_message = f"This user is for '{full_name}', Vantage email: '{vantage_email}'"
            
            # Send to VA via Telegram with error handling for disconnected sessions
            telegram_manager = get_telegram_manager()
            if telegram_manager:
                try:
                    success = await telegram_manager.send_message(
                        user_id,
                        self.TELEGRAM_VA_USERNAME, 
                        referral_message
                    )
                    
                    if success:
                        logger.info(f"✅ Sent VA referral message for user {discord_user.name}: {referral_message}")
                    else:
                        logger.error(f"❌ Failed to send VA referral message for user {discord_user.name}")
                        
                except Exception as telegram_error:
                    # Handle specific Telegram connection errors
                    error_str = str(telegram_error).lower()
                    if "cannot send requests while disconnected" in error_str or "sessionrevokederror" in error_str:
                        logger.error(f"🔌 Telegram session disconnected, cannot send VA referral message for {discord_user.name}")
                        logger.info(f"💡 Consider reconnecting Telegram session or checking TELEGRAM_VA_USERNAME configuration")
                    else:
                        logger.error(f"❌ Telegram error sending VA referral message for user {discord_user.name}: {telegram_error}")
            else:
                logger.error(f"❌ No telegram manager available to send referral message for user {discord_user.name}")
                
        except Exception as e:
            logger.error(f"❌ Error sending VA referral message for user {discord_user.name}: {e}")
    
    async def _send_staff_info_to_va(self, user_id: str, referring_staff: Optional[Dict], thread: discord.Thread):
        """Send staff information to VA when user sends their first message"""
        try:
            # Only send if we have referring staff info
            if not referring_staff:
                logger.info(f"No referring staff found for thread {thread.id}, skipping staff info message")
                await self._notify_staff_privately(
                    thread, 
                    f"⚠️ No referring staff found for user - cannot send staff information to VA"
                )
                return
            
            # Check if TELEGRAM_VA_USERNAME is configured
            if not self.TELEGRAM_VA_USERNAME:
                logger.warning(f"⚠️ TELEGRAM_VA_USERNAME not configured, skipping staff info message")
                await self._notify_staff_privately(
                    thread, 
                    f"⚠️ TELEGRAM_VA_USERNAME not configured - cannot send staff information to VA"
                )
                return
            
            # Extract full name and vantage email from staff config
            full_name = referring_staff.get('full_name', referring_staff.get('staff_name', 'Unknown'))
            vantage_email = referring_staff.get('vantage_email', 'unknown@email.com')
            
            # Create the staff information message in the requested format
            staff_info_message = f"THIS USER IS UPGRADING FOR: {full_name}\nWITH EMAIL: {vantage_email}"
            
            # Send to VA via Telegram with error handling for disconnected sessions
            telegram_manager = get_telegram_manager()
            if telegram_manager:
                try:
                    success = await telegram_manager.send_message(
                        user_id,
                        self.TELEGRAM_VA_USERNAME, 
                        staff_info_message
                    )
                    
                    if success:
                        logger.info(f"✅ Sent staff info to VA for thread {thread.id}: {staff_info_message}")
                    else:
                        logger.error(f"❌ Failed to send staff info to VA for thread {thread.id}")
                        await self._notify_staff_privately(
                            thread, 
                            f"❌ Failed to send staff information to VA (send_message returned False)"
                        )
                        
                except Exception as telegram_error:
                    # Handle specific Telegram connection errors
                    error_str = str(telegram_error).lower()
                    if "cannot send requests while disconnected" in error_str or "sessionrevokederror" in error_str:
                        logger.error(f"🔌 Telegram session disconnected, cannot send staff info for thread {thread.id}")
                        await self._notify_staff_privately(
                            thread, 
                            f"🔌 Telegram session disconnected - cannot send staff information to VA\nError: {telegram_error}"
                        )
                    else:
                        logger.error(f"❌ Telegram error sending staff info for thread {thread.id}: {telegram_error}")
                        await self._notify_staff_privately(
                            thread, 
                            f"❌ Telegram communication error - cannot send staff information to VA\nError: {telegram_error}"
                        )
            else:
                logger.error(f"❌ No telegram manager available to send staff info for thread {thread.id}")
                await self._notify_staff_privately(
                    thread, 
                    f"❌ Telegram manager unavailable - cannot send staff information to VA"
                )
                
        except Exception as e:
            logger.error(f"❌ Error sending staff info to VA for thread {thread.id}: {e}")
            await self._notify_staff_privately(
                thread, 
                f"❌ Unexpected error sending staff information to VA: {e}"
            )
    
    async def _log_session_creation(self, user: Union[discord.User, discord.Member], thread: discord.Thread, 
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
            if isinstance(message.channel, discord.Thread):
                await self._end_session(message.channel, user_id)
            return
        
        # Check if this is the user's first message in the thread
        is_first_message = message.channel.id in self.threads_awaiting_first_message
        if is_first_message:
            # Remove from awaiting set
            self.threads_awaiting_first_message.discard(message.channel.id)
            
            # Get referring staff info and send to VA before user's message
            referring_staff = await self._get_referring_staff(message.author.id)
            if isinstance(message.channel, discord.Thread):
                await self._send_staff_info_to_va(user_id, referring_staff, message.channel)
            
            # Small delay to ensure staff info arrives before user message
            await asyncio.sleep(0.5)
        
        # Forward message to Telegram - send as natural conversation
        telegram_manager = get_telegram_manager()
        if telegram_manager:
            # Check if TELEGRAM_VA_USERNAME is configured
            if not self.TELEGRAM_VA_USERNAME:
                # Notify staff privately about configuration issue
                if isinstance(message.channel, discord.Thread):
                    await self._notify_staff_privately(
                        message.channel, 
                        f"TELEGRAM_VA_USERNAME not configured - VA communication disabled\nUser: {message.author.mention}"
                    )
                await message.add_reaction("⏳")  # Just acknowledge with reaction
                return
                
            try:
                # Format as natural message (VA sees this as coming from the dummy account)
                natural_message = f"{message.content}"
                
                success = await telegram_manager.send_message(
                    user_id, 
                    self.TELEGRAM_VA_USERNAME, 
                    natural_message
                )
                
                if not success:
                    # Notify staff privately instead of alerting the user
                    if isinstance(message.channel, discord.Thread):
                        await self._notify_staff_privately(
                            message.channel, 
                            f"Failed to send user message to VA (send_message returned False)\nUser: {message.author.mention}\nMessage: {message.content[:100]}..."
                        )
                    # Give user a generic message without technical details
                    await message.add_reaction("⏳")  # Just add a reaction to acknowledge
                    
            except Exception as telegram_error:
                # Handle specific Telegram connection errors
                error_str = str(telegram_error).lower()
                if "cannot send requests while disconnected" in error_str or "sessionrevokederror" in error_str:
                    logger.error(f"🔌 Telegram session disconnected for thread {message.channel.id}")
                    # Notify staff privately about the technical issue
                    if isinstance(message.channel, discord.Thread):
                        await self._notify_staff_privately(
                            message.channel, 
                            f"Telegram session disconnected - cannot send messages to VA\nUser: {message.author.mention}\nError: {telegram_error}"
                        )
                    # Give user a generic response without technical details
                    await message.add_reaction("⏳")  # Just acknowledge with reaction
                else:
                    logger.error(f"❌ Telegram error in thread {message.channel.id}: {telegram_error}")
                    # Notify staff privately about other Telegram errors
                    if isinstance(message.channel, discord.Thread):
                        await self._notify_staff_privately(
                            message.channel, 
                            f"Telegram communication error\nUser: {message.author.mention}\nError: {telegram_error}"
                        )
                    await message.add_reaction("⏳")  # Just acknowledge with reaction
        else:
            # Notify staff privately that Telegram manager is unavailable
            if isinstance(message.channel, discord.Thread):
                await self._notify_staff_privately(
                    message.channel, 
                    f"Telegram manager unavailable - VA communication system down\nUser: {message.author.mention}"
                )
            await message.add_reaction("⏳")  # Just acknowledge with reaction
    
    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        """Handle thread deletion - clean up VIP sessions automatically"""
        try:
            # Check if this was a VIP chat thread
            if thread.id in self.thread_sessions:
                user_id = self.thread_sessions[thread.id]
                logger.info(f"🧹 VIP thread {thread.id} deleted, cleaning up session for user {user_id}")
                
                # Use the centralized cleanup method
                await self._cleanup_session(user_id, reason="Thread deleted by staff")
                
                logger.info(f"✅ Successfully cleaned up VIP session for user {user_id} after thread deletion")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up session after thread deletion: {e}")
    
    async def handle_va_reply(self, user_id: str, message_content: str, telegram_message=None):
        """Handle VA reply from Telegram - send as your actual Discord account"""
        try:
            logger.info(f"🔍 DEBUG: Handling VA reply for user {user_id}: {message_content[:50]}...")
            logger.info(f"🔍 DEBUG: Active threads: {list(self.active_threads.keys())}")
            
            if user_id not in self.active_threads:
                logger.warning(f"No active thread found for user {user_id}")
                return False
            
            thread = self.active_threads[user_id]
            logger.info(f"🔍 DEBUG: Found thread {thread.id} for user {user_id}")
           
            # Handle media messages (video, voice, etc.)
            if telegram_message and telegram_message.media:
                try:
                    logger.info(f"🔍 DEBUG: Processing media message...")
                    
                    # Download media to temporary file
                    import tempfile
                    import os
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        file_path = await telegram_message.download_media(temp_dir)
                        
                        if file_path:
                            logger.info(f"🔍 DEBUG: Downloaded media to {file_path}")
                            
                            # Send media file to Discord
                            with open(file_path, 'rb') as f:
                                file_name = os.path.basename(file_path)
                                
                                # Clean up filename for voice messages to look more natural
                                if file_name.startswith('voice_'):
                                    clean_file_name = "voice-message.ogg"
                                    content_prefix = ""  # Don't add extra text for voice messages
                                elif file_name.startswith('document_') and file_name.endswith('.mp4'):
                                    clean_file_name = "video-message.mp4"
                                    content_prefix = ""
                                elif file_name.startswith('photo_'):
                                    clean_file_name = "image.jpg"
                                    content_prefix = ""
                                else:
                                    clean_file_name = file_name
                                    content_prefix = ""
                                
                                # Get referring staff info for referral replacements (if text content exists)
                                referring_staff = await self._get_referring_staff(int(user_id))
                                processed_message = self._replace_referral_info(message_content, referring_staff) if message_content else ""
                                
                                # Combine content prefix with processed message
                                final_message = f"{content_prefix}{processed_message}" if processed_message else content_prefix
                                final_message = final_message.strip() if final_message else None
                                
                                discord_file = discord.File(f, filename=clean_file_name)
                                
                                # Send media via regular bot (webhooks don't support file uploads easily)
                                # Note: For media, we use the regular bot since webhook file uploads are complex
                                logger.info(f"🔍 DEBUG: Using bot for media upload...")
                                await thread.send(content=final_message, file=discord_file)
                                logger.info(f"✅ Sent media to thread {thread.id}")
                            
                            return True
                        else:
                            logger.error("❌ Failed to download media file")
                            
                except Exception as media_error:
                    logger.error(f"❌ Error handling media: {media_error}")
                    # Continue with text-only fallback
            
            # Handle text messages (existing logic)
            # Skip if no text content (media was already handled above)
            if not message_content or not message_content.strip():
                logger.warning(f"⚠️ No text content to send for user {user_id}")
                return True  # Media was already sent if applicable
            
            # Get referring staff info for this user and replace referral links/codes
            referring_staff = await self._get_referring_staff(int(user_id))
            processed_message = self._replace_referral_info(message_content, referring_staff)
            
            if processed_message != message_content:
                logger.info(f"📋 Processed referral replacements for user {user_id}")
            else:
                logger.info(f"ℹ️ No referral replacements needed for user {user_id}")
            
            # Option 1: Use fake Aidan account to send as your account (no APP tag, 100% safe)
            try:
                from src.fake_personal_account import send_as_fake_aidan
                
                logger.info(f"🔍 DEBUG: Sending message via fake Aidan account...")
                success = await send_as_fake_aidan(processed_message, thread)
                
                if success:
                    logger.info(f"✅ Sent VA reply as fake Aidan account to thread {thread.id}")
                    return True
                else:
                    logger.warning(f"⚠️ Fake Aidan account message failed, trying fallback...")
                    
            except Exception as fake_account_error:
                logger.error(f"❌ Fake Aidan account failed: {fake_account_error}")
            
            # Option 2: Fallback to regular bot message (clean, no embed)
            logger.info(f"🔍 DEBUG: Using fallback bot message...")
            await thread.send(processed_message)
            logger.info(f"✅ Sent VA reply as bot message to thread {thread.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending VA reply: {e}")
            return False
    
    async def _end_session(self, thread: discord.Thread, user_id: str):
        """End a VIP chat session manually"""
        try:
            # Send manual completion message
            embed = discord.Embed(
                title="✅ VIP Chat Session Ended",
                description="Your VIP chat session has been ended manually.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value=(
                    "• This thread will be archived shortly\n"
                    "• You can create a new session anytime using the VIP upgrade button\n"
                    "• Contact staff if you need further assistance"
                ),
                inline=False
            )
            
            await thread.send(embed=embed)
            
            # Clean up session
            await self._cleanup_session(user_id, reason="Manual session end")
            
            # Archive thread after a delay
            await asyncio.sleep(30)
            await thread.edit(archived=True, reason="Manual session end")
            
            logger.info(f"✅ Manually ended VIP session for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error ending VIP session for user {user_id}: {e}")
    
    @tasks.loop(minutes=5)
    async def monitor_vip_completions(self):
        """Monitor for VIP upgrade completions by checking Telegram group membership"""
        try:
            telegram_manager = get_telegram_manager()
            if not telegram_manager:
                return
            
            # Check each active session to see if their dummy account was added to VIP group
            for user_id, thread in list(self.active_threads.items()):
                try:
                    # Skip if already marked as completed
                    if user_id in self.completed_upgrades:
                        continue
                    
                    # Check if dummy account is now in VIP group
                    is_in_vip_group = await self._check_dummy_in_vip_group(user_id)
                    
                    if is_in_vip_group:
                        logger.info(f"🎉 VIP upgrade completed for user {user_id} - dummy account added to VIP group")
                        await self._complete_vip_upgrade(user_id, thread, "VA_VERIFICATION")
                        
                except Exception as e:
                    logger.error(f"❌ Error checking VIP completion for user {user_id}: {e}")
            
            # Clean up orphaned thread sessions (threads that no longer exist)
            orphaned_threads = []
            for user_id, thread in list(self.active_threads.items()):
                try:
                    # Check if thread still exists by trying to access its name
                    _ = thread.name
                except:
                    # Thread no longer exists or is inaccessible
                    orphaned_threads.append(user_id)
            
            for user_id in orphaned_threads:
                logger.info(f"🧹 Cleaning up orphaned session for user {user_id}")
                await self._cleanup_session(user_id, reason="Thread deleted")
                
        except Exception as e:
            logger.error(f"❌ Error in VIP completion monitoring: {e}")
    
    @monitor_vip_completions.before_loop
    async def before_monitor(self):
        """Wait for bot to be ready before starting monitoring task"""
        await self.bot.wait_until_ready()
    
    async def _check_dummy_in_vip_group(self, discord_user_id: str) -> bool:
        """Check if the dummy account for this user is in the VIP Telegram group"""
        try:
            telegram_manager = get_telegram_manager()
            if not telegram_manager or discord_user_id not in telegram_manager.active_sessions:
                return False
            
            account = telegram_manager.active_sessions[discord_user_id]
            if not account.client or not account.is_connected:
                return False
            
            # Check if VIP group is configured
            if not self.TELEGRAM_VIP_GROUP_ID and not self.TELEGRAM_VIP_GROUP_USERNAME:
                logger.warning("⚠️ VIP group not configured - cannot check membership")
                return False
            
            # Get VIP group entity
            vip_group = None
            try:
                if self.TELEGRAM_VIP_GROUP_ID:
                    vip_group = await account.client.get_entity(int(self.TELEGRAM_VIP_GROUP_ID))
                elif self.TELEGRAM_VIP_GROUP_USERNAME:
                    vip_group = await account.client.get_entity(self.TELEGRAM_VIP_GROUP_USERNAME)
            except Exception as e:
                logger.error(f"❌ Failed to get VIP group entity: {e}")
                return False
            
            if not vip_group:
                return False
            
            # Check if account (self) is a member of the VIP group
            try:
                # Get account's own user entity
                me = await account.client.get_me()
                
                # Check if we're a participant in the VIP group
                participants = await account.client.get_participants(vip_group, limit=None)
                
                for participant in participants:
                    try:
                        # Get participant ID using various methods
                        participant_id = None
                        if hasattr(participant, 'id'):
                            participant_id = getattr(participant, 'id', None)
                        elif hasattr(participant, 'user_id'):
                            participant_id = getattr(participant, 'user_id', None)
                        
                        if participant_id and participant_id == getattr(me, 'id', None):
                            logger.info(f"✅ Dummy account {account.phone} found in VIP group for user {discord_user_id}")
                            return True
                    except Exception as participant_error:
                        # Some participant types may not have accessible ID fields
                        logger.debug(f"Could not get ID from participant: {participant_error}")
                        continue
                
                logger.info(f"🔍 Dummy account {account.phone} not found in VIP group for user {discord_user_id}")
                return False
                
            except Exception as e:
                logger.error(f"❌ Error checking VIP group membership for user {discord_user_id}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in _check_dummy_in_vip_group for user {discord_user_id}: {e}")
            return False
    
    async def _assign_vip_role(self, discord_user_id: str) -> bool:
        """Assign VIP role to Discord user"""
        try:
            if not self.VIP_ROLE_ID:
                logger.error("❌ VIP_ROLE_ID not configured - cannot assign VIP role")
                return False
            
            # Get the user from Discord
            user = self.bot.get_user(int(discord_user_id))
            if not user:
                logger.error(f"❌ Could not find Discord user {discord_user_id}")
                return False
            
            # Get the guild and role
            guild = self.bot.get_guild(self.GUILD_ID)
            if not guild:
                logger.error(f"❌ Could not find guild {self.GUILD_ID}")
                return False
            
            member = guild.get_member(int(discord_user_id))
            if not member:
                logger.error(f"❌ User {discord_user_id} is not a member of guild {self.GUILD_ID}")
                return False
            
            vip_role = guild.get_role(int(self.VIP_ROLE_ID))
            if not vip_role:
                logger.error(f"❌ VIP role {self.VIP_ROLE_ID} not found in guild")
                return False
            
            # Check if user already has VIP role
            if vip_role in member.roles:
                logger.info(f"✅ User {discord_user_id} already has VIP role")
                return True
            
            # Assign VIP role
            await member.add_roles(vip_role, reason="Automated VIP upgrade completion")
            logger.info(f"✅ Successfully assigned VIP role to user {discord_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error assigning VIP role to user {discord_user_id}: {e}")
            return False
    
    async def _remove_dummy_from_vip_group(self, discord_user_id: str) -> bool:
        """Remove dummy account from VIP Telegram group"""
        try:
            telegram_manager = get_telegram_manager()
            if not telegram_manager or discord_user_id not in telegram_manager.active_sessions:
                logger.error(f"❌ No active Telegram session for user {discord_user_id}")
                return False
            
            account = telegram_manager.active_sessions[discord_user_id]
            if not account.client or not account.is_connected:
                logger.error(f"❌ Telegram account not connected for user {discord_user_id}")
                return False
            
            # Check if VIP group is configured
            if not self.TELEGRAM_VIP_GROUP_ID and not self.TELEGRAM_VIP_GROUP_USERNAME:
                logger.error("❌ VIP group not configured - cannot remove from group")
                return False
            
            # Get VIP group entity
            try:
                if self.TELEGRAM_VIP_GROUP_ID:
                    vip_group = await account.client.get_entity(int(self.TELEGRAM_VIP_GROUP_ID))
                elif self.TELEGRAM_VIP_GROUP_USERNAME:
                    vip_group = await account.client.get_entity(self.TELEGRAM_VIP_GROUP_USERNAME)
                else:
                    return False
            except Exception as e:
                logger.error(f"❌ Failed to get VIP group entity: {e}")
                return False
            
            # Leave the VIP group
            try:
                # Use the first entity if get_entity returns a list
                if isinstance(vip_group, list):
                    vip_group = vip_group[0]
                await account.client.delete_dialog(vip_group)
                logger.info(f"✅ Successfully removed dummy account {account.phone} from VIP group for user {discord_user_id}")
                return True
            except Exception as e:
                logger.error(f"❌ Error removing dummy account from VIP group for user {discord_user_id}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in _remove_dummy_from_vip_group for user {discord_user_id}: {e}")
            return False
    
    async def _clear_dummy_chat_history(self, discord_user_id: str) -> bool:
        """Clear chat history for the dummy Telegram account"""
        try:
            telegram_manager = get_telegram_manager()
            if not telegram_manager or discord_user_id not in telegram_manager.active_sessions:
                logger.error(f"❌ No active Telegram session for user {discord_user_id}")
                return False
            
            account = telegram_manager.active_sessions[discord_user_id]
            if not account.client or not account.is_connected:
                logger.error(f"❌ Telegram account not connected for user {discord_user_id}")
                return False
            
            # Clear chat history with VA if configured
            if self.TELEGRAM_VA_USERNAME:
                try:
                    va_entity = await account.client.get_entity(self.TELEGRAM_VA_USERNAME)
                    # Use the first entity if get_entity returns a list
                    if isinstance(va_entity, list):
                        va_entity = va_entity[0]
                    await account.client.delete_dialog(va_entity, revoke=True)
                    logger.info(f"✅ Cleared chat history with VA for dummy account {account.phone}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not clear VA chat history for user {discord_user_id}: {e}")
            
            # Clear any other relevant chat histories
            try:
                # Get all dialogs and clear recent ones related to VIP process
                dialogs = await account.client.get_dialogs(limit=10)
                for dialog in dialogs:
                    # Skip groups and channels, only clear private chats
                    if dialog.is_user:
                        try:
                            await account.client.delete_dialog(dialog.entity, revoke=True)
                            logger.info(f"✅ Cleared dialog {dialog.name} for dummy account {account.phone}")
                        except:
                            # Some dialogs might not be clearable, that's okay
                            pass
                
                logger.info(f"✅ Successfully cleared chat history for dummy account {account.phone} for user {discord_user_id}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error clearing chat history for user {discord_user_id}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in _clear_dummy_chat_history for user {discord_user_id}: {e}")
            return False
    
    async def _complete_vip_upgrade(self, discord_user_id: str, thread: discord.Thread, completion_reason: str):
        """Complete a VIP upgrade with full automation workflow"""
        try:
            # Mark as completed to avoid duplicate processing
            self.completed_upgrades.add(discord_user_id)
            
            # Step 1: Assign VIP role to Discord user
            vip_role_assigned = await self._assign_vip_role(discord_user_id)
            
            # Step 2: Remove dummy account from VIP Telegram group
            removed_from_vip = await self._remove_dummy_from_vip_group(discord_user_id)
            
            # Step 3: Clear Telegram chat history for the dummy account
            chat_cleared = await self._clear_dummy_chat_history(discord_user_id)
            
            # Send completion message to thread
            embed = discord.Embed(
                title="🎉 VIP Upgrade Complete!",
                description="Congratulations! Your VIP upgrade has been fully processed and automated.",
                color=discord.Color.gold()
            )
            
            # Build status message based on automation results
            automation_status = []
            automation_status.append(f"✅ VIP verification: Complete")
            automation_status.append(f"{'✅' if vip_role_assigned else '⚠️'} Discord VIP role: {'Assigned' if vip_role_assigned else 'Manual assignment needed'}")
            automation_status.append(f"{'✅' if removed_from_vip else '⚠️'} VIP group cleanup: {'Complete' if removed_from_vip else 'Manual cleanup needed'}")
            automation_status.append(f"{'✅' if chat_cleared else '⚠️'} Chat history: {'Cleared' if chat_cleared else 'Manual clearing needed'}")
            automation_status.append(f"✅ Session cleanup: Automated")
            
            embed.add_field(
                name="🔄 Automation Status",
                value="\n".join(automation_status),
                inline=False
            )
            
            embed.add_field(
                name="🚀 Next Steps",
                value=(
                    "• Your Discord VIP role provides access to premium channels\n"
                    "• Join VIP trading signals and exclusive content\n"
                    "• Access priority support and resources\n"
                    "• This session will close automatically in 30 seconds"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Automated completion via {completion_reason}")
            
            await thread.send(embed=embed)
            
            # Notify staff about the completion with automation details
            await self._notify_staff_vip_completion(discord_user_id, thread, completion_reason, {
                'vip_role_assigned': vip_role_assigned,
                'removed_from_vip': removed_from_vip,
                'chat_cleared': chat_cleared
            })
            
            # Clean up session after a delay to allow user to read the message
            await asyncio.sleep(30)
            await self._cleanup_session(discord_user_id, reason=f"VIP upgrade completed ({completion_reason})")
            
            # Archive the thread
            try:
                await thread.edit(archived=True, reason="VIP upgrade completed automatically")
                logger.info(f"📦 Archived thread {thread.id} for completed VIP upgrade")
            except Exception as e:
                logger.error(f"❌ Failed to archive thread {thread.id}: {e}")
            
            logger.info(f"🎉 Successfully completed automated VIP upgrade for user {discord_user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in automated VIP upgrade completion for user {discord_user_id}: {e}")
    
    async def _notify_staff_vip_completion(self, discord_user_id: str, thread: discord.Thread, completion_reason: str, automation_status: Optional[Dict] = None):
        """Notify staff about VIP upgrade completion"""
        try:
            staff_user = self.bot.get_user(self.ADMIN_USER_ID)
            if not staff_user:
                return
            
            # Get user info for notification
            discord_user = None
            try:
                discord_user = self.bot.get_user(int(discord_user_id))
            except:
                pass
            
            user_info = f"{discord_user.mention} ({discord_user.name})" if discord_user else f"User ID: {discord_user_id}"
            
            embed = discord.Embed(
                title="🎉 VIP Upgrade Completed",
                description=f"A VIP upgrade has been automatically completed and verified.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="👤 User",
                value=user_info,
                inline=True
            )
            
            embed.add_field(
                name="🔍 Verification Method",
                value=completion_reason.replace("_", " ").title(),
                inline=True
            )
            
            # Add automation status if provided
            if automation_status:
                status_lines = []
                status_lines.append(f"{'✅' if automation_status.get('vip_role_assigned') else '❌'} Discord VIP Role Assignment")
                status_lines.append(f"{'✅' if automation_status.get('removed_from_vip') else '❌'} VIP Group Cleanup")
                status_lines.append(f"{'✅' if automation_status.get('chat_cleared') else '❌'} Chat History Clearing")
                
                embed.add_field(
                    name="🤖 Automation Results",
                    value="\n".join(status_lines),
                    inline=False
                )
                
                # Alert if any automation steps failed
                if not all(automation_status.values()):
                    embed.add_field(
                        name="⚠️ Manual Action Required",
                        value="Some automation steps failed. Please check the logs and complete manually if needed.",
                        inline=False
                    )
            
            embed.add_field(
                name="📍 Thread",
                value=thread.mention,
                inline=True
            )
            
            embed.add_field(
                name="⚡ Actions Taken",
                value=(
                    "• Session automatically completed\n"
                    "• User notified of completion\n"
                    "• Thread archived\n"
                    "• Telegram account released"
                ),
                inline=False
            )
            
            embed.set_footer(text="Automated VIP completion system")
            
            # Send notification to VIP upgrade channel
            channel = self.bot.get_channel(self.VIP_UPGRADE_CHANNEL_ID)
            if channel:
                await channel.send(f"{staff_user.mention}", embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error notifying staff about VIP completion: {e}")
    
    async def _cleanup_session(self, discord_user_id: str, reason: str = "Manual cleanup"):
        """Clean up a VIP session without sending messages to thread"""
        try:
            # Clear chat history and release Telegram account
            telegram_manager = get_telegram_manager()
            if telegram_manager:
                try:
                    if self.TELEGRAM_VA_USERNAME:
                        account = telegram_manager.active_sessions.get(discord_user_id)
                        if account:
                            history_cleared = await telegram_manager.clear_chat_history(discord_user_id, self.TELEGRAM_VA_USERNAME)
                            if history_cleared:
                                logger.info(f"✅ Cleared chat history for user {discord_user_id}")
                            else:
                                logger.warning(f"⚠️ Failed to clear chat history for user {discord_user_id}")
                    else:
                        logger.warning(f"⚠️ TELEGRAM_VA_USERNAME not configured, skipping chat history cleanup for user {discord_user_id}")
                except Exception as telegram_error:
                    logger.error(f"❌ Error clearing chat history for user {discord_user_id}: {telegram_error}")
                
                # Release the account
                await telegram_manager.release_account(discord_user_id)
            
            # Clean up session tracking
            if discord_user_id in self.active_threads:
                del self.active_threads[discord_user_id]
            
            # Find and clean up thread mapping
            thread_id_to_remove = None
            for thread_id, user_id in self.thread_sessions.items():
                if user_id == discord_user_id:
                    thread_id_to_remove = thread_id
                    break
            
            if thread_id_to_remove:
                del self.thread_sessions[thread_id_to_remove]
                # Clean up first message tracking
                self.threads_awaiting_first_message.discard(thread_id_to_remove)
            
            logger.info(f"🧹 Cleaned up VIP session for user {discord_user_id}: {reason}")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up session for user {discord_user_id}: {e}")
    
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

    @app_commands.command(name="debug_fake_aidan", description="[ADMIN] Debug fake Aidan account status")
    @app_commands.default_permissions(administrator=True)
    async def debug_fake_aidan(self, interaction: discord.Interaction):
        """Debug the fake Aidan account system"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        try:
            from src.fake_personal_account import get_fake_account_manager
            
            fake_manager = get_fake_account_manager()
            status = fake_manager.get_status()
            
            embed = discord.Embed(
                title="🔍 Fake Aidan Account Debug Status",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 System Status",
                value=(
                    f"**Manager Active:** {'✅ Yes' if status['active'] else '❌ No'}\n"
                    f"**Fake Accounts:** {len(status['fake_accounts'])}\n"
                    f"**Aidan Available:** {'✅ Yes' if status['aidan_account_available'] else '❌ No'}\n"
                    f"**Aidan Initialized:** {'✅ Yes' if status['aidan_account_initialized'] else '❌ No'}"
                ),
                inline=False
            )
            
            if status['fake_accounts']:
                embed.add_field(
                    name="🎭 Available Accounts",
                    value=", ".join(status['fake_accounts']),
                    inline=False
                )
            
            # Test webhook URL if available
            if status['aidan_account_available']:
                try:
                    aidan_account = fake_manager.fake_accounts['aidan']
                    webhook_url = aidan_account.webhook_url if aidan_account else "Not available"
                    embed.add_field(
                        name="🔗 Webhook URL",
                        value=f"`{webhook_url[:50]}...`" if len(webhook_url) > 50 else f"`{webhook_url}`",
                        inline=False
                    )
                except:
                    embed.add_field(
                        name="🔗 Webhook URL",
                        value="❌ Error retrieving webhook URL",
                        inline=False
                    )
            
            embed.add_field(
                name="💡 Troubleshooting",
                value=(
                    "• **If Manager Not Active:** Check webhook creation in VIP channel\n"
                    "• **If Aidan Not Available:** Webhook 'Fake Aidan VIP' not found\n"
                    "• **If Not Initialized:** Webhook setup failed during bot startup"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error in debug_fake_aidan command: {e}")
            await interaction.response.send_message(
                f"❌ Debug failed: {str(e)}", 
                ephemeral=True
            )
    
    @commands.command(name='complete_vip')
    @commands.has_any_role('Staff', 'Admin', 'Support')
    async def complete_vip_manually(self, ctx, user_id: Optional[str] = None):
        """Manually complete a VIP upgrade for a user
        
        Usage: !complete_vip @user or !complete_vip user_id
        """
        try:
            # Parse user ID from mention or direct ID
            if ctx.message.mentions:
                target_user = ctx.message.mentions[0]
                target_user_id = str(target_user.id)
            elif user_id:
                target_user_id = user_id.strip('<@!>')
                try:
                    target_user = await self.bot.fetch_user(int(target_user_id))
                except:
                    await ctx.send("❌ Invalid user ID or user not found.")
                    return
            else:
                await ctx.send("❌ Please specify a user by mentioning them or providing their ID.\nUsage: `!complete_vip @user` or `!complete_vip user_id`")
                return
            
            # Check if user has an active VIP session
            if target_user_id not in self.active_threads:
                await ctx.send(f"❌ No active VIP session found for {target_user.mention if 'target_user' in locals() else target_user_id}")
                return
            
            # Complete the VIP upgrade
            thread = self.active_threads[target_user_id]
            await self._complete_vip_upgrade(target_user_id, thread, f"Manually completed by {ctx.author.mention}")
            
            await ctx.send(f"✅ VIP upgrade manually completed for {target_user.mention if 'target_user' in locals() else target_user_id}")
            logger.info(f"✅ VIP manually completed for user {target_user_id} by {ctx.author.id}")
            
        except Exception as e:
            logger.error(f"❌ Error in complete_vip_manually: {e}")
            await ctx.send("❌ An error occurred while completing the VIP upgrade.")
    
    @commands.command(name='vip_status')
    @commands.has_any_role('Staff', 'Admin', 'Support')
    async def check_vip_status(self, ctx):
        """Check status of all active VIP sessions"""
        try:
            if not self.active_threads:
                await ctx.send("📊 No active VIP sessions currently.")
                return
            
            status_embed = discord.Embed(
                title="🎯 Active VIP Sessions Status",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            for user_id, thread in self.active_threads.items():
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    status_embed.add_field(
                        name=f"👤 {user.display_name}",
                        value=f"**Thread:** {thread.mention}\n**Status:** Active",
                        inline=True
                    )
                except:
                    status_embed.add_field(
                        name=f"👤 User ID: {user_id}",
                        value=f"**Thread:** {thread.mention}\n**Status:** Active",
                        inline=True
                    )
            
            await ctx.send(embed=status_embed)
            
        except Exception as e:
            logger.error(f"❌ Error in check_vip_status: {e}")
            await ctx.send("❌ An error occurred while checking VIP status.")

async def setup(bot):
    await bot.add_cog(VIPSessionManager(bot))