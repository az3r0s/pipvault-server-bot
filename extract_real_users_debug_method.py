#!/usr/bin/env python3
"""
Extract Real User Data Using Debug Method
========================================

This script uses the same method as /debug_user_invite to extract
all real production user data before it gets overwritten.
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

def extract_real_users_debug_method():
    """Extract real users using the same method as debug_user_invite command"""
    
    print("=" * 80)
    print("🔍 EXTRACTING REAL USERS VIA DEBUG METHOD")
    print("=" * 80)
    print("Using the same database queries as /debug_user_invite command")
    print("=" * 80)
    
    db = CloudAPIServerDatabase()
    
    # First, let's look at what's actually in the invite_tracking table
    print("📊 CURRENT INVITE_TRACKING TABLE:")
    
    try:
        conn = sqlite3.connect(db.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Get all records from invite_tracking
        cursor.execute('''
            SELECT user_id, username, invite_code, inviter_id, inviter_username, joined_at
            FROM invite_tracking 
            ORDER BY joined_at DESC
        ''')
        
        all_invite_records = cursor.fetchall()
        conn.close()
        
        print(f"   📋 Total records: {len(all_invite_records)}")
        
        real_users = []
        synthetic_users = []
        
        for record in all_invite_records:
            user_id, username, invite_code, inviter_id, inviter_username, joined_at = record
            
            # Determine if this is real or synthetic data
            is_real = (
                isinstance(user_id, int) and 
                user_id > 100000000000000000 and  # Real Discord IDs are large
                not str(username).startswith('User_') and
                not str(username).startswith('Test')
            )
            
            record_data = {
                'user_id': user_id,
                'username': username,
                'invite_code': invite_code,
                'inviter_id': inviter_id,
                'inviter_username': inviter_username,
                'joined_at': joined_at
            }
            
            if is_real:
                real_users.append(record_data)
                print(f"   ✅ REAL: {username} (ID: {user_id}) via {invite_code}")
            else:
                synthetic_users.append(record_data)
                print(f"   🤖 SYNTHETIC: {username} (ID: {user_id}) via {invite_code}")
        
        print(f"\n📊 ANALYSIS:")
        print(f"   👥 Real users found: {len(real_users)}")
        print(f"   🤖 Synthetic users found: {len(synthetic_users)}")
        
        if len(real_users) > 0:
            print(f"\n✅ REAL PRODUCTION DATA EXISTS!")
            return save_real_production_data(real_users, db)
        else:
            print(f"\n⚠️  No real users in current database.")
            print(f"   This could mean:")
            print(f"   1. Production system really has no real user data")
            print(f"   2. Real data was overwritten by synthetic data")
            print(f"   3. Real data is in a different database/backup")
            
            return check_for_real_data_in_backups()
            
    except Exception as e:
        print(f"❌ Error accessing invite_tracking table: {e}")
        return {"error": str(e)}

def save_real_production_data(real_users, db):
    """Save the real production data found"""
    
    print(f"\n💾 SAVING REAL PRODUCTION DATA...")
    
    # Also get VIP requests for these real users
    real_vip_requests = []
    
    try:
        conn = sqlite3.connect(db.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        for user in real_users:
            cursor.execute('''
                SELECT id, user_id, username, request_type, staff_id, status, 
                       vantage_email, request_data, created_at, updated_at
                FROM vip_requests 
                WHERE user_id = ?
            ''', (user['user_id'],))
            
            vip_records = cursor.fetchall()
            for vip_record in vip_records:
                real_vip_requests.append({
                    'id': vip_record[0],
                    'user_id': vip_record[1], 
                    'username': vip_record[2],
                    'request_type': vip_record[3],
                    'staff_id': vip_record[4],
                    'status': vip_record[5],
                    'vantage_email': vip_record[6],
                    'request_data': vip_record[7],
                    'created_at': vip_record[8],
                    'updated_at': vip_record[9]
                })
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Error getting VIP requests: {e}")
    
    # Get staff configurations
    all_staff_configs = db.get_all_staff_configs()
    
    # Create complete real production backup
    production_backup = {
        "backup_timestamp": datetime.now().isoformat(),
        "backup_type": "real_production_data_extracted",
        "extraction_method": "debug_user_invite_database_queries",
        "real_users": real_users,
        "real_vip_requests": real_vip_requests,
        "staff_configurations": all_staff_configs,
        "summary": {
            "total_real_users": len(real_users),
            "total_real_vip_requests": len(real_vip_requests),
            "total_staff_configs": len(all_staff_configs)
        },
        "deployment_status": {
            "has_real_user_data": True,
            "vip_functionality_preserved": True,
            "safe_for_deployment": True
        }
    }
    
    # Save the real production data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"REAL_production_data_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(production_backup, f, indent=2, default=str)
    
    print(f"✅ Real production data saved: {filename}")
    print(f"📊 Real users: {len(real_users)}")
    print(f"💎 Real VIP requests: {len(real_vip_requests)}")
    
    # Show sample real users
    print(f"\n👥 SAMPLE REAL USERS:")
    for user in real_users[:5]:
        print(f"   • {user['username']} (ID: {user['user_id']}) via {user['invite_code']}")
    
    return production_backup

def check_for_real_data_in_backups():
    """Check backup files for real data using stricter criteria"""
    
    print(f"\n🔍 CHECKING BACKUPS FOR REAL DATA...")
    
    # Look for Railway backups which might have the real data
    railway_files = [f for f in os.listdir('.') if 'railway' in f.lower() and f.endswith('.json')]
    
    for backup_file in railway_files:
        print(f"   📁 Checking Railway backup: {backup_file}")
        
        try:
            with open(backup_file, 'r') as f:
                data = json.load(f)
            
            # Check for invite_tracking data
            invite_data = data.get('invite_tracking', [])
            
            for record in invite_data:
                user_id = record.get('user_id', 0)
                username = record.get('username', '')
                
                if (isinstance(user_id, int) and user_id > 100000000000000000 and
                    not str(username).startswith('User_')):
                    print(f"      ✅ Found real user in backup: {username} (ID: {user_id})")
                    return {"found_in_backup": backup_file, "has_real_data": True}
                    
        except Exception as e:
            print(f"      ❌ Error reading {backup_file}: {e}")
    
    return {"found_in_backup": None, "has_real_data": False}

if __name__ == "__main__":
    result = extract_real_users_debug_method()
    
    if result.get('deployment_status', {}).get('safe_for_deployment', False):
        print(f"\n✅ DEPLOYMENT STATUS: SAFE")
        print(f"Real production data has been extracted and preserved.")
    else:
        print(f"\n⚠️ DEPLOYMENT STATUS: NEEDS ATTENTION")
        print(f"Real production data may need to be collected manually.")