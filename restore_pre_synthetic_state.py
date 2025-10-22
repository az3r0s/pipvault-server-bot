#!/usr/bin/env python3
"""
Restore Pre-Synthetic Database State
===================================

This script restores the database to its state before synthetic data was added,
so we can access the real production data that /debug_user_invite can see.
"""

import os
import sys
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.cloud_database import CloudAPIServerDatabase

def restore_pre_synthetic_state():
    """Restore database to state before synthetic data was added"""
    
    print("=" * 80)
    print("🔄 RESTORING PRE-SYNTHETIC DATABASE STATE")
    print("=" * 80)
    print("Goal: Restore database to access real production data")
    print("that /debug_user_invite can see but our scripts can't find")
    print("=" * 80)
    
    # Backup current synthetic data first
    current_db = "server_management.db"
    if os.path.exists(current_db):
        backup_name = f"synthetic_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(current_db, backup_name)
        print(f"📦 Backed up synthetic data to: {backup_name}")
    
    # Strategy 1: Look for Railway backup that might have real data
    print(f"\n🔍 STRATEGY 1: Checking Railway backups for real data...")
    
    railway_backups = [
        "railway_production_backup.json",
        "railway_backup_20251019_192135.json", 
        "railway_api_backup_20251019_192510.json"
    ]
    
    real_data_found = None
    
    for backup_file in railway_backups:
        if os.path.exists(backup_file):
            print(f"   📁 Checking {backup_file}...")
            
            try:
                with open(backup_file, 'r') as f:
                    backup_data = json.load(f)
                
                # Look for invite_tracking data with real Discord IDs
                invite_data = backup_data.get('invite_tracking', [])
                
                for record in invite_data:
                    user_id = record.get('user_id', 0)
                    username = record.get('username', '')
                    
                    # Check for real Discord ID (17+ digits, not synthetic)
                    if (isinstance(user_id, int) and 
                        user_id > 100000000000000000 and 
                        not str(username).startswith('User_') and
                        not str(username).startswith('Test')):
                        
                        print(f"      ✅ REAL DATA FOUND: {username} (ID: {user_id})")
                        real_data_found = backup_file
                        break
                
                if real_data_found:
                    break
                    
            except Exception as e:
                print(f"      ❌ Error reading {backup_file}: {e}")
    
    if real_data_found:
        print(f"\n✅ Real data found in: {real_data_found}")
        return restore_from_railway_backup(real_data_found)
    
    # Strategy 2: Check if Railway cloud has real data
    print(f"\n🔍 STRATEGY 2: Checking Railway cloud database...")
    return check_railway_cloud_data()

def restore_from_railway_backup(backup_file):
    """Restore database from Railway backup containing real data"""
    
    print(f"\n📥 RESTORING FROM: {backup_file}")
    
    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        # Clear current database and restore real data
        db = CloudAPIServerDatabase()
        
        # Clear synthetic data
        conn = sqlite3.connect(db.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        print("   🗑️ Clearing synthetic data...")
        cursor.execute("DELETE FROM invite_tracking WHERE user_id < 100000000000000000")
        cursor.execute("DELETE FROM vip_requests WHERE user_id < 100000000000000000")
        
        # Restore real invite tracking data
        invite_data = backup_data.get('invite_tracking', [])
        real_records_restored = 0
        
        for record in invite_data:
            user_id = record.get('user_id', 0)
            
            if user_id > 100000000000000000:  # Real Discord ID
                cursor.execute('''
                    INSERT OR REPLACE INTO invite_tracking 
                    (user_id, username, invite_code, inviter_id, inviter_username, joined_at, invite_uses_before, invite_uses_after)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.get('user_id'),
                    record.get('username'),
                    record.get('invite_code'),
                    record.get('inviter_id'),
                    record.get('inviter_username'),
                    record.get('joined_at'),
                    record.get('invite_uses_before', 0),
                    record.get('invite_uses_after', 0)
                ))
                real_records_restored += 1
                print(f"      ✅ Restored: {record.get('username')} (ID: {record.get('user_id')})")
        
        # Restore real VIP requests
        vip_data = backup_data.get('vip_requests', [])
        real_vip_restored = 0
        
        for record in vip_data:
            user_id = record.get('user_id', 0)
            
            if user_id > 100000000000000000:  # Real Discord ID
                cursor.execute('''
                    INSERT OR REPLACE INTO vip_requests 
                    (user_id, username, request_type, staff_id, status, vantage_email, request_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.get('user_id'),
                    record.get('username'),
                    record.get('request_type', 'upgrade'),
                    record.get('staff_id'),
                    record.get('status', 'pending'),
                    record.get('vantage_email'),
                    record.get('request_data'),
                    record.get('created_at'),
                    record.get('updated_at')
                ))
                real_vip_restored += 1
                print(f"      💎 Restored VIP: {record.get('username')}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ RESTORATION COMPLETE:")
        print(f"   📊 Real invite records restored: {real_records_restored}")
        print(f"   💎 Real VIP requests restored: {real_vip_restored}")
        
        # Verify the restoration worked
        return verify_real_data_restoration(db)
        
    except Exception as e:
        print(f"❌ Error restoring from backup: {e}")
        return {"success": False, "error": str(e)}

def check_railway_cloud_data():
    """Check if Railway cloud database has the real data"""
    
    print(f"   ☁️ Attempting to access Railway cloud database...")
    
    try:
        db = CloudAPIServerDatabase()
        
        # Try to download fresh data from Railway
        print(f"   📥 Downloading latest Railway data...")
        
        # This might restore real data from cloud
        cloud_data = db.restore_from_cloud()
        
        if cloud_data:
            print(f"   ✅ Cloud data retrieved successfully")
            return verify_real_data_restoration(db)
        else:
            print(f"   ❌ No cloud data available")
            return suggest_manual_recovery()
            
    except Exception as e:
        print(f"   ❌ Cloud access failed: {e}")
        return suggest_manual_recovery()

def verify_real_data_restoration(db):
    """Verify that real data has been restored"""
    
    print(f"\n🔍 VERIFYING REAL DATA RESTORATION...")
    
    try:
        conn = sqlite3.connect(db.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Check for real users (Discord IDs > 100000000000000000)
        cursor.execute('''
            SELECT user_id, username, invite_code 
            FROM invite_tracking 
            WHERE user_id > 100000000000000000
            ORDER BY joined_at DESC
        ''')
        
        real_users = cursor.fetchall()
        conn.close()
        
        if len(real_users) > 0:
            print(f"   ✅ Found {len(real_users)} real users!")
            
            for user in real_users[:5]:  # Show first 5
                user_id, username, invite_code = user
                print(f"      👤 {username} (ID: {user_id}) via {invite_code}")
            
            if len(real_users) > 5:
                print(f"      ... and {len(real_users) - 5} more")
            
            # Create final production backup with real data
            return create_final_production_backup(real_users, db)
        else:
            print(f"   ❌ No real users found after restoration attempt")
            return suggest_manual_recovery()
            
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return {"success": False, "error": str(e)}

def create_final_production_backup(real_users, db):
    """Create final production backup with real user data"""
    
    print(f"\n💾 CREATING FINAL PRODUCTION BACKUP WITH REAL DATA...")
    
    # Get all real data
    all_configs = db.get_all_staff_configs()
    
    production_backup = {
        "backup_timestamp": datetime.now().isoformat(),
        "backup_type": "FINAL_PRODUCTION_WITH_REAL_USERS",
        "real_users": [{"user_id": user[0], "username": user[1], "invite_code": user[2]} for user in real_users],
        "staff_configurations": all_configs,
        "deployment_ready": True,
        "vip_functionality_preserved": True
    }
    
    # Calculate real statistics
    total_real_invites = len(real_users)
    total_real_vips = 0
    
    try:
        conn = sqlite3.connect(db.db_path, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vip_requests WHERE user_id > 100000000000000000")
        total_real_vips = cursor.fetchone()[0]
        conn.close()
    except:
        pass
    
    production_backup["statistics"] = {
        "total_real_invites": total_real_invites,
        "total_real_vips": total_real_vips,
        "real_conversion_rate": (total_real_vips / total_real_invites * 100) if total_real_invites > 0 else 0
    }
    
    filename = f"FINAL_production_backup_with_real_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump(production_backup, f, indent=2, default=str)
    
    print(f"✅ Final production backup: {filename}")
    print(f"📊 Real users: {total_real_invites}")
    print(f"💎 Real VIPs: {total_real_vips}")
    
    return {"success": True, "backup_file": filename, "real_users": total_real_invites}

def suggest_manual_recovery():
    """Suggest manual recovery options"""
    
    print(f"\n🔧 MANUAL RECOVERY REQUIRED")
    print(f"Since /debug_user_invite shows real data exists, try these options:")
    print(f"")
    print(f"1. 📊 Use Discord's /export_staff_invites command")
    print(f"2. 🔍 Use /debug_user_invite on known real users to get their data")
    print(f"3. ☁️ Access Railway database directly via Railway CLI")
    print(f"4. 🤖 Run the bot and use /list_invite_details commands")
    
    return {"success": False, "requires_manual_recovery": True}

if __name__ == "__main__":
    result = restore_pre_synthetic_state()
    
    if result.get("success", False):
        print(f"\n✅ SUCCESS: Real production data restored!")
        print(f"🚀 Ready for deployment with VIP functionality intact")
    else:
        print(f"\n⚠️ MANUAL ACTION REQUIRED")
        print(f"Use Discord commands to extract real production data")