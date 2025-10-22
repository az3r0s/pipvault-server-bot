#!/usr/bin/env python3
"""
Backup Railway Cloud Database
=============================

This script connects to the Railway cloud database and creates a complete backup
of all existing data before deploying the welcome system.
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.cloud_database import CloudAPIServerDatabase

async def backup_railway_data():
    print("=" * 80)
    print("☁️ BACKING UP RAILWAY CLOUD DATABASE")
    print("=" * 80)
    
    # Set Railway cloud URL
    railway_url = "https://web-production-1299f.up.railway.app"
    
    print(f"🌐 Connecting to Railway: {railway_url}")
    
    # Initialize database with Railway URL
    db = CloudAPIServerDatabase(railway_url)
    
    print("📡 Attempting to restore existing data from Railway...")
    
    # First restore any existing cloud data to local database
    await db.restore_from_cloud()
    
    print("📊 Generating comprehensive backup...")
    
    # Now backup to local file for safekeeping
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    backup_data = {}
    total_records = 0
    
    # Get all tables data
    tables = ['staff_invites', 'invite_tracking', 'vip_requests', 'onboarding_progress', 'onboarding_analytics']
    
    print("\n📋 Table-by-table backup:")
    for table in tables:
        try:
            cursor.execute(f'SELECT * FROM {table}')
            rows = [dict(row) for row in cursor.fetchall()]
            backup_data[table] = rows
            total_records += len(rows)
            print(f"  ✅ {table}: {len(rows)} records")
            
            # Show sample data for verification
            if len(rows) > 0:
                sample = dict(rows[0])
                # Hide sensitive data
                for key in sample:
                    if len(str(sample[key])) > 50:
                        sample[key] = str(sample[key])[:50] + "..."
                print(f"     Sample: {sample}")
                
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ {table}: Table doesn't exist yet ({e})")
            backup_data[table] = []
    
    conn.close()
    
    # Create timestamped backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"railway_backup_{timestamp}.json"
    
    # Save comprehensive backup
    with open(backup_filename, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)
    
    print(f"\n✅ Railway backup completed!")
    print(f"💾 Backup saved to: {backup_filename}")
    print(f"📊 Total records backed up: {total_records}")
    
    if total_records > 0:
        print(f"\n🛡️ Your {total_records} records are safely backed up!")
        print("🚀 You can now deploy the welcome system with confidence.")
    else:
        print("\n💡 No existing data found in Railway database.")
        print("🚀 Safe to deploy welcome system - this appears to be a fresh installation.")
    
    # Also create backup copy with standard name for deployment
    with open('railway_production_backup.json', 'w') as f:
        json.dump(backup_data, f, separators=(',', ':'))  # Compact format
    
    print(f"📋 Production backup also saved as: railway_production_backup.json")
    
    return backup_data, total_records

if __name__ == "__main__":
    asyncio.run(backup_railway_data())