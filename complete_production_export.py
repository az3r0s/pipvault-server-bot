#!/usr/bin/env python3
"""
Complete Production Data Export
==============================

This script uses all available methods to extract the real production data,
including the live invite tracking that Discord shows in /list_staff_invites
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

def complete_production_export():
    print("=" * 80)
    print("📤 COMPLETE PRODUCTION DATA EXPORT")
    print("=" * 80)
    
    db = CloudAPIServerDatabase()
    
    export_data = {
        "export_timestamp": datetime.now().isoformat(),
        "export_type": "complete_production_data",
        "staff_members": {},
        "invite_relationships": [],
        "vip_conversions": [],
        "live_invite_data": {},
        "discord_api_data": {},
        "database_data": {},
        "summary": {}
    }
    
    print("1️⃣ Getting staff configuration...")
    
    # Get staff config
    staff_config = db.load_staff_config()
    if staff_config and 'staff_members' in staff_config:
        staff_list = staff_config['staff_members']
        print(f"   ✅ Found {len(staff_list)} configured staff members")
        
        for discord_id, staff_data in staff_list.items():
            export_data['staff_members'][discord_id] = {
                "discord_id": discord_id,
                "username": staff_data.get('username', 'Unknown'),
                "invite_code": staff_data.get('invite_code', ''),
                "configured": True,
                "live_stats": {
                    "total_invites": 0,
                    "vip_converts": 0,
                    "conversion_rate": 0.0
                },
                "invited_users": []
            }
    
    print("2️⃣ Getting live invite status data...")
    
    # Get the live invite status (this shows the real numbers)
    invite_status = db.get_staff_invite_status()
    if invite_status:
        print(f"   ✅ Found live data for {len(invite_status)} invite codes")
        export_data['live_invite_data'] = invite_status
        
        # Match invite codes to staff members
        for invite_code, status_data in invite_status.items():
            # Find which staff member has this invite code
            for staff_id, staff_info in export_data['staff_members'].items():
                if staff_info['invite_code'] == invite_code:
                    if isinstance(status_data, dict):
                        staff_info['live_stats']['total_invites'] = status_data.get('total_invites', 0)
                        staff_info['live_stats']['vip_converts'] = status_data.get('vip_converts', 0)
                        staff_info['live_stats']['conversion_rate'] = status_data.get('conversion_rate', 0.0)
                        staff_info['username'] = status_data.get('username', staff_info['username'])
                    break
    
    print("3️⃣ Getting database relationships...")
    
    # Get database data
    try:
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get invite tracking
        cursor.execute('SELECT * FROM invite_tracking')
        invite_records = [dict(row) for row in cursor.fetchall()]
        export_data['database_data']['invite_tracking'] = invite_records
        
        for record in invite_records:
            relationship = {
                "invited_user_id": record.get('user_id'),
                "invited_username": record.get('username'),
                "inviter_id": record.get('inviter_id'),
                "inviter_username": record.get('inviter_username'),
                "invite_code": record.get('invite_code'),
                "joined_at": record.get('joined_at'),
                "uses_before": record.get('invite_uses_before'),
                "uses_after": record.get('invite_uses_after')
            }
            export_data['invite_relationships'].append(relationship)
        
        # Get VIP requests
        cursor.execute('SELECT * FROM vip_requests')
        vip_records = [dict(row) for row in cursor.fetchall()]
        export_data['database_data']['vip_requests'] = vip_records
        
        for record in vip_records:
            vip_conversion = {
                "user_id": record.get('user_id'),
                "username": record.get('username'),
                "staff_id": record.get('staff_id'),
                "request_type": record.get('request_type'),
                "status": record.get('status'),
                "vantage_email": record.get('vantage_email'),
                "created_at": record.get('created_at')
            }
            export_data['vip_conversions'].append(vip_conversion)
        
        print(f"   ✅ Database: {len(invite_records)} invite records, {len(vip_records)} VIP records")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
    
    print("4️⃣ Trying Discord API methods...")
    
    # Try to get more data through various methods
    try:
        # Get users by invite code for each staff member
        for staff_id, staff_info in export_data['staff_members'].items():
            invite_code = staff_info['invite_code']
            if invite_code and hasattr(db, 'get_users_by_invite_code'):
                try:
                    users = db.get_users_by_invite_code(invite_code)
                    if users:
                        staff_info['invited_users'] = users
                        print(f"   ✅ Found {len(users)} users for {staff_info['username']}")
                except Exception as e:
                    print(f"   ⚠️ Could not get users for {invite_code}: {e}")
        
        # Get debug info
        debug_info = db.debug_staff_invites_table()
        if debug_info:
            export_data['discord_api_data']['debug_info'] = debug_info
            
    except Exception as e:
        print(f"   ⚠️ API methods failed: {e}")
    
    print("5️⃣ Calculating summary...")
    
    # Calculate totals from live data
    total_live_invites = sum(
        staff['live_stats']['total_invites'] 
        for staff in export_data['staff_members'].values()
    )
    total_live_vips = sum(
        staff['live_stats']['vip_converts'] 
        for staff in export_data['staff_members'].values()
    )
    
    export_data['summary'] = {
        "total_staff_configured": len(export_data['staff_members']),
        "total_live_invites": total_live_invites,
        "total_live_vips": total_live_vips,
        "live_conversion_rate": (total_live_vips / total_live_invites * 100) if total_live_invites > 0 else 0,
        "database_invite_records": len(export_data['invite_relationships']),
        "database_vip_records": len(export_data['vip_conversions'])
    }
    
    # Save export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"complete_production_export_{timestamp}.json"
    
    with open(export_filename, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    # Print detailed summary
    print(f"\n📊 COMPLETE EXPORT SUMMARY:")
    print(f"✅ Staff members configured: {export_data['summary']['total_staff_configured']}")
    print(f"📈 Live invite data: {total_live_invites} invites, {total_live_vips} VIPs ({export_data['summary']['live_conversion_rate']:.1f}%)")
    print(f"💾 Database records: {len(export_data['invite_relationships'])} invites, {len(export_data['vip_conversions'])} VIPs")
    
    print(f"\n👥 STAFF PERFORMANCE (LIVE DATA):")
    for staff_id, staff in export_data['staff_members'].items():
        stats = staff['live_stats']
        if stats['total_invites'] > 0:
            print(f"  • {staff['username']}: {stats['total_invites']} invites, {stats['vip_converts']} VIPs ({stats['conversion_rate']:.1f}%)")
        else:
            print(f"  • {staff['username']}: No live data")
    
    print(f"\n💾 Complete export saved to: {export_filename}")
    print(f"🔗 Includes both live Discord data and database records")
    print(f"🛡️ This is your complete production backup!")
    
    return export_data

if __name__ == "__main__":
    complete_production_export()