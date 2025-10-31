"""
Tests for database layer including migrations and cloud operations
"""

import unittest
import os
import sqlite3
from datetime import datetime
from unittest.mock import patch, MagicMock
from ..database.migrations import MigrationManager
from ..database.cloud_database import CloudAPIServerDatabase

class TestDatabaseMigrations(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_db.sqlite"
        # Ensure test DB doesn't exist
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.migration_manager = MigrationManager(self.test_db)
    
    def tearDown(self):
        # Clean up test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
    def test_migrations_table_created(self):
        """Test that migrations table is created properly"""
        self.migration_manager.init_migrations()
        
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Check migrations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='migrations'
        """)
        self.assertIsNotNone(cursor.fetchone())
        
        # Check table structure
        cursor.execute('PRAGMA table_info(migrations)')
        columns = {row[1] for row in cursor.fetchall()}
        
        expected_columns = {'migration_id', 'migration_name', 'applied_at'}
        self.assertEqual(columns, expected_columns)
        
        conn.close()
        
    def test_migrations_applied_in_order(self):
        """Test that migrations are applied in correct order"""
        self.assertTrue(self.migration_manager.create_all_tables())
        
        applied = self.migration_manager.get_applied_migrations()
        expected_order = [
            'create_invite_tracking',
            'create_staff_invites',
            'create_vip_requests',
            'create_onboarding_progress'
        ]
        
        self.assertEqual(applied, expected_order)
        
    def test_duplicate_migrations_handled(self):
        """Test that duplicate migrations are handled properly"""
        # Apply migrations first time
        self.assertTrue(self.migration_manager.create_all_tables())
        
        # Try to apply again
        self.assertTrue(self.migration_manager.create_all_tables())
        
        # Check only one instance of each migration
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT migration_name, COUNT(*) FROM migrations GROUP BY migration_name')
        counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        for name in counts.values():
            self.assertEqual(name, 1)  # Each migration should only appear once
            
        conn.close()

class TestCloudDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_cloud_db.sqlite"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
        # Mock cloud API URL
        self.cloud_url = "http://test-api"
        self.db = CloudAPIServerDatabase(self.cloud_url)
        self.db.db_path = self.test_db
        
    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
    def test_staff_invite_tracking(self):
        """Test staff invite code management"""
        # Add staff invite
        staff_id = 123456
        username = "test_staff"
        invite = "abc123"
        
        self.assertTrue(
            self.db.update_staff_invite_code(staff_id, username, invite)
        )
        
        # Verify invite was added
        invite_codes = self.db.get_all_staff_invite_codes()
        self.assertIn(invite, invite_codes)
        
        # Check staff status
        status = self.db.get_staff_invite_status()
        self.assertIn(staff_id, status)
        self.assertEqual(status[staff_id]['staff_username'], username)
        self.assertEqual(status[staff_id]['invite_code'], invite)
        
    def test_invite_usage_tracking(self):
        """Test tracking member joins through invites"""
        user_id = 789012
        username = "new_member"
        invite = "xyz789"
        inviter_id = 123456
        inviter_name = "staff_member"
        uses_before = 5
        uses_after = 6
        
        self.assertTrue(
            self.db.track_user_invite(
                user_id, username, invite,
                inviter_id, inviter_name,
                uses_before, uses_after
            )
        )
        
        # Check tracking record
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM invite_tracking WHERE user_id = ?',
            (user_id,)
        )
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[1], username)  # username
        self.assertEqual(row[2], invite)    # invite_code
        self.assertEqual(row[3], inviter_id) # inviter_id
        
        conn.close()
        
    @patch('requests.post')
    def test_cloud_backup(self, mock_post):
        """Test cloud backup functionality"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Add some test data
        self.db.update_staff_invite_code(123, "staff1", "invite1")
        self.db.track_user_invite(456, "user1", "invite1", 123, "staff1", 0, 1)
        
        # Trigger backup
        self.assertTrue(self.db.backup_to_cloud())
        
        # Verify backup was called
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args
        
        # Check endpoint
        self.assertTrue(call_args[0][0].endswith('/backup_discord_data'))
        
        # Check backup data structure
        backup_data = call_args[1]['json']['discord_data']
        self.assertIn('staff_invites', backup_data)
        self.assertIn('invite_tracking', backup_data)
        
    @patch('requests.get')
    def test_cloud_restore(self, mock_get):
        """Test cloud restore functionality"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'discord_data': {
                'staff_invites': [{
                    'staff_id': 123,
                    'staff_username': 'test_staff',
                    'invite_code': 'test_invite'
                }],
                'invite_tracking': [{
                    'user_id': 456,
                    'username': 'test_user',
                    'invite_code': 'test_invite',
                    'inviter_id': 123,
                    'inviter_username': 'test_staff',
                    'invite_uses_before': 0,
                    'invite_uses_after': 1
                }]
            }
        }
        mock_get.return_value = mock_response
        
        # Perform restore
        self.assertTrue(self.db.restore_from_cloud())
        
        # Verify data was restored
        status = self.db.get_staff_invite_status()
        self.assertIn(123, status)
        self.assertEqual(status[123]['staff_username'], 'test_staff')
        
        # Check referrals were restored
        referrals = self.db.get_staff_referrals(123)
        self.assertEqual(len(referrals), 1)
        self.assertEqual(referrals[0]['username'], 'test_user')

if __name__ == '__main__':
    unittest.main()