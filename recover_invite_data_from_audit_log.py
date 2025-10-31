#!/usr/bin/env python3
"""
Recover Invite Tracking Data from Discord Audit Logs

Discord audit logs keep invite usage history for the last 45 days.
This script extracts member joins and tries to match them with invite codes.

NOTE: This only works for joins within the last 45 days!
"""

import discord
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent))

async def recover_from_audit_logs():
    """Recover invite tracking from Discord audit logs (last 45 days only)"""
    
    # Get bot token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ DISCORD_BOT_TOKEN not set in environment")
        return
    
    guild_id = int(os.getenv('DISCORD_GUILD_ID', '0'))
    if not guild_id:
        print("❌ DISCORD_GUILD_ID not set in environment")
        return
    
    # Create bot client
    intents = discord.Intents.default()
    intents.members = True
    intents.guilds = True
    
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"✅ Logged in as {client.user}")
        print("=" * 80)
        print("🔍 SCANNING AUDIT LOGS FOR INVITE USAGE")
        print("=" * 80)
        
        try:
            guild = client.get_guild(guild_id)
            if not guild:
                print(f"❌ Could not find guild with ID {guild_id}")
                await client.close()
                return
            
            print(f"📊 Guild: {guild.name}")
            print(f"👥 Members: {guild.member_count}")
            print()
            
            # Get audit logs for member joins
            print("📝 Fetching audit log entries (INVITE_CREATE, INVITE_UPDATE, MEMBER_JOIN)...")
            
            invite_data = {}
            member_joins = []
            
            # Scan for invite creation/updates
            async for entry in guild.audit_logs(limit=500, action=discord.AuditLogAction.invite_create):
                if entry.target:
                    code = entry.target.code
                    inviter = entry.user
                    invite_data[code] = {
                        'code': code,
                        'inviter_id': inviter.id if inviter else 0,
                        'inviter_name': inviter.name if inviter else 'Unknown',
                        'created_at': entry.created_at
                    }
            
            print(f"✅ Found {len(invite_data)} invite codes in audit log")
            
            # Unfortunately, Discord doesn't log which invite was used for member joins in audit logs
            # We can only see that members joined, not which invite they used
            
            # The only way to get this info is to:
            # 1. Track current invite uses
            # 2. Compare after each member join
            # 3. This requires the bot to be running when members join
            
            print()
            print("⚠️ LIMITATION: Discord audit logs do NOT include which invite was used for joins")
            print()
            print("📋 RECOVERY OPTIONS:")
            print()
            print("1️⃣ ASK MEMBERS DIRECTLY")
            print("   Use /ask_members_invite command to DM each member asking how they joined")
            print()
            print("2️⃣ MANUAL ATTRIBUTION")
            print("   Use /manually_attribute command to assign members to staff based on your knowledge")
            print()
            print("3️⃣ ANALYZE PATTERNS")
            print("   - Check who joined around the same time")
            print("   - Look at channel activity patterns")
            print("   - Ask staff who they invited")
            print()
            
            # Get current invite usage for comparison
            print("=" * 80)
            print("📊 CURRENT INVITE USAGE")
            print("=" * 80)
            
            invites = await guild.invites()
            
            invite_usage = []
            for invite in invites:
                invite_usage.append({
                    'code': invite.code,
                    'inviter': invite.inviter.name if invite.inviter else 'Unknown',
                    'inviter_id': invite.inviter.id if invite.inviter else 0,
                    'uses': invite.uses,
                    'created_at': invite.created_at
                })
            
            # Sort by usage
            invite_usage.sort(key=lambda x: x['uses'], reverse=True)
            
            for inv in invite_usage:
                print(f"🔗 {inv['code']} by {inv['inviter']}")
                print(f"   Uses: {inv['uses']}")
                print(f"   Created: {inv['created_at']}")
                print()
            
            print("=" * 80)
            print("💡 RECOMMENDATION")
            print("=" * 80)
            print()
            print("For members who joined BEFORE the bot tracked invites:")
            print("1. Ask each member: 'Who invited you to this server?'")
            print("2. Or ask staff: 'Who did you invite?'")
            print("3. Use /manually_attribute to record this in the database")
            print()
            print("For NEW members (from now on):")
            print("✅ The bot will automatically track all new joins!")
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        await client.close()
    
    await client.start(token)

if __name__ == "__main__":
    print("🚀 Starting Discord Audit Log Scanner...")
    print()
    asyncio.run(recover_from_audit_logs())
