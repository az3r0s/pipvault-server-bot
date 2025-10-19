"""
Cloud API Backup Reader
======================

Read and display backup data from PipVault cloud database exports.
Shows all your invite tracking, staff, and VIP data in a readable format.
"""

import json
import sys
from datetime import datetime

def read_backup_file(backup_file):
    """Read and display backup data in a neat console format"""
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        backup_info = backup_data.get('backup_info', {})
        cloud_data = backup_data.get('cloud_data', {})
        
        print("🔍 PIPVAULT CLOUD BACKUP READER")
        print("=" * 50)
        
        # Backup metadata
        print(f"📅 Created: {backup_info.get('created_at', 'Unknown')}")
        print(f"🌐 Source: {backup_info.get('source', 'Unknown')}")
        print(f"📡 Cloud URL: {backup_info.get('cloud_url', 'Unknown')}")
        print(f"🔧 Type: {backup_info.get('backup_type', 'Unknown')}")
        print()
        
        # Summary
        total_records = 0
        for table_name, table_data in cloud_data.items():
            if isinstance(table_data, list):
                total_records += len(table_data)
        
        print(f"📊 SUMMARY:")
        print(f"   Tables: {len(cloud_data)}")
        print(f"   Total Records: {total_records}")
        print()
        
        # Detailed breakdown
        for table_name, table_data in cloud_data.items():
            if isinstance(table_data, list):
                print(f"📋 {table_name.upper()}: {len(table_data)} records")
                print("-" * 40)
                
                if len(table_data) > 0:
                    # Show first few records as examples
                    for i, record in enumerate(table_data[:3]):  # Show first 3
                        print(f"   Record {i+1}:")
                        for key, value in record.items():
                            # Truncate long values
                            display_value = str(value)
                            if len(display_value) > 50:
                                display_value = display_value[:47] + "..."
                            print(f"     {key}: {display_value}")
                        print()
                    
                    if len(table_data) > 3:
                        print(f"     ... and {len(table_data) - 3} more records")
                        print()
                else:
                    print("   (No records)")
                    print()
        
        # Special analysis for important tables
        if 'invite_tracking' in cloud_data:
            invite_data = cloud_data['invite_tracking']
            print(f"🎯 INVITE TRACKING ANALYSIS:")
            print(f"   Total invites tracked: {len(invite_data)}")
            
            # Count unique inviters
            inviters = set()
            recent_joins = 0
            cutoff_date = datetime.now().replace(month=datetime.now().month-1)  # Last month
            
            for invite in invite_data:
                if invite.get('inviter_username'):
                    inviters.add(invite['inviter_username'])
                
                # Count recent joins (rough check)
                joined_at = invite.get('joined_at', '')
                if joined_at and '2024' in joined_at:  # Basic recency check
                    recent_joins += 1
            
            print(f"   Unique inviters: {len(inviters)}")
            print(f"   Recent joins: {recent_joins}")
            print()
        
        if 'staff_invites' in cloud_data:
            staff_data = cloud_data['staff_invites']
            print(f"👥 STAFF INVITES ANALYSIS:")
            print(f"   Total staff invite codes: {len(staff_data)}")
            
            active_codes = 0
            for staff_invite in staff_data:
                if staff_invite.get('active', True):  # Assume active if not specified
                    active_codes += 1
            
            print(f"   Active codes: {active_codes}")
            print()
        
        if 'vip_requests' in cloud_data:
            vip_data = cloud_data['vip_requests']
            print(f"💎 VIP REQUESTS ANALYSIS:")
            print(f"   Total VIP requests: {len(vip_data)}")
            
            status_counts = {}
            for vip_request in vip_data:
                status = vip_request.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                print(f"   {status.title()}: {count}")
            print()
        
        print("✅ BACKUP READ COMPLETE")
        print(f"📁 File: {backup_file}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Backup file not found: {backup_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in backup file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading backup: {e}")
        return False

def list_backup_files():
    """List all available backup files in current directory"""
    import os
    import glob
    
    print("📁 AVAILABLE BACKUP FILES:")
    print("=" * 30)
    
    backup_files = glob.glob("pipvault_cloud_backup_*.json")
    
    if not backup_files:
        print("No backup files found in current directory.")
        return []
    
    # Sort by creation time (newest first)
    backup_files.sort(key=os.path.getctime, reverse=True)
    
    for i, file in enumerate(backup_files, 1):
        file_size = os.path.getsize(file)
        file_time = datetime.fromtimestamp(os.path.getctime(file))
        
        print(f"{i:2d}. {file}")
        print(f"     Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        print(f"     Created: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    return backup_files

def main():
    if len(sys.argv) > 1:
        backup_file = sys.argv[1]
        read_backup_file(backup_file)
    else:
        print("🔍 PIPVAULT BACKUP READER")
        print("=" * 30)
        print()
        
        backup_files = list_backup_files()
        
        if backup_files:
            print("Usage:")
            print(f"  python {sys.argv[0]} <backup_file>")
            print()
            print("Example:")
            print(f"  python {sys.argv[0]} {backup_files[0]}")
        else:
            print("No backup files found. Create a backup first with:")
            print("  python backup_cloud_api.py")

if __name__ == "__main__":
    main()