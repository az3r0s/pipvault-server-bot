"""
Invite Sync System
=================

Provides enhanced invite synchronization functionality by tracking who joined through each invite link.
Works alongside the invite_tracker cog to ensure accurate attribution of joins to staff invites.
"""

from typing import Dict, List, Optional, Set, Tuple, Union, cast
import discord
from discord.ext import commands, tasks
from discord import app_commands, Invite, AuditLogEntry, AuditLogAction, Member, Guild
import logging
import asyncio
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.cloud_database import CloudAPIServerDatabase

logger = logging.getLogger(__name__)

class InviteSyncExtension:
    """Helper class to add invite syncing functionality to the InviteTracker cog"""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.member_join_history: Dict[int, Dict[str, List[discord.Member]]] = {}
        # {guild_id: {invite_code: [member1, member2, ...]}}

    async def sync_invite_joins(self, cog, guild: discord.Guild) -> Tuple[int, List[str]]:
        """
        Syncs invite usage data with Discord and updates the database
        Returns (number of updates made, list of sync messages)
        """
        sync_messages = []
        updates = 0
        
        try:
            if not guild:
                return 0, ["Guild not found"]
                
            # Get current invites
            try:
                guild_invites = await guild.invites()
            except discord.Forbidden:
                return 0, ["Missing invite permissions"]
            except Exception as e:
                return 0, [f"Error fetching invites: {e}"]
                
            # Track current invite usage
            invite_usage = {
                invite.code: invite.uses
                for invite in guild_invites
            }
            
            # Compare with our cached usage to find used invites
            cached_usage = cog.invite_cache.get(guild.id, {})
            used_invites = []
            
            for code, uses in invite_usage.items():
                old_uses = cached_usage.get(code, 0)
                if uses > old_uses:
                    # This invite was used
                    for invite in guild_invites:
                        if invite.code == code:
                            used_invites.append((invite, uses - old_uses))
                            break
                            
            # Update cache
            cog.invite_cache[guild.id] = invite_usage
            
            # Process each used invite
            for invite, use_count in used_invites:
                if not invite.inviter:
                    continue
                    
                # Get staff record for this invite
                staff_data = cog.db.get_staff_invite_status()
                if not staff_data:
                    continue
                    
                # Find which staff member owns this invite
                owner_id = None
                for staff_id, info in staff_data.items():
                    if info.get('invite_code') == invite.code:
                        owner_id = staff_id
                        break
                
                if not owner_id:
                    continue
                    
                # Get new members who used this invite
                try:
                    recent_members = []
                    # Get member join events from audit log
                    async for entry in guild.audit_logs(limit=use_count, action=AuditLogAction.member_join):
                        if isinstance(entry.target, discord.Member):
                            recent_members.append(entry.target)
                            
                    # Record joins in database
                    for member in recent_members:
                        cog.db.track_user_invite(
                            user_id=member.id,
                            username=str(member),
                            invite_code=invite.code,
                            inviter_id=owner_id,
                            inviter_username=str(invite.inviter),
                            uses_before=cached_usage.get(invite.code, 0),
                            uses_after=invite_usage[invite.code]
                        )
                        updates += 1
                        sync_messages.append(
                            f"Tracked {member.name} joining via {invite.inviter.name}'s invite"
                        )
                        
                except discord.Forbidden:
                    sync_messages.append("Missing audit log permissions")
                except Exception as e:
                    sync_messages.append(f"Error processing audit logs: {e}")
                    
            # Update cache one final time
            cog.invite_cache[guild.id] = invite_usage
            logger.info(f"✅ Synced {updates} invite joins for {guild.name}")
            
        except Exception as e:
            logger.error(f"❌ Error syncing invite joins: {e}")
            sync_messages.append(f"Error during sync: {str(e)}")
        
        return updates, sync_messages
                
                if joined_members:
                    # Store in history
                    if guild.id not in self.member_join_history:
                        self.member_join_history[guild.id] = {}
                    self.member_join_history[guild.id][invite.code] = joined_members
                    
                    # Update database records
                    staff_config = await self.bot.db.get_staff_config_by_invite(invite.code)
                    if staff_config:
                        staff_id = staff_config.get('staff_id')
                        if staff_id:
                            for member in joined_members:
                                # Only update if not already tracked
                                existing = await self.bot.db.get_user_invite(member.id)
                                if not existing or existing.get('invite_code') != invite.code:
                                    await self.bot.db.record_user_join(
                                        user_id=member.id,
                                        username=str(member),
                                        invite_code=invite.code,
                                        inviter_id=staff_id,
                                        inviter_username=staff_config.get('staff_username', 'Unknown'),
                                        uses_before=invite.uses - 1,
                                        uses_after=invite.uses
                                    )
                                    updates += 1
                                    sync_messages.append(
                                        f"Synced member {member.name} (joined via {invite.code})"
                                    )

            logger.info(f"✅ Synced {updates} invite joins for {guild.name}")
            
        except Exception as e:
            logger.error(f"❌ Error syncing invite joins: {e}")
            sync_messages.append(f"Error during sync: {str(e)}")
        
        return updates, sync_messages

    async def get_invite_member_list(self, guild: discord.Guild, invite_code: str) -> List[discord.Member]:
        """Get list of members who joined through a specific invite"""
        if guild.id in self.member_join_history:
            return self.member_join_history[guild.id].get(invite_code, [])
        return []

    async def clear_sync_history(self, guild: discord.Guild):
        """Clear cached join history for a guild"""
        if guild.id in self.member_join_history:
            self.member_join_history.pop(guild.id)
            logger.info(f"🧹 Cleared join history for {guild.name}")

class InviteSync(commands.Cog):
    """
    Enhanced invite tracking functionality
    Adds commands to manage invite synchronization with Discord
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.sync_extension = InviteSyncExtension(self)
        self._last_sync: Dict[int, datetime] = {}  # guild_id: last_sync_time
        self.db = CloudAPIServerDatabase()
        
        # Start background sync task
        self.background_sync.start()
    
    def cog_unload(self):
        self.background_sync.cancel()
        
    @app_commands.command(
        name="invites",
        description="View your invite statistics and member joins"
    )
    async def view_invites(self, interaction: discord.Interaction):
        """View invite statistics for the current user"""
        await interaction.response.defer()
        
        try:
            if not interaction.guild:
                await interaction.followup.send(
                    "❌ This command must be used in a server",
                    ephemeral=True
                )
                return
                
            # Get invite stats for this user
            referrals = self.db.get_staff_referrals(interaction.user.id)
            
            if not referrals:
                await interaction.followup.send(
                    "❌ No invite data found. Either you're not registered as staff or no one has used your invite link yet.",
                    ephemeral=True
                )
                return
                
            # Create stats embed
            embed = discord.Embed(
                title="📊 Your Invite Statistics",
                color=discord.Color.blue()
            )
            
            # Basic stats
            total_joins = len(referrals)
            last_join = datetime.fromisoformat(referrals[0]['joined_at']) if referrals else None
            
            embed.add_field(
                name="Total Joins",
                value=f"👥 {total_joins} member{'s' if total_joins != 1 else ''}",
                inline=True
            )
            
            if last_join:
                embed.add_field(
                    name="Last Join",
                    value=f"🕒 {discord.utils.format_dt(last_join, 'R')}",
                    inline=True
                )
            
            # Recent joins
            if referrals:
                recent = referrals[:5]  # Show 5 most recent
                joins_list = []
                for ref in recent:
                    join_time = datetime.fromisoformat(ref['joined_at'])
                    joins_list.append(
                        f"• {ref['username']} - {discord.utils.format_dt(join_time, 'R')}"
                    )
                    
                embed.add_field(
                    name="Recent Joins",
                    value="\n".join(joins_list) if joins_list else "None yet",
                    inline=False
                )
                
            # Add invite link info if we have permission
            staff_info = self.db.get_staff_invite_status().get(interaction.user.id)
            if staff_info and staff_info.get('invite_code'):
                guild = interaction.guild
                try:
                    if guild.me.guild_permissions.manage_guild:
                        invites = await guild.invites()
                        for invite in invites:
                            if invite.code == staff_info['invite_code']:
                                embed.add_field(
                                    name="Your Invite Link",
                                    value=f"🔗 {invite.url}\n`/create_staff_invite` to create a new one",
                                    inline=False
                                )
                                break
                except discord.Forbidden:
                    embed.add_field(
                        name="Note",
                        value="⚠️ Missing permissions to view invite links",
                        inline=False
                    )
                except Exception as e:
                    logger.error(f"Error getting invite links: {e}")
                    
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error showing invite stats: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching your invite statistics.",
                ephemeral=True
            )
            
    @app_commands.command(
        name="leaderboard",
        description="View the staff invite leaderboard"
    )
    @app_commands.describe(
        timeframe="Time period to show stats for",
        private="Whether to show the response privately"
    )
    @app_commands.choices(timeframe=[
        app_commands.Choice(name="All Time", value="all"),
        app_commands.Choice(name="This Month", value="month"),
        app_commands.Choice(name="This Week", value="week")
    ])
    async def invite_leaderboard(
        self,
        interaction: discord.Interaction,
        timeframe: str = "all",
        private: bool = False
    ):
        """Show the staff invite leaderboard"""
        await interaction.response.defer(ephemeral=private)
        
        try:
            # Get all staff stats
            staff_data = self.db.get_staff_invite_status()
            
            if not staff_data:
                await interaction.followup.send(
                    "❌ No staff invite data found.",
                    ephemeral=True
                )
                return
                
            # Calculate stats for each staff member
            leaderboard = []
            for staff_id, info in staff_data.items():
                referrals = self.db.get_staff_referrals(staff_id)
                
                # Filter by timeframe
                now = datetime.now()
                filtered_refs = []
                for ref in referrals:
                    join_time = datetime.fromisoformat(ref['joined_at'])
                    
                    if timeframe == "month":
                        if join_time.year == now.year and join_time.month == now.month:
                            filtered_refs.append(ref)
                    elif timeframe == "week":
                        # Simple week check - within last 7 days
                        if (now - join_time).days <= 7:
                            filtered_refs.append(ref)
                    else:  # "all"
                        filtered_refs.append(ref)
                        
                if filtered_refs:
                    member = interaction.guild.get_member(staff_id)
                    name = member.display_name if member else info['staff_username']
                    leaderboard.append((name, len(filtered_refs)))
                    
            # Sort by invite count
            leaderboard.sort(key=lambda x: x[1], reverse=True)
            
            # Create embed
            embed = discord.Embed(
                title="🏆 Staff Invite Leaderboard",
                description=f"Top inviters - {timeframe.title()} Time",
                color=discord.Color.gold()
            )
            
            # Format leaderboard
            if leaderboard:
                medals = {0: "🥇", 1: "🥈", 2: "🥉"}
                board_text = []
                for i, (name, count) in enumerate(leaderboard[:10]):  # Top 10
                    medal = medals.get(i, "•")
                    board_text.append(
                        f"{medal} **{name}**: {count} member{'s' if count != 1 else ''}"
                    )
                    
                embed.add_field(
                    name="Rankings",
                    value="\n".join(board_text),
                    inline=False
                )
            else:
                embed.add_field(
                    name="No Data",
                    value="No invite activity found for this time period.",
                    inline=False
                )
                
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error showing leaderboard: {e}")
            await interaction.followup.send(
                "❌ An error occurred while generating the leaderboard.",
                ephemeral=True
            )
    
    @tasks.loop(hours=1)
    async def background_sync(self):
        """Periodically sync invite data with Discord"""
        for guild in self.bot.guilds:
            try:
                # Only sync if it's been more than 6 hours
                last_sync = self._last_sync.get(guild.id)
                if not last_sync or (datetime.now() - last_sync) > timedelta(hours=6):
                    updates, _ = await self.sync_extension.sync_invite_joins(self, guild)
                    if updates > 0:
                        logger.info(f"🔄 Background sync updated {updates} records for {guild.name}")
                    self._last_sync[guild.id] = datetime.now()
            except Exception as e:
                logger.error(f"❌ Error in background sync for {guild.name}: {e}")
    
    @commands.hybrid_command(name="sync_invites")
    @commands.has_permissions(manage_guild=True)
    async def sync_invites(self, ctx):
        """Manually trigger invite data synchronization with Discord"""
        try:
            if not ctx.guild:
                await ctx.send("❌ This command must be used in a server")
                return
                
            async with ctx.typing():
                updates, messages = await self.sync_extension.sync_invite_joins(self, ctx.guild)
                
                embed = discord.Embed(
                    title="🔄 Invite Sync Results",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                if updates > 0:
                    embed.description = f"✅ Successfully synced {updates} invite records"
                    if messages:
                        embed.add_field(
                            name="📝 Sync Details",
                            value="\n".join(f"• {msg}" for msg in messages[:10]),
                            inline=False
                        )
                        if len(messages) > 10:
                            embed.add_field(
                                name="",
                                value=f"...and {len(messages) - 10} more updates",
                                inline=False
                            )
                else:
                    embed.description = "✅ No updates needed - invite data already in sync"
                
                self._last_sync[ctx.guild.id] = datetime.now()
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"❌ Error in sync_invites: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="list_invite_joins")
    @commands.has_permissions(manage_guild=True)
    async def list_invite_joins(self, ctx, invite_code: str):
        """List all members who joined through a specific invite code"""
        try:
            if not ctx.guild:
                await ctx.send("❌ This command must be used in a server")
                return
                
            members = await self.sync_extension.get_invite_member_list(ctx.guild, invite_code)
            
            embed = discord.Embed(
                title=f"👥 Members Joined via {invite_code}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if members:
                # Group members by join date
                by_month = {}
                for member in members:
                    if not isinstance(member, discord.Member):
                        continue
                    month = member.joined_at.strftime('%B %Y') if member.joined_at else 'Unknown'
                    if month not in by_month:
                        by_month[month] = []
                    by_month[month].append(member)
                
                # Add fields for each month
                for month, month_members in sorted(by_month.items()):
                    embed.add_field(
                        name=f"📅 {month}",
                        value="\n".join(f"• {m.name}" for m in month_members),
                        inline=False
                    )
                
                embed.description = f"Found {len(members)} members"
            else:
                embed.description = "No members found who joined using this invite"
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error in list_invite_joins: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="clear_invite_sync")
    @commands.has_permissions(administrator=True)
    async def clear_invite_sync(self, ctx):
        """Clear cached invite sync data and force a fresh sync"""
        try:
            if not ctx.guild:
                await ctx.send("❌ This command must be used in a server")
                return
                
            await self.sync_extension.clear_sync_history(ctx.guild)
            updates, _ = await self.sync_extension.sync_invite_joins(self, ctx.guild)
            
            embed = discord.Embed(
                title="🧹 Invite Sync Cache Cleared",
                description=f"Cache cleared and resynced {updates} records",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error in clear_invite_sync: {e}")
            await ctx.send(f"❌ Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(InviteSync(bot))