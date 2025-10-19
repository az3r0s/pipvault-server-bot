from typing import Optional
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import os
from datetime import datetime, time, timezone

logger = logging.getLogger(__name__)

class EmbedManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configuration
        self.FREE_SIGNALS_CHANNEL_ID = int(os.getenv('FREE_SIGNALS_CHANNEL_ID', '0'))
        self.VIP_UPGRADE_CHANNEL_ID = int(os.getenv('VIP_UPGRADE_CHANNEL_ID', '1420009598709923963'))
        
        # Start weekly CTA task
        self.weekly_cta_task.start()

    def check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permissions"""
        if not interaction.guild:
            return False
            
        # Check if user is the server owner
        if interaction.user.id == interaction.guild.owner_id:
            return True
            
        # Check if user has administrator permissions
        if hasattr(interaction.user, 'guild_permissions'):
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
        
        # Main welcome embed with better visual design
        embed = discord.Embed(
            title="🏆 Welcome to PipVault!",
            description="```yaml\n🌟 Your Path to Prosperity Starts Here 🌟\n```\n\n**Hey there, future trading legend!** 🚀\n\nWelcome to our **elite trading community** where we turn market moves into profit opportunities!\n\n> *Join dozens of successful traders on their journey to financial freedom* 💎",
            color=0x2E8B57  # Professional green
        )

        # Visual enhancement without external images
        
        embed.add_field(
            name="🎯 **Quick Start Guide**",
            value="""**Step 1:** Read our comprehensive rules
📜 **Rules Channel:** <#1401614582845280316>

**Step 2:** Stay updated with announcements  
📢 **Updates Channel:** <#1401614583801712732>

**Step 3:** Join the conversation
💬 **Community Channels:** Jump into any trading discussion!

**💡 Pro Tip:** Take your time to explore and get familiar with our community culture.""",
            inline=False
        )

        embed.add_field(
            name="💎 **Premium VIP Access**",
            value="""**🌟 What You Get:**
• ✨ Premium Gold signals with high accuracy
• 📊 Advanced market analysis and insights
• 🎯 Professional trading setups and strategies
• 🤖 MT5 auto-trading integration *(Beta)*

**💰 How to Access:**
Trade with our **Vantage IB partner** for full VIP access!

**🎁 The Best Part:** No monthly fees — just active trading

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        embed.add_field(
            name="🆓 **Free Community Benefits**",
            value="""**Available to ALL Members Immediately:**

**📈 Market Education:**
• Daily market insights and analysis
• Educational content and trading guides
• Expert trading tips and strategies

**🤝 Community Support:**
• Active trader discussions
• Peer learning and support
• Question and answer sessions

**💡 Perfect For:** Learning, growing, and building your trading foundation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # Advanced features showcase
        embed.add_field(
            name="🚀 **Advanced Features (Beta Testing)**",
            value="""**🤖 Discord Bot Integration:** *(Limited Beta Access)*

**📊 Available Commands:**
• `/mt5-stats` - View your complete trading performance
• `/mt5-accounts` - Manage multiple MT5 accounts  
• `/mt5-leaderboard` - See community rankings
• `/refresh-mt5-stats` - Update your cached data

**⚙️ Automation Features:**
• Automated copy trading system
• Real-time performance tracking
• Advanced risk management
• Multi-account support

**⚠️ Beta Status:** These features are currently available to selected beta testers only. Full public release coming soon!

**Want early access?** Contact our staff about beta testing and MT5 account linking! 🔗

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # Call to action with enhanced styling
        embed.add_field(
            name="⭐ **Ready to Start Your Success Story?**",
            value="""**🎯 Your Next Steps:**

**Step 1:** Read the rules and get familiar
**Step 2:** Ask questions — our community helps each other  
**Step 3:** Contact staff about VIP access through Vantage
**Step 4:** Start small, think big, trade smart!

**🏆 Welcome to the PipVault family!** ✨

*Where disciplined trading meets prosperity* 🎯

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # Add footer with branding
        embed.set_footer(text="PipVault Trading Community • Your Path to Prosperity")

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
            title="📋 PipVault — Server Rules",
            description="**Your Path to Prosperity**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n*Building wealth through disciplined trading and respectful community*\n\n**Please read and follow all rules to maintain our professional trading environment** 📈\n\n",
            color=0xff0000
        )

        embed1.add_field(
            name="**1️⃣ Respect & Professional Conduct**",
            value="""**Foundation of Our Community:**

• **Treat all members** with respect and professionalism
• **Zero tolerance** for harassment, bullying, or personal attacks
• **Keep discussions** trading-focused and constructive
• **Maintain positive atmosphere** — support each other's growth

**Why This Matters:** Professional conduct creates an environment where everyone can learn and succeed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        embed1.add_field(
            name="**2️⃣ Content & Communication Guidelines**",
            value="""**Keep Content Relevant:**

• **Focus areas:** Trading, finance, and market analysis
• **Avoid:** Spam, excessive messaging, or ALL CAPS writing
• **Prohibited:** NSFW, inappropriate, or illegal content
• **Channel usage:** Use proper channels for their intended purposes

**Communication Quality:** Clear, respectful, and valuable contributions help everyone learn better.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # Content and trading rules
        embed2 = discord.Embed(
            title="📊 Trading & Content Guidelines",
            description="**Essential guidelines for safe and responsible trading discussions:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0xff0000
        )

        embed2.add_field(
            name="**3️⃣ Trading & Risk Management**",
            value="""**🚨 CRITICAL DISCLAIMER:**
• **Educational purpose only** — All content is for learning and information
• **Not financial advice** — We do not provide investment recommendations
• **High risk warning** — CFDs and leveraged trading carry substantial risk of loss

**Your Responsibilities:**
• Always seek independent financial advice before trading
• Never share signals from other paid services or groups
• Always DYOR (Do Your Own Research) and understand all risks
• Only trade with money you can afford to lose completely

**Why This Matters:** Your financial safety is our top priority.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        embed2.add_field(
            name="**4️⃣ Promotion & External Content**",
            value="""**Prohibited Activities:**

• **No promotion** of competing trading services or groups
• **No affiliate links** or referral codes without permission
• **No unsolicited DMs** for promotions or sales
• **No spam** of external trading resources

**The Right Way:**
• Ask staff permission before sharing external trading resources
• Focus on educational value, not promotion
• Contribute to discussions rather than just promoting

**Community First:** We prioritize member value over commercial interests.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # VIP and bot usage rules
        embed3 = discord.Embed(
            title="🤖 VIP Access & Bot Guidelines",
            description="**Guidelines for VIP content and Discord bot usage:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0xff0000
        )

        embed3.add_field(
            name="**5️⃣ VIP Access & Channel Integrity**",
            value="""**VIP Content Protection:**

• **Exclusive access** — VIP content sharing outside the server is strictly prohibited
• **Respect boundaries** — VIP channels are for VIP members only
• **No begging** for upgrades, signals, or special access
• **Value the privilege** — VIP access is earned through our partnership model

**Bot Command Usage:**
• Use `/mt5-stats` and bot commands appropriately
• Respect rate limits and don't spam commands
• Report any issues to staff promptly

**Why This Matters:** Protecting VIP content ensures continued high-quality service.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        embed3.add_field(
            name="**6️⃣ Multi-Account & Bot Usage**",
            value="""**Account Management Security:**

• **Admin-only linking** — MT5 account linking is managed by administrators for security
• **One person, multiple accounts** — Demo and live accounts supported per user
• **No stat manipulation** — Any attempts to manipulate stats or leaderboard rankings will result in permanent ban

**Responsible Usage:**
• Use Discord bot commands responsibly and in appropriate channels
• Don't abuse the system or try to circumvent security measures
• Report technical issues to staff promptly for quick resolution

**Security First:** Our admin-managed approach ensures your account safety.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # Enforcement embed
        embed4 = discord.Embed(
            title="⚠️ Enforcement & Contact Information",
            description="**Fair and consistent rule enforcement for all community members:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0xff0000
        )

        embed4.add_field(
            name="**⚠️ Progressive Enforcement System**",
            value="""**Our Approach:** Education first, enforcement when necessary

**Violation Levels:**
• **1st Violation** — Warning + education about rules
• **2nd Violation** — Temporary mute (24-48 hours)  
• **3rd Violation** — Temporary ban (3-7 days)
• **Severe violations** — Immediate permanent ban

**What Constitutes Violations:**
*Sharing VIP content outside server, promoting competitors, harassment, circumventing security measures, or repeated rule breaking*

**Our Goal:** Help members understand and follow rules rather than just punish.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        embed4.add_field(
            name="**📞 Staff Support & Contact**",
            value="""**Need Help?**

**Questions about:**
• Rule interpretations or clarifications
• MT5 account linking and setup
• VIP access and requirements
• Technical issues or bot problems

**How to Contact:**
• DM any staff member directly
• Ask in appropriate channels
• Open a support ticket if available

**Important:** Staff decisions are final in all rule interpretations and disputes. We aim to be fair and consistent in all decisions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # Regulatory compliance embed
        embed5 = discord.Embed(
            title="📋 Regulatory Disclosures & Legal Notices",
            color=0x800080
        )

        embed5.add_field(
            name="**⚠️ FCA COMPLIANCE NOTICE**",
            value="""This Discord server and its content are not regulated by the Financial Conduct Authority (FCA). We do not provide financial advice, investment recommendations, or portfolio management services.""",
            inline=False
        )

        embed5.add_field(
            name="**🚨 HIGH RISK WARNING**",
            value="""• CFDs and leveraged products carry high risk of rapid money loss
• 74-89% of retail investor accounts lose money when trading CFDs
• You should consider whether you understand how CFDs work
• Only trade with money you can afford to lose completely""",
            inline=False
        )

        embed5.add_field(
            name="**📊 EDUCATIONAL PURPOSE DISCLAIMER**",
            value="""• All content is for educational and informational purposes only
• No content constitutes financial, investment, or trading advice
• Past performance does not guarantee future results
• Individual results may vary significantly""",
            inline=False
        )

        # Final regulatory embed
        embed6 = discord.Embed(
            title="🏛️ Regulatory Status & Compliance",
            color=0x800080
        )

        embed6.add_field(
            name="**🏛️ REGULATORY STATUS**",
            value="""• We are not authorized by the FCA or any financial regulatory body
• We do not accept client funds or execute trades on behalf of clients
• We are not covered by the Financial Services Compensation Scheme (FSCS)
• We are not subject to the Financial Ombudsman Service (FOS)""",
            inline=False
        )

        embed6.add_field(
            name="**💼 PROFESSIONAL ADVICE REQUIREMENT**",
            value="""Before making any financial decisions:
• Seek advice from an FCA-authorized financial advisor
• Ensure the advisor is suitable for your circumstances
• Verify advisor credentials on the FCA register
• Consider your financial situation and risk tolerance""",
            inline=False
        )

        embed6.set_footer(text="Last updated: September 2025 | Rules subject to change with community notice")

        # Send all embeds
        await channel.send(embed=embed1)
        await channel.send(embed=embed2)
        await channel.send(embed=embed3)
        await channel.send(embed=embed4)
        await channel.send(embed=embed5)
        await channel.send(embed=embed6)

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
            description="**🎯 HOW WE TRADE OUR SIGNALS**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nOur signals primarily focus on **Gold (XAUUSD)** 🥇 — offering excellent volatility and consistent opportunities for profit.\n\n",
            color=0x0099ff
        )

        embed1.add_field(
            name="**📊 Signal Format Example:**",
            value="""```
📱 TRADING SIGNAL #1

📊 XAUUSD: SELL
💰 Position Size: 5% risk
🚀 Entry: 2650.0 - 2652.0
🚫 SL: 2655.0

🎯 TP1: 2648.0
🎯 TP2: 2646.0
🎯 TP3: 2644.0
🎯 TP4: 2642.0
🎯 TP5: 2640.0
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        embed1.add_field(
            name="**🔧 Recommended Broker:**",
            value="**Vantage Markets** (optimized pricing & execution)\n\n*Why Vantage?* Tightest spreads, fastest execution, and seamless MT5 integration with our copy trading system.",
            inline=False
        )

        # Trading methods embed
        embed2 = discord.Embed(
            title="📌 Trading Methods & Strategies",
            description="**Choose the method that best suits your trading style and risk tolerance:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x0099ff
        )

        embed2.add_field(
            name="**📌 MAIN METHOD — LAYER & MANAGE**",
            value="""**Step 1: Entry Setup**
• 📍 **Layer your entries** across the zone 
  *Example: LIMIT SELL at 2650, 2651, and 2652*

• ⚖️ **Position sizing options:**
  - Equal sizes at each layer, OR
  - Largest size in the middle of the zone

• 🛑 **CRITICAL:** Set your Stop Loss (SL) on ALL limit orders immediately

**Step 2: Profit Management**
• ✅ **Close 50% of your position** at TP1
• 📊 **Take more partials** at each subsequent TP
• 📈 **Trail your SL** as price moves in your favor

**💡 Strategy Goal:**
*Capture the full move from start to finish — banking profits along the way while leaving runners for big trends.*""",
            inline=False
        )

        # Alternative method embed
        embed3 = discord.Embed(
            title="📈 Alternative Trading Strategy",
            description="**For traders who prefer capital protection over maximum profit potential:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x0099ff
        )

        embed3.add_field(
            name="**📌 ALTERNATIVE METHOD — STEP-UP STOP LOSS**",
            value="""**Phase 1: Patient Entry**
• ⏳ **Wait for confirmation** — price bounce from entry zone OR TP1 hit
• 🔒 **Move SL to Break Even** on ALL entries at this stage

**Phase 2: Progressive Protection**
• 📈 **TP2 hit?** → Move SL to TP1
• 📈 **TP3 hit?** → Move SL to TP2  
• 📈 **Continue pattern** for each subsequent TP level

**Phase 3: Runner Management**
• 🪙 **Keep small runners** for any remaining open targets
• �️ **Risk-free profit** locked in at every step

**💡 Method Focus:**
*Capital protection first — locking in safety as the trade progresses while keeping the door open for profit from runners.*""",
            inline=False
        )

        embed3.add_field(
            name="✨ **Pro Tip:**",
            value="""**Find Your Trading Style:**

Experiment with both methods to discover what matches your:
• Risk appetite 📊
• Trading psychology 🧠  
• Available time for management ⏰

**Remember:** Consistency in execution beats perfect strategy every time! 🎯""",
            inline=False
        )

        # MT5 integration embed
        embed4 = discord.Embed(
            title="🤖 MT5 Integration & Automation",
            description="**Experience the future of copy trading with our advanced MT5 integration:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x0099ff
        )

        embed4.add_field(
            name="**🤖 AUTOMATED COPY TRADING FEATURES**",
            value="""**🔗 Account Integration:**
• Link your MT5 account through our Discord bot
• Secure admin-only linking process for safety

**⚙️ Smart Automation:**
• Automated position sizing based on your risk settings
• Multi-account support (demo + live accounts)
• Configurable stats and performance tracking

**📊 Performance Monitoring:**
• Real-time tracking with `/mt5-stats` command
• Community leaderboard with `/mt5-leaderboard`
• Detailed analytics and trade history""",
            inline=False
        )

        embed4.add_field(
            name="**⚠️ DEVELOPMENT STATUS**",
            value="""**🧪 Currently in BETA testing phase**

✅ **Available now:** Demo account trials  
🔜 **Coming soon:** Full live account integration

**Want early access?** Contact our staff team to register your interest for full beta testing!""",
            inline=False
        )

        embed4.add_field(
            name="**🚫 MISSED A SIGNAL?**",
            value="""**⚠️ Golden Rule: DON'T CHASE!**

**Why not chase?**
• We provide 5-10 high-quality signals daily
• Quality over quantity approach
• Next opportunity is never far away

**If we suggest re-entry:**
• Use **MAXIMUM 50%** of normal position size
• Wait for clear confirmation
• Patience beats desperation every time! 🎯""",
            inline=False
        )

        # Membership options embed
        embed5 = discord.Embed(
            title="💎 VIP Membership & Access",
            description="**Choose the VIP option that best fits your trading goals:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x0099ff
        )

        embed5.add_field(
            name="**💎 VANTAGE IB PARTNERSHIP**",
            value="""**🌟 RECOMMENDED CHOICE**

**💰 Cost:** FREE — No monthly fees
**📋 Requirements:** Remain active trader with Vantage

**✅ What You Get:**
• 🎯 Signals optimized for Vantage execution
• 📊 Best pricing and minimal slippage  
• 🤖 Full MT5 integration and copy trading
• 📈 Priority support and analysis
• � Community leaderboard access

**Why Vantage?** Our partnership ensures optimal signal execution and seamless automation.""",
            inline=False
        )

        embed5.add_field(
            name="**🔗 MT5 ACCOUNT LINKING PROCESS**",
            value="""**🔐 Secure & Simple Setup:**

**Step 1:** Contact our staff team
**Step 2:** Secure verification process  
**Step 3:** Account linking completed

**📊 Features:**
• Multiple accounts supported (demo + live)
• Automated performance tracking
• Risk management integration
• Admin-only security protocols

**💡 Pro Tip:** Start with a demo account to test the system risk-free!""",
            inline=False
        )

        # Bot commands and final info embed
        embed6 = discord.Embed(
            title="🔧 Bot Commands & Additional Info",
            description="**Master our Discord bot commands and risk management system:**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x0099ff
        )

        embed6.add_field(
            name="**📊 ESSENTIAL BOT COMMANDS**",
            value="""**📈 Performance Tracking:**
• `/mt5-stats` — Your complete trading statistics
• `/mt5-accounts` — View all linked accounts
• `/mt5-account-stats` — Performance by specific account

**🏆 Community Features:**  
• `/mt5-leaderboard` — Community rankings
• `/refresh-mt5-stats` — Update cached data

**💡 Pro Tip:** Use these commands regularly to track your progress and stay motivated!""",
            inline=False
        )

        embed6.add_field(
            name="**💼 SMART RISK MANAGEMENT**",
            value="""**📊 Default Risk Settings:**
• **Gold Signals:** 5% account risk per trade
• **Forex Signals:** 3% account risk per trade  
• **Re-entry Signals:** 2% account risk per trade

**⚙️ Customization Options:**
• Bot uses these values automatically
• Fully customizable per account
• Contact staff for personalized settings

**🛡️ Why This Matters:** Proper risk management is the foundation of profitable trading!""",
            inline=False
        )

        embed6.add_field(
            name="**📈 WANT PROOF?**",
            value="""**🔍 Verified Performance Data:**

Check our **results channels** for real VIP performance data!

**What you'll find:**
• Verified trading results
• Community member success stories  
• Transparent performance metrics
• Live trading screenshots

**💪 Our members' success speaks for itself!**""",
            inline=False
        )

        embed6.add_field(
            name="**❓ NEED MORE HELP?**",
            value="""**🤝 We're Here for You:**

**Staff Support:**
• DM any staff member anytime
• Fast response times
• Personal trading guidance
• Technical support available

**💪 We're committed to your success — never hesitate to ask questions!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            inline=False
        )

        # NEW: Enhanced tips and security embed
        embed7 = discord.Embed(
            title="🚀 Pro Tips & Security",
            color=0x0099ff
        )

        embed7.add_field(
            name="**📱 MOBILE TRADING OPTIMIZATION**",
            value="""• Enable push notifications for Discord signals
• Set up MT5 mobile app with same account
• Use price alerts at key entry/exit levels
• Keep phone charged during high-impact news
• Pre-set lot sizes in your trading app for speed""",
            inline=False
        )

        embed7.add_field(
            name="**⏰ OPTIMAL TRADING HOURS**",
            value="""• **Gold Peak Hours:** London (8-12 GMT) & NY (13-17 GMT)
• **High Volatility:** Major news events & market opens
• **Lower Spreads:** During overlapping sessions  
• **Weekend Gaps:** Monitor Sunday 10PM GMT opening
• **Avoid:** Christmas/New Year & low-liquidity hours""",
            inline=False
        )

        embed7.add_field(
            name="**🛡️ SECURITY & BEST PRACTICES**",
            value="""• **Never share** your MT5 login credentials with anyone
• Use **strong passwords** and **2FA** where available
• **Verify all signals** come from official channels only
• **Screenshot** your trades for personal records
• **Review monthly** performance to track progress
• **Set up** email/SMS alerts for large drawdowns""",
            inline=False
        )

        embed7.add_field(
            name="**📊 MAXIMIZE YOUR SUCCESS**",
            value="""• **Journal everything:** wins, losses, emotions, lessons
• **Test strategies** on demo before going live
• **Start small** and scale up as confidence grows
• **Set daily/weekly** loss limits and stick to them
• **Celebrate wins** but stay humble and focused""",
            inline=False
        )

        # Send all embeds
        await channel.send(embed=embed1)
        await channel.send(embed=embed2)
        await channel.send(embed=embed3)
        await channel.send(embed=embed4)
        await channel.send(embed=embed5)
        await channel.send(embed=embed6)
        await channel.send(embed=embed7)

    @app_commands.command(name="post_cta_embed", description="Post the CTA (Call to Action) embed to specified channel")
    @app_commands.describe(channel="Channel to post the CTA embed in")
    async def post_cta_embed(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Post the CTA embed to the specified channel"""
        
        if not self.check_admin_permissions(interaction):
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        target_channel = channel or interaction.channel
        await interaction.response.defer(ephemeral=True)

        try:
            await self.send_cta_embed(target_channel)
            await interaction.followup.send(f"✅ CTA embed posted successfully to {target_channel.name if hasattr(target_channel, 'name') else 'the channel'}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to post CTA embed: {str(e)}", ephemeral=True)

    async def send_cta_embed(self, channel):
        """Send CTA embed to the specified channel"""
        
        # Create the CTA embed
        embed = discord.Embed(
            title="🚀 HOW TO START COPY TRADING NOW",
            description=(
                "We've made it simpler than ever to get started and join the Pipvault **FREE VIP Group**, where you'll get access to:\n\n"
                "✅ 5-7+ high quality trades per day\n"
                "✅ 85% success rate on gold signals\n"
                "✅ Step-by-step guidance on how to take the trades\n"
                "✅ Weekly mindset coaching\n"
                "✅ Trusted broker partnership for your security\n\n"
                "And the best part:\n"
                "**❌ No setup costs**\n"
                "**❌ No monthly fees**\n"
                "**❌ No contracts ever**\n\n"
                "Here's how to get started:\n\n"
                "1️⃣ Click the **'JOIN FREE'** button under this message to begin setup\n"
                "2️⃣ Follow along in the support chat and complete each step\n"
                "3️⃣ Once you're done and verified, our team will contact you to bring you into the VIP Group.\n\n"
                "(As always, this is NOT financial advice and past profits do not guarantee future results)\n\n"
                "**👇 Tap below to start now!**"
            ),
            color=discord.Color.gold()
        )
        
        # Create the JOIN FREE button
        class CTAView(discord.ui.View):
            def __init__(self, vip_upgrade_channel_id: int):
                super().__init__(timeout=None)
                self.vip_upgrade_channel_id = vip_upgrade_channel_id
            
            @discord.ui.button(label='JOIN FREE', style=discord.ButtonStyle.success, emoji='🚀')
            async def join_free_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                try:
                    # Get the VIP upgrade channel
                    vip_channel = interaction.guild.get_channel(self.vip_upgrade_channel_id)
                    if not vip_channel:
                        await interaction.response.send_message("❌ VIP upgrade channel not found. Please contact support.", ephemeral=True)
                        return
                    
                    # Create embed response
                    response_embed = discord.Embed(
                        title="🎯 VIP Upgrade Started!",
                        description=(
                            f"Great choice! Head over to {vip_channel.mention} to begin your VIP upgrade process.\n\n"
                            "Our team is ready to help you get started with copy trading and access to our premium signals!"
                        ),
                        color=discord.Color.green()
                    )
                    
                    await interaction.response.send_message(embed=response_embed, ephemeral=True)
                    
                except Exception as e:
                    logger.error(f"Error in CTA button click: {e}")
                    await interaction.response.send_message("❌ Something went wrong. Please try again or contact support.", ephemeral=True)
        
        # Send the embed with the button
        view = CTAView(self.VIP_UPGRADE_CHANNEL_ID)
        await channel.send(embed=embed, view=view)

    @tasks.loop(hours=168)  # 168 hours = 1 week
    async def weekly_cta_task(self):
        """Automatically post CTA embed weekly"""
        try:
            if self.FREE_SIGNALS_CHANNEL_ID and self.FREE_SIGNALS_CHANNEL_ID != 0:
                channel = self.bot.get_channel(self.FREE_SIGNALS_CHANNEL_ID)
                if channel:
                    await self.send_cta_embed(channel)
                    logger.info(f"✅ Weekly CTA embed posted to {channel.name}")
                else:
                    logger.warning(f"⚠️ Free signals channel {self.FREE_SIGNALS_CHANNEL_ID} not found")
            else:
                logger.warning("⚠️ FREE_SIGNALS_CHANNEL_ID not configured for weekly CTA task")
        except Exception as e:
            logger.error(f"❌ Error in weekly CTA task: {e}")

    @weekly_cta_task.before_loop
    async def before_weekly_cta_task(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()

    async def cog_unload(self):
        """Cancel tasks when cog is unloaded"""
        self.weekly_cta_task.cancel()

async def setup(bot):
    await bot.add_cog(EmbedManagement(bot))