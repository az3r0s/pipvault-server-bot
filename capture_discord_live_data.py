#!/usr/bin/env python3
"""
Capture Live Discord Data
========================

This script simulates what the Discord bot does when it runs /list_staff_invites
to capture the real invite tracking data from Discord's API
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.cloud_database import CloudAPIServerDatabase

async def capture_discord_live_data():
    print("=" * 80)
    print("📡 CAPTURING LIVE DISCORD DATA")
    print("=" * 80)
    
    db = CloudAPIServerDatabase()
    
    # Get staff configuration
    staff_config = db.load_staff_config()
    staff_members = staff_config.get('staff_members', {})
    
    print(f"👥 Found {len(staff_members)} staff members in config")
    
    live_data = {
        "capture_timestamp": datetime.now().isoformat(),
        "capture_method": "simulated_discord_api",
        "staff_members": {},
        "invite_codes_found": {},
        "live_invite_data": {},
        "missing_data_explanation": ""
    }
    
    print("\n🔍 Analyzing why live data is missing...")
    
    # The key issue: Discord invite codes are not in the staff config
    print("❌ PROBLEM IDENTIFIED:")
    print("   • Staff config has Discord IDs and usernames")
    print("   • Staff config has Vantage referral links")
    print("   • Staff config does NOT have Discord invite codes")
    print("   • Without invite codes, we can't track Discord invites")
    
    # Extract what we do have
    for name, staff_info in staff_members.items():
        staff_id = str(staff_info.get('discord_id', ''))
        live_data['staff_members'][staff_id] = {
            "name": name,
            "discord_id": staff_info.get('discord_id'),
            "username": staff_info.get('username'),
            "vantage_referral_link": staff_info.get('vantage_referral_link'),
            "vantage_ib_code": staff_info.get('vantage_ib_code'),
            "discord_invite_code": "MISSING",
            "live_invite_stats": "CANNOT_ACCESS_WITHOUT_INVITE_CODE"
        }
    
    # Explain the data gap
    live_data['missing_data_explanation'] = """
    EXPLANATION OF MISSING LIVE DATA:
    
    The Discord bot shows real invite statistics when running because it:
    1. Connects to Discord's live API
    2. Fetches current invite codes for each staff member
    3. Calculates invite usage in real-time
    4. Displays current statistics
    
    Our backup scripts can't access this data because:
    1. The invite codes are not stored in the local database
    2. The invite codes are not in the staff configuration
    3. The Discord API connection requires the bot to be running
    4. Live Discord data is not persisted locally
    
    TO GET THE REAL DATA:
    1. Use Discord's /export_staff_invites command (recommended)
    2. Or run the bot and capture data while it's connected to Discord
    3. Or add invite codes to the staff configuration manually
    
    WHAT WE CAN BACKUP:
    ✅ Staff member Discord IDs and usernames
    ✅ Vantage referral configuration
    ✅ Email templates and channel configuration
    ✅ Database structure (ready for invite data)
    
    WHAT WE CANNOT BACKUP LOCALLY:
    ❌ Live Discord invite statistics
    ❌ Real-time invite usage counts
    ❌ VIP conversion rates from live data
    ❌ Current member invite relationships
    """
    
    # Save the analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"discord_live_data_analysis_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(live_data, f, indent=2, default=str)
    
    print(f"\n📊 LIVE DATA ANALYSIS SUMMARY:")
    print(f"✅ Staff configuration: {len(staff_members)} members")
    print(f"✅ Vantage integration: Complete")
    print(f"❌ Discord invite codes: Missing")
    print(f"❌ Live invite statistics: Not accessible")
    
    print(f"\n👥 STAFF MEMBERS FOUND:")
    for name, staff_info in staff_members.items():
        print(f"  • {name} ({staff_info['username']}): ID {staff_info['discord_id']}")
    
    print(f"\n💾 Analysis saved to: {filename}")
    
    print(f"\n🎯 RECOMMENDATION:")
    print(f"Since local scripts cannot access live Discord data,")
    print(f"use Discord's built-in /export_staff_invites command")
    print(f"to get the complete production backup with real statistics.")
    
    # Also create a minimal backup of what we CAN save
    minimal_backup = {
        "backup_timestamp": datetime.now().isoformat(),
        "backup_type": "staff_configuration_only",
        "staff_members": staff_members,
        "config_data": staff_config,
        "note": "This backup contains staff configuration but not live Discord invite data"
    }
    
    minimal_filename = f"staff_config_backup_{timestamp}.json"
    with open(minimal_filename, 'w') as f:
        json.dump(minimal_backup, f, indent=2, default=str)
    
    print(f"💾 Staff configuration backup: {minimal_filename}")
    
    return live_data

if __name__ == "__main__":
    asyncio.run(capture_discord_live_data())