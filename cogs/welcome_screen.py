"""
Welcome Screen System Cog
=========================

Handles the complete welcome screen and onboarding system for new members including:
- Sticky welcome embed with PipVault branding
- Progressive channel unlocking (welcome -> rules -> faq -> chat -> full access)
- Automatic role management (@Unverified -> @Verified)
- Database tracking and analytics
- Automatic redirects between verification steps
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from datetime import datetime
import json
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class WelcomeScreenSystem(commands.Cog):
    """Welcome screen and member onboarding system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.welcome_embed_message_id = None
        self.guild_id = int(self.bot.GUILD_ID) if hasattr(self.bot, 'GUILD_ID') else None
        
        # Channel IDs (will be configured via environment or commands)
        self.welcome_channel_id = None
        self.rules_channel_id = None
        self.faq_channel_id = None
        self.chat_channel_id = None
        self.announcements_channel_id = None
        
        # Role IDs
        self.unverified_role_id = None
        self.verified_role_id = None
    
    async def setup_roles_and_channels(self, guild: discord.Guild):
        """Setup required roles and get channel IDs"""
        try:
            # Find or create roles
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if not unverified_role:
                unverified_role = await guild.create_role(
                    name="Unverified",
                    color=discord.Color.orange(),
                    reason="Welcome system - for new members during verification"
                )
                logger.info("✅ Created @Unverified role")
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            if not verified_role:
                verified_role = await guild.create_role(
                    name="Verified",
                    color=discord.Color.green(),
                    reason="Welcome system - for verified members"
                )
                logger.info("✅ Created @Verified role")
            
            self.unverified_role_id = unverified_role.id
            self.verified_role_id = verified_role.id
            
            # Find channels by name
            for channel in guild.channels:
                if channel.name == "welcome":
                    self.welcome_channel_id = channel.id
                elif channel.name == "rules":
                    self.rules_channel_id = channel.id
                elif channel.name == "faq":
                    self.faq_channel_id = channel.id
                elif channel.name == "chat":
                    self.chat_channel_id = channel.id
                elif channel.name == "announcements":
                    self.announcements_channel_id = channel.id
            
            logger.info(f"✅ Welcome system setup complete for {guild.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup roles and channels: {e}")
            return False
    
    def create_welcome_embed(self) -> discord.Embed:
        """Create the main welcome embed with PipVault branding"""
        embed = discord.Embed(
            title="🏆 Welcome to PipVault!",
            description="""🌟 **Your Path to Prosperity Starts Here** 🌟

Hey there, future trading legend! 🚀

Welcome to our elite trading community where we turn market moves into profit opportunities!

Join dozens of successful traders on their journey to financial freedom 💎

🎯 **Quick Start Guide**
Step 1: Read our comprehensive rules
📜 Rules Channel: <#{}> 

Step 2: Stay updated with announcements  
📢 Updates Channel: <#{}>

Step 3: Join the conversation
💬 Community Channels: Jump into any trading discussion!

💡 Pro Tip: Take your time to explore and get familiar with our community culture.

💎 **Premium VIP Access**
🌟 What You Get:
• ✨ Premium Gold signals with high accuracy
• 📊 Advanced market analysis and insights
• 🎯 Professional trading setups and strategies
• 🤖 MT5 auto-trading integration (Beta)

💰 How to Access:
Trade with our Vantage IB partner for full VIP access!

🎁 The Best Part: No monthly fees — just active trading

🆓 **Free Community Benefits**
Available to ALL Members Immediately:

📈 Market Education:
• Daily market insights and analysis
• Educational content and trading guides
• Expert trading tips and strategies

🤝 Community Support:
• Active trader discussions
• Peer learning and support
• Question and answer sessions

💡 Perfect For: Learning, growing, and building your trading foundation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Verification Required**
To access all channels and features, complete these verification steps:

1️⃣ Welcome Acknowledgment - React with 🎯 below to confirm you've read this message
2️⃣ Server Rules Agreement - Visit <#{}> and react to the rules embed
3️⃣ FAQ Understanding - Visit <#{}> and react to any FAQ embed  
4️⃣ Community Introduction - Post a message in <#{}> to introduce yourself

⚡ **Ready to Start?**
React with 🎯 below to begin your verification journey and unlock access to our server rules!

📍 Next: After reacting, you'll be automatically taken to <#{}>""".format(
                self.rules_channel_id or "rules",
                self.announcements_channel_id or "announcements", 
                self.rules_channel_id or "rules",
                self.faq_channel_id or "faq",
                self.chat_channel_id or "chat",
                self.rules_channel_id or "rules"
            ),
            color=0x2E8B57  # Professional green matching PipVault brand
        )
        
        embed.set_footer(text="PipVault | Premium Trading Community")
        
        return embed
    
    async def add_onboarding_methods_to_database(self):
        """Add onboarding-specific methods to the database if not already present"""
        if not hasattr(self.bot.db, 'init_onboarding_progress'):
            # Add methods dynamically to the database instance
            
            async def init_onboarding_progress(user_id: str, username: str):
                """Initialize onboarding progress for a new user"""
                try:
                    if hasattr(self.bot.db, 'get_connection'):
                        # SQLite database
                        conn = self.bot.db.get_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO onboarding_progress 
                            (user_id, username, step, completed, welcome_reacted, rules_reacted, faq_reacted, chat_introduced, started_at, last_step_at)
                            VALUES (?, ?, 1, FALSE, FALSE, FALSE, FALSE, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ''', (user_id, username))
                        
                        conn.commit()
                        conn.close()
                        
                    # For cloud database, we'll handle this in the cloud API backup
                    await self.log_onboarding_event(user_id, "member_joined", "welcome_started")
                    logger.info(f"✅ Initialized onboarding for {username} ({user_id})")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to init onboarding progress: {e}")
            
            async def update_onboarding_step(user_id: str, step_name: str):
                """Update user's onboarding progress"""
                try:
                    if hasattr(self.bot.db, 'get_connection'):
                        conn = self.bot.db.get_connection()
                        cursor = conn.cursor()
                        
                        # Update the specific step
                        if step_name == "welcome_react":
                            cursor.execute('''
                                UPDATE onboarding_progress 
                                SET welcome_reacted = TRUE, step = 2, last_step_at = CURRENT_TIMESTAMP
                                WHERE user_id = ?
                            ''', (user_id,))
                        elif step_name == "rules_react":
                            cursor.execute('''
                                UPDATE onboarding_progress 
                                SET rules_reacted = TRUE, step = 3, last_step_at = CURRENT_TIMESTAMP
                                WHERE user_id = ?
                            ''', (user_id,))
                        elif step_name == "faq_react":
                            cursor.execute('''
                                UPDATE onboarding_progress 
                                SET faq_reacted = TRUE, step = 4, last_step_at = CURRENT_TIMESTAMP
                                WHERE user_id = ?
                            ''', (user_id,))
                        elif step_name == "chat_intro":
                            cursor.execute('''
                                UPDATE onboarding_progress 
                                SET chat_introduced = TRUE, completed = TRUE, completed_at = CURRENT_TIMESTAMP, last_step_at = CURRENT_TIMESTAMP
                                WHERE user_id = ?
                            ''', (user_id,))
                        
                        conn.commit()
                        conn.close()
                        
                    await self.log_onboarding_event(user_id, "step_completed", step_name)
                    logger.info(f"✅ Updated onboarding step {step_name} for user {user_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to update onboarding step: {e}")
            
            async def log_onboarding_event(user_id: str, event_type: str, step_name: str, metadata: dict | None = None):
                """Log onboarding analytics event"""
                try:
                    if hasattr(self.bot.db, 'get_connection'):
                        conn = self.bot.db.get_connection()
                        cursor = conn.cursor()
                        
                        metadata_json = json.dumps(metadata) if metadata else None
                        
                        cursor.execute('''
                            INSERT INTO onboarding_analytics (user_id, event_type, step_name, metadata)
                            VALUES (?, ?, ?, ?)
                        ''', (user_id, event_type, step_name, metadata_json))
                        
                        conn.commit()
                        conn.close()
                        
                except Exception as e:
                    logger.error(f"❌ Failed to log onboarding event: {e}")
            
            # Add methods to database instance
            self.bot.db.init_onboarding_progress = init_onboarding_progress
            self.bot.db.update_onboarding_step = update_onboarding_step
            self.log_onboarding_event = log_onboarding_event
    
    @app_commands.command(name="setup_welcome_embed", description="[ADMIN] Setup the sticky welcome embed in #welcome channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_welcome_embed(self, interaction: discord.Interaction):
        """Setup the main welcome embed"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ This command must be used in a server.")
                return
            
            # Setup roles and channels
            setup_success = await self.setup_roles_and_channels(guild)
            if not setup_success:
                await interaction.followup.send("❌ Failed to setup roles and channels.")
                return
            
            # Add database methods
            await self.add_onboarding_methods_to_database()
            
            # Find welcome channel
            welcome_channel = discord.utils.get(guild.channels, name="welcome")
            if not welcome_channel:
                await interaction.followup.send("❌ #welcome channel not found. Please create it first.")
                return
            
            # Ensure it's a text channel
            if not isinstance(welcome_channel, discord.TextChannel):
                await interaction.followup.send("❌ #welcome must be a text channel.")
                return
            
            # Clear any existing welcome embeds
            async for message in welcome_channel.history(limit=50):
                if message.author == self.bot.user and message.embeds:
                    try:
                        await message.delete()
                    except:
                        pass
            
            # Create and send new welcome embed
            embed = self.create_welcome_embed()
            welcome_message = await welcome_channel.send(embed=embed)
            
            # Add reaction
            await welcome_message.add_reaction("🎯")
            
            # Store message ID
            self.welcome_embed_message_id = welcome_message.id
            
            # Setup channel permissions for progressive unlock
            await self.setup_channel_permissions(guild)
            
            await interaction.followup.send(f"""✅ **Welcome Screen Setup Complete!**

📍 **Welcome embed posted** in {welcome_channel.mention}
🎯 **Reaction added** for verification start
🔐 **Channel permissions** configured for progressive unlock
👥 **Roles created**: @Unverified, @Verified

🚀 **New members will now:**
1. See only #welcome and #announcements initially
2. React with 🎯 to start verification
3. Progressively unlock channels as they complete steps
4. Get full access after completing introduction in #chat

💡 **Next**: Test the system by removing and re-adding a member, or temporarily giving yourself the @Unverified role.""")
            
        except Exception as e:
            logger.error(f"❌ Setup welcome embed failed: {e}")
            await interaction.followup.send(f"❌ Setup failed: {str(e)}")
    
    async def setup_channel_permissions(self, guild: discord.Guild):
        """Setup channel permissions for progressive unlock system"""
        try:
            if not self.unverified_role_id or not self.verified_role_id:
                logger.error("❌ Role IDs not set")
                return
                
            unverified_role = guild.get_role(self.unverified_role_id)
            verified_role = guild.get_role(self.verified_role_id)
            
            if not unverified_role or not verified_role:
                logger.error("❌ Could not find required roles for permission setup")
                return
            
            # Configure each channel's permissions
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    if channel.name == "welcome":
                        # Welcome: Unverified can read and react only
                        await channel.set_permissions(unverified_role, read_messages=True, send_messages=False, add_reactions=True)
                        await channel.set_permissions(verified_role, read_messages=True, send_messages=False, add_reactions=True)
                        
                    elif channel.name == "announcements":
                        # Announcements: Everyone can read, only staff can post
                        await channel.set_permissions(unverified_role, read_messages=True, send_messages=False, add_reactions=False)
                        await channel.set_permissions(verified_role, read_messages=True, send_messages=False, add_reactions=False)
                        
                    elif channel.name in ["rules", "faq"]:
                        # Rules/FAQ: Hidden initially, unlocked progressively, react only
                        await channel.set_permissions(unverified_role, read_messages=False)
                        await channel.set_permissions(verified_role, read_messages=True, send_messages=False, add_reactions=True)
                        
                    elif channel.name == "chat":
                        # Chat: Hidden initially, unlocked for final step
                        await channel.set_permissions(unverified_role, read_messages=False)
                        await channel.set_permissions(verified_role, read_messages=True, send_messages=True, add_reactions=True)
                        
                    else:
                        # All other channels: Verified only
                        await channel.set_permissions(unverified_role, read_messages=False)
                        await channel.set_permissions(verified_role, read_messages=True, send_messages=True, add_reactions=True)
            
            logger.info("✅ Channel permissions configured for progressive unlock")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup channel permissions: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joining - assign @Unverified role and initialize onboarding"""
        try:
            if member.bot:
                return  # Skip bots
            
            guild = member.guild
            if guild.id != self.guild_id:
                return  # Only handle our server
            
            # Get or create unverified role
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if not unverified_role:
                unverified_role = await guild.create_role(
                    name="Unverified",
                    color=discord.Color.orange(),
                    reason="Welcome system - for new members"
                )
            
            # Assign unverified role
            await member.add_roles(unverified_role, reason="New member - starting verification process")
            
            # Initialize onboarding progress
            if hasattr(self.bot.db, 'init_onboarding_progress'):
                await self.bot.db.init_onboarding_progress(str(member.id), str(member))
            
            logger.info(f"✅ New member {member} assigned @Unverified role and started onboarding")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle member join: {e}")
    
    @commands.Cog.listener() 
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction events for welcome system progression"""
        try:
            # Skip bot reactions
            if payload.user_id == self.bot.user.id:
                return
            
            guild = self.bot.get_guild(payload.guild_id)
            if not guild or guild.id != self.guild_id:
                return
            
            user = guild.get_member(payload.user_id)
            if not user or user.bot:
                return
            
            channel = guild.get_channel(payload.channel_id)
            if not channel:
                return
            
            # Check if user has unverified role (only they should trigger progression)
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if not unverified_role or unverified_role not in user.roles:
                return
            
            # Handle different reaction scenarios
            if str(payload.emoji) == "🎯" and payload.message_id == self.welcome_embed_message_id:
                # Step 1: Welcome reaction
                await self.handle_welcome_reaction(user, guild)
                
            elif channel.name == "rules" and payload.emoji.name in ["✅", "👍", "🎯"]:
                # Step 2: Rules reaction
                await self.handle_rules_reaction(user, guild, channel)
                
            elif channel.name == "faq" and payload.emoji.name in ["✅", "👍", "🎯"]:
                # Step 3: FAQ reaction  
                await self.handle_faq_reaction(user, guild, channel)
            
        except Exception as e:
            logger.error(f"❌ Failed to handle reaction: {e}")
    
    async def handle_welcome_reaction(self, user: discord.Member, guild: discord.Guild):
        """Handle welcome embed reaction - unlock rules channel"""
        try:
            # Update onboarding progress
            if hasattr(self.bot.db, 'update_onboarding_step'):
                await self.bot.db.update_onboarding_step(str(user.id), "welcome_react")
            
            # Unlock rules channel
            rules_channel = discord.utils.get(guild.channels, name="rules")
            if rules_channel:
                await rules_channel.set_permissions(user, read_messages=True, send_messages=False, add_reactions=True)
                
                # Redirect user to rules channel
                try:
                    await user.send(f"🎯 **Step 1 Complete!** Welcome acknowledged!\n\n🔓 **UNLOCKED**: {rules_channel.mention} is now available!\n\n📍 **Next**: Visit {rules_channel.mention} and react to the rules embed to continue verification.")
                except:
                    pass  # User has DMs disabled
            
            logger.info(f"✅ {user} completed welcome step - rules channel unlocked")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle welcome reaction: {e}")
    
    async def handle_rules_reaction(self, user: discord.Member, guild: discord.Guild, channel: discord.TextChannel):
        """Handle rules reaction - unlock FAQ channel"""
        try:
            # Update onboarding progress
            if hasattr(self.bot.db, 'update_onboarding_step'):
                await self.bot.db.update_onboarding_step(str(user.id), "rules_react")
            
            # Unlock FAQ channel
            faq_channel = discord.utils.get(guild.channels, name="faq")
            if faq_channel:
                await faq_channel.set_permissions(user, read_messages=True, send_messages=False, add_reactions=True)
                
                # Redirect user to FAQ channel
                try:
                    await user.send(f"✅ **Step 2 Complete!** Rules acknowledged!\n\n🔓 **UNLOCKED**: {faq_channel.mention} is now available!\n\n📍 **Next**: Visit {faq_channel.mention} and react to any FAQ embed to continue verification.")
                except:
                    pass
            
            logger.info(f"✅ {user} completed rules step - FAQ channel unlocked")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle rules reaction: {e}")
    
    async def handle_faq_reaction(self, user: discord.Member, guild: discord.Guild, channel: discord.TextChannel):
        """Handle FAQ reaction - unlock chat channel"""
        try:
            # Update onboarding progress
            if hasattr(self.bot.db, 'update_onboarding_step'):
                await self.bot.db.update_onboarding_step(str(user.id), "faq_react")
            
            # Unlock chat channel
            chat_channel = discord.utils.get(guild.channels, name="chat")
            if chat_channel:
                await chat_channel.set_permissions(user, read_messages=True, send_messages=True, add_reactions=True)
                
                # Redirect user to chat channel
                try:
                    await user.send(f"📚 **Step 3 Complete!** FAQ reviewed!\n\n🔓 **UNLOCKED**: {chat_channel.mention} is now available!\n\n📍 **Next**: Post an introduction message in {chat_channel.mention} to complete verification and unlock full server access!")
                except:
                    pass
            
            logger.info(f"✅ {user} completed FAQ step - chat channel unlocked")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle FAQ reaction: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle chat messages for final verification step"""
        try:
            if message.author.bot:
                return
            
            if not message.guild or message.guild.id != self.guild_id:
                return
            
            # Check if it's the chat channel
            if not isinstance(message.channel, discord.TextChannel) or message.channel.name != "chat":
                return
            
            user = message.author
            
            # Ensure user is a Member, not just User
            if not isinstance(user, discord.Member):
                return
            
            unverified_role = discord.utils.get(message.guild.roles, name="Unverified")
            verified_role = discord.utils.get(message.guild.roles, name="Verified")
            
            if not unverified_role or unverified_role not in user.roles:
                return  # User is not in verification process
            
            if not verified_role:
                return
            
            # Complete verification
            await self.complete_verification(user, message.guild)
            
        except Exception as e:
            logger.error(f"❌ Failed to handle chat message: {e}")
    
    async def complete_verification(self, user: discord.Member, guild: discord.Guild):
        """Complete the verification process - grant full access"""
        try:
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            verified_role = discord.utils.get(guild.roles, name="Verified")
            
            if not unverified_role or not verified_role:
                return
            
            # Update roles
            await user.remove_roles(unverified_role, reason="Verification completed")
            await user.add_roles(verified_role, reason="Verification completed")
            
            # Update onboarding progress
            if hasattr(self.bot.db, 'update_onboarding_step'):
                await self.bot.db.update_onboarding_step(str(user.id), "chat_intro")
            
            # Grant full channel access by removing individual permissions
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    try:
                        await channel.set_permissions(user, overwrite=None)  # Remove custom permissions
                    except:
                        pass
            
            # Send completion message
            chat_channel = discord.utils.get(guild.channels, name="chat")
            if chat_channel and isinstance(chat_channel, discord.TextChannel):
                embed = discord.Embed(
                    title="🎉 Welcome to PipVault!",
                    description=f"**{user.mention} has completed verification and gained full access to our trading community!**\n\nWelcome to your path to prosperity! 🚀",
                    color=0x2E8B57
                )
                await chat_channel.send(embed=embed)
            
            # Send completion DM
            try:
                await user.send(f"""🎉 **PipVault Verification Complete!**

Welcome to the full PipVault trading community! 🏆

You now have access to:
• 📈 All trading discussions and channels
• 💎 Premium community features  
• 🤖 MT5 bot commands (for linked accounts)
• 🎯 VIP upgrade pathways through Vantage partnership

🚀 **What's Next?**
• Explore our free market education content
• Join active trading discussions
• Ask about VIP access for premium signals
• Link your MT5 account for advanced features

Welcome to your path to prosperity! 📊✨

*Where disciplined trading meets financial freedom*""")
            except:
                pass
            
            logger.info(f"🎉 {user} completed full verification - granted @Verified role")
            
        except Exception as e:
            logger.error(f"❌ Failed to complete verification: {e}")
    
    @app_commands.command(name="onboarding_stats", description="[ADMIN] View onboarding completion statistics")
    @app_commands.default_permissions(administrator=True)
    async def onboarding_stats(self, interaction: discord.Interaction):
        """View onboarding statistics"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            if hasattr(self.bot.db, 'get_onboarding_stats'):
                stats = self.bot.db.get_onboarding_stats()
                
                embed = discord.Embed(
                    title="📊 Onboarding Statistics",
                    color=0x2E8B57
                )
                
                embed.add_field(
                    name="📈 Overall Stats",
                    value=f"""**Total Started**: {stats['total_started']}
**Total Completed**: {stats['total_completed']}
**Completion Rate**: {stats['completion_rate']:.1f}%""",
                    inline=False
                )
                
                if 'step_breakdown' in stats:
                    step_data = stats['step_breakdown']
                    embed.add_field(
                        name="🔄 Current Step Distribution",
                        value=f"""**Step 1 (Welcome)**: {step_data.get('step_1_welcome', 0)} users
**Step 2 (Rules)**: {step_data.get('step_2_rules', 0)} users
**Step 3 (FAQ)**: {step_data.get('step_3_faq', 0)} users
**Step 4 (Chat)**: {step_data.get('step_4_chat', 0)} users
**✅ Completed**: {step_data.get('completed', 0)} users""",
                        inline=False
                    )
                
                embed.set_footer(text="PipVault | Welcome System Analytics")
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Onboarding statistics not available")
                
        except Exception as e:
            logger.error(f"❌ Failed to get onboarding stats: {e}")
            await interaction.followup.send(f"❌ Failed to get statistics: {str(e)}")
    
    @app_commands.command(name="verify_member", description="[ADMIN] Manually verify a member and grant full access")
    @app_commands.describe(member="Member to verify")
    @app_commands.default_permissions(administrator=True)
    async def verify_member(self, interaction: discord.Interaction, member: discord.Member):
        """Manually verify a member"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            if member.bot:
                await interaction.followup.send("❌ Cannot verify bot accounts.")
                return
            
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ This command must be used in a server.")
                return
                
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            verified_role = discord.utils.get(guild.roles, name="Verified")
            
            if not verified_role:
                await interaction.followup.send("❌ @Verified role not found. Run `/setup_welcome_embed` first.")
                return
            
            # Update roles if needed
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role, reason=f"Manual verification by {interaction.user}")
            
            if verified_role not in member.roles:
                await member.add_roles(verified_role, reason=f"Manual verification by {interaction.user}")
            
            # Update database
            if hasattr(self.bot.db, 'update_onboarding_step'):
                if asyncio.iscoroutinefunction(self.bot.db.update_onboarding_step):
                    await self.bot.db.update_onboarding_step(str(member.id), "chat_intro")
                else:
                    self.bot.db.update_onboarding_step(str(member.id), "chat_intro")
            
            # Remove any custom channel permissions
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    try:
                        await channel.set_permissions(member, overwrite=None)
                    except:
                        pass
            
            await interaction.followup.send(f"✅ **Manual Verification Complete**\n\n{member.mention} has been granted the @Verified role and full server access.")
            
            logger.info(f"✅ {interaction.user} manually verified {member}")
            
        except Exception as e:
            logger.error(f"❌ Failed to manually verify member: {e}")
            await interaction.followup.send(f"❌ Verification failed: {str(e)}")

def setup(bot):
    bot.add_cog(WelcomeScreenSystem(bot))