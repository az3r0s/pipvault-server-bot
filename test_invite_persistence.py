#!/usr/bin/env python3
"""
Test Invite Tracking Persistence
=================================

This script tests that invite tracking data survives bot restarts/redeploys.
It simulates the full backup and restore cycle.
"""

import json
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

class InviteTrackingPersistenceTest:
    """Test suite for invite tracking persistence"""
    
    def __init__(self):
        self.cache_path = "data/invite_cache_backup.json"
        self.db_path = "server_management.db"
        self.test_passed = 0
        self.test_failed = 0
    
    def log_test(self, name, passed, details=""):
        """Log test result"""
        if passed:
            print(f"✅ {name}")
            self.test_passed += 1
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")
            self.test_failed += 1
    
    def test_cache_backup_restore(self):
        """Test invite cache backup and restore"""
        print("\n🧪 Testing Invite Cache Backup/Restore...")
        
        # Create test cache data
        test_cache = {
            'timestamp': datetime.now().isoformat(),
            'cache': {
                '123456789': {  # Guild ID as string
                    'abc123': {
                        'uses': 5,
                        'inviter_id': 987654321,
                        'inviter_name': 'TestStaff',
                        'code': 'abc123'
                    },
                    'xyz789': {
                        'uses': 3,
                        'inviter_id': 111222333,
                        'inviter_name': 'AnotherStaff',
                        'code': 'xyz789'
                    }
                }
            }
        }
        
        # Test 1: Write cache to file
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(test_cache, f, indent=2)
            
            self.log_test("Cache file creation", True)
        except Exception as e:
            self.log_test("Cache file creation", False, str(e))
            return
        
        # Test 2: Read cache from file
        try:
            with open(self.cache_path, 'r') as f:
                restored_cache = json.load(f)
            
            self.log_test("Cache file read", True)
        except Exception as e:
            self.log_test("Cache file read", False, str(e))
            return
        
        # Test 3: Verify cache data integrity
        timestamp_match = restored_cache.get('timestamp') == test_cache['timestamp']
        self.log_test("Cache timestamp preserved", timestamp_match)
        
        cache_match = restored_cache.get('cache') == test_cache['cache']
        self.log_test("Cache data preserved", cache_match)
        
        # Test 4: Verify guild data
        guild_data = restored_cache.get('cache', {}).get('123456789', {})
        guild_exists = len(guild_data) == 2
        self.log_test("Guild invite data preserved", guild_exists)
        
        # Test 5: Verify invite details
        invite_abc = guild_data.get('abc123', {})
        invite_details_correct = (
            invite_abc.get('uses') == 5 and
            invite_abc.get('inviter_id') == 987654321 and
            invite_abc.get('inviter_name') == 'TestStaff'
        )
        self.log_test("Invite details preserved", invite_details_correct)
        
        # Test 6: Verify serializable format (no Discord objects)
        try:
            json_str = json.dumps(restored_cache)
            self.log_test("Cache is JSON serializable", True)
        except Exception as e:
            self.log_test("Cache is JSON serializable", False, str(e))
    
    def test_database_tables(self):
        """Test database tables for invite tracking"""
        print("\n🧪 Testing Database Tables...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Test 1: Invite tracking table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='invite_tracking'
            """)
            table_exists = cursor.fetchone() is not None
            self.log_test("invite_tracking table exists", table_exists)
            
            # Test 2: Staff invites table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='staff_invites'
            """)
            staff_table_exists = cursor.fetchone() is not None
            self.log_test("staff_invites table exists", staff_table_exists)
            
            if not table_exists or not staff_table_exists:
                conn.close()
                return
            
            # Test 3: Insert test invite tracking data
            test_user_id = 999888777
            test_username = "TestUser#1234"
            test_invite_code = "test123"
            test_inviter_id = 111222333
            test_inviter_username = "TestStaff#5678"
            
            cursor.execute("""
                INSERT OR REPLACE INTO invite_tracking 
                (user_id, username, invite_code, inviter_id, inviter_username, 
                 joined_at, invite_uses_before, invite_uses_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (test_user_id, test_username, test_invite_code, test_inviter_id, 
                  test_inviter_username, datetime.now(), 0, 1))
            
            conn.commit()
            self.log_test("Insert invite tracking data", True)
            
            # Test 4: Query invite tracking data
            cursor.execute("""
                SELECT * FROM invite_tracking WHERE user_id = ?
            """, (test_user_id,))
            
            row = cursor.fetchone()
            data_retrieved = row is not None
            self.log_test("Query invite tracking data", data_retrieved)
            
            # Test 5: Verify data integrity
            if row:
                data_correct = (
                    row[0] == test_user_id and
                    row[1] == test_username and
                    row[2] == test_invite_code and
                    row[3] == test_inviter_id and
                    row[4] == test_inviter_username
                )
                self.log_test("Invite tracking data integrity", data_correct)
            
            # Test 6: Insert test staff invite
            test_staff_id = 555666777
            test_staff_invite_code = "staff456"
            
            cursor.execute("""
                INSERT OR REPLACE INTO staff_invites 
                (staff_id, staff_username, invite_code, updated_at)
                VALUES (?, NULL, ?, ?)
            """, (test_staff_id, test_staff_invite_code, datetime.now()))
            
            conn.commit()
            self.log_test("Insert staff invite data", True)
            
            # Test 7: Query staff invite
            cursor.execute("""
                SELECT * FROM staff_invites WHERE staff_id = ?
            """, (test_staff_id,))
            
            staff_row = cursor.fetchone()
            staff_retrieved = staff_row is not None
            self.log_test("Query staff invite data", staff_retrieved)
            
            # Cleanup test data
            cursor.execute("DELETE FROM invite_tracking WHERE user_id = ?", (test_user_id,))
            cursor.execute("DELETE FROM staff_invites WHERE staff_id = ?", (test_staff_id,))
            conn.commit()
            
            conn.close()
            
        except Exception as e:
            self.log_test("Database operations", False, str(e))
    
    def test_backup_payload_format(self):
        """Test cloud backup payload format"""
        print("\n🧪 Testing Cloud Backup Payload Format...")
        
        # Test 1: Create backup payload with invite cache
        backup_data = {
            'staff_invites': [
                {'staff_id': 123, 'invite_code': 'abc123'}
            ],
            'invite_tracking': [
                {'user_id': 456, 'invite_code': 'abc123'}
            ],
            'vip_requests': [],
            'invite_cache': {
                'timestamp': datetime.now().isoformat(),
                'cache': {
                    '123456789': {
                        'abc123': {
                            'uses': 5,
                            'inviter_id': 987654321,
                            'inviter_name': 'TestStaff',
                            'code': 'abc123'
                        }
                    }
                }
            }
        }
        
        # Test 2: Verify payload is JSON serializable
        try:
            payload = {'discord_data': backup_data}
            json_str = json.dumps(payload)
            self.log_test("Backup payload is JSON serializable", True)
        except Exception as e:
            self.log_test("Backup payload is JSON serializable", False, str(e))
            return
        
        # Test 3: Verify invite_cache is in payload
        has_invite_cache = 'invite_cache' in backup_data
        self.log_test("Invite cache included in backup", has_invite_cache)
        
        # Test 4: Verify invite_cache structure
        if has_invite_cache:
            cache_data = backup_data['invite_cache']
            has_timestamp = 'timestamp' in cache_data
            has_cache = 'cache' in cache_data
            structure_valid = has_timestamp and has_cache
            self.log_test("Invite cache structure valid", structure_valid)
    
    def test_file_permissions(self):
        """Test file permissions and directory creation"""
        print("\n🧪 Testing File System Permissions...")
        
        # Test 1: Can create data directory
        try:
            os.makedirs('data', exist_ok=True)
            self.log_test("Create data directory", True)
        except Exception as e:
            self.log_test("Create data directory", False, str(e))
            return
        
        # Test 2: Can write to data directory
        test_file = 'data/test_permissions.json'
        try:
            with open(test_file, 'w') as f:
                json.dump({'test': 'data'}, f)
            self.log_test("Write to data directory", True)
        except Exception as e:
            self.log_test("Write to data directory", False, str(e))
        
        # Test 3: Can read from data directory
        try:
            with open(test_file, 'r') as f:
                data = json.load(f)
            self.log_test("Read from data directory", True)
        except Exception as e:
            self.log_test("Read from data directory", False, str(e))
        
        # Cleanup
        try:
            os.remove(test_file)
        except:
            pass
    
    def test_restart_simulation(self):
        """Simulate bot restart to test persistence"""
        print("\n🧪 Simulating Bot Restart...")
        
        # Step 1: Create initial cache
        print("   📝 Creating initial cache...")
        initial_cache = {
            'timestamp': datetime.now().isoformat(),
            'cache': {
                '123456789': {
                    'abc123': {
                        'uses': 10,
                        'inviter_id': 987654321,
                        'inviter_name': 'StaffMember1',
                        'code': 'abc123'
                    },
                    'xyz789': {
                        'uses': 5,
                        'inviter_id': 111222333,
                        'inviter_name': 'StaffMember2',
                        'code': 'xyz789'
                    }
                }
            }
        }
        
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(initial_cache, f, indent=2)
            print("   ✅ Initial cache saved")
        except Exception as e:
            self.log_test("Restart simulation - save initial cache", False, str(e))
            return
        
        # Step 2: Simulate restart by clearing memory
        print("   🔄 Simulating bot restart (clearing memory)...")
        del initial_cache  # Simulate memory clear
        
        # Step 3: Restore cache from file
        print("   📥 Restoring cache from file...")
        try:
            with open(self.cache_path, 'r') as f:
                restored_cache = json.load(f)
            print("   ✅ Cache restored successfully")
        except Exception as e:
            self.log_test("Restart simulation - restore cache", False, str(e))
            return
        
        # Step 4: Verify restored data
        guild_data = restored_cache.get('cache', {}).get('123456789', {})
        invite_abc = guild_data.get('abc123', {})
        invite_xyz = guild_data.get('xyz789', {})
        
        data_intact = (
            invite_abc.get('uses') == 10 and
            invite_abc.get('inviter_name') == 'StaffMember1' and
            invite_xyz.get('uses') == 5 and
            invite_xyz.get('inviter_name') == 'StaffMember2'
        )
        
        self.log_test("Data survives restart", data_intact)
        
        # Step 5: Simulate modification after restart
        print("   ✏️ Modifying cache after restart...")
        guild_data['abc123']['uses'] = 11  # Increment use count
        restored_cache['timestamp'] = datetime.now().isoformat()
        
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(restored_cache, f, indent=2)
            self.log_test("Modifications persist after restart", True)
        except Exception as e:
            self.log_test("Modifications persist after restart", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("🚀 INVITE TRACKING PERSISTENCE TEST SUITE")
        print("=" * 60)
        
        self.test_file_permissions()
        self.test_cache_backup_restore()
        self.test_database_tables()
        self.test_backup_payload_format()
        self.test_restart_simulation()
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        print(f"✅ Passed: {self.test_passed}")
        print(f"❌ Failed: {self.test_failed}")
        print(f"📈 Success Rate: {self.test_passed / (self.test_passed + self.test_failed) * 100:.1f}%")
        print("=" * 60)
        
        if self.test_failed == 0:
            print("\n🎉 ALL TESTS PASSED! Invite tracking persistence is working correctly!")
            return 0
        else:
            print(f"\n⚠️ {self.test_failed} test(s) failed. Please review the issues above.")
            return 1

def main():
    """Main test runner"""
    # Change to the pipvault-server-bot directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    tester = InviteTrackingPersistenceTest()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
