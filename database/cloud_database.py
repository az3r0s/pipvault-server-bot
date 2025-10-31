"""
Cloud API Database Management for Server Bot
============================================

Handles database operations using Railway's web service as cloud storage API.
This provides persistent storage that survives deployments using the same pattern
as the main trading service.
"""

import sqlite3
import requests
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import os
import json
from .migrations import MigrationManager

logger = logging.getLogger(__name__)

class CloudAPIServerDatabase:
    """Cloud API database manager for server bot features"""
    
    def __init__(self, cloud_url: Optional[str] = None):
        self.cloud_base_url = cloud_url or "https://web-production-1299f.up.railway.app"  # Same as trading service
        self.db_path = "server_management.db"  # Local SQLite for temp storage
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "staff_config.json")
        
        # Initialize database via migrations 
        self.migration_manager = MigrationManager(self.db_path)
        self.migration_manager.create_all_tables()
        
        # Load configuration
        self.load_staff_config()
    
    def get_connection(self):
        """Get a local SQLite database connection"""
        return sqlite3.connect(self.db_path, timeout=10.0)
        
    def load_staff_config(self) -> Dict:
        """Load staff configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    self.staff_config = json.load(f)
                logger.info("✅ Staff configuration loaded from file")
                return self.staff_config
            else:
                self.staff_config = {}  # Initialize empty if no file
                logger.info("ℹ️ No staff config file found - using empty config")
                return {}
        except Exception as e:
            logger.error(f"❌ Failed to load staff config: {e}")
            self.staff_config = {}
            return {}
            
    def update_staff_invite_code(self, staff_id: int, staff_username: str, invite_code: str) -> bool:
        """Update or add a staff invite code with username"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert or update staff invite
            cursor.execute('''
                INSERT INTO staff_invites (staff_id, staff_username, invite_code, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(staff_id) DO UPDATE SET
                    staff_username = excluded.staff_username,
                    invite_code = excluded.invite_code,
                    updated_at = CURRENT_TIMESTAMP
            ''', (staff_id, staff_username, invite_code))
            
            conn.commit()
            conn.close()
            
            # Trigger cloud backup
            asyncio.create_task(self.backup_to_cloud())
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update staff invite code: {e}")
            return False
            
    def get_all_staff_invite_codes(self) -> set:
        """Get all staff invite codes from database"""
        try:
            conn = self.get_connection() 
            cursor = conn.cursor()
            
            cursor.execute('SELECT invite_code FROM staff_invites')
            invite_codes = set(code[0] for code in cursor.fetchall() if code[0])
            
            conn.close()
            return invite_codes
            
        except Exception as e:
            logger.error(f"❌ Failed to get staff invite codes: {e}")
            return set()
            
    def get_staff_invite_status(self) -> Dict[int, Dict]:
        """Get staff invite status with usernames"""
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row  # For dict-like rows
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.*, COUNT(it.user_id) as member_count
                FROM staff_invites s
                LEFT JOIN invite_tracking it ON s.invite_code = it.invite_code  
                GROUP BY s.staff_id
            ''')
            
            invite_data = {}
            for row in cursor.fetchall():
                row_dict = dict(row)
                invite_data[row_dict['staff_id']] = row_dict
                
            conn.close()
            return invite_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get staff invite status: {e}")
            return {}
            
    def track_user_invite(self, user_id: int, username: str, invite_code: str, 
                         inviter_id: int, inviter_username: str,
                         uses_before: int, uses_after: int) -> bool:
        """Track a new user joining via invite"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO invite_tracking
                (user_id, username, invite_code, inviter_id, inviter_username, 
                 invite_uses_before, invite_uses_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, invite_code, inviter_id, inviter_username,
                 uses_before, uses_after))
            
            conn.commit()
            conn.close()
            
            # Trigger cloud backup
            asyncio.create_task(self.backup_to_cloud())
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to track user invite: {e}")
            return False
            
    def get_staff_referrals(self, staff_id: int) -> List[Dict]:
        """Get list of members who joined via a staff member's invite"""
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # First get staff's invite code
            cursor.execute('SELECT invite_code FROM staff_invites WHERE staff_id = ?', 
                         (staff_id,))
            staff_row = cursor.fetchone()
            
            if not staff_row:
                return []
                
            invite_code = staff_row['invite_code']
            
            # Get all members who used this invite
            cursor.execute('''
                SELECT * FROM invite_tracking 
                WHERE invite_code = ?
                ORDER BY joined_at DESC
            ''', (invite_code,))
            
            referrals = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return referrals
            
        except Exception as e:
            logger.error(f"❌ Failed to get staff referrals: {e}")
            return []
            
    async def backup_to_cloud(self):
        """Backup staff data to cloud API following trading service pattern"""
        if not self.cloud_base_url:
            logger.warning("No cloud API URL configured, skipping backup")
            return
            
        try:
            # Get all data from local SQLite
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row  # For dict-like access
            cursor = conn.cursor()
            
            # Get all tables data
            backup_data = {}
            
            # Staff invites
            cursor.execute('SELECT * FROM staff_invites')
            staff_invites = [dict(row) for row in cursor.fetchall()]
            backup_data['staff_invites'] = staff_invites
            
            # Invite tracking  
            cursor.execute('SELECT * FROM invite_tracking')
            invite_tracking = [dict(row) for row in cursor.fetchall()]
            backup_data['invite_tracking'] = invite_tracking
            
            conn.close()
            
            # Send to cloud endpoint with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    backup_endpoint = f"{self.cloud_base_url}/backup_discord_data"
                    response = requests.post(
                        backup_endpoint,
                        json={"discord_data": backup_data},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        logger.info("✅ Database backed up to cloud storage")
                        return True
                    else:
                        logger.warning(f"⚠️ Backup failed with status {response.status_code}")
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Wait before retry
                        continue
                    logger.error(f"❌ Failed to backup to cloud: {e}")
                    break
                    
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare backup data: {e}")
            return False
            
    async def restore_from_cloud(self):
        """Restore staff data from cloud API following trading service pattern"""
        if not self.cloud_base_url:
            logger.warning("No cloud API URL configured, skipping restore")
            return
            
        try:
            # Get data from cloud API
            restore_endpoint = f"{self.cloud_base_url}/get_discord_data_backup"
            response = requests.get(restore_endpoint, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"No cloud data to restore: {response.status_code}")
                return
                
            response_data = response.json()
            backup_data = response_data.get('discord_data', {})
            
            # Restore to local SQLite
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM staff_invites')
            cursor.execute('DELETE FROM invite_tracking')
            
            # Restore staff invites
            if 'staff_invites' in backup_data:
                for row in backup_data['staff_invites']:
                    cursor.execute('''
                        INSERT INTO staff_invites 
                        (staff_id, staff_username, invite_code, vantage_referral_link, 
                         vantage_ib_code, email_template, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row.get('staff_id'), row.get('staff_username'), row.get('invite_code'),
                          row.get('vantage_referral_link'), row.get('vantage_ib_code'), 
                          row.get('email_template'), row.get('created_at'), row.get('updated_at')))
            
            # Restore invite tracking
            if 'invite_tracking' in backup_data:
                for row in backup_data['invite_tracking']:
                    cursor.execute('''
                        INSERT INTO invite_tracking
                        (user_id, username, invite_code, inviter_id, inviter_username,
                         invite_uses_before, invite_uses_after, joined_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row.get('user_id'), row.get('username'), row.get('invite_code'),
                          row.get('inviter_id'), row.get('inviter_username'),
                          row.get('invite_uses_before'), row.get('invite_uses_after'),
                          row.get('joined_at')))
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Database restored from cloud backup")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restore from cloud: {e}")
            return False
            
    def debug_staff_invites_table(self) -> str:
        """Debug method to see all data in staff_invites table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM staff_invites')
            rows = cursor.fetchall()
            
            if not rows:
                return "No staff invite data found"
                
            debug_output = ["Staff Invites Table Data:"]
            for row in rows:
                debug_output.append(str(row))
                
            conn.close()
            return "\n".join(debug_output)
            
        except Exception as e:
            return f"Error getting debug data: {e}"