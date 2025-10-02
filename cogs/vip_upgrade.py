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

from server_bot.views.vip_upgrade import VIPUpgradeView

logger = logging.getLogger(__name__)

class VIPUpgrade(commands.Cog):
    """VIP upgrade system with invite tracking and staff attribution"""
    
    def __init__(self, bot):
        self.bot = bot
        self.VIP_UPGRADE_CHANNEL_ID = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '0'))
        self.VIP_ROLE_ID = os.getenv('VIP_ROLE_ID', '0')
        self.STAFF_NOTIFICATION_CHANNEL_ID = int(os.getenv('STAFF_NOTIFICATION_CHANNEL_ID', '0'))
        
        # Add persistent views
        self.bot.add_view(VIPUpgradeView())
    
    async def cog_load(self):
        """Called when cog is loaded"""
        logger.info("👑 VIP Upgrade system loaded")
    
    async def setup_sticky_embed(self, channel):
        """Set up the sticky embed in VIP upgrade channel"""
        try:
            # Clear old messages (optional - remove if you want to keep history)
            # await channel.purge(limit=10)
            
            # Create the main VIP upgrade embed
            embed = discord.Embed(
                title="👑 VIP Upgrade Center",
                description=(
                    "Welcome to the VIP upgrade system! Upgrade your account to unlock "
                    "premium trading signals, exclusive analysis, and VIP-only benefits."
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
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
            
            # Create permanent invite (ensure we're in a guild channel)
            if not interaction.guild or not isinstance(interaction.channel, (discord.TextChannel, discord.VoiceChannel)):
                await interaction.response.send_message("❌ This command must be run in a server text channel", ephemeral=True)
                return
                
            invite = await interaction.channel.create_invite(
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
                    name="🔗 Invite Link", 
                    value=f"[{invite.url}]({invite.url})\nCode: `{invite.code}`", 
                    inline=False
                )
                embed.add_field(
                    name="🏪 Vantage Referral", 
                    value=f"[Link]({staff_config['vantage_referral_link']})", 
                    inline=True
                )
                embed.add_field(
                    name="� IB Code", 
                    value=f"`{staff_config['vantage_ib_code']}`", 
                    inline=True
                )
                
                embed.set_footer(text="This invite link is permanent and will track all users who join through it")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
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
                    
                except discord.Forbidden:
                    logger.warning(f"Couldn't send invite DM to {staff_member.name}")
            
            else:
                await interaction.response.send_message("❌ Failed to save staff invite configuration", ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error creating staff invite: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
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

async def setup(bot):
    await bot.add_cog(VIPUpgrade(bot))