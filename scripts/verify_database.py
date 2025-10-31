"""
Test script to verify database functionality and cloud sync
"""

import asyncio
import os
import sys
from datetime import datetime
from database.migrations import MigrationManager
from database.cloud_database import CloudAPIServerDatabase
from utils.config import load_config

async def test_database_functionality():
    print("\n🧪 Testing Database Functionality")
    print("=" * 50)
    
    # Initialize test database
    test_db = "test_server_management.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    # Create migration manager
    print("\n1️⃣ Testing migrations...")
    migration_manager = MigrationManager(test_db)
    
    if migration_manager.create_all_tables():
        print("✅ All tables created successfully")
    else:
        print("❌ Failed to create tables")
        return False
        
    # Initialize cloud database
    print("\n2️⃣ Testing cloud database...")
    cloud_url = os.getenv('CLOUD_API_URL', 'https://web-production-1299f.up.railway.app')
    db = CloudAPIServerDatabase(cloud_url)
    db.db_path = test_db
    
    # Test staff invite operations
    print("\n3️⃣ Testing staff invite management...")
    staff_id = 123456789
    staff_name = "Test Staff"
    invite_code = "test-invite-abc"
    
    if db.update_staff_invite_code(staff_id, staff_name, invite_code):
        print("✅ Staff invite created")
    else:
        print("❌ Failed to create staff invite")
        return False
        
    # Verify invite code exists
    invite_codes = db.get_all_staff_invite_codes()
    if invite_code in invite_codes:
        print("✅ Staff invite verified")
    else:
        print("❌ Staff invite not found")
        return False
        
    # Test member join tracking
    print("\n4️⃣ Testing member join tracking...")
    member_id = 987654321
    member_name = "Test Member"
    
    if db.track_user_invite(
        member_id, member_name, invite_code,
        staff_id, staff_name, 0, 1
    ):
        print("✅ Member join tracked")
    else:
        print("❌ Failed to track member join")
        return False
        
    # Verify tracking data
    referrals = db.get_staff_referrals(staff_id)
    if referrals and len(referrals) == 1:
        print("✅ Referral data verified")
    else:
        print("❌ Referral data not found")
        return False
        
    # Test cloud backup
    print("\n5️⃣ Testing cloud backup...")
    if await db.backup_to_cloud():
        print("✅ Data backed up to cloud")
    else:
        print("❌ Cloud backup failed")
        return False
        
    # Test cloud restore
    print("\n6️⃣ Testing cloud restore...")
    # Delete local DB first
    os.remove(test_db)
    
    # Create new DB instance
    new_db = CloudAPIServerDatabase(cloud_url)
    new_db.db_path = test_db
    
    if await new_db.restore_from_cloud():
        print("✅ Data restored from cloud")
    else:
        print("❌ Cloud restore failed")
        return False
        
    # Verify restored data
    restored_invites = new_db.get_all_staff_invite_codes()
    if invite_code in restored_invites:
        print("✅ Restored data verified")
    else:
        print("❌ Restored data verification failed")
        return False
        
    print("\n✨ All tests passed successfully!")
    return True

async def main():
    try:
        if await test_database_functionality():
            print("\n🚀 Database system is ready for deployment!")
        else:
            print("\n❌ Database verification failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        sys.exit(1)
    finally:
        # Cleanup test database
        if os.path.exists("test_server_management.db"):
            os.remove("test_server_management.db")

if __name__ == "__main__":
    asyncio.run(main())