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
    
    @commands.hybrid_command(name="create_staff_invite")
    @commands.has_permissions(administrator=True)
    async def create_staff_invite(self, ctx, staff_member: discord.Member, 
                                 vantage_link: str, *, email_template: str):
        """
        Create a permanent invite link for a staff member and configure VIP attribution
        
        Parameters:
        - staff_member: The staff member to create invite for
        - vantage_link: Their Vantage referral link
        - email_template: Email template with placeholders
        """
        try:
            # Create a permanent invite link
            invite = await ctx.channel.create_invite(
                max_age=0,  # Never expires
                max_uses=0,  # Unlimited uses
                unique=True,  # Create unique invite
                reason=f"Staff invite for {staff_member.display_name}"
            )
            
            # Configure in database
            success = self.bot.db.add_staff_invite_config(
                staff_id=staff_member.id,
                staff_username=f"{staff_member.name}#{staff_member.discriminator}",
                invite_code=invite.code,
                vantage_referral_link=vantage_link,
                email_template=email_template
            )
            
            if success:
                embed = discord.Embed(
                    title="🔗 Staff Invite Created Successfully!",
                    description=f"Personal invite link created for {staff_member.mention}",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📋 Invite Details",
                    value=(
                        f"**Link**: {invite.url}\n"
                        f"**Code**: `{invite.code}`\n"
                        f"**Expires**: Never\n"
                        f"**Max Uses**: Unlimited"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="🔗 Vantage Link", 
                    value=f"[Referral Link]({vantage_link})", 
                    inline=True
                )
                embed.add_field(
                    name="📧 Email Template", 
                    value=f"```{email_template[:100]}...```", 
                    inline=False
                )
                
                # Send to channel
                await ctx.send(embed=embed)
                
                # Send DM to staff member with their details
                try:
                    dm_embed = discord.Embed(
                        title="🎉 Your Personal Invite Link",
                        description="Your personal Discord invite link has been created!",
                        color=discord.Color.blue()
                    )
                    dm_embed.add_field(
                        name="🔗 Your Invite Link",
                        value=f"**{invite.url}**\n\nShare this link to invite people and get VIP attribution!",
                        inline=False
                    )
                    dm_embed.add_field(
                        name="📊 Tracking",
                        value="All users who join through this link will be attributed to you for VIP upgrades.",
                        inline=False
                    )
                    
                    await staff_member.send(embed=dm_embed)
                    
                except discord.Forbidden:
                    logger.warning(f"Couldn't send DM to {staff_member.name}")
                
                logger.info(f"✅ Created staff invite {invite.code} for {staff_member.name}")
                
            else:
                await ctx.send("❌ Failed to save staff invite configuration")
                
        except Exception as e:
            logger.error(f"❌ Error creating staff invite: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="list_staff_invites")
    @commands.has_permissions(manage_guild=True)
    async def list_staff_invites(self, ctx):
        """List all configured staff invites"""
        try:
            # This would require a database method to get all staff configs
            # For now, show current invites and their usage
            invites = await ctx.guild.invites()
            
            embed = discord.Embed(
                title="🔗 Staff Invite Links",
                description="Current invite links and their usage",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for invite in invites:
                if invite.inviter:
                    # Check if this is a configured staff invite
                    staff_config = self.bot.db.get_staff_config_by_invite(invite.code)
                    if staff_config:
                        embed.add_field(
                            name=f"👤 {invite.inviter.display_name}",
                            value=(
                                f"**Code**: `{invite.code}`\n"
                                f"**Uses**: {invite.uses}\n"
                                f"**Link**: {invite.url}"
                            ),
                            inline=True
                        )
            
            if len(embed.fields) == 0:
                embed.add_field(
                    name="📝 No Staff Invites",
                    value="No staff invites configured yet. Use `/create_staff_invite` to create them.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error listing staff invites: {e}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.hybrid_command(name="invite_stats")
    @commands.has_permissions(manage_guild=True)
    async def invite_stats(self, ctx, staff_member: discord.Member = None):
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