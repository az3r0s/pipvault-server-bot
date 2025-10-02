from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class EmbedManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permissions"""
        if interaction.guild and hasattr(interaction.user, 'guild_permissions'):
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                return member.guild_permissions.administrator
        return False

    @app_commands.command(name="post_welcome_embed", description="Post the welcome embed to specified channel")
    @app_commands.describe(channel="Channel to post the welcome embed in")
    async def post_welcome_embed(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Post the welcome embed to the specified channel"""
        
        if not self.check_admin_permissions(interaction):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        target_channel = channel or interaction.channel
        await interaction.response.defer(ephemeral=True)

        try:
            await self.send_welcome_embeds(target_channel)
            await interaction.followup.send(f"✅ Welcome embed posted successfully to {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to post embed: {str(e)}", ephemeral=True)

    async def send_welcome_embeds(self, channel):
        """Send welcome embed to new members"""
        
        embed = discord.Embed(
            title="🎉 Welcome to Path to Prosperity!",
            description="Hey there, new trader! Welcome to our premier trading community! 🚀\n\n**Start your journey to financial success with us!**",
            color=0x00ff00
        )

        embed.add_field(
            name="📋 **Getting Started**",
            value="""• 📜 Read our <#1401614582845280316> to understand community guidelines
• 📢 Check <#announcements> for important updates
• 💬 Join conversations in our community channels""",
            inline=True
        )

        embed.add_field(
            name="💎 **VIP Benefits**",
            value="""• 🎯 Premium gold signals with high accuracy
• 📊 Advanced market analysis & insights
• 🤖 Multi-account MT5 integration""",
            inline=True
        )

        embed.add_field(
            name="🆓 **Free Access**",
            value="""• Daily signals and market analysis
• Educational content & trading tips
• Active community discussions""",
            inline=True
        )

        embed.add_field(
            name="🤖 **Discord Bot Features**",
            value="""• `/mt5-stats` - View your trading performance
• `/mt5-accounts` - Manage multiple accounts
• `/mt5-leaderboard` - Community rankings
• Contact staff to link your MT5 account!""",
            inline=False
        )

        embed.add_field(
            name="✨ **Ready to Get Started?**",
            value="**Read the rules, explore our channels, and start your path to prosperity! 📊✨**",
            inline=False
        )

        await channel.send(embed=embed)

    @app_commands.command(name="post_rules_embed", description="Post the rules embed to specified channel")
    @app_commands.describe(channel="Channel to post the rules embed in")
    async def post_rules_embed(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Post the rules embed to the specified channel"""
        
        if not self.check_admin_permissions(interaction):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        target_channel = channel or interaction.channel
        await interaction.response.defer(ephemeral=True)

        try:
            await self.send_rules_embeds(target_channel)
            await interaction.followup.send(f"✅ Rules embeds posted successfully to {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to post embeds: {str(e)}", ephemeral=True)

    async def send_rules_embeds(self, channel):
        """Send multiple rules embeds to avoid character limits"""
        
        # Main rules header
        embed1 = discord.Embed(
            title="📋 Path to Prosperity — Server Rules",
            description="*Building wealth through disciplined trading and respectful community*\n\n**Please read and follow all rules to maintain our professional trading environment** 📈",
            color=0xff0000
        )

        embed1.add_field(
            name="**1️⃣ Respect & Professional Conduct**",
            value="""• Treat all members with respect and professionalism
• No harassment, bullying, or personal attacks
• Keep discussions trading-focused and constructive
• Maintain a positive, supportive community atmosphere""",
            inline=False
        )

        embed1.add_field(
            name="**2️⃣ Channel Usage & Communication**",
            value="""• Use appropriate channels for their designated purposes
• No spam, excessive emojis, or off-topic discussions
• Keep conversations in English for moderation purposes
• Use proper grammar and avoid excessive caps/formatting""",
            inline=False
        )

        # Content and trading rules
        embed2 = discord.Embed(
            title="📊 Trading & Content Guidelines",
            color=0xff0000
        )

        embed2.add_field(
            name="**3️⃣ Trading Content & Signals**",
            value="""• No sharing signals from other sources or groups
• VIP content is exclusive — sharing outside is prohibited
• No financial advice — all content is educational only
• Respect intellectual property and content ownership""",
            inline=False
        )

        embed2.add_field(
            name="**4️⃣ Promotions & External Links**",
            value="""• No promotional content without staff approval
• No referral links, advertising, or competitor promotion
• No soliciting members for external services
• Staff-approved educational content only""",
            inline=False
        )

        # Technical and VIP rules
        embed3 = discord.Embed(
            title="🔧 Technical & VIP Guidelines",
            color=0xff0000
        )

        embed3.add_field(
            name="**5️⃣ VIP & Technical Usage**",
            value="""• VIP content is exclusive — sharing outside the server is prohibited
• Use `/mt5-stats` and bot commands appropriately
• No begging for upgrades, signals, or special access
• Respect MT5 account linking policies (admin-managed for security)""",
            inline=False
        )

        embed3.add_field(
            name="**6️⃣ Multi-Account & Bot Usage**",
            value="""• MT5 account linking is managed by administrators for security
• Use Discord bot commands responsibly and in appropriate channels
• No attempts to manipulate stats or leaderboard rankings
• Report any technical issues to staff promptly""",
            inline=False
        )

        # Enforcement embed
        embed4 = discord.Embed(
            title="⚠️ Enforcement & Contact Information",
            color=0xff0000
        )

        embed4.add_field(
            name="**⚠️ Enforcement & Consequences**",
            value="""• **1st Violation** — Warning + education about rules
• **2nd Violation** — Temporary mute (24-48 hours)
• **3rd Violation** — Temporary ban (3-7 days)
• **Severe violations** — Immediate permanent ban

*Violations include: sharing VIP content, promoting competitors, harassment, or circumventing security measures*""",
            inline=False
        )

        embed4.add_field(
            name="**📞 Contact Staff**",
            value="Questions about rules? Need help with MT5 linking? Contact our staff team.\n**Staff decisions are final in all rule interpretations and disputes.**",
            inline=False
        )

        # Send all embeds
        await channel.send(embed=embed1)
        await channel.send(embed=embed2)
        await channel.send(embed=embed3)
        await channel.send(embed=embed4)

    @app_commands.command(name="post_faq_embed", description="Post the FAQ embed to specified channel")
    @app_commands.describe(channel="Channel to post the FAQ embed in")
    async def post_faq_embed(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Post the FAQ embed to the specified channel"""
        
        if not self.check_admin_permissions(interaction):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        target_channel = channel or interaction.channel
        await interaction.response.defer(ephemeral=True)

        try:
            await self.send_faq_embeds(target_channel)
            await interaction.followup.send(f"✅ FAQ embeds posted successfully to {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to post embeds: {str(e)}", ephemeral=True)

    async def send_faq_embeds(self, channel):
        """Send multiple FAQ embeds to avoid character limits"""
        
        # Main FAQ intro
        embed1 = discord.Embed(
            title="❓ Frequently Asked Questions",
            description="**🎯 HOW WE TRADE OUR SIGNALS**\n\nOur signals primarily focus on **Gold (XAUUSD)** 🥇 — offering excellent volatility and consistent opportunities for profit.",
            color=0x0099ff
        )

        embed1.add_field(
            name="**📊 Signal Format Example:**",
            value="""```
📱 TRADING SIGNAL #1

📊 XAUUSD: SELL
💰 Position Size: 5% risk
🚀 Entry: 3665.0 - 3670.0
🚫 SL: 3675.0

🎯 TP1: 3660.0
🎯 TP2: 3655.0
🎯 TP3: 3650.0
🎯 TP4: 3645.0
🎯 TP5: 3640.0
```""",
            inline=False
        )

        embed1.add_field(
            name="**🔧 Recommended Broker:**",
            value="Vantage Markets (optimized pricing & execution)",
            inline=False
        )

        # Trading methods embed
        embed2 = discord.Embed(
            title="📌 Trading Methods & Strategies",
            color=0x0099ff
        )

        embed2.add_field(
            name="**📌 MAIN METHOD — LAYER & MANAGE**",
            value="""• 📍 **Layer your entries** across the zone — e.g. LIMIT SELL at 2650, 2651, and 2652.
• ⚖️ **Use equal position sizes** at each layer, or place the largest size in the middle of the zone.
• 🛑 **IMPORTANT:** Set your Stop Loss (SL) on all limits as soon as you place them.
• ✅ **Close 50% of your position** at TP1.
• 📊 **Take more partials** at each next TP.
• 📈 **Trail your SL** as price moves in your favour.

💡 This approach aims to capture the full move from start to finish — banking profits along the way while leaving a portion of your trade to ride big trends.""",
            inline=False
        )

        # Alternative method embed
        embed3 = discord.Embed(
            title="📈 Alternative Trading Strategy",
            color=0x0099ff
        )

        embed3.add_field(
            name="**📌 ALTERNATIVE METHOD — STEP-UP STOP LOSS**",
            value="""• ⏳ **Wait until price bounces** from your entry zone or TP1 is hit.
• 🔒 **Move SL to BE** (Break Even) on all entries at this stage.
• 📈 **When TP2 is hit,** move SL to TP1.
• 📈 **When TP3 is hit,** move SL to TP2, and so on.
• 🪙 **Keep small runners** for any open targets.

💡 This method focuses on capital protection first — locking in safety as the trade progresses while still leaving the door open for profit from runners.""",
            inline=False
        )

        # Send all embeds
        await channel.send(embed=embed1)
        await channel.send(embed=embed2)
        await channel.send(embed=embed3)

async def setup(bot):
    await bot.add_cog(EmbedManagement(bot))