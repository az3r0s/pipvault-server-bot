#!/usr/bin/env python3
"""
Comprehensive Production Data Backup
===================================

This script directly accesses the bot's actual database to backup all production data,
using the same approach that successfully found all 6 staff invites earlier.
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

def backup_production_data():
    print("=" * 80)
    print("📋 COMPREHENSIVE PRODUCTION DATA BACKUP")
    print("=" * 80)
    
    # First, let's find all database files in the bot directory
    print("🔍 Scanning for database files...")
    
    current_dir = Path(__file__).parent
    db_files = []
    
    # Look for .db files
    for db_file in current_dir.glob("*.db"):
        db_files.append(db_file)
        print(f"  📁 Found: {db_file.name} ({db_file.stat().st_size} bytes)")
    
    # Also check if there are any other database paths the bot might use
    potential_paths = [
        "server_management.db",
        "database.db", 
        "discord_bot.db",
        "pipvault.db"
    ]
    
    for path in potential_paths:
        if Path(path).exists() and Path(path) not in db_files:
            db_files.append(Path(path))
            print(f"  📁 Found: {path} ({Path(path).stat().st_size} bytes)")
    
    if not db_files:
        print("❌ No database files found!")
        return None
    
    # Backup data from each database file
    all_backup_data = {}
    total_records = 0
    
    for db_file in db_files:
        print(f"\n📊 Backing up data from: {db_file.name}")
        
        try:
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"  📋 Tables found: {tables}")
            
            db_backup = {}
            db_records = 0
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = [dict(row) for row in cursor.fetchall()]
                    db_backup[table] = rows
                    db_records += len(rows)
                    
                    if len(rows) > 0:
                        print(f"    ✅ {table}: {len(rows)} records")
                        
                        # Show sample for key tables
                        if table in ['staff_invites', 'invite_tracking', 'vip_requests'] and len(rows) > 0:
                            sample = dict(rows[0])
                            # Truncate long values for display
                            display_sample = {}
                            for key, value in sample.items():
                                if len(str(value)) > 50:
                                    display_sample[key] = str(value)[:50] + "..."
                                else:
                                    display_sample[key] = value
                            print(f"       Sample: {display_sample}")
                    else:
                        print(f"    ⭕ {table}: 0 records")
                        
                except Exception as e:
                    print(f"    ❌ Error reading {table}: {e}")
            
            conn.close()
            
            all_backup_data[f"database_{db_file.stem}"] = {
                "file_name": db_file.name,
                "file_size": db_file.stat().st_size,
                "tables": db_backup,
                "record_count": db_records
            }
            
            total_records += db_records
            print(f"  📊 Total records from {db_file.name}: {db_records}")
            
        except Exception as e:
            print(f"  ❌ Error accessing {db_file.name}: {e}")
    
    # Also try to get data through the CloudAPIServerDatabase methods
    print(f"\n🔗 Attempting to get data through CloudAPIServerDatabase...")
    try:
        # Initialize without forcing cloud connection
        db = CloudAPIServerDatabase()
        
        # Try to get staff configuration data (this worked before)
        if hasattr(db, 'load_staff_config'):
            staff_config = db.load_staff_config()
            if staff_config:
                all_backup_data['staff_configuration'] = staff_config
                print(f"  ✅ Staff configuration: {len(staff_config)} entries")
        
        # Try to get staff invite status (this showed the 6 invites before)
        if hasattr(db, 'get_staff_invite_status'):
            invite_status = db.get_staff_invite_status()
            if invite_status:
                all_backup_data['staff_invite_status'] = invite_status
                print(f"  ✅ Staff invite status: {len(invite_status)} entries")
        
        # Try debug method
        if hasattr(db, 'debug_staff_invites_table'):
            debug_info = db.debug_staff_invites_table()
            if debug_info:
                all_backup_data['debug_staff_info'] = debug_info
                print(f"  ✅ Debug staff info captured")
                
    except Exception as e:
        print(f"  ⚠️ CloudAPIServerDatabase methods failed: {e}")
    
    # Create comprehensive backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"production_backup_comprehensive_{timestamp}.json"
    
    backup_summary = {
        "backup_timestamp": timestamp,
        "backup_type": "comprehensive_production_backup",
        "total_records": total_records,
        "database_count": len(db_files),
        "databases_backed_up": [str(db) for db in db_files],
        "data": all_backup_data
    }
    
    # Save backup
    with open(backup_filename, 'w') as f:
        json.dump(backup_summary, f, indent=2, default=str)
    
    print(f"\n✅ COMPREHENSIVE BACKUP COMPLETED!")
    print(f"💾 Backup saved to: {backup_filename}")
    print(f"📊 Total records backed up: {total_records}")
    print(f"📁 Databases scanned: {len(db_files)}")
    
    # Summary
    if total_records > 0:
        print(f"\n🛡️ SUCCESS: {total_records} production records safely backed up!")
        print("🔍 Review the backup file to verify all expected data is present")
        print("🚀 You can now deploy the welcome system with confidence")
    else:
        print(f"\n⚠️ No records found in database files")
        print("🔍 The production data might be stored elsewhere")
    
    return backup_summary

if __name__ == "__main__":
    backup_production_data()