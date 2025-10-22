#!/usr/bin/env python3
"""
Test backup system by creating sample data
"""

import os
import sys
import asyncio
sys.path.append(os.path.dirname(__file__))

from utils.cloud_database import CloudAPIServerDatabase

async def create_test_data():
    print("🧪 Creating test data for backup system validation...")
    
    # Initialize database
    db = CloudAPIServerDatabase()
    
    # Add test staff invite
    db.manually_add_staff_invite(123456789, "ABC123")
    print("✅ Added test staff invite")
    
    # Add test invite tracking
    db.record_user_join(987654321, "TestMember", "ABC123", 123456789, "TestUser", 5, 6)
    print("✅ Added test invite tracking")
    
    # Add test VIP request
    db.create_vip_request(987654321, "TestMember", "upgrade", 123456789, "test@example.com")
    print("✅ Added test VIP request")
    
    # Test onboarding methods if they exist
    if hasattr(db, 'init_onboarding_progress'):
        await db.init_onboarding_progress("987654321", "TestMember")
        print("✅ Added test onboarding progress")
        
        await db.update_onboarding_step("987654321", "rules_accepted")
        print("✅ Updated onboarding step")
        
        await db.log_onboarding_event("987654321", "step_completed", "rules", {"test": True})
        print("✅ Added onboarding analytics")
    
    print("\n📊 Test data created successfully!")
    print("🔄 Now run generate_db_backup.py to test the backup system")

if __name__ == "__main__":
    asyncio.run(create_test_data())