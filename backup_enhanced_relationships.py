#!/usr/bin/env python3
"""
Enhanced Production Data Backup with Full Relationships
======================================================

This script captures all invite relationships, VIP conversions, and member tracking data
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

def backup_with_relationships():
    print("=" * 80)
    print("🔗 ENHANCED BACKUP - FULL RELATIONSHIPS & TRACKING")
    print("=" * 80)
    
    # Initialize database connection
    db = CloudAPIServerDatabase()
    
    backup_data = {
        "backup_timestamp": datetime.now().isoformat(),
        "backup_type": "enhanced_with_relationships",
        "staff_members": {},
        "invite_relationships": [],
        "vip_conversions": [],
        "member_tracking": [],
        "raw_database_data": {}
    }
    
    print("👥 Gathering staff member data...")
    
    # Get staff configuration
    staff_config = db.load_staff_config()
    print(f"  🔍 Staff config type: {type(staff_config)}")
    print(f"  📋 Staff config keys: {list(staff_config.keys()) if isinstance(staff_config, dict) else 'Not a dict'}")
    
    if staff_config:
        # Handle different possible data structures
        if isinstance(staff_config, dict):
            if 'staff_members' in staff_config:
                staff_list = staff_config['staff_members']
            else:
                # Maybe the config is the staff list directly
                staff_list = staff_config
        else:
            staff_list = staff_config
            
        print(f"  📊 Processing staff list: {type(staff_list)}")
        
        if isinstance(staff_list, list):
            for staff_entry in staff_list:
                if isinstance(staff_entry, dict):
                    staff_id = str(staff_entry.get('discord_id', ''))
                    backup_data['staff_members'][staff_id] = {
                        "discord_id": staff_entry.get('discord_id'),
                        "username": staff_entry.get('username'),
                        "invite_code": staff_entry.get('invite_code'),
                        "email_template": staff_entry.get('email_template', ''),
                        "total_invites": 0,
                        "vip_converts": 0,
                        "invite_rate": 0.0,
                        "invited_members": []
                    }
                else:
                    print(f"    ⚠️ Unexpected staff entry type: {type(staff_entry)}: {staff_entry}")
        elif isinstance(staff_list, dict):
            # Handle case where it's a dict of staff data
            for key, staff_entry in staff_list.items():
                if isinstance(staff_entry, dict) and 'discord_id' in staff_entry:
                    staff_id = str(staff_entry.get('discord_id', ''))
                    backup_data['staff_members'][staff_id] = {
                        "discord_id": staff_entry.get('discord_id'),
                        "username": staff_entry.get('username'),
                        "invite_code": staff_entry.get('invite_code'),
                        "email_template": staff_entry.get('email_template', ''),
                        "total_invites": 0,
                        "vip_converts": 0,
                        "invite_rate": 0.0,
                        "invited_members": []
                    }
                else:
                    print(f"    ℹ️ Config entry {key}: {staff_entry}")
        
        print(f"  ✅ Found {len(backup_data['staff_members'])} staff members")
    else:
        print("  ⚠️ No staff configuration found")
    
    # Get database relationships
    print("🔗 Gathering invite tracking relationships...")
    
    try:
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all invite tracking data
        cursor.execute('SELECT * FROM invite_tracking')
        invite_records = [dict(row) for row in cursor.fetchall()]
        
        print(f"  📊 Found {len(invite_records)} invite tracking records")
        
        for record in invite_records:
            user_id = str(record.get('user_id', ''))
            inviter_id = str(record.get('inviter_id', ''))
            invite_code = record.get('invite_code', '')
            
            # Add to relationships
            relationship = {
                "invited_user_id": user_id,
                "invited_username": record.get('username', ''),
                "inviter_id": inviter_id,
                "inviter_username": record.get('inviter_username', ''),
                "invite_code": invite_code,
                "joined_at": record.get('joined_at', ''),
                "invite_uses_before": record.get('invite_uses_before', 0),
                "invite_uses_after": record.get('invite_uses_after', 0)
            }
            backup_data['invite_relationships'].append(relationship)
            
            # Update staff member data
            if inviter_id in backup_data['staff_members']:
                backup_data['staff_members'][inviter_id]['total_invites'] += 1
                backup_data['staff_members'][inviter_id]['invited_members'].append({
                    "user_id": user_id,
                    "username": record.get('username', ''),
                    "joined_at": record.get('joined_at', ''),
                    "is_vip": False  # Will be updated below
                })
        
        # Get VIP request data
        cursor.execute('SELECT * FROM vip_requests')
        vip_records = [dict(row) for row in cursor.fetchall()]
        
        print(f"  🌟 Found {len(vip_records)} VIP requests")
        
        for vip_record in vip_records:
            user_id = str(vip_record.get('user_id', ''))
            staff_id = str(vip_record.get('staff_id', ''))
            
            vip_conversion = {
                "user_id": user_id,
                "username": vip_record.get('username', ''),
                "staff_id": staff_id,
                "request_type": vip_record.get('request_type', ''),
                "status": vip_record.get('status', ''),
                "vantage_email": vip_record.get('vantage_email', ''),
                "created_at": vip_record.get('created_at', ''),
                "updated_at": vip_record.get('updated_at', '')
            }
            backup_data['vip_conversions'].append(vip_conversion)
            
            # Update staff VIP count
            if staff_id in backup_data['staff_members']:
                if vip_record.get('status') in ['approved', 'completed']:
                    backup_data['staff_members'][staff_id]['vip_converts'] += 1
                
                # Mark member as VIP in invited_members list
                for member in backup_data['staff_members'][staff_id]['invited_members']:
                    if member['user_id'] == user_id:
                        member['is_vip'] = True
                        member['vip_status'] = vip_record.get('status', '')
        
        # Calculate conversion rates
        for staff_id, staff_data in backup_data['staff_members'].items():
            if staff_data['total_invites'] > 0:
                staff_data['invite_rate'] = (staff_data['vip_converts'] / staff_data['total_invites']) * 100
        
        # Get all raw table data for backup
        tables = ['staff_invites', 'invite_tracking', 'vip_requests', 'onboarding_progress', 'onboarding_analytics']
        for table in tables:
            try:
                cursor.execute(f'SELECT * FROM {table}')
                rows = [dict(row) for row in cursor.fetchall()]
                backup_data['raw_database_data'][table] = rows
            except sqlite3.OperationalError:
                backup_data['raw_database_data'][table] = []
        
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Error reading database: {e}")
    
    # Get additional data from CloudAPI methods
    print("🔍 Getting additional staff data...")
    
    try:
        # Get staff invite status
        invite_status = db.get_staff_invite_status()
        if invite_status:
            backup_data['staff_invite_status'] = invite_status
            print(f"  ✅ Staff invite status: {len(invite_status)} entries")
        
        # Get debug info
        debug_info = db.debug_staff_invites_table()
        if debug_info:
            backup_data['debug_staff_info'] = debug_info
            print(f"  ✅ Debug staff info captured")
            
    except Exception as e:
        print(f"  ⚠️ CloudAPI methods failed: {e}")
    
    # Calculate totals
    total_invites = sum(staff['total_invites'] for staff in backup_data['staff_members'].values())
    total_vips = sum(staff['vip_converts'] for staff in backup_data['staff_members'].values())
    total_members = len(backup_data['staff_members'])
    
    backup_data['summary'] = {
        "total_staff_members": total_members,
        "total_invites_tracked": total_invites,
        "total_vip_conversions": total_vips,
        "overall_vip_rate": (total_vips / total_invites * 100) if total_invites > 0 else 0
    }
    
    # Save enhanced backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"enhanced_relationships_backup_{timestamp}.json"
    
    with open(backup_filename, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)
    
    # Print summary
    print(f"\n📊 ENHANCED BACKUP SUMMARY:")
    print(f"✅ Staff members: {total_members}")
    print(f"✅ Total invites tracked: {total_invites}")
    print(f"✅ VIP conversions: {total_vips}")
    print(f"✅ Overall VIP rate: {backup_data['summary']['overall_vip_rate']:.1f}%")
    
    print(f"\n👥 STAFF PERFORMANCE:")
    for staff_id, staff_data in backup_data['staff_members'].items():
        if staff_data['total_invites'] > 0:
            print(f"  • {staff_data['username']}: {staff_data['total_invites']} invites, {staff_data['vip_converts']} VIPs ({staff_data['invite_rate']:.1f}%)")
    
    print(f"\n💾 Enhanced backup saved to: {backup_filename}")
    print(f"🔗 Includes full relationship tracking and member details")
    
    return backup_data

if __name__ == "__main__":
    backup_with_relationships()