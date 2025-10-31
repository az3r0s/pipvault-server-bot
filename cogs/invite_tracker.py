"""
Invite Tracking Cog
===================

Tracks which invite link each user joined through for proper staff attribution
in the VIP upgrade system.
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class InviteTracker(commands.Cog):
    """Tracks Discord invite usage for staff attribution"""
    
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}  # Cache of current invites {code: uses}
    
    async def cog_load(self):
        """Called when cog is loaded"""
        logger.info("🔗 Invite Tracker loaded")
        
        # Cache current invites for all guilds
        for guild in self.bot.guilds:
            try:
                await self.cache_guild_invites(guild)
                logger.info(f"✅ Cached invites for guild: {guild.name}")
            except Exception as e:
                logger.error(f"❌ Failed to cache invites for {guild.name}: {e}")
    
    async def cache_guild_invites(self, guild):
        """Cache current invite uses for a guild"""
        try:
            # Check if bot has permission to manage guild/view invites
            if not guild.me.guild_permissions.manage_guild:
                logger.warning(f"⚠️ Bot lacks 'Manage Server' permission in {guild.name} - invite tracking limited")
                return
            
            invites = await guild.invites()
            
            # Initialize cache for this guild if it doesn't exist
            if guild.id not in self.invite_cache:
                self.invite_cache[guild.id] = {}
            else:
                # Clear existing cache
                self.invite_cache[guild.id].clear()
            
            # Cache all invites
            for invite in invites:
                self.invite_cache[guild.id][invite.code] = {
                    'uses': invite.uses,
                    'inviter': invite.inviter,
                    'code': invite.code
                }
            
            logger.info(f"📊 Cached {len(invites)} invites for {guild.name}")
            
        except discord.Forbidden:
            logger.error(f"❌ Bot lacks permission to view invites for {guild.name}")
        except Exception as e:
            logger.error(f"❌ Error caching invites for {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Track which invite was used when a member joins"""
        try:
            guild = member.guild
            
            # Get current invites
            current_invites = await guild.invites()
            used_invite = None
            
            # Compare with cached invites to find which one was used
            if guild.id in self.invite_cache:
                for invite in current_invites:
                    cached_invite = self.invite_cache[guild.id].get(invite.code)
                    
                    if cached_invite and invite.uses > cached_invite['uses']:
                        # This invite was used
                        used_invite = {
                            'code': invite.code,
                            'inviter': invite.inviter,
                            'uses_before': cached_invite['uses'],
                            'uses_after': invite.uses
                        }
                        break
            
            # Record the join in database
            if used_invite:
                success = self.bot.db.record_user_join(
                    user_id=member.id,
                    username=f"{member.name}#{member.discriminator}",
                    invite_code=used_invite['code'],
                    inviter_id=used_invite['inviter'].id if used_invite['inviter'] else 0,
                    inviter_username=f"{used_invite['inviter'].name}#{used_invite['inviter'].discriminator}" if used_invite['inviter'] else "Unknown",
                    uses_before=used_invite['uses_before'],
                    uses_after=used_invite['uses_after']
                )
                
                if success:
                    # CRITICAL: Immediately backup to cloud for deployment persistence
                    try:
                        await self.bot.db.backup_to_cloud()
                        logger.info(f"☁️ Join data backed up to cloud API for user {member.name}")
                    except Exception as backup_error:
                        logger.error(f"❌ Failed to backup join data to cloud: {backup_error}")
                    
                    logger.info(f"👥 {member.name} joined via invite {used_invite['code']} by {used_invite['inviter'].name if used_invite['inviter'] else 'Unknown'}")
                    
                    # Send notification to staff member (optional)
                    if used_invite['inviter']:
                        try:
                            embed = discord.Embed(
                                title="🎉 New Member from Your Invite!",
                                description=f"**{member.mention}** just joined using your invite link!",
                                color=discord.Color.green(),
                                timestamp=datetime.now()
                            )
                            embed.add_field(
                                name="📊 Invite Stats",
                                value=f"Code: `{used_invite['code']}`\nTotal Uses: {used_invite['uses_after']}",
                                inline=False
                            )
                            embed.set_thumbnail(url=member.display_avatar.url)
                            
                            await used_invite['inviter'].send(embed=embed)
                        except:
                            pass  # Don't fail if we can't DM the inviter
            else:
                # Couldn't determine invite used
                logger.warning(f"⚠️ Couldn't determine invite used by {member.name}")
                
                # Record with unknown invite
                self.bot.db.record_user_join(
                    user_id=member.id,
                    username=f"{member.name}#{member.discriminator}",
                    invite_code="unknown",
                    inviter_id=0,
                    inviter_username="Unknown",
                    uses_before=0,
                    uses_after=0
                )
            
            # Update invite cache
            await self.cache_guild_invites(guild)
            
        except Exception as e:
            logger.error(f"❌ Error tracking member join: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Clean up invite tracking data when a member leaves"""
        try:
            # Remove the user from invite tracking
            success = self.bot.db.remove_user_invite_tracking(member.id)
            
            if success:
                # Immediately backup to cloud for persistence
                try:
                    await self.bot.db.backup_to_cloud()
                    logger.info(f"☁️ Leave data backed up to cloud API for user {member.name}")
                except Exception as backup_error:
                    logger.error(f"❌ Failed to backup leave data to cloud: {backup_error}")
                
                logger.info(f"🚪 Removed invite tracking for {member.name} ({member.id}) who left the server")
            else:
                logger.warning(f"⚠️ No invite tracking found for {member.name} ({member.id}) who left")
                
        except Exception as e:
            logger.error(f"❌ Error handling member leave: {e}")
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Update cache when new invite is created"""
        try:
            guild = invite.guild
            if guild.id not in self.invite_cache:
                self.invite_cache[guild.id] = {}
            
            self.invite_cache[guild.id][invite.code] = {
                'uses': invite.uses,
                'inviter': invite.inviter,
                'code': invite.code
            }
            
            logger.info(f"🔗 New invite created: {invite.code} by {invite.inviter.name}")
            
        except Exception as e:
            logger.error(f"❌ Error caching new invite: {e}")
    
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Update cache when invite is deleted"""
        try:
            guild = invite.guild
            if guild.id in self.invite_cache and invite.code in self.invite_cache[guild.id]:
                del self.invite_cache[guild.id][invite.code]
                logger.info(f"🗑️ Invite deleted: {invite.code}")
                
        except Exception as e:
            logger.error(f"❌ Error removing deleted invite: {e}")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Track when members get VIP role and update their referral status"""
        try:
            # Check if VIP role was added
            VIP_ROLE_ID = int(self.bot.get_env_var('VIP_ROLE_ID', '1401614579850543206'))
            
            before_vip = any(role.id == VIP_ROLE_ID for role in before.roles)
            after_vip = any(role.id == VIP_ROLE_ID for role in after.roles)
            
            # If user just got VIP role
            if not before_vip and after_vip:
                logger.info(f"🎉 {after.name} just became VIP! Checking for referral update...")
                
                # Get their invite info from database
                invite_info = self.bot.db.get_user_invite_info(after.id)
                
                if invite_info and invite_info.get('invite_code') != 'unknown':
                    # Get staff config for their invite
                    staff_config = self.bot.db.get_staff_config_by_invite(invite_info['invite_code'])
                    
                    if staff_config:
                        # Create VIP request to track this upgrade
                        request_id = self.bot.db.create_vip_request(
                            user_id=after.id,
                            username=f"{after.name}#{after.discriminator}",
                            request_type="role_promotion",
                            staff_id=staff_config['discord_id'],
                            request_data=f"User promoted to VIP by role assignment. Original invite: {invite_info['invite_code']}"
                        )
                        
                        if request_id:
                            # Mark as completed immediately
                            self.bot.db.update_vip_request_status(request_id, 'completed')
                            
                            # Backup to cloud
                            try:
                                await self.bot.db.backup_to_cloud()
                                logger.info(f"☁️ VIP promotion data backed up to cloud API for user {after.name}")
                            except Exception as backup_error:
                                logger.error(f"❌ Failed to backup VIP promotion data: {backup_error}")
                            
                            logger.info(f"✅ Updated VIP status for {after.name} - credited to staff {staff_config['username']}")
                        else:
                            logger.error(f"❌ Failed to create VIP request for {after.name}")
                    else:
                        logger.warning(f"⚠️ No staff config found for invite {invite_info['invite_code']} when {after.name} became VIP")
                else:
                    logger.warning(f"⚠️ No invite info found for {after.name} when they became VIP")
                    
        except Exception as e:
            logger.error(f"❌ Error handling member update for VIP role: {e}")
    
    @commands.hybrid_command(name="setup_staff_invite")
    @commands.has_permissions(administrator=True)
    async def setup_staff_invite(self, ctx, staff_member: discord.Member, invite_code: str, 
                                vantage_link: str, *, email_template: str):
        """
        Set up staff invite configuration for VIP attribution
        
        Parameters:
        - staff_member: The staff member
        - invite_code: Their Discord invite code
        - vantage_link: Their Vantage referral link
        - email_template: Email template with placeholders
        """
        try:
            success = self.bot.db.add_staff_invite_config(
                staff_id=staff_member.id,
                staff_username=f"{staff_member.name}#{staff_member.discriminator}",
                invite_code=invite_code,
                vantage_referral_link=vantage_link,
                email_template=email_template
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Staff Invite Configuration Updated",
                    description=f"Set up invite tracking for {staff_member.mention}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Invite Code", value=f"`{invite_code}`", inline=True)
                embed.add_field(name="Vantage Link", value=f"[Link]({vantage_link})", inline=True)
                embed.add_field(name="Email Template", value=f"```{email_template[:100]}...```", inline=False)
                
                await ctx.send(embed=embed)
                logger.info(f"✅ Staff invite config updated for {staff_member.name}")
            else:
                await ctx.send("❌ Failed to update staff invite configuration")
                
        except Exception as e:
            logger.error(f"❌ Error setting up staff invite: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    

    

    
    @commands.hybrid_command(name="debug_invites")
    @commands.has_permissions(manage_guild=True)
    async def debug_invites(self, ctx):
        """Debug current invite cache and live invite data"""
        try:
            guild = ctx.guild
            
            # Force refresh cache if it doesn't exist
            if guild.id not in self.invite_cache:
                await self.cache_guild_invites(guild)
            
            # Get current live invites
            current_invites = await guild.invites()
            
            embed = discord.Embed(
                title="🔍 Invite Debug Information",
                description=f"Debugging invite tracking for {guild.name}",
                color=discord.Color.blue()
            )
            
            # Show cache status
            cache_info = ""
            if guild.id in self.invite_cache:
                cache_count = len(self.invite_cache[guild.id])
                cache_info = f"✅ Cache exists with {cache_count} invites"
                
                # If cache was just created, mention it
                if cache_count > 0:
                    cache_info += "\n🔄 Cache refreshed during debug"
            else:
                cache_info = "❌ Failed to create cache for this guild"
            
            embed.add_field(
                name="📊 Cache Status",
                value=cache_info,
                inline=False
            )
            
            # Show live invites vs cached
            live_vs_cache = ""
            for invite in current_invites[:5]:  # Limit to first 5
                inviter_name = invite.inviter.name if invite.inviter else "System"
                cached_uses = "Not cached"
                cache_status = "❌"
                
                if guild.id in self.invite_cache and invite.code in self.invite_cache[guild.id]:
                    cached_uses = str(self.invite_cache[guild.id][invite.code]['uses'])
                    cache_status = "✅" if str(invite.uses) == cached_uses else "⚠️"
                
                live_vs_cache += f"{cache_status} **{invite.code}** ({inviter_name})\n"
                live_vs_cache += f"Live: {invite.uses} | Cached: {cached_uses}\n\n"
            
            if live_vs_cache:
                embed.add_field(
                    name="🔄 Live vs Cached Invites",
                    value=live_vs_cache[:1024],  # Discord field limit
                    inline=False
                )
            
            # Add bot permissions check
            perms = guild.me.guild_permissions
            perms_info = f"Manage Guild: {'✅' if perms.manage_guild else '❌'}\n"
            perms_info += f"Create Invites: {'✅' if perms.create_instant_invite else '❌'}\n"
            perms_info += f"View Audit Log: {'✅' if perms.view_audit_log else '❌'}"
            
            embed.add_field(
                name="🤖 Bot Permissions",
                value=perms_info,
                inline=True
            )
            
            # Show staff invite codes
            staff_invites = self.bot.db.get_all_staff_configs()
            staff_info = ""
            for staff in staff_invites[:5]:  # Limit to first 5
                username = staff.get('staff_username', 'Unknown')
                if username is None:
                    username = 'Unknown'
                staff_info += f"**{username}**: {staff['invite_code']}\n"
            
            if staff_info:
                embed.add_field(
                    name="👥 Staff Invite Codes",
                    value=staff_info,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error in debug_invites: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="refresh_invite_cache")
    @commands.has_permissions(manage_guild=True)
    async def refresh_invite_cache(self, ctx):
        """Manually refresh the invite cache"""
        try:
            await self.cache_guild_invites(ctx.guild)
            
            cache_count = len(self.invite_cache.get(ctx.guild.id, {}))
            await ctx.send(f"✅ Refreshed invite cache with {cache_count} invites")
            
        except Exception as e:
            logger.error(f"❌ Error refreshing invite cache: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="fix_staff_usernames")
    @commands.has_permissions(administrator=True)
    async def fix_staff_usernames(self, ctx):
        """Fix missing staff usernames in database by syncing with config"""
        try:
            # Get all staff configs from database
            staff_configs = self.bot.db.get_all_staff_configs()
            fixed_count = 0
            
            for staff_config in staff_configs:
                if staff_config.get('staff_username') is None or staff_config.get('staff_username') == 'None':
                    # Try to get the username from the config file
                    staff_from_config = self.bot.db.get_staff_config_by_invite(staff_config['invite_code'])
                    
                    if staff_from_config and staff_from_config.get('username'):
                        # Update the database with the correct username
                        success = self.bot.db.update_staff_username(
                            staff_config['staff_id'], 
                            staff_from_config['username']
                        )
                        
                        if success:
                            fixed_count += 1
                            logger.info(f"✅ Fixed username for staff ID {staff_config['staff_id']}")
            
            if fixed_count > 0:
                # Backup to cloud
                try:
                    await self.bot.db.backup_to_cloud()
                    logger.info("☁️ Staff username fixes backed up to cloud")
                except Exception as backup_error:
                    logger.error(f"❌ Failed to backup staff username fixes: {backup_error}")
            
            await ctx.send(f"✅ Fixed {fixed_count} staff usernames in database")
            
        except Exception as e:
            logger.error(f"❌ Error fixing staff usernames: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="update_existing_vips")
    @commands.has_permissions(administrator=True)
    async def update_existing_vips(self, ctx):
        """Check all current VIP members and update their referral status if needed"""
        try:
            VIP_ROLE_ID = int(self.bot.get_env_var('VIP_ROLE_ID', '1401614579850543206'))
            vip_role = ctx.guild.get_role(VIP_ROLE_ID)
            
            if not vip_role:
                await ctx.send(f"❌ VIP role not found (ID: {VIP_ROLE_ID})")
                return
            
            updated_count = 0
            checked_count = 0
            
            await ctx.send("🔍 Checking all VIP members for referral updates...")
            
            for member in vip_role.members:
                checked_count += 1
                
                # Get their invite info from database
                invite_info = self.bot.db.get_user_invite_info(member.id)
                
                if invite_info and invite_info.get('invite_code') != 'unknown':
                    # Get staff config for their invite
                    staff_config = self.bot.db.get_staff_config_by_invite(invite_info['invite_code'])
                    
                    if staff_config:
                        # Check if they already have a completed VIP request
                        existing_requests = self.bot.db.get_user_vip_requests(member.id)
                        has_completed_request = any(req['status'] == 'completed' for req in existing_requests)
                        
                        if not has_completed_request:
                            # Create VIP request to track this existing VIP
                            request_id = self.bot.db.create_vip_request(
                                user_id=member.id,
                                username=f"{member.name}#{member.discriminator}",
                                request_type="existing_vip_sync",
                                staff_id=staff_config['discord_id'],
                                request_data=f"Existing VIP member sync. Original invite: {invite_info['invite_code']}"
                            )
                            
                            if request_id:
                                # Mark as completed immediately
                                self.bot.db.update_vip_request_status(request_id, 'completed')
                                updated_count += 1
                                
                                logger.info(f"✅ Synced existing VIP {member.name} - credited to staff {staff_config['username']}")
            
            # Backup to cloud
            if updated_count > 0:
                try:
                    await self.bot.db.backup_to_cloud()
                    logger.info(f"☁️ VIP sync data backed up to cloud API")
                except Exception as backup_error:
                    logger.error(f"❌ Failed to backup VIP sync data: {backup_error}")
            
            embed = discord.Embed(
                title="✅ VIP Sync Complete",
                description=f"Checked {checked_count} VIP members\nUpdated {updated_count} referral statuses",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error updating existing VIPs: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="invite_stats")
    @commands.has_permissions(manage_guild=True)
    async def invite_stats(self, ctx, staff_member: Optional[discord.Member] = None):
        """Show invite and VIP conversion stats for a staff member"""
        try:
            target = staff_member or ctx.author
            stats = self.bot.db.get_staff_vip_stats(target.id)
            
            embed = discord.Embed(
                title=f"📊 Invite Stats for {target.display_name}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📈 Total Invites",
                value=str(stats['total_invites']),
                inline=True
            )
            embed.add_field(
                name="👑 VIP Conversions", 
                value=str(stats['vip_conversions']),
                inline=True
            )
            embed.add_field(
                name="⏳ Pending Requests",
                value=str(stats['pending_requests']),
                inline=True
            )
            embed.add_field(
                name="🎯 Conversion Rate",
                value=f"{stats['conversion_rate']:.1f}%",
                inline=True
            )
            
            embed.set_thumbnail(url=target.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error getting invite stats: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="sync_member_invites")
    @commands.has_permissions(administrator=True)
    async def sync_member_invites(self, ctx):
        """Reconstruct invite tracking by comparing current member counts with invite usage"""
        await ctx.send("🔄 Starting intelligent member invite reconstruction... This may take a moment.")
        
        try:
            guild = ctx.guild
            
            # Get all guild invites with their full details
            guild_invites = await guild.invites()
            
            # Get staff invite configurations
            staff_configs = self.bot.db.get_all_staff_configs()
            staff_invite_map = {config.get('invite_code'): config for config in staff_configs if config.get('invite_code')}
            
            # Build report of current vs expected members
            report_data = []
            total_synced = 0
            total_updated = 0
            
            for invite in guild_invites:
                if invite.code not in staff_invite_map:
                    continue  # Skip non-staff invites
                
                staff_config = staff_invite_map[invite.code]
                staff_id = staff_config.get('staff_id')
                staff_name = staff_config.get('staff_username', f'Staff {staff_id}')
                
                # Get current invite usage from Discord
                discord_uses = invite.uses or 0
                
                # Get tracked members from database for this invite
                tracked_members = self.bot.db.get_users_by_invite_code(invite.code)
                tracked_count = len(tracked_members) if tracked_members else 0
                
                # Get staff VIP stats
                staff_stats = self.bot.db.get_staff_vip_stats(staff_id)
                db_total_invites = staff_stats.get('total_invites', 0) if staff_stats else 0
                
                # Calculate discrepancy
                missing_members = discord_uses - tracked_count
                
                report_data.append({
                    'staff_name': staff_name,
                    'staff_id': staff_id,
                    'invite_code': invite.code,
                    'discord_uses': discord_uses,
                    'tracked_count': tracked_count,
                    'db_total': db_total_invites,
                    'missing': missing_members,
                    'inviter': invite.inviter
                })
                
                total_synced += tracked_count
            
            # Create detailed results embed
            embed = discord.Embed(
                title="📊 Invite Tracking Analysis",
                description="Comparison of Discord invite usage vs database tracking",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Summary statistics
            total_discord_uses = sum(item['discord_uses'] for item in report_data)
            total_missing = sum(item['missing'] for item in report_data)
            
            embed.add_field(
                name="� Overall Statistics",
                value=(
                    f"**Total Discord Uses:** {total_discord_uses}\n"
                    f"**Tracked in Database:** {total_synced}\n"
                    f"**Missing/Untracked:** {total_missing}\n"
                    f"**Staff Invites Analyzed:** {len(report_data)}"
                ),
                inline=False
            )
            
            # Detailed breakdown per staff
            staff_details = []
            for item in sorted(report_data, key=lambda x: x['discord_uses'], reverse=True):
                status_icon = "✅" if item['missing'] == 0 else "⚠️" if item['missing'] < 5 else "❌"
                staff_details.append(
                    f"{status_icon} **{item['staff_name']}** (`{item['invite_code']}`)\n"
                    f"   Discord: {item['discord_uses']} | Tracked: {item['tracked_count']} | Missing: {item['missing']}"
                )
            
            if len(staff_details) <= 7:
                embed.add_field(
                    name="👥 Per-Staff Analysis",
                    value="\n\n".join(staff_details) if staff_details else "No staff invites found",
                    inline=False
                )
            else:
                # Split into multiple fields
                mid = len(staff_details) // 2
                embed.add_field(
                    name="👥 Per-Staff Analysis (1/2)",
                    value="\n\n".join(staff_details[:mid]),
                    inline=False
                )
                embed.add_field(
                    name="👥 Per-Staff Analysis (2/2)",
                    value="\n\n".join(staff_details[mid:]),
                    inline=False
                )
            
            # Explanation and recommendations
            embed.add_field(
                name="💡 Understanding the Data",
                value=(
                    "**Discord Uses**: Total times this invite was used (from Discord API)\n"
                    "**Tracked**: Members we have recorded in the database\n"
                    "**Missing**: Discrepancy that may be due to:\n"
                    "  • Members who left the server\n"
                    "  • Database was cleared/reset\n"
                    "  • Bot was offline during joins\n"
                    "  • Invite was used before tracking started"
                ),
                inline=False
            )
            
            if total_missing > 0:
                embed.add_field(
                    name="� Next Steps",
                    value=(
                        "The missing members represent historical data that cannot be recovered automatically. "
                        "Going forward, all new joins will be tracked properly.\n\n"
                        "**Action Items:**\n"
                        "1. Current members who become VIP will be credited correctly\n"
                        "2. Run `/update_existing_vips` to credit existing VIP members\n"
                        "3. Historical invite counts are for reference only"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Status",
                    value="All invite usage is properly tracked! No discrepancies found.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ Bot lacks permission to view invites. Please grant 'Manage Server' permission.")
        except Exception as e:
            logger.error(f"❌ Error in member invite analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await ctx.send(f"❌ Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))