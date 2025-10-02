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
from datetime import datetime

logger = logging.getLogger(__name__)

class StaffVIPApprovalView(discord.ui.View):
    """View for staff to approve/deny VIP requests from DMs"""
    
    def __init__(self, request_id: int, user_id: int, user_name: str):
        super().__init__(timeout=86400)  # 24 hour timeout
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

class VIPUpgradeView(discord.ui.View):
    """Main VIP upgrade button view"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @discord.ui.button(
        label="👑 Upgrade to VIP",
        style=discord.ButtonStyle.primary,
        custom_id="vip_upgrade_start",
        emoji="👑"
    )
    async def upgrade_to_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle initial VIP upgrade button click"""
        try:
            # Load staff config to check if user is staff
            vip_cog = interaction.client.get_cog('VIPUpgrade')
            config = vip_cog.bot.db.load_staff_config() if vip_cog else None
            
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
            
            # Add button to mark as completed
            view = AccountCreatedView(request_id)
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
        """Handle email proof submission"""
        try:
            # Send instructions for image upload
            embed = discord.Embed(
                title="📸 Upload Email Screenshot",
                description=(
                    "Please **upload a screenshot** of your sent email in this channel.\n\n"
                    "**Required in screenshot:**\n"
                    "• Show the email was sent to support@vantage.com\n"
                    "• Include the subject line and your message\n"
                    "• Make sure your email address is visible\n\n"
                    "After uploading, our staff will review and approve your VIP upgrade."
                ),
                color=discord.Color.blue()
            )
            
            embed.set_footer(text=f"Request ID: {self.request_id}")
            
            # Update status to awaiting proof
            bot = interaction.client
            db = bot.db
            db.update_vip_request_status(self.request_id, 'awaiting_proof')
            
            # Send to vip-tickets channel for staff review
            config = db.load_staff_config()
            vip_tickets_channel_id = int(config["channels"]["vip_tickets_channel"])
            vip_tickets_channel = interaction.client.get_channel(vip_tickets_channel_id)
            
            if vip_tickets_channel and isinstance(vip_tickets_channel, (discord.TextChannel, discord.Thread)):
                ticket_embed = discord.Embed(
                    title="🎫 New VIP Upgrade - Email Proof Required",
                    description=(
                        f"**User:** {interaction.user.mention} ({interaction.user.display_name})\n"
                        f"**Request ID:** {self.request_id}\n"
                        f"**Status:** Awaiting email proof screenshot\n\n"
                        "User will upload screenshot proof in the VIP upgrade channel."
                    ),
                    color=discord.Color.orange()
                )
                await vip_tickets_channel.send(embed=ticket_embed)
                
                # Send DM notification to responsible staff member
                try:
                    # Get request details to find staff member
                    request_details = db.get_vip_requests_by_status('awaiting_proof')
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
                                request_type='existing_account',
                                request_id=self.request_id,
                                staff_config=staff_config,
                                image_proof=None  # TODO: Add image proof when implemented
                            )
                except Exception as e:
                    logger.error(f"Failed to send staff DM notification: {e}")
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
            
        except Exception as e:
            logger.error(f"Error in email proof modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please contact staff for assistance.",
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
