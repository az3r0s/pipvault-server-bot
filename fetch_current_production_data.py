#!/usr/bin/env python3
"""
Fetch Current Production Data from Railway
==========================================

This script fetches the current, up-to-date production data from Railway
to get real user relationships for VIP functionality.
"""

import os
import sys
import json
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.cloud_database import CloudAPIServerDatabase

async def fetch_current_production_data():
    """Fetch current production data from Railway cloud"""
    
    print("=" * 80)
    print("📡 FETCHING CURRENT PRODUCTION DATA FROM RAILWAY")
    print("=" * 80)
    print("Getting live, up-to-date user relationships and VIP data")
    print("=" * 80)
    
    db = CloudAPIServerDatabase()
    
    print("🔄 Step 1: Connecting to Railway cloud database...")
    
    try:
        # Use the proper async method to get cloud data
        print("   📥 Downloading current data from Railway...")
        cloud_data = await db.backup_to_cloud()
        
        if not cloud_data:
            print("   ❌ No data returned from Railway")
            return try_alternative_method()
        
        print("   ✅ Successfully connected to Railway")
        
        # Parse the cloud data
        if isinstance(cloud_data, dict) and 'data' in cloud_data:
            production_data = cloud_data['data']
        else:
            production_data = cloud_data
        
        print(f"🔍 Step 2: Analyzing current production data...")
        
        # Extract invite tracking data
        invite_data = production_data.get('invite_tracking', [])
        vip_data = production_data.get('vip_requests', [])
        staff_data = production_data.get('staff_invites', [])
        
        print(f"   📊 Invite tracking records: {len(invite_data)}")
        print(f"   💎 VIP request records: {len(vip_data)}")
        print(f"   👥 Staff invite configs: {len(staff_data)}")
        
        # Filter for real users (not synthetic)
        real_users = []
        real_vips = []
        
        for record in invite_data:
            user_id = record.get('user_id', 0)
            username = record.get('username', '')
            
            # Real Discord IDs are 17-19 digits and don't start with synthetic patterns
            if (isinstance(user_id, int) and 
                user_id > 100000000000000000 and 
                not str(username).startswith('User_') and
                not str(username).startswith('Test')):
                real_users.append(record)
                print(f"   ✅ Real user: {username} (ID: {user_id}) via {record.get('invite_code', 'unknown')}")
        
        for record in vip_data:
            user_id = record.get('user_id', 0)
            username = record.get('username', '')
            
            if (isinstance(user_id, int) and 
                user_id > 100000000000000000 and 
                not str(username).startswith('User_') and
                not str(username).startswith('Test')):
                real_vips.append(record)
                print(f"   💎 Real VIP: {username} (ID: {user_id}) - Status: {record.get('status', 'unknown')}")
        
        print(f"\n📊 CURRENT PRODUCTION SUMMARY:")
        print(f"   👥 Real users found: {len(real_users)}")
        print(f"   💎 Real VIP requests: {len(real_vips)}")
        
        if len(real_users) == 0:
            print(f"\n⚠️  No real users found in current production data!")
            print(f"   This could mean:")
            print(f"   1. Production database was overwritten with synthetic data")
            print(f"   2. Real users exist but are stored differently")
            print(f"   3. Need to access a different Railway database/table")
            return try_alternative_method()
        
        # Save current production data
        return save_current_production_data(real_users, real_vips, staff_data)
        
    except Exception as e:
        print(f"   ❌ Error fetching from Railway: {e}")
        return try_alternative_method()

def try_alternative_method():
    """Try alternative methods to get production data"""
    
    print(f"\n🔄 TRYING ALTERNATIVE METHODS...")
    
    print(f"\n1️⃣ Method: Direct Railway API Call")
    try:
        # Try direct API call to Railway
        import requests
        
        # Check if we have Railway API URL
        cloud_url = os.getenv('CLOUD_API_URL', 'https://web-production-1299f.up.railway.app')
        
        print(f"   📡 Trying direct API call to: {cloud_url}")
        
        # Try to get data directly from Railway API
        response = requests.get(f"{cloud_url}/api/backup", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Got response from Railway API")
            
            # Process the data
            invite_data = data.get('invite_tracking', [])
            real_users = [r for r in invite_data if r.get('user_id', 0) > 100000000000000000]
            
            if len(real_users) > 0:
                print(f"   🎯 Found {len(real_users)} real users via API!")
                return {"success": True, "method": "railway_api", "real_users": real_users}
            else:
                print(f"   ❌ No real users in API response")
        else:
            print(f"   ❌ API call failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ API method failed: {e}")
    
    print(f"\n2️⃣ Method: Railway CLI Database Export")
    print(f"   To get the current production data, you can:")
    print(f"   1. Install Railway CLI: npm install -g @railway/cli")
    print(f"   2. Login: railway login") 
    print(f"   3. Export database: railway connect [your-service]")
    print(f"   4. Run database export commands")
    
    print(f"\n3️⃣ Method: Discord Bot Commands")
    print(f"   Use your Discord bot to export current data:")
    print(f"   • /export_staff_invites")
    print(f"   • /list_invite_details for each staff member")
    print(f"   • /debug_user_invite for known users")
    
    return {"success": False, "requires_manual_action": True}

def save_current_production_data(real_users, real_vips, staff_data):
    """Save the current production data"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    production_backup = {
        "backup_timestamp": datetime.now().isoformat(),
        "backup_type": "current_production_data_from_railway",
        "source": "live_railway_database",
        "real_invite_tracking": real_users,
        "real_vip_requests": real_vips,
        "staff_configurations": staff_data,
        "statistics": {
            "total_real_users": len(real_users),
            "total_real_vips": len(real_vips),
            "total_staff_configs": len(staff_data)
        },
        "deployment_status": {
            "has_real_user_data": len(real_users) > 0,
            "vip_functionality_preserved": len(real_users) > 0,
            "safe_for_deployment": len(real_users) > 0
        }
    }
    
    # Calculate stats by staff member
    staff_stats = {}
    for user in real_users:
        invite_code = user.get('invite_code', 'unknown')
        if invite_code not in staff_stats:
            staff_stats[invite_code] = {"invites": 0, "vips": 0}
        staff_stats[invite_code]["invites"] += 1
    
    for vip in real_vips:
        # Find invite code for this user
        user_id = vip.get('user_id')
        for user in real_users:
            if user.get('user_id') == user_id:
                invite_code = user.get('invite_code', 'unknown')
                if invite_code in staff_stats:
                    staff_stats[invite_code]["vips"] += 1
                break
    
    production_backup["staff_statistics"] = staff_stats
    
    filename = f"current_production_backup_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(production_backup, f, indent=2, default=str)
    
    print(f"\n💾 CURRENT PRODUCTION DATA SAVED: {filename}")
    
    # Show summary
    print(f"\n📊 PRODUCTION DATA SUMMARY:")
    for invite_code, stats in staff_stats.items():
        conversion_rate = (stats["vips"] / stats["invites"] * 100) if stats["invites"] > 0 else 0
        print(f"   🔗 {invite_code}: {stats['invites']} invites, {stats['vips']} VIPs ({conversion_rate:.1f}%)")
    
    return {
        "success": True,
        "backup_file": filename,
        "real_users": len(real_users),
        "deployment_ready": len(real_users) > 0
    }

async def main():
    """Main async function"""
    result = await fetch_current_production_data()
    
    if result.get("success", False):
        print(f"\n✅ SUCCESS: Current production data fetched!")
        print(f"🚀 Ready for deployment with real user data")
    else:
        print(f"\n⚠️ MANUAL ACTION REQUIRED")
        print(f"Use Discord bot commands or Railway CLI to get current data")

if __name__ == "__main__":
    asyncio.run(main())