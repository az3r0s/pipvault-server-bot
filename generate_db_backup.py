#!/usr/bin/env python3
"""
Generate database backup for PipVault Discord Bot Railway deployment
Run this locally to test backup functionality and get backup data
"""

import os
import sys
import asyncio
import json
sys.path.append(os.path.dirname(__file__))

from utils.cloud_database import CloudAPIServerDatabase

async def main():
    print("=" * 80)
    print("🔄 Generating PipVault Discord Bot database backup...")
    print("=" * 80)
    
    # Setup database using same logic as the bot
    try:
        cloud_url = os.getenv('CLOUD_API_URL', 'https://web-production-1299f.up.railway.app')
        if os.getenv('CLOUD_API_URL'):  # Only use cloud if explicitly set
            db = CloudAPIServerDatabase(cloud_url)
            print(f"✅ Using Cloud API database: {cloud_url}")
            print("📡 This will backup data from Railway cloud database")
        else:
            db = CloudAPIServerDatabase()  # Local SQLite fallback
            print("⚠️ Using local SQLite database")
            print("📍 CLOUD_API_URL not set - this will backup local test data only")
            print(f"💡 To backup Railway data, set CLOUD_API_URL environment variable")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        db = CloudAPIServerDatabase()  # Fallback
        print("📦 Fallback to local SQLite database")
        
    db.init_database()  # This is a sync method, not async
    
    # Test backup functionality
    await db.backup_to_cloud()
    
    # Also get the backup data locally for inspection
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    backup_data = {}
    
    # Get all tables data
    tables = ['staff_invites', 'invite_tracking', 'vip_requests', 'onboarding_progress', 'onboarding_analytics']
    
    for table in tables:
        try:
            cursor.execute(f'SELECT * FROM {table}')
            rows = [dict(row) for row in cursor.fetchall()]
            backup_data[table] = rows
            print(f"📊 {table}: {len(rows)} records")
        except sqlite3.OperationalError as e:
            print(f"⚠️ {table}: Table doesn't exist yet ({e})")
            backup_data[table] = []
    
    conn.close()
    
    # Save backup to file for inspection
    json_backup = json.dumps(backup_data, indent=2)
    with open('discord_bot_backup.json', 'w') as f:
        f.write(json_backup)
    
    print(f"\n✅ Database backup completed!")
    print(f"💾 Local backup saved to: discord_bot_backup.json")
    print(f"☁️ Cloud backup triggered (if API URL configured)")
    
    # Show summary
    total_records = sum(len(records) for records in backup_data.values())
    print(f"\n📊 Total records backed up: {total_records}")
    
    if total_records > 0:
        print("\n🛡️ Your data is safe for Railway deployment!")
    else:
        print("\n💡 No data found - this is normal for a fresh installation")

if __name__ == "__main__":
    asyncio.run(main())