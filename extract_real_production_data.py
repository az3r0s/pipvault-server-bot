#!/usr/bin/env python3
"""
Extract Real Production User Data
================================

This script attempts to extract real Discord user IDs and relationships
from the production system to ensure VIP functionality works correctly.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.cloud_database import CloudAPIServerDatabase

def extract_real_production_data():
    """Extract real production data to avoid breaking VIP functionality"""
    
    print("=" * 80)
    print("🚨 EXTRACTING REAL PRODUCTION USER DATA")
    print("=" * 80)
    print("CRITICAL: VIP functionality requires real Discord user IDs")
    print("Synthetic IDs will break VIP role assignment and staff attribution")
    print("=" * 80)
    
    db = CloudAPIServerDatabase()
    
    print("🔍 SEARCHING FOR REAL USER DATA SOURCES...")
    
    # Strategy 1: Check if there's a production database backup
    print("\n1️⃣ Checking for production database backups...")
    backup_files = [f for f in os.listdir('.') if 'backup' in f.lower() and f.endswith('.json')]
    
    real_users_found = []
    real_vip_requests_found = []
    
    for backup_file in backup_files:
        print(f"   📁 Checking {backup_file}")
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Look for real invite tracking data
            invite_data = backup_data.get('database_data', {}).get('invite_tracking', [])
            vip_data = backup_data.get('database_data', {}).get('vip_requests', [])
            
            # Filter out obvious test data
            for record in invite_data:
                user_id = record.get('user_id', 0)
                username = record.get('username', '')
                
                # Skip synthetic test data
                if (isinstance(user_id, int) and user_id > 100000000000000000 and  # Real Discord IDs are 17-19 digits
                    not username.startswith('User_') and 
                    not username.startswith('Test')):
                    real_users_found.append(record)
                    print(f"      ✅ Real user found: {username} (ID: {user_id})")
            
            for record in vip_data:
                user_id = record.get('user_id', 0)
                username = record.get('username', '')
                
                if (isinstance(user_id, int) and user_id > 100000000000000000 and
                    not username.startswith('User_') and 
                    not username.startswith('Test')):
                    real_vip_requests_found.append(record)
                    print(f"      ✅ Real VIP request: {username} (ID: {user_id})")
                    
        except Exception as e:
            print(f"      ❌ Error reading {backup_file}: {e}")
    
    print(f"\n📊 REAL DATA DISCOVERY RESULTS:")
    print(f"   👥 Real users found: {len(real_users_found)}")
    print(f"   💎 Real VIP requests found: {len(real_vip_requests_found)}")
    
    if not real_users_found and not real_vip_requests_found:
        print(f"\n🚨 CRITICAL PROBLEM:")
        print(f"   No real production user data found in any backup files!")
        print(f"   This means either:")
        print(f"   1. Production system has no real user data (only test data)")
        print(f"   2. Real data exists but isn't captured in backups")
        print(f"   3. Real data is stored differently than expected")
        
        print(f"\n🔍 ALTERNATIVE DATA SOURCES TO CHECK:")
        print(f"   1. Live Discord server member list")
        print(f"   2. Discord bot commands: /export_staff_invites")
        print(f"   3. Production server direct database access")
        print(f"   4. Discord API guild member enumeration")
        print(f"   5. Manual data collection from Discord UI")
        
        return suggest_data_collection_strategy()
    
    # If we found real data, process it
    print(f"\n✅ REAL DATA FOUND - Processing...")
    return process_real_data(real_users_found, real_vip_requests_found)

def suggest_data_collection_strategy():
    """Suggest how to collect real production data"""
    
    print(f"\n🎯 DATA COLLECTION STRATEGY:")
    print(f"\nSince VIP functionality REQUIRES real Discord user IDs, you have these options:")
    
    print(f"\n📊 OPTION 1: Discord Bot Export (Recommended)")
    print(f"   Run in your production Discord server:")
    print(f"   • /export_staff_invites")
    print(f"   • /list_invite_details [each staff member]")
    print(f"   • Copy the output and create import script")
    
    print(f"\n🔗 OPTION 2: Live Discord API Connection")
    print(f"   Connect bot to production Discord server:")
    print(f"   • Enumerate guild members")
    print(f"   • Check invite usage for each staff invite")
    print(f"   • Build user relationships from live data")
    
    print(f"\n📋 OPTION 3: Manual Discord Data Collection")
    print(f"   From Discord server UI:")
    print(f"   • Check each staff member's invite link usage")
    print(f"   • List members who joined via each invite")
    print(f"   • Document VIP members and their staff attribution")
    
    print(f"\n⚠️  OPTION 4: Deploy Without Historical Data (RISKY)")
    print(f"   Deploy with synthetic data but:")
    print(f"   • VIP functionality may be broken for existing members")
    print(f"   • Staff attribution for past joins will be lost")
    print(f"   • Only new joins after deployment will work correctly")
    
    print(f"\n🚨 CRITICAL REQUIREMENT:")
    print(f"For VIP upgrade functionality to work, we need:")
    print(f"   ✅ Real Discord user IDs (17-19 digit numbers)")
    print(f"   ✅ Actual usernames matching Discord members")
    print(f"   ✅ Correct staff attribution for each user")
    print(f"   ✅ Accurate VIP status tracking")
    
    return {
        "deployment_safe": False,
        "requires_real_data": True,
        "vip_functionality_at_risk": True,
        "recommended_action": "export_staff_invites_command"
    }

def process_real_data(real_users, real_vip_requests):
    """Process real user data found in backups"""
    
    print(f"Processing {len(real_users)} real users and {len(real_vip_requests)} VIP requests...")
    
    # Create deployment-ready data with real users
    deployment_data = {
        "real_users": real_users,
        "real_vip_requests": real_vip_requests,
        "deployment_safe": True,
        "vip_functionality_preserved": True
    }
    
    # Save real data for deployment
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"real_production_data_for_deployment_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(deployment_data, f, indent=2, default=str)
    
    print(f"✅ Real production data saved: {filename}")
    return deployment_data

if __name__ == "__main__":
    result = extract_real_production_data()
    
    print(f"\n🎯 DEPLOYMENT RECOMMENDATION:")
    if result.get('deployment_safe', False):
        print(f"✅ SAFE TO DEPLOY with real user data")
    else:
        print(f"🚨 NOT SAFE TO DEPLOY - Real user data required first")
        print(f"🔧 Action needed: {result.get('recommended_action', 'collect_real_data')}")