"""
VIP Upgrade Views
================

Interactive Discord UI components for the VIP upgrade system.
Handles button clicks and modal forms for VIP upgrade process.
"""

import discord
from discord import ui
import logging
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class StaffVIPApprovalView(discord.ui.View):
    """View for staff to approve/deny VIP requests from DMs"""
    
    def __init__(self, request_id: int, user_id: int, user_name: str):
        super().__init__(timeout=259200)  # 72 hour timeout
        self.request_id = request_id
        self.user_id = user_id
        self.user_name = user_name
    
    @discord.ui.button(
        label="✅ Approve VIP",
        style=discord.ButtonStyle.success,
        custom_id="approve_vip_dm"
    )
    async def approve_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve VIP request from DM"""
        try:
            # Get the bot instance and database
            bot = interaction.client
            vip_cog = bot.get_cog('VIPUpgrade')
            
            if not vip_cog:
                await interaction.response.send_message("❌ VIP system not available.", ephemeral=True)
                return
            
            # Update request status in database
            success = bot.db.update_vip_request_status(self.request_id, 'completed')
            
            if success:
                # Get the guild and user
                guild = bot.get_guild(int(vip_cog.GUILD_ID))
                if not guild:
                    await interaction.response.send_message("❌ Guild not found.", ephemeral=True)
                    return
                
                member = guild.get_member(self.user_id)
                if not member:
                    await interaction.response.send_message("❌ User not found in guild.", ephemeral=True)
                    return
                
                # Add VIP role
                vip_role_id = int(vip_cog.VIP_ROLE_ID)
                vip_role = guild.get_role(vip_role_id)
                
                if vip_role:
                    await member.add_roles(vip_role, reason=f"VIP approved by {interaction.user.name}")
                    
                    # Send confirmation to staff
                    embed = discord.Embed(
                        title="✅ VIP Request Approved",
                        description=f"Successfully granted VIP role to **{self.user_name}**",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed)
                    
                    # Notify user in VIP upgrade channel
                    vip_channel = guild.get_channel(int(vip_cog.VIP_UPGRADE_CHANNEL_ID))
                    if vip_channel:
                        user_embed = discord.Embed(
                            title="🎉 VIP Upgrade Approved!",
                            description=f"Congratulations {member.mention}! Your VIP upgrade has been approved.",
                            color=discord.Color.gold()
                        )
                        await vip_channel.send(embed=user_embed)
                    
                    # Disable buttons
                    for item in self.children:
                        item.disabled = True
                    await interaction.edit_original_response(view=self)
                    
                else:
                    await interaction.response.send_message("❌ VIP role not found.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to update request status.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"❌ Error in VIP approval: {e}")
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
    
    @discord.ui.button(
        label="❌ Deny VIP",
        style=discord.ButtonStyle.danger,
        custom_id="deny_vip_dm"
    )
    async def deny_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deny VIP request from DM"""
        try:
            # Show modal for denial reason
            modal = DenialReasonModal(self.request_id, self.user_id, self.user_name, self)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"❌ Error in VIP denial: {e}")
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

class DenialReasonModal(discord.ui.Modal):
    """Modal for staff to enter denial reason"""
    
    def __init__(self, request_id: int, user_id: int, user_name: str, view: StaffVIPApprovalView):
        super().__init__(title="VIP Denial Reason")
        self.request_id = request_id
        self.user_id = user_id
        self.user_name = user_name
        self.view = view
    
    reason = discord.ui.TextInput(
        label="Reason for denial",
        placeholder="Please explain why this VIP request is being denied...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the bot instance
            bot = interaction.client
            vip_cog = bot.get_cog('VIPUpgrade')
            
            if not vip_cog:
                await interaction.response.send_message("❌ VIP system not available.", ephemeral=True)
                return
            
            # Update request status in database
            success = bot.db.update_vip_request_status(self.request_id, 'denied')
            
            if success:
                # Get the guild and VIP upgrade channel
                guild = bot.get_guild(int(vip_cog.GUILD_ID))
                if guild:
                    vip_channel = guild.get_channel(int(vip_cog.VIP_UPGRADE_CHANNEL_ID))
                    member = guild.get_member(self.user_id)
                    
                    if vip_channel and member:
                        # Send denial message to user in VIP upgrade channel
                        embed = discord.Embed(
                            title="❌ VIP Upgrade Denied",
                            description=f"Sorry {member.mention}, your VIP upgrade request has been denied.",
                            color=discord.Color.red()
                        )
                        embed.add_field(
                            name="Reason:",
                            value=self.reason.value,
                            inline=False
                        )
                        embed.set_footer(text="You can submit a new request after addressing the concerns mentioned above.")
                        
                        await vip_channel.send(embed=embed)
                
                # Confirm to staff
                embed = discord.Embed(
                    title="❌ VIP Request Denied",
                    description=f"VIP request for **{self.user_name}** has been denied.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Reason", value=self.reason.value, inline=False)
                await interaction.response.send_message(embed=embed)
                
                # Disable buttons in original message
                for item in self.view.children:
                    item.disabled = True
                await interaction.edit_original_response(view=self.view)
                
            else:
                await interaction.response.send_message("❌ Failed to update request status.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"❌ Error in VIP denial: {e}")
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

async def send_staff_vip_notification(bot, staff_discord_id: int, user_id: int, user_name: str, 
                                    request_type: str, request_id: int, staff_config: dict, 
                                    image_proof = None):
    """Send DM notification to staff member about VIP upgrade request"""
    try:
        # Get staff member
        staff_member = bot.get_user(staff_discord_id)
        if not staff_member:
            logger.warning(f"Could not find staff member with ID {staff_discord_id}")
            return
        
        # Create embed based on request type
        if request_type == "existing_account":
            embed = discord.Embed(
                title="📧 VIP Upgrade - Email Sent",
                description=f"**{user_name}** has submitted their VIP upgrade request with email proof.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="👤 User",
                value=f"<@{user_id}> ({user_name})",
                inline=True
            )
            embed.add_field(
                name="💼 Your IB Code",
                value=staff_config.get('vantage_ib_code', 'N/A'),
                inline=True
            )
            embed.add_field(
                name="📧 Action Required",
                value="Please check if the user has sent their email correctly and approve/deny below.",
                inline=False
            )
            
            if image_proof:
                embed.set_image(url=image_proof.url)
                embed.add_field(
                    name="📎 Email Proof",
                    value="Image attached above",
                    inline=False
                )
        
        else:  # new_account
            embed = discord.Embed(
                title="🆕 VIP Upgrade - Account Created",
                description=f"**{user_name}** has marked their new Vantage account creation as complete.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="👤 User",
                value=f"<@{user_id}> ({user_name})",
                inline=True
            )
            embed.add_field(
                name="💼 Your IB Code",
                value=staff_config.get('vantage_ib_code', 'N/A'),
                inline=True
            )
            embed.add_field(
                name="✅ Action Required",
                value="Please verify their account was created correctly and approve/deny below.",
                inline=False
            )
        
        embed.set_footer(text=f"Request ID: {request_id} | Use buttons below to approve/deny")
        
        # Create approval view
        view = StaffVIPApprovalView(request_id, user_id, user_name)
        
        # Send DM
        await staff_member.send(embed=embed, view=view)
        logger.info(f"✅ Sent VIP notification DM to {staff_member.name} for user {user_name}")
        
    except discord.Forbidden:
        logger.warning(f"Could not DM staff member {staff_discord_id} (DMs disabled)")
    except Exception as e:
        logger.error(f"❌ Error sending staff notification: {e}")

class VIPRestartView(discord.ui.View):
    """View for handling VIP request restart/cancel"""
    
    def __init__(self, user_id: int, active_requests: list):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.active_requests = active_requests
    
    @discord.ui.button(
        label="🔄 Cancel & Restart Fresh",
        style=discord.ButtonStyle.danger,
        custom_id="vip_restart_fresh"
    )
    async def restart_fresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel all active requests and start fresh"""
        try:
            # Cancel all active requests
            vip_cog = interaction.client.get_cog('VIPUpgrade')
            db = vip_cog.bot.db if vip_cog else None
            
            if db:
                cancelled_count = 0
                for request in self.active_requests:
                    if db.update_vip_request_status(request.get('id'), 'cancelled'):
                        cancelled_count += 1
                
                embed = discord.Embed(
                    title="✅ Requests Cancelled - Starting Fresh",
                    description=f"Cancelled {cancelled_count} active request(s). You can now start a new VIP upgrade process.",
                    color=discord.Color.green()
                )
                
                # Show the account question immediately
                account_embed = discord.Embed(
                    title="👑 VIP Upgrade Process",
                    description="Do you already have a Vantage trading account?",
                    color=discord.Color.blue()
                )
                account_embed.add_field(
                    name="🤔 Choose Your Path",
                    value=(
                        "**✅ Yes** - I have an existing Vantage account\n"
                        "**🆕 No** - I need to create a new account\n\n"
                        "Select the option that applies to you:"
                    ),
                    inline=False
                )
                
                # Disable restart buttons
                for item in self.children:
                    item.disabled = True
                
                # Send confirmation then show new flow
                await interaction.response.edit_message(embed=embed, view=self)
                
                # Show fresh VIP upgrade process
                account_view = VantageAccountView(interaction.user.id, vip_cog.bot if vip_cog else None)
                await interaction.followup.send(embed=account_embed, view=account_view, ephemeral=True)
                
            else:
                await interaction.response.send_message("❌ Database unavailable. Please try again.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error restarting VIP process: {e}")
            await interaction.response.send_message("❌ An error occurred. Please contact an admin.", ephemeral=True)
    
    @discord.ui.button(
        label="✅ Keep Existing & Continue",
        style=discord.ButtonStyle.secondary,
        custom_id="vip_keep_existing"
    )
    async def keep_existing(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Keep existing requests and just dismiss this message"""
        embed = discord.Embed(
            title="✅ Keeping Existing Requests",
            description="Your active VIP requests remain unchanged. You can continue where you left off or wait for staff review.",
            color=discord.Color.blue()
        )
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)

class VIPUpgradeView(discord.ui.View):
    """Main VIP upgrade button view"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @discord.ui.button(
        label="Upgrade to VIP",
        style=discord.ButtonStyle.primary,
        custom_id="vip_upgrade_start",
        emoji="👑"
    )
    async def upgrade_to_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle VIP upgrade button click - directly create VIP chat thread"""
        try:
            # Check if user already has VIP role
            vip_cog = interaction.client.get_cog('VIPUpgrade')
            if vip_cog and vip_cog.VIP_ROLE_ID:
                vip_role_id = int(vip_cog.VIP_ROLE_ID)
                if interaction.guild:
                    vip_role = interaction.guild.get_role(vip_role_id)
                    if vip_role and isinstance(interaction.user, discord.Member) and vip_role in interaction.user.roles:
                        embed = discord.Embed(
                            title="👑 Already VIP!",
                            description="You already have VIP access! This channel is for new members upgrading to VIP.",
                            color=discord.Color.gold()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
            
            # Check if Telegram manager is available first
            try:
                import src.telegram.manager as telegram_module
                telegram_manager = telegram_module.telegram_manager
                print(f"🔍 DEBUG: telegram_manager = {telegram_manager}")
                print(f"🔍 DEBUG: telegram_manager type = {type(telegram_manager)}")
                if telegram_manager is None:
                    print("🔍 DEBUG: telegram_manager is None")
                if not telegram_manager:
                    print(f"🔍 DEBUG: telegram_manager failed boolean check: {telegram_manager}")
                    await interaction.response.send_message(
                        "❌ VIP chat system is currently unavailable (telegram_manager not available). Please try again later.",
                        ephemeral=True
                    )
                    return
                else:
                    print(f"🔍 DEBUG: telegram_manager is available: {telegram_manager}")
            except ImportError as e:
                print(f"🔍 DEBUG: ImportError when importing telegram_manager: {e}")
                await interaction.response.send_message(
                    "❌ VIP chat system is currently unavailable (import error). Please try again later.",
                    ephemeral=True
                )
                return
            
            # Get VIP session manager and create chat session directly
            session_manager = interaction.client.get_cog('VIPSessionManager')
            if not session_manager:
                await interaction.response.send_message(
                    "❌ VIP session manager is not loaded. Please try again later.",
                    ephemeral=True
                )
                return
            
            # Create VIP chat session (this handles the interaction response)
            success = await session_manager.create_vip_session(interaction)
            # Note: create_vip_session handles the interaction response internally
            
        except Exception as e:
            logger.error(f"❌ Error in VIP upgrade: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Failed to create VIP upgrade session. Please try again or contact support.",
                    ephemeral=True
                )
    


    async def upgrade_to_vip_original(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle initial VIP upgrade button click"""
        try:
            # Load staff config to check if user is staff
            vip_cog = interaction.client.get_cog('VIPUpgrade')
            config = vip_cog.bot.db.load_staff_config() if vip_cog else None
            
            # Check for existing active requests for this user
            db = vip_cog.bot.db if vip_cog else None
            if db:
                # Check for pending/awaiting requests
                pending_requests = db.get_user_vip_requests(interaction.user.id)
                active_requests = [req for req in pending_requests if req.get('status') in ['pending', 'awaiting_proof', 'email_sent']]
                
                if active_requests:
                    # User has active requests - offer to cancel and restart
                    embed = discord.Embed(
                        title="⚠️ Active VIP Request Found",
                        description=(
                            f"You already have {len(active_requests)} active VIP request(s).\n\n"
                            "**Options:**\n"
                            "• **Continue** - Keep existing request and dismiss this message\n"
                            "• **Restart** - Cancel all active requests and start fresh\n\n"
                            "Choose wisely - restarting will cancel any progress you've made."
                        ),
                        color=discord.Color.orange()
                    )
                    
                    # Show active requests
                    request_info = []
                    for req in active_requests[:3]:  # Show max 3
                        status_emoji = {
                            'pending': '⏳',
                            'email_sent': '📧', 
                            'awaiting_proof': '📸'
                        }.get(req.get('status', 'pending'), '❓')
                        request_info.append(f"{status_emoji} Request #{req.get('id', 'Unknown')} - {req.get('status', 'Unknown').replace('_', ' ').title()}")
                    
                    embed.add_field(
                        name="📋 Your Active Requests",
                        value='\n'.join(request_info) if request_info else "No details available",
                        inline=False
                    )
                    
                    # Create restart view
                    restart_view = VIPRestartView(interaction.user.id, active_requests)
                    await interaction.response.send_message(embed=embed, view=restart_view, ephemeral=True)
                    return
            
            # Check if user is staff member (either in config or has admin permissions)
            is_staff = False
            if config and 'staff_members' in config:
                for staff_member in config['staff_members'].values():
                    if staff_member['discord_id'] == interaction.user.id:
                        is_staff = True
                        break
            
            # Also check for administrator permissions as staff
            if not is_staff and isinstance(interaction.user, discord.Member):
                if interaction.user.guild_permissions.administrator:
                    is_staff = True
            
            # Check if user already has VIP role
            vip_role_id = int(vip_cog.VIP_ROLE_ID) if vip_cog and vip_cog.VIP_ROLE_ID else None
            
            if vip_role_id and interaction.guild:
                vip_role = interaction.guild.get_role(vip_role_id)
                if vip_role and isinstance(interaction.user, discord.Member) and vip_role in interaction.user.roles:
                    if not is_staff:
                        # Regular VIP member - deny access
                        embed = discord.Embed(
                            title="👑 Already VIP!",
                            description="You already have VIP access! This channel is for new members upgrading to VIP.",
                            color=discord.Color.gold()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    # Staff member with VIP - allow them to continue but with a note
                    # We'll continue to the normal flow but note this in logs
                    logger.info(f"Staff member {interaction.user.name} ({interaction.user.id}) accessing VIP upgrade as staff")
            
            # Show the account question view
            embed = discord.Embed(
                title="👑 VIP Upgrade Process",
                description="Do you already have a Vantage trading account?",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Choose Your Path:",
                value=(
                    "🟢 **Yes** - I have an existing Vantage account\n"
                    "🔵 **No** - I need to create a new account"
                ),
                inline=False
            )
            
            view = VantageAccountView(interaction.user.id, interaction.client)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error in VIP upgrade start: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

class VantageAccountView(discord.ui.View):
    """View for existing Vantage account question"""
    
    def __init__(self, user_id: int, bot=None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.bot = bot
    
    @discord.ui.button(
        label="✅ Yes, I have an account", 
        style=discord.ButtonStyle.success,
        custom_id="vantage_existing"
    )
    async def has_existing_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle existing account flow"""
        try:
            # Get user's invite information
            # Use the bot's database instance instead of creating a new one
            db = self.bot.db
            invite_info = db.get_user_invite_info(interaction.user.id)
            
            # Get staff configuration - fallback to default if no invite found
            if invite_info:
                staff_config = db.get_staff_config_by_invite(invite_info['invite_code'])
            else:
                staff_config = None
            
            # If no staff config found, use first available staff member as fallback
            if not staff_config:
                config = db.load_staff_config()
                if "staff_members" in config and config["staff_members"]:
                    # Get first available staff member as fallback
                    for staff_key, staff_info in config["staff_members"].items():
                        staff_config = staff_info
                        # Create fake invite info for tracking
                        if not invite_info:
                            invite_info = {
                                'invite_code': 'default_fallback',
                                'inviter_username': staff_info.get('username', 'Unknown Staff')
                            }
                        break
            
            if not staff_config:
                embed = discord.Embed(
                    title="⚠️ Configuration Missing",
                    description="No staff configuration found. Please contact an admin to set up the VIP system.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Final safety check
            if not isinstance(staff_config, dict) or 'discord_id' not in staff_config:
                embed = discord.Embed(
                    title="⚠️ Configuration Error",
                    description="Invalid staff configuration. Please contact an admin.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create VIP request in database
            request_data = json.dumps({
                'invite_code': invite_info['invite_code'] if invite_info else 'default_fallback',
                'inviter': invite_info['inviter_username'] if invite_info else 'Unknown',
                'request_type': 'existing_account'
            })
            
            request_id = db.create_vip_request(
                user_id=interaction.user.id,
                username=f"{interaction.user.name}#{interaction.user.discriminator}",
                request_type='existing_account',
                staff_id=staff_config['discord_id'],
                request_data=request_data
            )
            
            if not request_id:
                await interaction.response.send_message("❌ Failed to create VIP request. Please try again.", ephemeral=True)
                return
            
            # Get email template from config
            bot = interaction.client
            config = bot.db.load_staff_config()
            
            # Show email template with placeholders filled (user fills in name themselves)
            email_template = config["email_template"]["body_template"].format(
                username=interaction.user.display_name,
                discord_id=interaction.user.id,
                staff_name=staff_config['username'],
                request_id=request_id,
                ib_code=staff_config['vantage_ib_code']
            )
            
            embed = discord.Embed(
                title="📧 Email Template for VIP Upgrade",
                description=(
                    "Please send the following email **from your Vantage account email** "
                    f"to complete your VIP upgrade:"
                ),
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📧 Email Details:",
                value=(
                    f"**To:** {config['email_template']['recipient']}\n"
                    f"**Subject:** {config['email_template']['subject']}\n\n"
                    f"**Email Body:**\n```\n{email_template}\n```"
                ),
                inline=False
            )
            
            # Disable the view buttons to hide the original message
            for item in self.children:
                item.disabled = True
            
            embed.add_field(
                name="📋 Important Instructions:",
                value=(
                    "• **Fill in your name** in the template where indicated\n"
                    "• Send from the **same email** as your Vantage account\n" 
                    "• Keep the subject line **exactly as shown**\n"
                    "• **Take a screenshot** of the sent email\n"
                    f"• Your request ID is: `{request_id}`\n\n"
                    "**After sending, click the button below and upload your screenshot!**"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Attributed to staff: {staff_config['username']}")
            
            # Add button to mark as sent with image proof
            view = EmailSentView(request_id, require_proof=True)
            
            # Edit the original message to disable buttons (hide the initial choice)
            try:
                await interaction.response.edit_message(view=self)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            except:
                # Fallback if editing fails
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error in existing account flow: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
    
    @discord.ui.button(
        label="🆕 No, I need a new account",
        style=discord.ButtonStyle.primary, 
        custom_id="vantage_new"
    )
    async def needs_new_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle new account flow"""
        try:
            # Get user's invite information
            # Use the bot's database instance instead of creating a new one
            bot = interaction.client
            db = bot.db
            invite_info = db.get_user_invite_info(interaction.user.id)
            
            # Get staff configuration - fallback to default if no invite found
            if invite_info:
                staff_config = db.get_staff_config_by_invite(invite_info['invite_code'])
            else:
                staff_config = None
            
            # If no staff config found, use first available staff member as fallback
            if not staff_config:
                config = db.load_staff_config()
                if "staff_members" in config and config["staff_members"]:
                    # Get first available staff member as fallback
                    for staff_key, staff_info in config["staff_members"].items():
                        staff_config = staff_info
                        # Create fake invite info for tracking
                        if not invite_info:
                            invite_info = {
                                'invite_code': 'default_fallback',
                                'inviter_username': staff_info.get('username', 'Unknown Staff')
                            }
                        break
            
            if not staff_config:
                embed = discord.Embed(
                    title="⚠️ Configuration Missing",
                    description="No staff configuration found. Please contact an admin to set up the VIP system.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Final safety check
            if not isinstance(staff_config, dict) or 'discord_id' not in staff_config:
                embed = discord.Embed(
                    title="⚠️ Configuration Error",
                    description="Invalid staff configuration. Please contact an admin.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create VIP request in database
            request_data = json.dumps({
                'invite_code': invite_info['invite_code'] if invite_info else 'default_fallback',
                'inviter': invite_info['inviter_username'] if invite_info else 'Unknown',
                'request_type': 'new_account'
            })
            
            request_id = db.create_vip_request(
                user_id=interaction.user.id,
                username=f"{interaction.user.name}#{interaction.user.discriminator}",
                request_type='new_account',
                staff_id=staff_config['discord_id'],
                request_data=request_data
            )
            
            if not request_id:
                await interaction.response.send_message("❌ Failed to create VIP request. Please try again.", ephemeral=True)
                return
            
            # Show referral link and walkthrough
            embed = discord.Embed(
                title="🆕 Create Your Vantage Account",
                description="Follow these steps to create your Vantage account and get VIP access:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🔗 Step 1: Sign Up",
                value=(
                    f"[Click here to create your Vantage account]({staff_config['vantage_referral_link']})\n"
                    "⚠️ **Important:** Use this specific link for proper attribution!"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📧 Step 2: Verify Email",
                value="Complete the email verification process from Vantage",
                inline=False
            )
            
            embed.add_field(
                name="💰 Step 3: Make Deposit",
                value="Make your initial deposit to activate VIP access",
                inline=False
            )
            
            embed.add_field(
                name="✅ Step 4: Confirm Completion",
                value="Click the button below once you've completed all steps",
                inline=False
            )
            
            embed.set_footer(text=f"Request ID: {request_id} | Attributed to: {staff_config['username']}")
            
            # Disable the view buttons to hide the original message
            for item in self.children:
                item.disabled = True
            
            # Add button to mark as completed
            view = AccountCreatedView(request_id)
            
            # Edit the original message to disable buttons (hide the initial choice)
            try:
                await interaction.response.edit_message(view=self)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            except:
                # Fallback if editing fails
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error in new account flow: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

class EmailSentView(discord.ui.View):
    """View for confirming email was sent"""
    
    def __init__(self, request_id: int, require_proof: bool = False):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.request_id = request_id
        self.require_proof = require_proof
    
    @discord.ui.button(
        label="✅ I've sent the email (Upload proof)",
        style=discord.ButtonStyle.success,
        custom_id="email_sent_confirm"
    )
    async def confirm_email_sent(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm email was sent with image proof"""
        if self.require_proof:
            # Show modal for image upload
            modal = EmailProofModal(self.request_id)
            await interaction.response.send_modal(modal)
        else:
            # Original flow without proof requirement
            try:
                bot = interaction.client
                db = bot.db
                success = db.update_vip_request_status(self.request_id, 'email_sent')
                
                if success:
                    embed = discord.Embed(
                        title="✅ Email Confirmation Received",
                        description=(
                            "Thank you! We've received confirmation that you sent the email.\n\n"
                            "**Next Steps:**\n"
                            "• Our team will verify your Vantage account\n"
                            "• VIP access will be granted within 24-48 hours\n"
                            "• You'll receive a DM confirmation when complete"
                        ),
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text=f"Request ID: {self.request_id}")
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Failed to update request. Please contact an admin.", ephemeral=True)
                    
            except Exception as e:
                logger.error(f"❌ Error confirming email sent: {e}")
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)


class EmailProofModal(discord.ui.Modal):
    """Modal for users to upload email proof"""
    
    def __init__(self, request_id: int):
        super().__init__(title="📧 Email Proof Required")
        self.request_id = request_id
    
    email_proof_note = discord.ui.TextInput(
        label="Confirmation",
        placeholder="Type: I have sent the email and will upload proof",
        style=discord.TextStyle.short,
        default="I have sent the email and will upload proof",
        max_length=100,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle email proof submission - now with direct file upload"""
        try:
            # Update status to awaiting proof
            bot = interaction.client
            db = bot.db
            db.update_vip_request_status(self.request_id, 'awaiting_proof')
            
            # Show the file upload modal directly
            upload_modal = EmailProofUploadModal(self.request_id)
            await interaction.response.send_modal(upload_modal)
            
        except Exception as e:
            logger.error(f"Error in email proof modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please contact staff for assistance.",
                ephemeral=True
            )

class EmailProofUploadModal(discord.ui.Modal):
    """Modal for uploading email proof screenshot with file attachment"""
    
    def __init__(self, request_id: int):
        super().__init__(title="📸 Upload Email Proof Screenshot")
        self.request_id = request_id
    
    screenshot_note = discord.ui.TextInput(
        label="Upload Your Email Screenshot",
        placeholder="Please attach your email screenshot using the attachment button below this text box, then click Submit",
        style=discord.TextStyle.paragraph,
        default="I am uploading my email proof screenshot",
        max_length=500,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle screenshot upload with attachment"""
        try:
            # Check if user attached any files
            if not hasattr(interaction, 'data') or 'attachments' not in interaction.data or not interaction.data['attachments']:
                await interaction.response.send_message(
                    "❌ **No screenshot attached!**\n\n"
                    "Please try again and make sure to:\n"
                    "1. Click the 📎 attachment button in the modal\n"
                    "2. Select your email screenshot file\n"
                    "3. Then click Submit\n\n"
                    "**Required:** Screenshot showing your email was sent to Vantage support.",
                    ephemeral=True
                )
                return
            
            # Get the attachment
            attachment_data = interaction.data['attachments'][0]
            attachment_url = attachment_data.get('url')
            attachment_filename = attachment_data.get('filename', 'screenshot')
            attachment_content_type = attachment_data.get('content_type', '')
            
            # Validate it's an image
            if not attachment_content_type.startswith('image/'):
                await interaction.response.send_message(
                    "❌ **Invalid file type!**\n\n"
                    "Please upload an **image file** (PNG, JPG, GIF, etc.) of your email screenshot.",
                    ephemeral=True
                )
                return
            
            # Update request status and notify staff
            bot = interaction.client
            db = bot.db
            success = db.update_vip_request_status(self.request_id, 'proof_uploaded')
            
            if not success:
                await interaction.response.send_message(
                    "❌ Failed to update request status. Please contact an admin.",
                    ephemeral=True
                )
                return
            
            # Send confirmation to user
            embed = discord.Embed(
                title="✅ Screenshot Uploaded Successfully!",
                description=(
                    "Thank you! Your email proof has been received and forwarded to staff.\n\n"
                    "**What happens next:**\n"
                    "• Staff will review your email screenshot\n"
                    "• You'll receive a DM notification with the decision\n"
                    "• VIP access will be granted within 24 hours if approved\n\n"
                    "**Uploaded file:** " + attachment_filename
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Request ID: {self.request_id}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Send staff DM with the screenshot
            try:
                # Get request details to find responsible staff member
                request_details = db.get_vip_requests_by_status('proof_uploaded')
                current_request = None
                for req in request_details:
                    if req['id'] == self.request_id:
                        current_request = req
                        break
                
                if current_request and current_request['staff_id']:
                    staff_config = db.get_staff_by_discord_id(current_request['staff_id'])
                    if staff_config:
                        # Create a mock attachment object for the notification
                        class MockAttachment:
                            def __init__(self, url, filename, content_type):
                                self.url = url
                                self.filename = filename  
                                self.content_type = content_type
                        
                        mock_attachment = MockAttachment(attachment_url, attachment_filename, attachment_content_type)
                        
                        await send_staff_vip_notification(
                            bot=bot,
                            staff_discord_id=current_request['staff_id'],
                            user_id=interaction.user.id,
                            user_name=interaction.user.display_name,
                            request_type='existing_account',
                            request_id=self.request_id,
                            staff_config=staff_config,
                            image_proof=mock_attachment
                        )
                        
                        logger.info(f"✅ Email proof uploaded for request {self.request_id} by {interaction.user.name}")
                        
            except Exception as e:
                logger.error(f"Failed to send staff notification with uploaded image: {e}")
                # Still show success to user since the upload worked
                
        except Exception as e:
            logger.error(f"Error in email proof upload modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred processing your upload. Please try again or contact an admin.",
                ephemeral=True
            )


class AccountCreatedView(discord.ui.View):
    """View for confirming new account was created"""
    
    def __init__(self, request_id: int):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.request_id = request_id
    
    @discord.ui.button(
        label="✅ Account created & funded",
        style=discord.ButtonStyle.success,
        custom_id="account_created_confirm"
    )
    async def confirm_account_created(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm new account was created and funded"""
        try:
            # Show modal to collect Vantage email
            modal = VantageEmailModal(self.request_id)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"❌ Error in account created confirmation: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

class VantageEmailModal(discord.ui.Modal):
    """Modal for collecting Vantage account email"""
    
    def __init__(self, request_id: int):
        super().__init__(title="Vantage Account Email")
        self.request_id = request_id
    
    email_input = discord.ui.TextInput(
        label="Vantage Account Email",
        placeholder="Enter the email address used for your Vantage account...",
        style=discord.TextStyle.short,
        max_length=100,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle email submission"""
        try:
            email = self.email_input.value.strip()
            
            # Basic email validation
            if "@" not in email or "." not in email:
                await interaction.response.send_message("❌ Please enter a valid email address.", ephemeral=True)
                return
            
            # Update request with email and set to pending verification
            bot = interaction.client
            db = bot.db
            success = db.update_vip_request_status(self.request_id, 'account_created', email)
            
            if success:
                embed = discord.Embed(
                    title="🎉 VIP Request Submitted!",
                    description=(
                        "Thank you for providing your Vantage account information!\n\n"
                        "**Next Steps:**\n"
                        "• Our team will verify your account and deposit\n"
                        "• VIP access will be granted within 24-48 hours\n"
                        "• You'll receive a DM confirmation when complete\n"
                        f"• Your Vantage email: `{email}`"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Request ID: {self.request_id}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Send DM notification to responsible staff member
                try:
                    # Get request details to find staff member
                    request_details = db.get_vip_requests_by_status('account_created')
                    current_request = None
                    for req in request_details:
                        if req['id'] == self.request_id:
                            current_request = req
                            break
                    
                    if current_request and current_request['staff_id']:
                        staff_config = db.get_staff_by_discord_id(current_request['staff_id'])
                        if staff_config:
                            await send_staff_vip_notification(
                                bot=interaction.client,
                                staff_discord_id=current_request['staff_id'],
                                user_id=interaction.user.id,
                                user_name=interaction.user.display_name,
                                request_type='new_account',
                                request_id=self.request_id,
                                staff_config=staff_config
                            )
                except Exception as e:
                    logger.error(f"Failed to send staff DM notification: {e}")
                
            else:
                await interaction.response.send_message("❌ Failed to save email. Please contact an admin.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"❌ Error in email modal submission: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
