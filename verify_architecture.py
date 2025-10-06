#!/usr/bin/env python3
"""
Simple test to verify clean architecture implementation.
"""

import os
import json
import sys

def test_config_structure():
    """Test that config file has proper clean architecture structure"""
    config_path = "config/staff_config.json"
    
    if not os.path.exists(config_path):
        print("❌ Config file not found!")
        return False
        
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("✅ Testing config file structure...")
    
    staff_members = config.get("staff_members", {})
    
    for staff_name, staff_info in staff_members.items():
        print(f"  Checking {staff_name}...")
        
        # Check required fields exist
        required_fields = ['discord_id', 'username', 'vantage_referral_link', 'vantage_ib_code']
        for field in required_fields:
            if field not in staff_info:
                print(f"    ❌ Missing field: {field}")
                return False
            print(f"    ✅ {field}: {staff_info[field]}")
        
        # Check that invite_code is NOT in config (clean architecture)
        if 'invite_code' in staff_info:
            print(f"    ❌ invite_code found in config (should be database-only)")
            return False
        else:
            print(f"    ✅ invite_code not in config (clean architecture)")
    
    print("✅ Config structure is clean!")
    return True

def test_database_methods():
    """Test database methods with clean architecture"""
    try:
        from utils.cloud_database import CloudAPIServerDatabase
        
        print("✅ Successfully imported CloudAPIServerDatabase")
        
        # Initialize database
        db = CloudAPIServerDatabase()
        print("✅ Database initialized")
        
        # Test getting staff by Discord ID (should combine config + database)
        test_discord_id = 243819020040536065  # Aidan's ID from config
        
        staff_info = db.get_staff_by_discord_id(test_discord_id)
        if staff_info:
            print(f"✅ Retrieved staff info for Discord ID {test_discord_id}")
            print(f"  Username: {staff_info.get('username')}")
            print(f"  Vantage Link: {staff_info.get('vantage_referral_link')}")
            print(f"  Vantage IB Code: {staff_info.get('vantage_ib_code')}")
            print(f"  Invite Code: {staff_info.get('invite_code', 'None (not generated yet)')}")
        else:
            print(f"❌ Could not retrieve staff info for Discord ID {test_discord_id}")
            return False
            
        print("✅ Database methods working with clean architecture!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing database methods: {e}")
        return False

def main():
    print("🔧 Testing Clean Architecture Implementation")
    print("=" * 50)
    
    # Test 1: Config file structure
    config_ok = test_config_structure()
    print()
    
    # Test 2: Database methods
    if config_ok:
        db_ok = test_database_methods()
    else:
        print("⚠️ Skipping database tests due to config issues")
        db_ok = False
    
    print()
    print("=" * 50)
    if config_ok and db_ok:
        print("🎉 All tests passed! Clean architecture is working correctly.")
    else:
        print("❌ Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main()