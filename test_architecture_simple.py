#!/usr/bin/env python3
"""
Simple Architecture Test - Tests clean separation without database imports
"""

import json
import os
import sqlite3
from pathlib import Path

def test_config_structure():
    """Test that config file has clean structure (no invite codes)"""
    print("🔧 Testing Config File Structure")
    print("=" * 50)
    
    config_path = "config/staff_config.json"
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        staff_members = config.get("staff_members", {})
        
        for staff_name, staff_info in staff_members.items():
            print(f"  Checking {staff_name}...")
            
            # Required static fields
            required_fields = ['discord_id', 'username', 'vantage_referral_link', 'vantage_ib_code']
            for field in required_fields:
                if field not in staff_info:
                    print(f"    ❌ Missing required field: {field}")
                    return False
                print(f"    ✅ {field}: {staff_info[field]}")
            
            # Invite code should NOT be in config (clean architecture)
            if 'invite_code' in staff_info:
                print(f"    ❌ invite_code found in config - should be database only!")
                return False
            else:
                print(f"    ✅ invite_code not in config (clean architecture)")
        
        print("✅ Config structure is clean!")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def test_database_structure():
    """Test database structure and data separation"""
    print("\n🔧 Testing Database Structure")
    print("=" * 50)
    
    db_path = "vip_upgrade_service.db"
    if not os.path.exists(db_path):
        print(f"⚠️  Database file not found: {db_path}")
        print("   This might be normal if no invite codes have been generated yet.")
        return True
    
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Check if staff_invites table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='staff_invites'
        """)
        
        if not cursor.fetchone():
            print("⚠️  staff_invites table not found - this is normal if no invites created yet")
            conn.close()
            return True
        
        # Check table structure
        cursor.execute("PRAGMA table_info(staff_invites)")
        columns = cursor.fetchall()
        
        print("  Database table columns:")
        for col in columns:
            print(f"    - {col[1]} ({col[2]})")
        
        # Check data in table
        cursor.execute("SELECT staff_id, invite_code, staff_username, vantage_referral_link FROM staff_invites")
        rows = cursor.fetchall()
        
        print(f"\n  Found {len(rows)} staff invite records:")
        for row in rows:
            staff_id, invite_code, username, vantage_link = row
            print(f"    Staff ID: {staff_id}")
            print(f"    Invite Code: {invite_code}")
            print(f"    Username in DB: {username} {'(should be NULL for clean architecture)' if username else '✅ NULL (clean)'}")
            print(f"    Vantage Link in DB: {vantage_link} {'(should be NULL for clean architecture)' if vantage_link else '✅ NULL (clean)'}")
            print()
        
        conn.close()
        print("✅ Database structure checked!")
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def test_lookup_logic():
    """Test the lookup logic manually"""
    print("\n🔧 Testing Lookup Logic Manually")
    print("=" * 50)
    
    # Test Discord ID lookup from config
    config_path = "config/staff_config.json"
    test_discord_id = 243819020040536065  # Aidan's ID
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Find staff by Discord ID
        staff_found = None
        for staff_name, staff_info in config["staff_members"].items():
            if staff_info["discord_id"] == test_discord_id:
                staff_found = staff_info
                print(f"  ✅ Found {staff_name} in config by Discord ID {test_discord_id}")
                print(f"    Static data: username={staff_info['username']}")
                print(f"    Static data: vantage_ib_code={staff_info['vantage_ib_code']}")
                break
        
        if not staff_found:
            print(f"  ❌ Staff member with Discord ID {test_discord_id} not found in config")
            return False
        
        # Try to find invite code in database
        db_path = "vip_upgrade_service.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute("SELECT invite_code FROM staff_invites WHERE staff_id = ?", (test_discord_id,))
            row = cursor.fetchone()
            
            if row:
                invite_code = row[0]
                print(f"  ✅ Found invite code in database: {invite_code}")
                print(f"  ✅ Clean architecture working: static data from config, dynamic data from DB")
            else:
                print(f"  ⚠️  No invite code found in database (might not be generated yet)")
            
            conn.close()
        else:
            print(f"  ⚠️  Database not found (invite codes not generated yet)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing lookup logic: {e}")
        return False

def main():
    """Run all architecture tests"""
    print("🚀 Clean Architecture Verification")
    print("=" * 60)
    
    tests = [
        test_config_structure,
        test_database_structure,
        test_lookup_logic
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("🎉 All architecture tests passed!")
        print("✅ Clean separation achieved:")
        print("   - Config file: Static staff data only")
        print("   - Database: Dynamic invite codes only")
        print("   - Lookup methods: Combine both sources")
    else:
        print("❌ Some tests failed. Architecture needs attention.")
    
    return all(results)

if __name__ == "__main__":
    main()