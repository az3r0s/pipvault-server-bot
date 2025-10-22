#!/usr/bin/env python3
"""
Test restore functionality for PipVault Discord Bot Railway deployment
Run this locally to test cloud restore functionality
"""

import os
import sys
import asyncio
sys.path.append(os.path.dirname(__file__))

from utils.cloud_database import CloudAPIServerDatabase

async def main():
    print("=" * 80)
    print("🔄 Testing PipVault Discord Bot database restore...")
    print("=" * 80)
    
    # Setup database
    db = CloudAPIServerDatabase()
    await db.init_database()
    
    # Test restore functionality
    print("🔄 Attempting to restore from cloud...")
    await db.restore_from_cloud()
    
    # Check what was restored
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    tables = ['staff_invites', 'invite_tracking', 'vip_requests', 'onboarding_progress', 'onboarding_analytics']
    
    total_records = 0
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
            count = cursor.fetchone()['count']
            total_records += count
            print(f"📊 {table}: {count} records restored")
        except sqlite3.OperationalError:
            print(f"⚠️ {table}: Table doesn't exist yet")
    
    conn.close()
    
    print(f"\n✅ Restore test completed!")
    print(f"📊 Total records restored: {total_records}")
    
    if total_records > 0:
        print("\n🛡️ Cloud restore is working correctly!")
    else:
        print("\n💡 No data restored - either no cloud backup exists or API not configured")

if __name__ == "__main__":
    asyncio.run(main())