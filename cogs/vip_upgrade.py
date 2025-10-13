"""
VIP Upgrade Cog
===============

Main cog for handling VIP upgrade system including:
- Sticky embed management
- VIP upgrade process coordination
- Staff notifications and management
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
from datetime import datetime
import os

from views.vip_upgrade import VIPUpgradeView

logger = logging.getLogger(__name__)

class VIPUpgrade(commands.Cog):
    """VIP upgrade system with invite tracking and staff attribution"""
    
    def __init__(self, bot):
        self.bot = bot
        self.VIP_UPGRADE_CHANNEL_ID = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '0'))
        self.VIP_ROLE_ID = os.getenv('VIP_ROLE_ID', '0')
        self.GUILD_ID = os.getenv('DISCORD_GUILD_ID', '0')
        self.STAFF_NOTIFICATION_CHANNEL_ID = int(os.getenv('STAFF_NOTIFICATION_CHANNEL_ID', '0'))
        
        # Add persistent views
        self.bot.add_view(VIPUpgradeView())
    
    async def cog_load(self):
        """Called when cog is loaded"""
        logger.info("👑 VIP Upgrade system loaded")
    
    async def setup_sticky_embed(self, channel):
        """Set up the sticky embed in VIP upgrade channel"""
        try:
            # Check if sticky embed already exists
            async for message in channel.history(limit=50):
                if message.author == self.bot.user and message.embeds:
                    embed = message.embeds[0]
                    if embed.title == "👑 VIP Upgrade Center":
                        logger.info(f"✅ VIP upgrade sticky embed already exists in {channel.name}")
                        return message
            
            # Clear old bot messages to avoid duplicates
            messages_to_delete = []
            async for message in channel.history(limit=20):
                if message.author == self.bot.user:
                    messages_to_delete.append(message)
            
            for message in messages_to_delete:
                try:
                    await message.delete()
                except:
                    pass
            
            # Create the main VIP upgrade embed
            embed = discord.Embed(
                title="👑 VIP Upgrade Center",
                description=(
                    "Welcome to the VIP upgrade system! Upgrade your account to unlock "
                    "premium trading signals, exclusive analysis, and VIP-only benefits."
                ),
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🎯 VIP Benefits",
                value=(
                    "• 📈 Premium trading signals\n"
                    "• 🔍 Detailed market analysis\n"
                    "• 💎 VIP-only channels\n"
                    "• 🚀 Priority support\n"
                    "• 📊 Advanced trading tools"
                ),
                inline=True
            )
            
            embed.add_field(
                name="📋 How It Works",
                value=(
                    "1️⃣ Click **Upgrade to VIP** below\n"
                    "2️⃣ Choose your account type\n"
                    "3️⃣ Follow the guided process\n"
                    "4️⃣ Get VIP access within 24-48h"
                ),
                inline=True
            )
            
            embed.add_field(
                name="ℹ️ Requirements",
                value=(
                    "• Valid Vantage trading account\n"
                    "• Account verification completed\n"
                    "• Minimum deposit requirement met\n"
                    "• Follow attribution guidelines"
                ),
                inline=False
            )
            
            embed.set_footer(
                text="Click the button below to start your VIP upgrade process",
                icon_url=self.bot.user.display_avatar.url
            )
            
            # Send with VIP upgrade view
            view = VIPUpgradeView()
            message = await channel.send(embed=embed, view=view)
            
            # Pin the message
            await message.pin()
            
            logger.info(f"✅ VIP upgrade sticky embed set up in {channel.name}")
            return message
            
        except Exception as e:
            logger.error(f"❌ Error setting up sticky embed: {e}")
            return None
    
    @app_commands.command(name="setup_vip_channel", description="[ADMIN] Set up VIP upgrade channel")
    @app_commands.describe(channel="The channel to set up VIP upgrade system in")
    @app_commands.default_permissions(administrator=True)
    async def setup_vip_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Set up VIP upgrade system in a channel"""
        try:
            target_channel = channel or interaction.channel
            
            # Set up sticky embed
            message = await self.setup_sticky_embed(target_channel)
            
            if message:
                embed = discord.Embed(
                    title="✅ VIP Upgrade System Setup Complete",
                    description=f"VIP upgrade system has been set up in {target_channel.mention}",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📋 Next Steps",
                    value=(
                        "1. Configure staff invite links with `/setup_staff_invite`\n"
                        "2. Set VIP role ID in environment variables\n"
                        "3. Test the upgrade process\n"
                        "4. Monitor pending requests"
                    ),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to set up VIP upgrade system", ephemeral=True)
                
        except Exception as e:
            logger.error(f"❌ Error in setup_vip_channel: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="vip_requests", description="[STAFF] View pending VIP requests")
    @app_commands.describe(status="Filter by request status")
    @app_commands.choices(status=[
        app_commands.Choice(name="Pending", value="pending"),
        app_commands.Choice(name="Email Sent", value="email_sent"),
        app_commands.Choice(name="Account Created", value="account_created"),
        app_commands.Choice(name="Completed", value="completed"),
        app_commands.Choice(name="All", value="all")
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def view_vip_requests(self, interaction: discord.Interaction, status: str = "pending"):
        """View VIP requests filtered by status"""
        try:
            requests = self.bot.db.get_vip_requests_by_status(status)
            
            embed = discord.Embed(
                title=f"📋 VIP Requests ({status.title()})",
                description=f"Found {len(requests)} requests",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if not requests:
                embed.add_field(
                    name="📝 No Requests",
                    value=f"No VIP requests found with status: {status}",
                    inline=False
                )
            else:
                # Show up to 10 requests
                for i, request in enumerate(requests[:10]):
                    embed.add_field(
                        name=f"Request #{request['id']}",
                        value=(
                            f"**User**: <@{request['user_id']}>\n"
                            f"**Type**: {request['request_type'].replace('_', ' ').title()}\n"
                            f"**Status**: {request['status'].title()}\n"
                            f"**Created**: <t:{int(datetime.fromisoformat(request['created_at']).timestamp())}:R>"
                        ),
                        inline=True
                    )
                
                if len(requests) > 10:
                    embed.set_footer(text=f"Showing 10 of {len(requests)} requests. Use filters to narrow results.")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error viewing VIP requests: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="approve_vip", description="[ADMIN] Approve a VIP request")
    @app_commands.describe(
        request_id="The VIP request ID to approve",
        user="The user to grant VIP access to"
    )
    @app_commands.default_permissions(administrator=True)
    async def approve_vip_request(self, interaction: discord.Interaction, request_id: int, user: discord.Member):
        """Approve a VIP request and grant VIP role"""
        try:
            # Update request status
            success = self.bot.db.update_vip_request_status(request_id, 'completed')
            
            if not success:
                await interaction.response.send_message(f"❌ Failed to update request {request_id}", ephemeral=True)
                return
            
            # Grant VIP role if configured
            if self.VIP_ROLE_ID and self.VIP_ROLE_ID != '0':
                vip_role = interaction.guild.get_role(int(self.VIP_ROLE_ID))
                if vip_role:
                    await user.add_roles(vip_role)
                    role_text = f"✅ Granted {vip_role.name} role"
                else:
                    role_text = "⚠️ VIP role not found"
            else:
                role_text = "⚠️ VIP role not configured"
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ VIP Request Approved",
                description=f"VIP request {request_id} has been approved for {user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Role Status", value=role_text, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            # Send DM to user
            try:
                dm_embed = discord.Embed(
                    title="🎉 VIP Access Granted!",
                    description=(
                        "Congratulations! Your VIP upgrade request has been approved.\n\n"
                        "You now have access to:\n"
                        "• 📈 Premium trading signals\n"
                        "• 🔍 Detailed market analysis\n"
                        "• 💎 VIP-only channels\n"
                        "• 🚀 Priority support"
                    ),
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                dm_embed.set_footer(text="Welcome to Zinrai VIP!")
                
                await user.send(embed=dm_embed)
                
            except discord.Forbidden:
                logger.warning(f"Couldn't send VIP approval DM to {user.name}")
            
            logger.info(f"✅ VIP request {request_id} approved for {user.name}")
            
        except Exception as e:
            logger.error(f"❌ Error approving VIP request: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="deny_vip", description="[ADMIN] Deny a VIP request")
    @app_commands.describe(
        request_id="The VIP request ID to deny",
        reason="Reason for denial (optional)"
    )
    @app_commands.default_permissions(administrator=True)
    async def deny_vip_request(self, interaction: discord.Interaction, request_id: int, reason: str = None):
        """Deny a VIP request"""
        try:
            # Update request status
            success = self.bot.db.update_vip_request_status(request_id, 'denied')
            
            if not success:
                await interaction.response.send_message(f"❌ Failed to update request {request_id}", ephemeral=True)
                return
            
            # Send confirmation
            embed = discord.Embed(
                title="❌ VIP Request Denied",
                description=f"VIP request {request_id} has been denied",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"❌ VIP request {request_id} denied. Reason: {reason}")
            
        except Exception as e:
            logger.error(f"❌ Error denying VIP request: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="create_staff_invite", description="[ADMIN] Create invite for staff member (must be in config)")
    @app_commands.describe(
        staff_member="The staff member to create an invite for (must exist in staff_config.json)"
    )
    @app_commands.default_permissions(administrator=True)
    async def create_staff_invite(self, interaction: discord.Interaction, staff_member: discord.Member):
        """Create a permanent invite link for a staff member using config file"""
        try:
            # Check if staff member exists in config
            staff_config = self.bot.db.get_staff_by_discord_id(staff_member.id)
            if not staff_config:
                await interaction.response.send_message(
                    f"❌ **{staff_member.display_name}** is not found in the staff configuration file.\n"
                    f"Please add them to `staff_config.json` first with their Discord ID: `{staff_member.id}`",
                    ephemeral=True
                )
                return
            
            # Create permanent server invite using first available channel
            if not interaction.guild:
                await interaction.response.send_message("❌ This command must be run in a server", ephemeral=True)
                return
            
            # Find the first text channel to create invite from
            invite_channel = None
            for channel in interaction.guild.text_channels:
                if channel.permissions_for(interaction.guild.me).create_instant_invite:
                    invite_channel = channel
                    break
            
            if not invite_channel:
                await interaction.response.send_message("❌ Cannot create invite - no suitable channel found", ephemeral=True)
                return
                
            invite = await invite_channel.create_invite(
                max_age=0,  # Never expires
                max_uses=0,  # Unlimited uses
                temporary=False,  # Permanent membership
                unique=True,  # Create unique invite
                reason=f"Staff invite for {staff_member.display_name}"
            )
            
            # Update config file with invite code
            success = self.bot.db.update_staff_invite_code(staff_member.id, invite.code)
            
            if success:
                embed = discord.Embed(
                    title="✅ Staff Invite Created Successfully",
                    description=f"Created permanent invite link for {staff_member.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="📋 Details", 
                    value=f"**Code:** `{invite.code}`\n**Uses:** Unlimited\n**Expires:** Never", 
                    inline=False
                )
                embed.add_field(
                    name="🏪 Vantage Referral", 
                    value=f"[Link]({staff_config['vantage_referral_link']})", 
                    inline=True
                )
                embed.add_field(
                    name="🏦 IB Code", 
                    value=f"`{staff_config['vantage_ib_code']}`", 
                    inline=True
                )
                
                embed.set_footer(text="This invite link is permanent and will track all users who join through it")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Send the invite link as a separate message for easy copying
                await interaction.followup.send(f"🔗 **Invite Link for Easy Copying:**\n{invite.url}", ephemeral=True)
                
                # Send DM to staff member with their invite link
                try:
                    dm_embed = discord.Embed(
                        title="🎉 Your Personal Invite Link is Ready!",
                        description="You now have a permanent invite link that will track VIP conversions to you.",
                        color=discord.Color.blue()
                    )
                    dm_embed.add_field(
                        name="🔗 Your Invite Link",
                        value=f"[{invite.url}]({invite.url})",
                        inline=False
                    )
                    dm_embed.add_field(
                        name="📊 How It Works",
                        value=(
                            "• Share this link to invite new members\n"
                            "• When they upgrade to VIP, you get credit\n"
                            "• Track your stats with `/invite_stats`\n"
                            "• All VIP upgrades will use your referral links"
                        ),
                        inline=False
                    )
                    
                    await staff_member.send(embed=dm_embed)
                    await interaction.followup.send(f"✅ **DM sent successfully** to {staff_member.mention}", ephemeral=True)
                    
                except discord.Forbidden:
                    logger.warning(f"Couldn't send invite DM to {staff_member.name} - DMs disabled")
                    await interaction.followup.send(
                        f"⚠️ **Could not send DM** to {staff_member.mention}\n"
                        f"They may have DMs disabled from server members.\n"
                        f"Please share the invite link with them manually:\n{invite.url}", 
                        ephemeral=True
                    )
                except Exception as dm_error:
                    logger.error(f"Error sending DM to {staff_member.name}: {dm_error}")
                    await interaction.followup.send(
                        f"❌ **Error sending DM** to {staff_member.mention}: {str(dm_error)}\n"
                        f"Please share the invite link with them manually:\n{invite.url}", 
                        ephemeral=True
                    )
            
            else:
                await interaction.response.send_message("❌ Failed to save staff invite configuration", ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error creating staff invite: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="test_dm", description="[ADMIN] Test if bot can DM a user")
    @app_commands.describe(user="User to test DM with")
    @app_commands.default_permissions(administrator=True)
    async def test_dm(self, interaction: discord.Interaction, user: discord.Member):
        """Test if the bot can send DMs to a specific user"""
        try:
            test_embed = discord.Embed(
                title="🧪 DM Test Message",
                description="This is a test message from the Zinrai Server Bot to verify DM functionality.",
                color=discord.Color.blue()
            )
            test_embed.add_field(
                name="✅ Success!",
                value="If you're seeing this message, the bot can successfully send you DMs.",
                inline=False
            )
            
            await user.send(embed=test_embed)
            
            await interaction.response.send_message(
                f"✅ **DM Test Successful!** Successfully sent test message to {user.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ **DM Test Failed!** Cannot send DMs to {user.mention}\n"
                f"**Possible reasons:**\n"
                f"• They have DMs disabled from server members\n"
                f"• They have blocked the bot\n"
                f"• Their privacy settings prevent DMs",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ **DM Test Error!** Error sending DM to {user.mention}: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="list_staff_invites", description="[ADMIN] List all configured staff invites")
    @app_commands.default_permissions(administrator=True)
    async def list_staff_invites(self, interaction: discord.Interaction):
        """List all configured staff invite links"""
        try:
            # Get all staff configurations from database
            staff_configs = self.bot.db.get_all_staff_configs()
            
            if not staff_configs:
                embed = discord.Embed(
                    title="📋 No Staff Invites Configured",
                    description="No staff invite links have been set up yet.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="🚀 Get Started",
                    value="Use `/create_staff_invite` to create invite links for your staff members.",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Staff Invite Configuration",
                description=f"Currently configured staff invite links ({len(staff_configs)} total)",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for config in staff_configs[:10]:  # Limit to 10 to avoid embed size limits
                staff_member = interaction.guild.get_member(config['staff_id'])
                staff_name = staff_member.display_name if staff_member else config['staff_username']
                
                # Get stats for this staff member
                stats = self.bot.db.get_staff_vip_stats(config['staff_id'])
                
                embed.add_field(
                    name=f"👤 {staff_name}",
                    value=(
                        f"🔗 Code: `{config['invite_code']}`\n"
                        f"📊 Invites: {stats['total_invites']} | VIP: {stats['vip_conversions']}\n"
                        f"📈 Rate: {stats['conversion_rate']:.1f}%"
                    ),
                    inline=True
                )
            
            if len(staff_configs) > 10:
                embed.set_footer(text=f"Showing first 10 of {len(staff_configs)} staff configurations")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error listing staff invites: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="delete_staff_invite", description="[ADMIN] Delete a specific staff member's invite")
    @app_commands.describe(staff_member="The staff member whose invite to delete")
    @app_commands.default_permissions(administrator=True)
    async def delete_staff_invite(self, interaction: discord.Interaction, staff_member: discord.Member):
        """Delete a specific staff member's invite link"""
        try:
            # Check if staff member has an invite configured
            staff_config = self.bot.db.get_staff_by_discord_id(staff_member.id)
            if not staff_config or not staff_config.get('invite_code'):
                await interaction.response.send_message(
                    f"❌ **{staff_member.display_name}** doesn't have an invite link configured.",
                    ephemeral=True
                )
                return
            
            invite_code = staff_config['invite_code']
            
            # Find and delete the Discord invite
            discord_invite = None
            for invite in await interaction.guild.invites():
                if invite.code == invite_code:
                    discord_invite = invite
                    break
            
            # Delete from Discord if it exists
            if discord_invite:
                try:
                    await discord_invite.delete(reason=f"Staff invite deletion by {interaction.user.display_name}")
                    discord_deleted = True
                except Exception as e:
                    logger.warning(f"Could not delete Discord invite {invite_code}: {e}")
                    discord_deleted = False
            else:
                discord_deleted = False
            
            # Clear the invite code from database
            success = self.bot.db.update_staff_invite_code(staff_member.id, None)
            
            if success:
                embed = discord.Embed(
                    title="✅ Staff Invite Deleted",
                    description=f"Successfully removed invite link for {staff_member.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="🗑️ Cleanup Status",
                    value=(
                        f"**Invite Code:** `{invite_code}`\n"
                        f"**Discord Invite:** {'✅ Deleted' if discord_deleted else '⚠️ Not found/already deleted'}\n"
                        f"**Database:** ✅ Cleared"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="📝 Next Steps",
                    value=f"You can create a new invite for {staff_member.mention} using `/create_staff_invite`",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"🗑️ Deleted staff invite for {staff_member.display_name} (code: {invite_code})")
                
            else:
                await interaction.response.send_message(
                    f"❌ Failed to remove invite configuration for {staff_member.mention}",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"❌ Error deleting staff invite: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="delete_invite_by_code", description="[ADMIN] Delete invite by specific invite code")
    @app_commands.describe(invite_code="The invite code to delete (e.g., F82HtFnC6X)")
    @app_commands.default_permissions(administrator=True)
    async def delete_invite_by_code(self, interaction: discord.Interaction, invite_code: str):
        """Delete an invite by its specific code - useful when Discord IDs don't match"""
        try:
            # Find the invite in database
            staff_configs = self.bot.db.get_all_staff_configs()
            target_config = None
            
            for config in staff_configs:
                if config.get('invite_code') == invite_code:
                    target_config = config
                    break
            
            if not target_config:
                await interaction.response.send_message(
                    f"❌ **Invite code `{invite_code}` not found** in staff configuration.",
                    ephemeral=True
                )
                return
            
            # Find and delete the Discord invite
            discord_invite = None
            for invite in await interaction.guild.invites():
                if invite.code == invite_code:
                    discord_invite = invite
                    break
            
            # Delete from Discord if it exists
            if discord_invite:
                try:
                    await discord_invite.delete(reason=f"Invite deletion by code by {interaction.user.display_name}")
                    discord_deleted = True
                except Exception as e:
                    logger.warning(f"Could not delete Discord invite {invite_code}: {e}")
                    discord_deleted = False
            else:
                discord_deleted = False
            
            # Clear the invite code from database
            success = self.bot.db.update_staff_invite_code(target_config['staff_id'], None)
            
            if success:
                # Try to find the Discord user
                staff_member = interaction.guild.get_member(target_config['staff_id'])
                staff_name = staff_member.display_name if staff_member else target_config['staff_username']
                
                embed = discord.Embed(
                    title="✅ Invite Deleted by Code",
                    description=f"Successfully removed invite `{invite_code}`",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="👤 Staff Member",
                    value=(
                        f"**Username:** {target_config['staff_username']}\n"
                        f"**Discord ID:** {target_config['staff_id']}\n"
                        f"**Current User:** {staff_member.mention if staff_member else '❌ Not found in server'}"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="🗑️ Cleanup Status",
                    value=(
                        f"**Invite Code:** `{invite_code}`\n"
                        f"**Discord Invite:** {'✅ Deleted' if discord_deleted else '⚠️ Not found/already deleted'}\n"
                        f"**Database:** ✅ Cleared"
                    ),
                    inline=False
                )
                
                if staff_member:
                    embed.add_field(
                        name="📝 Next Steps",
                        value=f"You can create a new invite for {staff_member.mention} using `/create_staff_invite`",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⚠️ Note",
                        value="User not found in server. You may need to update their Discord ID in staff config.",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"🗑️ Deleted invite by code: {invite_code} for {staff_name}")
                
            else:
                await interaction.response.send_message(
                    f"❌ Failed to remove invite configuration for code `{invite_code}`",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"❌ Error deleting invite by code: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="vip_stats", description="View VIP upgrade statistics")
    @app_commands.default_permissions(manage_guild=True)
    async def vip_stats(self, interaction: discord.Interaction):
        """Show VIP upgrade statistics"""
        try:
            # This would require database queries for stats
            embed = discord.Embed(
                title="📊 VIP Upgrade Statistics",
                description="Overview of VIP upgrade system performance",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Placeholder stats - would be populated from database
            embed.add_field(name="Total Requests", value="🔢 Coming Soon", inline=True)
            embed.add_field(name="Approved", value="✅ Coming Soon", inline=True)
            embed.add_field(name="Pending", value="⏳ Coming Soon", inline=True)
            embed.add_field(name="Conversion Rate", value="📈 Coming Soon", inline=True)
            embed.add_field(name="Top Staff", value="👑 Coming Soon", inline=True)
            embed.add_field(name="This Month", value="📅 Coming Soon", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error showing VIP stats: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="list_invite_users", description="[ADMIN] Show all users who joined through a specific invite")
    @app_commands.describe(staff_member="The staff member whose invite users to list")
    @app_commands.default_permissions(administrator=True)
    async def list_invite_users(self, interaction: discord.Interaction, staff_member: discord.Member):
        """List all users who joined through a specific staff member's invite"""
        try:
            # Get staff member's invite code
            staff_config = self.bot.db.get_staff_by_discord_id(staff_member.id)
            if not staff_config or not staff_config.get('invite_code'):
                # Debug: Let's check if the user exists with a different ID
                all_configs = self.bot.db.get_all_staff_configs()
                matching_configs = []
                for config in all_configs:
                    if config.get('staff_username', '').lower() == staff_member.display_name.lower():
                        matching_configs.append(config)
                
                embed = discord.Embed(
                    title="❌ Staff Member Not Found",
                    description=f"**{staff_member.display_name}** doesn't have an invite code configured.",
                    color=discord.Color.red()
                )
                
                embed.add_field(
                    name="🔍 Debug Info",
                    value=(
                        f"**Looking for Discord ID:** {staff_member.id}\n"
                        f"**Username:** {staff_member.display_name}\n"
                        f"**Possible matches:** {len(matching_configs)}"
                    ),
                    inline=False
                )
                
                if matching_configs:
                    match_info = []
                    for config in matching_configs[:3]:  # Show max 3 matches
                        match_info.append(
                            f"• Username: {config.get('staff_username', 'Unknown')}\n"
                            f"  Discord ID: {config.get('staff_id', 'Unknown')}\n"
                            f"  Invite Code: {config.get('invite_code', 'None')}"
                        )
                    
                    embed.add_field(
                        name="🔧 Possible Discord ID Mismatch",
                        value='\n'.join(match_info),
                        inline=False
                    )
                    
                    embed.add_field(
                        name="💡 Solution",
                        value=(
                            "Use `/delete_invite_by_code [code]` to delete the old entry,\n"
                            "then `/create_staff_invite` to create a new one with correct ID."
                        ),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="💡 Solution", 
                        value="Use `/create_staff_invite` to create an invite for this staff member.",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            invite_code = staff_config['invite_code']
            
            # Get all users who joined through this invite
            invite_users = self.bot.db.get_users_by_invite_code(invite_code)
            
            if not invite_users:
                embed = discord.Embed(
                    title="📋 No Users Found",
                    description=f"No users have joined through **{staff_member.display_name}**'s invite yet.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="📊 Invite Details",
                    value=(
                        f"**Staff Member:** {staff_member.mention}\n"
                        f"**Invite Code:** `{invite_code}`\n"
                        f"**Total Joins:** 0"
                    ),
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create embed with user list
            embed = discord.Embed(
                title=f"👥 Users from {staff_member.display_name}'s Invite",
                description=f"All users who joined through invite code `{invite_code}`",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Summary",
                value=(
                    f"**Staff Member:** {staff_member.mention}\n"
                    f"**Invite Code:** `{invite_code}`\n"
                    f"**Total Joins:** {len(invite_users)}"
                ),
                inline=False
            )
            
            # Show user list (paginated if too many)
            user_list = []
            vip_count = 0
            active_count = 0
            
            for i, user_data in enumerate(invite_users[:25]):  # Limit to 25 to avoid embed limits
                user_id = user_data.get('user_id')
                username = user_data.get('username', 'Unknown')
                join_date = user_data.get('joined_at', 'Unknown')
                
                # Check if user is still in server
                member = interaction.guild.get_member(int(user_id)) if user_id else None
                
                # Check if user has VIP role
                has_vip = False
                if member and self.VIP_ROLE_ID:
                    vip_role = interaction.guild.get_role(int(self.VIP_ROLE_ID))
                    has_vip = vip_role and vip_role in member.roles
                
                if member:
                    active_count += 1
                if has_vip:
                    vip_count += 1
                
                # Format user entry
                status_emoji = "🟢" if member else "🔴"
                vip_emoji = "👑" if has_vip else ""
                user_mention = member.mention if member else f"~~{username}~~"
                
                user_list.append(f"{i+1}. {status_emoji} {user_mention} {vip_emoji}")
            
            if user_list:
                embed.add_field(
                    name=f"👥 Users (Showing {len(user_list)}/{len(invite_users)})",
                    value='\n'.join(user_list),
                    inline=False
                )
            
                embed.add_field(
                    name="📈 Statistics",
                    value=(
                        f"🟢 **Active in Server:** {active_count}/{len(invite_users)}\n"
                        f"👑 **VIP Members:** {vip_count}/{len(invite_users)}\n"
                        f"📊 **VIP Conversion Rate:** {(vip_count/len(invite_users)*100):.1f}%"
                    ),
                    inline=True
                )
                
                # Add IB attribution info
                embed.add_field(
                    name="💼 IB Attribution",
                    value=(
                        f"**IB Code:** {staff_config.get('vantage_ib_code', 'N/A')}\n"
                        f"**Referral Link:** [View]({staff_config.get('vantage_referral_link', '#')})"
                    ),
                    inline=True
                )
            
            if len(invite_users) > 25:
                embed.set_footer(text=f"Showing first 25 of {len(invite_users)} users. Use pagination commands for more.")
            else:
                embed.set_footer(text=f"🟢 Active in server | 👑 VIP member | 🔴 Left server")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error listing invite users: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="list_users_by_code", description="[ADMIN] Show all users who joined through a specific invite code")
    @app_commands.describe(invite_code="The invite code to look up (e.g., abc123def)")
    @app_commands.default_permissions(administrator=True)
    async def list_users_by_code(self, interaction: discord.Interaction, invite_code: str):
        """List all users who joined through a specific invite code"""
        try:
            # Get all users who joined through this invite code
            invite_users = self.bot.db.get_users_by_invite_code(invite_code)
            
            if not invite_users:
                embed = discord.Embed(
                    title="📋 No Users Found",
                    description=f"No users have joined through invite code `{invite_code}`.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="💡 Possible Reasons",
                    value=(
                        "• Invalid or expired invite code\n"
                        "• No users have used this invite yet\n"
                        "• Invite code was deleted/recreated"
                    ),
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Find staff member who owns this invite
            staff_config = None
            staff_configs = self.bot.db.get_all_staff_configs()
            for config in staff_configs:
                if config.get('invite_code') == invite_code:
                    staff_config = config
                    break
            
            staff_member = None
            if staff_config:
                staff_member = interaction.guild.get_member(staff_config['staff_id'])
            
            # Create embed with user list
            embed = discord.Embed(
                title=f"👥 Users from Invite Code `{invite_code}`",
                description=f"All users who joined through this invite",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if staff_member and staff_config:
                embed.add_field(
                    name="👤 Staff Attribution",
                    value=(
                        f"**Staff Member:** {staff_member.mention}\n"
                        f"**IB Code:** {staff_config.get('vantage_ib_code', 'N/A')}\n"
                        f"**Total Joins:** {len(invite_users)}"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📊 Invite Details",
                    value=(
                        f"**Invite Code:** `{invite_code}`\n"
                        f"**Staff Member:** Unknown/Not Found\n"
                        f"**Total Joins:** {len(invite_users)}"
                    ),
                    inline=False
                )
            
            # Show user list (paginated if too many)
            user_list = []
            vip_count = 0
            active_count = 0
            
            for i, user_data in enumerate(invite_users[:25]):  # Limit to 25 to avoid embed limits
                user_id = user_data.get('user_id')
                username = user_data.get('username', 'Unknown')
                join_date = user_data.get('joined_at', 'Unknown')
                
                # Check if user is still in server
                member = interaction.guild.get_member(int(user_id)) if user_id else None
                
                # Check if user has VIP role
                has_vip = False
                if member and self.VIP_ROLE_ID:
                    vip_role = interaction.guild.get_role(int(self.VIP_ROLE_ID))
                    has_vip = vip_role and vip_role in member.roles
                
                if member:
                    active_count += 1
                if has_vip:
                    vip_count += 1
                
                # Format user entry with join date
                status_emoji = "🟢" if member else "🔴"
                vip_emoji = "👑" if has_vip else ""
                user_mention = member.mention if member else f"~~{username}~~"
                
                # Format join date
                if join_date and join_date != 'Unknown':
                    try:
                        # Assuming join_date is in ISO format
                        from datetime import datetime as dt
                        join_dt = dt.fromisoformat(join_date.replace('Z', '+00:00'))
                        formatted_date = join_dt.strftime('%m/%d/%y')
                    except:
                        formatted_date = "Unknown"
                else:
                    formatted_date = "Unknown"
                
                user_list.append(f"{i+1}. {status_emoji} {user_mention} {vip_emoji} `({formatted_date})`")
            
            if user_list:
                embed.add_field(
                    name=f"👥 Users (Showing {len(user_list)}/{len(invite_users)})",
                    value='\n'.join(user_list),
                    inline=False
                )
            
                embed.add_field(
                    name="📈 Statistics",
                    value=(
                        f"🟢 **Active in Server:** {active_count}/{len(invite_users)}\n"
                        f"👑 **VIP Members:** {vip_count}/{len(invite_users)}\n"
                        f"📊 **VIP Conversion Rate:** {(vip_count/len(invite_users)*100):.1f}%"
                    ),
                    inline=True
                )
            
            if len(invite_users) > 25:
                embed.set_footer(text=f"Showing first 25 of {len(invite_users)} users. 🟢 Active | 👑 VIP | 🔴 Left | (Join Date)")
            else:
                embed.set_footer(text=f"🟢 Active in server | 👑 VIP member | 🔴 Left server | (Join Date)")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error listing users by code: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="fix_staff_discord_id", description="[ADMIN] Fix Discord ID mismatch for staff member")
    @app_commands.describe(
        staff_member="The current Discord user",
        old_invite_code="Their existing invite code that needs ID updated"
    )
    @app_commands.default_permissions(administrator=True)
    async def fix_staff_discord_id(self, interaction: discord.Interaction, staff_member: discord.Member, old_invite_code: str):
        """Fix Discord ID mismatch for a staff member"""
        try:
            # Find the staff config with the old invite code
            all_configs = self.bot.db.get_all_staff_configs()
            target_config = None
            
            for config in all_configs:
                if config.get('invite_code') == old_invite_code:
                    target_config = config
                    break
            
            if not target_config:
                await interaction.response.send_message(
                    f"❌ No staff configuration found with invite code `{old_invite_code}`",
                    ephemeral=True
                )
                return
            
            old_discord_id = target_config.get('staff_id')
            new_discord_id = staff_member.id
            
            if old_discord_id == new_discord_id:
                await interaction.response.send_message(
                    f"✅ Discord ID already matches! {staff_member.mention} is correctly configured.",
                    ephemeral=True
                )
                return
            
            # Update the Discord ID in the database
            success = self.bot.db.update_staff_discord_id(old_discord_id, new_discord_id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Discord ID Updated Successfully",
                    description=f"Fixed Discord ID mismatch for {staff_member.mention}",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="🔧 Changes Made",
                    value=(
                        f"**Staff Member:** {staff_member.mention}\n"
                        f"**Invite Code:** `{old_invite_code}`\n"
                        f"**Old Discord ID:** {old_discord_id}\n"
                        f"**New Discord ID:** {new_discord_id}"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="✅ What Works Now",
                    value=(
                        f"• `/list_invite_users {staff_member.mention}` will work\n"
                        f"• `/delete_staff_invite {staff_member.mention}` will work\n"
                        f"• VIP upgrade attribution will work correctly\n"
                        f"• All existing invite tracking data preserved"
                    ),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"✅ Fixed Discord ID for {staff_member.display_name}: {old_discord_id} → {new_discord_id}")
                
            else:
                await interaction.response.send_message(
                    f"❌ Failed to update Discord ID in database. Please contact a developer.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"❌ Error fixing staff Discord ID: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="manage_invite_permissions", description="[ADMIN] Manage who can create invites")
    @app_commands.describe(
        action="Enable or disable invite creation for everyone",
        role="Specific role to grant/revoke invite permissions (optional)"
    )
    async def manage_invite_permissions(self, interaction: discord.Interaction, 
                                      action: str, role: discord.Role = None):
        """Manage server invite creation permissions"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        try:
            guild = interaction.guild
            everyone_role = guild.default_role
            
            if action.lower() == "disable":
                # Remove create_instant_invite permission from @everyone
                permissions = everyone_role.permissions
                permissions.create_instant_invite = False
                await everyone_role.edit(permissions=permissions)
                
                embed = discord.Embed(
                    title="🔒 Invite Creation Disabled",
                    description="Regular members can no longer create invite links. Only staff with specific permissions can create invites.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="📋 What This Means",
                    value=(
                        "• Only administrators and assigned staff can create invites\n"
                        "• Staff invites are managed through `/create_staff_invite`\n"
                        "• This ensures proper VIP upgrade attribution"
                    ),
                    inline=False
                )
                
            elif action.lower() == "enable":
                # Restore create_instant_invite permission to @everyone
                permissions = everyone_role.permissions
                permissions.create_instant_invite = True
                await everyone_role.edit(permissions=permissions)
                
                embed = discord.Embed(
                    title="🔓 Invite Creation Enabled",
                    description="All members can now create invite links.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="⚠️ Warning",
                    value="This may affect VIP upgrade attribution accuracy since members could join through non-staff invites.",
                    inline=False
                )
                
            else:
                await interaction.response.send_message("❌ Action must be 'enable' or 'disable'", ephemeral=True)
                return
            
            # Handle specific role permissions
            if role:
                role_permissions = role.permissions
                if action.lower() == "disable":
                    role_permissions.create_instant_invite = False
                    embed.add_field(
                        name=f"🚫 Role Updated",
                        value=f"Removed invite permissions from {role.mention}",
                        inline=False
                    )
                else:
                    role_permissions.create_instant_invite = True
                    embed.add_field(
                        name=f"✅ Role Updated", 
                        value=f"Granted invite permissions to {role.mention}",
                        inline=False
                    )
                await role.edit(permissions=role_permissions)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Admin {interaction.user.name} {action}d invite creation permissions")
            
        except Exception as e:
            logger.error(f"❌ Error managing invite permissions: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="check_invite_permissions", description="[ADMIN] Check who can create invites")
    async def check_invite_permissions(self, interaction: discord.Interaction):
        """Check current invite creation permissions"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        try:
            guild = interaction.guild
            everyone_role = guild.default_role
            
            embed = discord.Embed(
                title="🔍 Invite Permission Status",
                description="Current invite creation permissions in this server",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Check @everyone permissions
            everyone_can_invite = everyone_role.permissions.create_instant_invite
            embed.add_field(
                name="👥 @everyone Role",
                value="✅ Can create invites" if everyone_can_invite else "❌ Cannot create invites",
                inline=False
            )
            
            # Check roles that can create invites
            roles_with_invite = []
            for role in guild.roles:
                if role != everyone_role and role.permissions.create_instant_invite:
                    roles_with_invite.append(role.mention)
            
            if roles_with_invite:
                embed.add_field(
                    name="🎭 Roles with Invite Permissions",
                    value="\n".join(roles_with_invite[:10]),  # Limit to 10 roles
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎭 Roles with Invite Permissions", 
                    value="None (besides Administrator roles)",
                    inline=False
                )
            
            # Show staff invite status from database
            staff_invites = []
            staff_status = self.bot.db.get_staff_invite_status()
            for username, invite_code in staff_status.items():
                status = f"✅ {invite_code}" if invite_code else "❌ No invite"
                staff_invites.append(f"**{username}**: {status}")
            
            if staff_invites:
                embed.add_field(
                    name="👑 Staff Invite Status",
                    value="\n".join(staff_invites),
                    inline=False
                )
            
            embed.set_footer(text="💡 Use /manage_invite_permissions to change these settings")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error checking invite permissions: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="add_existing_staff_invite", description="[ADMIN] Manually add existing staff invite code")
    @app_commands.describe(
        staff_member="The staff member who owns the invite",
        invite_code="The invite code (without discord.gg/)"
    )
    async def add_existing_staff_invite(self, interaction: discord.Interaction, 
                                      staff_member: discord.Member, invite_code: str):
        """Manually add existing staff invite codes"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        try:
            success = self.bot.db.manually_add_staff_invite(staff_member.id, invite_code)
            
            if success:
                embed = discord.Embed(
                    title="✅ Staff Invite Added",
                    description=f"Successfully added invite code `{invite_code}` for {staff_member.mention}",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="🔗 Invite Link",
                    value=f"https://discord.gg/{invite_code}",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Failed to Add Invite",
                    description="Could not add the staff invite. Check that the staff member is configured properly.",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error adding staff invite: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="debug_staff_database", description="[ADMIN] Debug staff invites database")
    async def debug_staff_database(self, interaction: discord.Interaction):
        """Debug staff invites database"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        try:
            debug_info = self.bot.db.debug_staff_invites_table()
            
            embed = discord.Embed(
                title="🔍 Database Debug Info",
                description=debug_info,
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="diagnose_invites", description="[ADMIN] Comprehensive invite system diagnosis")
    async def diagnose_invites(self, interaction: discord.Interaction):
        """Comprehensive invite system diagnosis"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            diagnosis = []
            
            # 1. Check database invite codes
            diagnosis.append("🔍 **DATABASE ANALYSIS**")
            try:
                # Get staff configs which contain invite codes
                staff_configs = self.bot.db.get_all_staff_configs()
                db_invites = [(config['staff_id'], config.get('invite_code')) for config in staff_configs if config.get('invite_code')]
                diagnosis.append(f"Total staff in database: {len(db_invites)}")
                
                for staff_id, invite_code in db_invites:
                    try:
                        user = self.bot.get_user(staff_id)
                        username = user.display_name if user else f"User {staff_id}"
                        diagnosis.append(f"• {username}: `{invite_code}`")
                    except:
                        diagnosis.append(f"• User {staff_id}: `{invite_code}`")
                        
            except Exception as e:
                diagnosis.append(f"❌ Database error: {str(e)}")
            
            # 2. Check Discord invites
            diagnosis.append("\n🌐 **DISCORD INVITES ANALYSIS**")
            try:
                if interaction.guild:
                    guild_invites = await interaction.guild.invites()
                    diagnosis.append(f"Total guild invites: {len(guild_invites)}")
                    
                    active_codes = {}
                    for invite in guild_invites:
                        inviter_name = invite.inviter.display_name if invite.inviter else "Unknown"
                        active_codes[invite.code] = {
                            'inviter': invite.inviter.id if invite.inviter else None,
                            'inviter_name': inviter_name,
                            'uses': invite.uses or 0,
                            'max_uses': invite.max_uses or 0,
                            'max_age': invite.max_age or 0,
                            'temporary': invite.temporary
                        }
                        
                        status = "🟢 Active"
                        max_age = invite.max_age or 0
                        if max_age > 0:
                            status += f" (expires in {max_age}s)"
                        if invite.temporary:
                            status += " (temporary)"
                            
                        diagnosis.append(f"• `{invite.code}` by {inviter_name}: {invite.uses or 0} uses - {status}")
                else:
                    diagnosis.append("❌ Guild not found")
                    active_codes = {}
                    
            except Exception as e:
                diagnosis.append(f"❌ Discord API error: {str(e)}")
                active_codes = {}
            
            # 3. Compare database vs Discord
            diagnosis.append("\n🔄 **SYNCHRONIZATION CHECK**")
            try:
                db_codes = set(code for _, code in db_invites)
                discord_codes = set(active_codes.keys())
                
                # Find mismatches
                db_only = db_codes - discord_codes
                discord_only = discord_codes - db_codes
                matching = db_codes & discord_codes
                
                diagnosis.append(f"Codes in both DB and Discord: {len(matching)}")
                diagnosis.append(f"Codes only in database (expired): {len(db_only)}")
                diagnosis.append(f"Codes only in Discord (not tracked): {len(discord_only)}")
                
                if db_only:
                    diagnosis.append("⚠️ **EXPIRED CODES IN DATABASE:**")
                    for code in db_only:
                        diagnosis.append(f"  • `{code}` - should be removed")
                
                if discord_only:
                    diagnosis.append("⚠️ **UNTRACKED DISCORD INVITES:**")
                    for code in discord_only:
                        invite_info = active_codes[code]
                        diagnosis.append(f"  • `{code}` by {invite_info['inviter_name']} - should be added to DB")
                        
            except Exception as e:
                diagnosis.append(f"❌ Comparison error: {str(e)}")
            
            # 4. Check staff invite statistics
            diagnosis.append("\n📊 **INVITE STATISTICS**")
            try:
                # Get individual staff VIP stats
                total_invites = 0
                staff_with_stats = 0 
                
                for config in staff_configs:
                    try:
                        stats = self.bot.db.get_staff_vip_stats(config['staff_id'])
                        if stats and stats.get('total_invites', 0) > 0:
                            staff_with_stats += 1
                            total_invites += stats['total_invites']
                            
                            user = self.bot.get_user(config['discord_id'])
                            username = user.display_name if user else config.get('name', f"User {config['discord_id']}")
                            diagnosis.append(f"• {username}: {stats['total_invites']} invites")
                    except Exception as e:
                        pass  # Skip errors for individual staff
                        
                diagnosis.append(f"Total recorded invites across all staff: {total_invites}")
                diagnosis.append(f"Staff members with recorded invites: {staff_with_stats}/{len(staff_configs)}")
                    
            except Exception as e:
                diagnosis.append(f"❌ Statistics error: {str(e)}")
            
            # 5. Recommendations
            diagnosis.append("\n💡 **RECOMMENDATIONS**")
            try:
                if db_only:
                    diagnosis.append("1. Clean expired invite codes from database")
                if discord_only:
                    diagnosis.append("2. Add untracked Discord invites to database")
                if total_invites == 0:
                    diagnosis.append("3. Check invite tracking system - no invites recorded")
                    diagnosis.append("4. Verify member join event handler is working")
                
                diagnosis.append("5. Consider running /fix_invite_tracking to repair synchronization")
                    
            except:
                diagnosis.append("Error generating recommendations")
            
            # Create and send embed
            diagnosis_text = "\n".join(diagnosis)
            
            # Split into multiple embeds if too long
            if len(diagnosis_text) > 4000:
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in diagnosis:
                    if current_length + len(line) > 3900:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_length = len(line)
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                
                # Send first chunk as response
                embed = discord.Embed(
                    title="🏥 Invite System Diagnosis (1/1)" if len(chunks) == 1 else f"🏥 Invite System Diagnosis (1/{len(chunks)})",
                    description=chunks[0],
                    color=discord.Color.orange()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Send additional chunks
                for i, chunk in enumerate(chunks[1:], 2):
                    embed = discord.Embed(
                        title=f"🏥 Invite System Diagnosis ({i}/{len(chunks)})",
                        description=chunk,
                        color=discord.Color.orange()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="🏥 Invite System Diagnosis",
                    description=diagnosis_text,
                    color=discord.Color.orange()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Diagnosis failed: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="fix_invite_tracking", description="[ADMIN] Fix invite tracking synchronization issues")
    async def fix_invite_tracking(self, interaction: discord.Interaction):
        """Fix invite tracking synchronization issues"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            fixes_applied = []
            
            # 1. Get database and Discord invite codes
            try:
                db_invites = self.bot.db.get_all_staff_configs()
                db_codes = {config['staff_id']: config.get('invite_code') for config in db_invites if config.get('invite_code')}
                
                guild_invites = await interaction.guild.invites()
                discord_codes = {}
                for invite in guild_invites:
                    if invite.inviter:
                        discord_codes[invite.code] = {
                            'inviter_id': invite.inviter.id,
                            'inviter_name': invite.inviter.display_name,
                            'uses': invite.uses or 0
                        }
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to fetch invite data: {str(e)}", ephemeral=True)
                return
            
            # 2. Find expired codes in database
            db_code_set = set(db_codes.values())
            discord_code_set = set(discord_codes.keys())
            expired_codes = db_code_set - discord_code_set
            untracked_codes = discord_code_set - db_code_set
            
            # 3. Remove expired codes from database
            if expired_codes:
                fixes_applied.append(f"🗑️ **REMOVED EXPIRED CODES ({len(expired_codes)}):**")
                for staff_id, code in db_codes.items():
                    if code in expired_codes:
                        try:
                            user = self.bot.get_user(staff_id)
                            username = user.display_name if user else f"User {staff_id}"
                            
                            # Clear the expired invite code
                            self.bot.db.update_staff_invite_code(staff_id, None)
                            fixes_applied.append(f"  • Removed expired code `{code}` from {username}")
                        except Exception as e:
                            fixes_applied.append(f"  • Failed to remove code `{code}`: {str(e)}")
            
            # 4. Add untracked Discord invites to database
            if untracked_codes:
                fixes_applied.append(f"\n➕ **ADDED UNTRACKED CODES ({len(untracked_codes)}):**")
                for code in untracked_codes:
                    try:
                        invite_info = discord_codes[code]
                        inviter_id = invite_info['inviter_id']
                        inviter_name = invite_info['inviter_name']
                        
                        # Check if this user needs a code assigned
                        staff_config = self.bot.db.get_staff_by_discord_id(inviter_id)
                        if staff_config and not staff_config.get('invite_code'):
                            # Assign this code to the staff member
                            self.bot.db.update_staff_invite_code(inviter_id, code)
                            fixes_applied.append(f"  • Assigned code `{code}` to {inviter_name}")
                        else:
                            # Just record the invite exists
                            fixes_applied.append(f"  • Found code `{code}` by {inviter_name} (already tracked or not staff)")
                    except Exception as e:
                        fixes_applied.append(f"  • Failed to process code `{code}`: {str(e)}")
            
            # 5. Update mismatched codes (like CZ89XauEx -> jCZ89XauEx for Fin)
            fixes_applied.append(f"\n🔄 **UPDATED MISMATCHED CODES:**")
            mismatched_found = False
            
            for staff_id, db_code in db_codes.items():
                if db_code and db_code in expired_codes:
                    # Look for a similar code in Discord
                    user = self.bot.get_user(staff_id)
                    username = user.display_name if user else f"User {staff_id}"
                    
                    # Find if there's a Discord invite by the same user
                    matching_discord_code = None
                    for discord_code, info in discord_codes.items():
                        if info['inviter_id'] == staff_id:
                            matching_discord_code = discord_code
                            break
                    
                    if matching_discord_code:
                        try:
                            self.bot.db.update_staff_invite_code(staff_id, matching_discord_code)
                            fixes_applied.append(f"  • Updated {username}: `{db_code}` → `{matching_discord_code}`")
                            mismatched_found = True
                        except Exception as e:
                            fixes_applied.append(f"  • Failed to update {username}: {str(e)}")
            
            if not mismatched_found:
                fixes_applied.append("  • No mismatched codes found")
            
            # 6. Verify invite statistics tracking
            fixes_applied.append(f"\n📊 **INVITE STATISTICS VERIFICATION:**")
            try:
                # Check if we have any recorded invite statistics
                all_configs = self.bot.db.get_all_staff_configs()
                staff_with_stats = 0
                total_recorded_invites = 0
                
                for config in all_configs:
                    try:
                        stats = self.bot.db.get_staff_vip_stats(config['staff_id'])
                        if stats and stats.get('total_invites', 0) > 0:
                            staff_with_stats += 1
                            total_recorded_invites += stats['total_invites']
                    except:
                        pass
                
                fixes_applied.append(f"  • Staff with recorded invites: {staff_with_stats}/{len(all_configs)}")
                fixes_applied.append(f"  • Total recorded invites: {total_recorded_invites}")
                
                if total_recorded_invites == 0:
                    fixes_applied.append("  • ⚠️ No invite statistics found - check member join event handler")
                
            except Exception as e:
                fixes_applied.append(f"  • Error checking statistics: {str(e)}")
            
            # 7. Summary
            fixes_applied.append(f"\n✅ **FIX SUMMARY:**")
            fixes_applied.append(f"  • Removed {len(expired_codes)} expired codes")
            fixes_applied.append(f"  • Processed {len(untracked_codes)} untracked codes")
            fixes_applied.append(f"  • Updated database synchronization")
            fixes_applied.append(f"  • Verified invite tracking system")
            
            # Send results
            fixes_text = "\n".join(fixes_applied)
            
            # Split into multiple embeds if too long
            if len(fixes_text) > 4000:
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in fixes_applied:
                    if current_length + len(line) > 3900:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_length = len(line)
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                
                # Send first chunk as response
                embed = discord.Embed(
                    title="🔧 Invite Tracking Fix Results (1/1)" if len(chunks) == 1 else f"🔧 Invite Tracking Fix Results (1/{len(chunks)})",
                    description=chunks[0],
                    color=discord.Color.green()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Send additional chunks
                for i, chunk in enumerate(chunks[1:], 2):
                    embed = discord.Embed(
                        title=f"🔧 Invite Tracking Fix Results ({i}/{len(chunks)})",
                        description=chunk,
                        color=discord.Color.green()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="🔧 Invite Tracking Fix Results",
                    description=fixes_text,
                    color=discord.Color.green()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Suggest running diagnosis again
            embed = discord.Embed(
                title="🔍 Next Steps",
                description="Run `/diagnose_invites` again to verify all issues have been resolved.",
                color=discord.Color.blue()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Fix failed: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="regenerate_all_invites", description="[ADMIN] Generate fresh invite codes for all staff members")
    async def regenerate_all_invites(self, interaction: discord.Interaction):
        """Generate fresh invite codes for all staff members"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            results = []
            staff_configs = self.bot.db.get_all_staff_configs()
            
            if not staff_configs:
                await interaction.followup.send("❌ No staff configurations found in database.", ephemeral=True)
                return
            
            results.append(f"🔄 **REGENERATING INVITES FOR {len(staff_configs)} STAFF MEMBERS**\n")
            
            # First, delete all existing invites created by the bot
            try:
                if interaction.guild:
                    guild_invites = await interaction.guild.invites()
                    bot_invites = [invite for invite in guild_invites if invite.inviter and invite.inviter.id == self.bot.user.id]
                else:
                    results.append("❌ Guild not found\n")
                    await interaction.followup.send("❌ Guild not found", ephemeral=True)
                    return
                
                if bot_invites:
                    results.append(f"🗑️ **CLEANING UP OLD INVITES ({len(bot_invites)}):**")
                    for invite in bot_invites:
                        try:
                            await invite.delete(reason="Regenerating fresh staff invites")
                            results.append(f"  • Deleted old invite: `{invite.code}`")
                        except discord.NotFound:
                            results.append(f"  • Invite `{invite.code}` already deleted")
                        except Exception as e:
                            results.append(f"  • Failed to delete `{invite.code}`: {str(e)}")
                    results.append("")
                
            except Exception as e:
                results.append(f"⚠️ Warning: Could not clean up old invites: {str(e)}\n")
            
            # Generate fresh invites for each staff member
            results.append("✨ **GENERATING FRESH INVITES:**")
            successful_invites = []
            failed_invites = []
            
            for config in staff_configs:
                staff_id = config['staff_id']
                try:
                    user = self.bot.get_user(staff_id)
                    username = user.display_name if user else f"User {staff_id}"
                    
                    # Create a fresh permanent invite
                    if interaction.guild:
                        invite = await interaction.guild.create_invite(
                            max_age=0,        # Never expires
                            max_uses=0,       # Unlimited uses
                            temporary=False,  # Members stay permanently
                            unique=True,      # Force create new unique invite
                            reason=f"Fresh staff invite for {username}"
                        )
                    else:
                        raise Exception("Guild not available")
                    
                    # Update database with new invite code
                    success = self.bot.db.update_staff_invite_code(staff_id, invite.code)
                    
                    if success:
                        successful_invites.append({
                            'username': username,
                            'staff_id': staff_id,
                            'invite_code': invite.code,
                            'invite_url': f"https://discord.gg/{invite.code}"
                        })
                        results.append(f"  ✅ {username}: `{invite.code}` → https://discord.gg/{invite.code}")
                    else:
                        failed_invites.append(username)
                        results.append(f"  ❌ {username}: Created invite but failed to save to database")
                        
                except Exception as e:
                    failed_invites.append(username)
                    results.append(f"  ❌ {username}: {str(e)}")
            
            # Summary
            results.append(f"\n📊 **GENERATION SUMMARY:**")
            results.append(f"  • Successfully created: {len(successful_invites)}")
            results.append(f"  • Failed: {len(failed_invites)}")
            
            if successful_invites:
                results.append(f"\n🔗 **TESTING INVITE LINKS:**")
                # Test each invite link
                for invite_data in successful_invites:
                    try:
                        # Fetch the invite to verify it exists and get current stats
                        fetched_invite = await self.bot.fetch_invite(invite_data['invite_code'])
                        results.append(f"  ✅ {invite_data['username']}: Link works, {fetched_invite.uses or 0} uses")
                    except discord.NotFound:
                        results.append(f"  ❌ {invite_data['username']}: Link not found!")
                    except Exception as e:
                        results.append(f"  ⚠️ {invite_data['username']}: Test failed: {str(e)}")
            
            # Recommendations
            results.append(f"\n💡 **NEXT STEPS:**")
            results.append("1. Test invite links manually by clicking them")
            results.append("2. Run `/list_staff_invites` to verify database updates")
            results.append("3. Test VIP upgrade flow to ensure invite tracking works")
            results.append("4. Run `/diagnose_invites` to verify synchronization")
            
            # Send results
            results_text = "\n".join(results)
            
            # Split into multiple embeds if too long
            if len(results_text) > 4000:
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in results:
                    if current_length + len(line) > 3900:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_length = len(line)
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                
                # Send first chunk as response
                embed = discord.Embed(
                    title="🔄 Fresh Invite Generation Results (1/1)" if len(chunks) == 1 else f"🔄 Fresh Invite Generation Results (1/{len(chunks)})",
                    description=chunks[0],
                    color=discord.Color.gold()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Send additional chunks
                for i, chunk in enumerate(chunks[1:], 2):
                    embed = discord.Embed(
                        title=f"🔄 Fresh Invite Generation Results ({i}/{len(chunks)})",
                        description=chunk,
                        color=discord.Color.gold()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="🔄 Fresh Invite Generation Results",
                    description=results_text,
                    color=discord.Color.gold()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Send a summary card with working links for easy testing
            if successful_invites:
                test_embed = discord.Embed(
                    title="🧪 Quick Link Test Card",
                    description="Click these links to verify they work:",
                    color=discord.Color.blue()
                )
                
                for invite_data in successful_invites[:10]:  # Limit to first 10 to avoid embed limits
                    test_embed.add_field(
                        name=invite_data['username'],
                        value=f"[Test Link](https://discord.gg/{invite_data['invite_code']})",
                        inline=True
                    )
                
                if len(successful_invites) > 10:
                    test_embed.add_field(
                        name="...",
                        value=f"And {len(successful_invites) - 10} more",
                        inline=True
                    )
                
                await interaction.followup.send(embed=test_embed, ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Invite regeneration failed: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="test_invite_flow", description="[ADMIN] Test the complete VIP upgrade invite tracking flow")
    async def test_invite_flow(self, interaction: discord.Interaction):
        """Test the complete VIP upgrade invite tracking flow"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            test_results = []
            
            # 1. Check VIP upgrade channel setup
            test_results.append("🧪 **VIP UPGRADE FLOW TEST**\n")
            
            vip_channel = self.bot.get_channel(self.VIP_UPGRADE_CHANNEL_ID)
            if vip_channel:
                test_results.append(f"✅ VIP Channel: {vip_channel.mention}")
            else:
                test_results.append(f"❌ VIP Channel not found (ID: {self.VIP_UPGRADE_CHANNEL_ID})")
            
            # 2. Check staff invite codes
            test_results.append(f"\n🔗 **STAFF INVITE STATUS:**")
            staff_configs = self.bot.db.get_all_staff_configs()
            active_invites = 0
            
            for config in staff_configs:
                staff_id = config['staff_id']
                invite_code = config.get('invite_code')
                
                try:
                    user = self.bot.get_user(staff_id)
                    username = user.display_name if user else f"User {staff_id}"
                    
                    if invite_code:
                        try:
                            # Test if invite is valid
                            fetched_invite = await self.bot.fetch_invite(invite_code)
                            uses = fetched_invite.uses or 0
                            test_results.append(f"  ✅ {username}: `{invite_code}` ({uses} uses)")
                            active_invites += 1
                        except discord.NotFound:
                            test_results.append(f"  ❌ {username}: `{invite_code}` (INVALID)")
                        except Exception as e:
                            test_results.append(f"  ⚠️ {username}: `{invite_code}` (Error: {str(e)})")
                    else:
                        test_results.append(f"  ❌ {username}: No invite code assigned")
                        
                except Exception as e:
                    test_results.append(f"  ❌ User {staff_id}: Error: {str(e)}")
            
            # 3. Test invite tracking system
            test_results.append(f"\n📊 **INVITE TRACKING SYSTEM:**")
            test_results.append(f"  • Active staff invites: {active_invites}/{len(staff_configs)}")
            
            # Check if invite tracker cog is loaded
            invite_tracker = self.bot.get_cog('InviteTracker')
            if invite_tracker:
                test_results.append(f"  ✅ Invite Tracker cog loaded")
            else:
                test_results.append(f"  ❌ Invite Tracker cog not found")
            
            # 4. Check VIP role configuration
            test_results.append(f"\n👑 **VIP ROLE CONFIGURATION:**")
            if self.VIP_ROLE_ID:
                vip_role = interaction.guild.get_role(int(self.VIP_ROLE_ID))
                if vip_role:
                    test_results.append(f"  ✅ VIP Role: {vip_role.mention} ({len(vip_role.members)} members)")
                else:
                    test_results.append(f"  ❌ VIP Role not found (ID: {self.VIP_ROLE_ID})")
            else:
                test_results.append(f"  ❌ VIP_ROLE_ID not configured")
            
            # 5. Test database functionality
            test_results.append(f"\n💾 **DATABASE FUNCTIONALITY:**")
            try:
                # Test basic database operations
                test_configs = self.bot.db.get_all_staff_configs()
                test_results.append(f"  ✅ Database connection working ({len(test_configs)} staff configs)")
                
                # Test invite tracking methods
                try:
                    staff_status = self.bot.db.get_staff_invite_status()
                    test_results.append(f"  ✅ Invite status method working")
                except Exception as e:
                    test_results.append(f"  ⚠️ Invite status method: {str(e)}")
                    
            except Exception as e:
                test_results.append(f"  ❌ Database error: {str(e)}")
            
            # 6. Test member join simulation
            test_results.append(f"\n🎯 **MEMBER JOIN SIMULATION:**")
            test_results.append(f"  📝 To test invite tracking:")
            test_results.append(f"     1. Use one of the staff invite links")
            test_results.append(f"     2. Join with an alt account")
            test_results.append(f"     3. Check if the join is tracked with `/list_staff_invites`")
            test_results.append(f"     4. Verify VIP upgrade button appears")
            
            # 7. Summary and recommendations
            test_results.append(f"\n✅ **TEST SUMMARY:**")
            issues_found = []
            
            if not vip_channel:
                issues_found.append("VIP channel not found")
            if active_invites < len(staff_configs):
                issues_found.append(f"Only {active_invites}/{len(staff_configs)} staff have working invites")
            if not invite_tracker:
                issues_found.append("Invite tracker cog not loaded")
            if not self.VIP_ROLE_ID or not interaction.guild.get_role(int(self.VIP_ROLE_ID)):
                issues_found.append("VIP role not configured properly")
            
            if issues_found:
                test_results.append(f"  ⚠️ Issues found: {len(issues_found)}")
                for issue in issues_found:
                    test_results.append(f"     • {issue}")
                test_results.append(f"\n  🔧 Run `/regenerate_all_invites` to fix invite issues")
            else:
                test_results.append(f"  🎉 All systems appear to be working correctly!")
                test_results.append(f"  🧪 Ready for live testing with invite links")
            
            # Send results
            results_text = "\n".join(test_results)
            
            # Split into multiple embeds if too long
            if len(results_text) > 4000:
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in test_results:
                    if current_length + len(line) > 3900:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_length = len(line)
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                
                # Send first chunk as response
                embed = discord.Embed(
                    title="🧪 VIP Upgrade Flow Test (1/1)" if len(chunks) == 1 else f"🧪 VIP Upgrade Flow Test (1/{len(chunks)})",
                    description=chunks[0],
                    color=discord.Color.purple()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Send additional chunks
                for i, chunk in enumerate(chunks[1:], 2):
                    embed = discord.Embed(
                        title=f"🧪 VIP Upgrade Flow Test ({i}/{len(chunks)})",
                        description=chunk,
                        color=discord.Color.purple()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="🧪 VIP Upgrade Flow Test Results",
                    description=results_text,
                    color=discord.Color.purple()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Test failed: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="cleanup_unauthorized_invites", description="[ADMIN] Remove invites not created by staff")
    async def cleanup_unauthorized_invites(self, interaction: discord.Interaction):
        """Clean up invites that weren't created by authorized staff"""
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
                return
            all_invites = await guild.invites()
            
            # Get authorized staff invite codes from database (only bot-generated staff invites)
            # Get authorized invite codes from staff configs
            staff_configs = self.bot.db.get_all_staff_configs()
            authorized_invite_codes = [(config['staff_id'], config.get('invite_code')) for config in staff_configs if config.get('invite_code')]
            
            # Find unauthorized invites (everything except bot-generated staff invites)
            unauthorized_invites = []
            staff_invites = []
            
            for invite in all_invites:
                if invite.code in authorized_invite_codes and invite.inviter and invite.inviter.id == self.bot.user.id:
                    # This is a bot-generated staff invite - keep it
                    staff_invites.append(invite)
                else:
                    # This is unauthorized - remove it (including admin-created invites)
                    unauthorized_invites.append(invite)
            
            # Show confirmation embed
            embed = discord.Embed(
                title="🧹 Invite Cleanup Analysis",
                description="Analysis of current server invites",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="✅ Bot-Generated Staff Invites (Will Keep)",
                value=f"{len(staff_invites)} official staff invites found",
                inline=True
            )
            
            embed.add_field(
                name="❌ All Other Invites (Will Remove)",
                value=f"{len(unauthorized_invites)} non-staff invites found\n*(Including admin-created invites)*",
                inline=True
            )
            
            if unauthorized_invites:
                unauthorized_list = []
                for invite in unauthorized_invites[:5]:  # Show first 5
                    unauthorized_list.append(f"• `{invite.code}` by {invite.inviter.name}")
                
                if len(unauthorized_invites) > 5:
                    unauthorized_list.append(f"• ...and {len(unauthorized_invites) - 5} more")
                
                embed.add_field(
                    name="📋 Invites to Remove (All Non-Staff)",
                    value="\n".join(unauthorized_list),
                    inline=False
                )
                
                # Add confirmation buttons
                view = InviteCleanupConfirmView(unauthorized_invites)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                embed.add_field(
                    name="🎉 All Clean!",
                    value="No unauthorized invites found. All invites are official bot-generated staff invites.",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error analyzing invites: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class InviteCleanupConfirmView(discord.ui.View):
    """Confirmation view for invite cleanup"""
    
    def __init__(self, unauthorized_invites):
        super().__init__(timeout=300)  # 5 minute timeout
        self.unauthorized_invites = unauthorized_invites
    
    async def on_timeout(self):
        """Handle view timeout"""
        for item in self.children:
            try:
                item.disabled = True
            except AttributeError:
                pass
    
    @discord.ui.button(label="🗑️ Remove All Non-Staff Invites", style=discord.ButtonStyle.danger)
    async def confirm_cleanup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and execute invite cleanup"""
        try:
            # Acknowledge the interaction immediately
            await interaction.response.defer(ephemeral=True)
            
            removed_count = 0
            errors = []
            
            for invite in self.unauthorized_invites:
                try:
                    await invite.delete(reason="Unauthorized invite cleanup by admin")
                    removed_count += 1
                except Exception as e:
                    errors.append(f"Failed to remove {invite.code}: {str(e)}")
            
            embed = discord.Embed(
                title="✅ Invite Cleanup Complete",
                description=f"Successfully removed {removed_count} non-staff invites\n\n**Only bot-generated staff invites remain**",
                color=discord.Color.green()
            )
            
            if errors:
                embed.add_field(
                    name="⚠️ Errors",
                    value="\n".join(errors[:5]),  # Show first 5 errors
                    inline=False
                )
            
            # Disable the view
            for item in self.children:
                try:
                    item.disabled = True
                except AttributeError:
                    pass
            
            # Use followup instead of response since we already deferred
            if interaction.message:
                await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            try:
                await interaction.followup.send(f"❌ Error during cleanup: {str(e)}", ephemeral=True)
            except Exception as followup_error:
                logger.error(f"Failed to send followup error message: {followup_error}")
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_cleanup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the cleanup"""
        try:
            embed = discord.Embed(
                title="❌ Cleanup Cancelled",
                description="No invites were removed.",
                color=discord.Color.red()
            )
            
            # Disable the view
            for item in self.children:
                try:
                    item.disabled = True
                except AttributeError:
                    pass
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error cancelling cleanup: {e}")
            try:
                await interaction.response.send_message("❌ Cleanup cancelled", ephemeral=True)
            except:
                pass

async def setup(bot):
    await bot.add_cog(VIPUpgrade(bot))