"""
Comprehensive test for clean architecture implementation.
Tests the separation between static config data and dynamic database data.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List

# Import the database class
from utils.cloud_database import CloudAPIServerDatabase

class TestCleanArchitecture:
    def __init__(self):
        self.db_path = "test_staff_data.db"
        self.config_path = "config/staff_config.json"
        
        # Remove test database if it exists
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        # Initialize database
        self.db = CloudAPIServerDatabase(self.db_path)
        
    def test_config_file_structure(self):
        """Test that config file has clean structure without invite_code fields"""
        print("\n🧪 Testing config file structure...")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        staff_members = config.get("staff_members", {})
        
        for staff_name, staff_info in staff_members.items():
            # Check required static fields exist
            required_fields = ['discord_id', 'username', 'vantage_referral_link', 'vantage_ib_code']
            for field in required_fields:
                assert field in staff_info, f"❌ Missing required field '{field}' for {staff_name}"
                
            # Check that invite_code field is not present (clean architecture)
            assert 'invite_code' not in staff_info, f"❌ invite_code field should not be in config for {staff_name}"
            
        print(f"✅ Config file has clean structure with {len(staff_members)} staff members")
        print("   - All required static fields present")
        print("   - No invite_code fields (clean separation)")
        
    def test_database_operations(self):
        """Test database operations with clean architecture"""
        print("\n🧪 Testing database operations...")
        
        # Test data
        test_discord_id = 243819020040536065  # Aidan's ID from config
        test_invite_code = "TEST123456"
        
        # Test 1: Update invite code (should work since Discord ID exists in config)
        success = self.db.update_staff_invite_code(test_discord_id, test_invite_code)
        assert success, "❌ Failed to update staff invite code"
        print("✅ Successfully updated invite code for existing staff member")
        
        # Test 2: Get staff by Discord ID (should combine config + database data)
        staff_data = self.db.get_staff_by_discord_id(test_discord_id)
        assert staff_data is not None, "❌ Failed to get staff by Discord ID"
        assert staff_data['discord_id'] == test_discord_id, "❌ Wrong Discord ID returned"
        assert staff_data['invite_code'] == test_invite_code, "❌ Wrong invite code returned"
        assert staff_data['username'] == "thegoldtradingresults", "❌ Wrong username (should come from config)"
        assert 'vantage_referral_link' in staff_data, "❌ Missing vantage_referral_link (should come from config)"
        print("✅ Successfully retrieved combined staff data (config + database)")
        
        # Test 3: Get staff by invite code (should work with clean architecture)
        staff_by_invite = self.db.get_staff_config_by_invite(test_invite_code)
        assert staff_by_invite is not None, "❌ Failed to get staff by invite code"
        assert staff_by_invite['discord_id'] == test_discord_id, "❌ Wrong Discord ID from invite lookup"
        assert staff_by_invite['invite_code'] == test_invite_code, "❌ Wrong invite code returned"
        print("✅ Successfully retrieved staff data by invite code")
        
        # Test 4: Try to update invite code for non-existent staff (should fail)
        fake_discord_id = 999999999999999999
        success = self.db.update_staff_invite_code(fake_discord_id, "FAKE123")
        assert not success, "❌ Should have failed for non-existent staff member"
        print("✅ Correctly rejected invite code update for non-existent staff")
        
    def test_database_schema(self):
        """Test that database has correct schema structure"""
        print("\n🧪 Testing database schema...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check staff_invites table structure
        cursor.execute("PRAGMA table_info(staff_invites)")
        columns = cursor.fetchall()
        
        expected_columns = [
            'staff_id', 'staff_username', 'invite_code', 
            'vantage_referral_link', 'vantage_ib_code', 
            'email_template', 'created_at', 'updated_at'
        ]
        
        actual_columns = [col[1] for col in columns]
        
        for expected_col in expected_columns:
            assert expected_col in actual_columns, f"❌ Missing column: {expected_col}"
            
        print("✅ Database schema has correct structure")
        
        # Check that redundant columns are NULL (clean architecture)
        cursor.execute("SELECT staff_username, vantage_referral_link, vantage_ib_code FROM staff_invites")
        rows = cursor.fetchall()
        
        for row in rows:
            staff_username, vantage_link, ib_code = row
            # These should be NULL in clean architecture (data comes from config)
            assert staff_username is None, "❌ staff_username should be NULL (comes from config)"
            assert vantage_link is None, "❌ vantage_referral_link should be NULL (comes from config)"
            assert ib_code is None, "❌ vantage_ib_code should be NULL (comes from config)"
            
        print("✅ Redundant columns correctly set to NULL (clean architecture)")
        
        conn.close()
        
    def test_all_staff_members(self):
        """Test operations for all staff members in config"""
        print("\n🧪 Testing all staff members...")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        staff_members = config.get("staff_members", {})
        
        for staff_name, staff_info in staff_members.items():
            discord_id = staff_info['discord_id']
            test_invite = f"TEST_{staff_name.upper()}_123"
            
            # Test update invite code
            success = self.db.update_staff_invite_code(discord_id, test_invite)
            assert success, f"❌ Failed to update invite code for {staff_name}"
            
            # Test retrieval
            retrieved = self.db.get_staff_by_discord_id(discord_id)
            assert retrieved is not None, f"❌ Failed to retrieve {staff_name}"
            assert retrieved['invite_code'] == test_invite, f"❌ Wrong invite code for {staff_name}"
            assert retrieved['username'] == staff_info['username'], f"❌ Wrong username for {staff_name}"
            
        print(f"✅ Successfully tested all {len(staff_members)} staff members")
        
    def cleanup(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        print("🧹 Cleaned up test database")
        
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Clean Architecture Tests")
        print("=" * 50)
        
        try:
            self.test_config_file_structure()
            self.test_database_operations()
            self.test_database_schema()
            self.test_all_staff_members()
            
            print("\n" + "=" * 50)
            print("🎉 ALL TESTS PASSED! Clean Architecture Implementation Successful!")
            print("\n📋 Summary:")
            print("   ✅ Config file contains only static data")
            print("   ✅ Database contains only dynamic data (invite codes)")
            print("   ✅ Methods correctly combine config + database data")
            print("   ✅ Redundant database columns set to NULL")
            print("   ✅ All staff members work correctly")
            
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
        except Exception as e:
            print(f"\n💥 UNEXPECTED ERROR: {e}")
        finally:
            self.cleanup()

if __name__ == "__main__":
    tester = TestCleanArchitecture()
    tester.run_all_tests()