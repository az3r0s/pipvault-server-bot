"""
Database Rebuild Utility
========================

This script rebuilds the invite tracking database from persistent log files.
Use this if the database is corrupted or needs to be restored.

Usage:
    python rebuild_from_logs.py

CRITICAL: This will OVERWRITE existing database invite tracking data!
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

def rebuild_database_from_logs():
    """Rebuild invite tracking database from JSON logs"""
    
    print("=" * 80)
    print("🔧 DATABASE REBUILD FROM LOGS")
    print("=" * 80)
    
    # Paths
    json_log = Path("invite_logs/invite_joins.json")
    db_path = Path("pipvault_server.db")
    
    if not json_log.exists():
        print("❌ No log file found at invite_logs/invite_joins.json")
        print("   Nothing to rebuild from.")
        return False
    
    if not db_path.exists():
        print("❌ Database file not found at pipvault_server.db")
        print("   Please ensure the database exists first.")
        return False
    
    # Load logs
    print("\n📖 Reading log file...")
    with open(json_log, 'r', encoding='utf-8') as f:
        all_joins = json.load(f)
    
    print(f"✅ Found {len(all_joins)} join events in logs")
    
    if not all_joins:
        print("⚠️  No joins to restore")
        return True
    
    # Confirm with user
    print("\n⚠️  WARNING: This will overwrite existing invite_tracking table data!")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ Rebuild cancelled")
        return False
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = sqlite3.connect(db_path, timeout=10.0)
    cursor = conn.cursor()
    
    # Clear existing invite tracking data
    print("🗑️  Clearing existing invite_tracking table...")
    cursor.execute('DELETE FROM invite_tracking')
    conn.commit()
    
    # Insert from logs
    print("\n📝 Rebuilding from logs...")
    inserted = 0
    errors = 0
    
    for i, join in enumerate(all_joins, 1):
        if i % 10 == 0 or i == len(all_joins):
            print(f"   Processing {i}/{len(all_joins)}...", end='\r')
        
        try:
            # Convert timestamp to proper format
            timestamp = join.get('timestamp')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                except:
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            cursor.execute('''
                INSERT INTO invite_tracking 
                (user_id, username, invite_code, inviter_id, inviter_username, 
                 joined_at, invite_uses_before, invite_uses_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(join.get('user_id', 0)),
                join.get('username', 'Unknown'),
                join.get('invite_code', 'unknown'),
                int(join.get('staff_id', 0)),
                join.get('staff_username', 'Unknown'),
                dt,
                join.get('uses_before', 0),
                join.get('uses_after', 0)
            ))
            
            inserted += 1
            
        except Exception as e:
            errors += 1
            print(f"\n⚠️  Error processing join {i}: {e}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n\n✅ Rebuild complete!")
    print(f"   Inserted: {inserted}")
    print(f"   Errors: {errors}")
    print(f"   Total: {len(all_joins)}")
    
    # Verify
    print("\n🔍 Verifying rebuild...")
    conn = sqlite3.connect(db_path, timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM invite_tracking')
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"✅ Database now contains {count} invite tracking records")
    
    if count == inserted:
        print("✅ Verification successful - all records match!")
        return True
    else:
        print(f"⚠️  Warning: Expected {inserted} but found {count} in database")
        return False

def preview_logs():
    """Preview what's in the logs without making changes"""
    
    print("=" * 80)
    print("👁️  LOG FILE PREVIEW")
    print("=" * 80)
    
    json_log = Path("invite_logs/invite_joins.json")
    
    if not json_log.exists():
        print("❌ No log file found")
        return
    
    with open(json_log, 'r', encoding='utf-8') as f:
        all_joins = json.load(f)
    
    print(f"\n📊 Total joins in log: {len(all_joins)}")
    
    if not all_joins:
        print("   (empty)")
        return
    
    # Show first and last entries
    print("\n📝 First Entry:")
    print(json.dumps(all_joins[0], indent=2))
    
    print("\n📝 Last Entry:")
    print(json.dumps(all_joins[-1], indent=2))
    
    # Count by invite code
    invite_counts = {}
    for join in all_joins:
        code = join.get('invite_code', 'unknown')
        invite_counts[code] = invite_counts.get(code, 0) + 1
    
    print("\n📈 Joins by Invite Code:")
    for code, count in sorted(invite_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {code}: {count} joins")

if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 80)
    print(" INVITE TRACKING DATABASE REBUILD UTILITY")
    print("=" * 80)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--preview':
        preview_logs()
    else:
        print("\nOptions:")
        print("1. Preview logs (no changes)")
        print("2. Rebuild database from logs")
        print("3. Cancel")
        
        choice = input("\nChoose option (1-3): ").strip()
        
        if choice == '1':
            preview_logs()
        elif choice == '2':
            success = rebuild_database_from_logs()
            if success:
                print("\n✅ Database successfully rebuilt from logs!")
            else:
                print("\n❌ Rebuild failed or was cancelled")
        else:
            print("❌ Cancelled")
