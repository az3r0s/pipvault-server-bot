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
            await self.cache_guild_invites(guild)
    
    async def cache_guild_invites(self, guild):
        """Cache current invite uses for a guild"""
        try:
            invites = await guild.invites()
            self.invite_cache[guild.id] = {}
            
            for invite in invites:
                self.invite_cache[guild.id][invite.code] = {
                    'uses': invite.uses,
                    'inviter': invite.inviter,
                    'code': invite.code
                }
            
            logger.info(f"📊 Cached {len(invites)} invites for {guild.name}")
            
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
            else:
                cache_info = "❌ No cache found for this guild"
            
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
                
                if guild.id in self.invite_cache and invite.code in self.invite_cache[guild.id]:
                    cached_uses = str(self.invite_cache[guild.id][invite.code]['uses'])
                
                live_vs_cache += f"**{invite.code}** ({inviter_name})\n"
                live_vs_cache += f"Live: {invite.uses} | Cached: {cached_uses}\n\n"
            
            if live_vs_cache:
                embed.add_field(
                    name="🔄 Live vs Cached Invites",
                    value=live_vs_cache[:1024],  # Discord field limit
                    inline=False
                )
            
            # Show staff invite codes
            staff_invites = self.bot.db.get_all_staff_configs()
            staff_info = ""
            for staff in staff_invites[:5]:  # Limit to first 5
                staff_info += f"**{staff['staff_username']}**: {staff['invite_code']}\n"
            
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

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))