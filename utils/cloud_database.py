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

logger = logging.getLogger(__name__)

class CloudAPIServerDatabase:
    """Cloud API database manager for server bot features"""
    
    def __init__(self, cloud_url: Optional[str] = None):
        self.cloud_base_url = cloud_url or "https://web-production-1299f.up.railway.app"  # Same as trading service
        self.db_path = "server_management.db"  # Local SQLite for temp storage
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "staff_config.json")
        self.init_database()
        self.load_staff_config()
        # Note: restore_from_cloud() will be called by the bot startup process
    
    def get_connection(self):
        """Get a local SQLite database connection"""
        return sqlite3.connect(self.db_path, timeout=10.0)
    
    def init_database(self):
        """Initialize SQLite database with cloud API backup capability"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Invite tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invite_tracking (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    invite_code TEXT,
                    inviter_id INTEGER,
                    inviter_username TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    invite_uses_before INTEGER,
                    invite_uses_after INTEGER
                )
            ''')
            
            # Staff invite configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staff_invites (
                    staff_id INTEGER PRIMARY KEY,
                    staff_username TEXT,
                    invite_code TEXT,
                    vantage_referral_link TEXT,
                    vantage_ib_code TEXT,
                    email_template TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # VIP upgrade requests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vip_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    request_type TEXT,
                    staff_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    vantage_email TEXT,
                    request_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ SQLite Server database initialized with cloud API backup capability")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQLite database: {e}")
            raise
    
    def load_staff_config(self) -> Dict:
        """Load staff configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load staff config: {e}")
            return {}
    
    def update_staff_invite_code(self, discord_id: int, invite_code: str) -> bool:
        """Update invite code for a staff member in database"""
        try:
            # Get staff info from config
            config = self.load_staff_config()
            staff_info = None
            
            for staff_key, info in config["staff_members"].items():
                if info["discord_id"] == discord_id:
                    staff_info = info
                    break
            
            if not staff_info:
                logger.warning(f"Staff member with Discord ID {discord_id} not found in config")
                return False
            
            # Store in database
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO staff_invites 
                (staff_id, staff_username, invite_code, vantage_referral_link, vantage_ib_code, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (discord_id, staff_info['username'], invite_code, 
                  staff_info['vantage_referral_link'], staff_info['vantage_ib_code'], 
                  datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated invite code for staff {discord_id}: {invite_code}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update staff invite code: {e}")
            return False
    
    def get_all_staff_invite_codes(self) -> set:
        """Get all staff invite codes from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT invite_code FROM staff_invites WHERE invite_code IS NOT NULL')
            results = cursor.fetchall()
            conn.close()
            
            return {row[0] for row in results if row[0]}
            
        except Exception as e:
            logger.error(f"Failed to get staff invite codes: {e}")
            return set()
    
    def get_staff_invite_status(self) -> Dict:
        """Get staff invite status from database"""
        try:
            config = self.load_staff_config()
            result = {}
            
            if config and 'staff_members' in config:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                for staff_key, staff_info in config['staff_members'].items():
                    discord_id = staff_info['discord_id']
                    username = staff_info['username']
                    
                    # Get invite code from database
                    cursor.execute('SELECT invite_code FROM staff_invites WHERE staff_id = ?', (discord_id,))
                    row = cursor.fetchone()
                    
                    invite_code = row[0] if row and row[0] else None
                    result[username] = invite_code
                
                conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get staff invite status: {e}")
            return {}
    
    def debug_staff_invites_table(self) -> str:
        """Debug method to see all data in staff_invites table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM staff_invites')
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return "❌ No data in staff_invites table"
            
            result = "📊 Staff Invites Table Contents:\n"
            for row in rows:
                result += f"• Staff ID: {row[0]}, Username: {row[1]}, Invite: {row[2]}\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error reading staff_invites table: {e}"
    
    def manually_add_staff_invite(self, discord_id: int, invite_code: str) -> bool:
        """Manually add existing staff invite codes"""
        return self.update_staff_invite_code(discord_id, invite_code)
    
    def record_user_join(self, user_id: int, username: str, invite_code: str, 
                        inviter_id: int, inviter_username: str, 
                        uses_before: int, uses_after: int) -> bool:
        """Record when a user joins through a specific invite"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO invite_tracking 
                (user_id, username, invite_code, inviter_id, inviter_username, 
                 joined_at, invite_uses_before, invite_uses_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, invite_code, inviter_id, inviter_username,
                  datetime.now(), uses_before, uses_after))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Recorded user join: {username} via invite {invite_code}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error recording user join: {e}")
            return False
    
    def get_user_invite_info(self, user_id: int) -> Optional[Dict]:
        """Get invite information for a user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT invite_code, inviter_id, inviter_username, joined_at
                FROM invite_tracking 
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'invite_code': row[0],
                    'inviter_id': row[1], 
                    'inviter_username': row[2],
                    'joined_at': row[3]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user invite info: {e}")
            return None
    
    def create_vip_request(self, user_id: int, username: str, request_type: str, 
                          attributed_staff: str, staff_ib_code: str) -> int:
        """Create a new VIP upgrade request"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO vip_requests (user_id, username, request_type, staff_id, status, request_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, request_type, 0, 'pending', 
                  json.dumps({'attributed_staff': attributed_staff, 'staff_ib_code': staff_ib_code}),
                  datetime.now()))
            
            request_id = cursor.lastrowid or 0
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Created VIP request {request_id} for {attributed_staff}")
            return request_id
            
        except Exception as e:
            logger.error(f"❌ Error creating VIP request: {e}")
            return 0
    
    async def backup_to_cloud(self):
        """Backup staff data to cloud API following trading service pattern"""
        if not self.cloud_base_url:
            logger.warning("No cloud API URL configured, skipping backup")
            return
            
        try:
            # Get all data from local SQLite
            conn = sqlite3.connect(self.db_path)
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
            
            # VIP requests
            cursor.execute('SELECT * FROM vip_requests')
            vip_requests = [dict(row) for row in cursor.fetchall()]
            backup_data['vip_requests'] = vip_requests
            
            conn.close()
            
            # Send to cloud API
            backup_endpoint = f"{self.cloud_base_url}/backup_server_data"
            response = requests.post(backup_endpoint, json=backup_data, timeout=30)
            
            if response.status_code == 200:
                logger.info("✅ Successfully backed up staff data to cloud API")
            else:
                logger.error(f"❌ Cloud backup failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Error backing up to cloud: {e}")
    
    async def restore_from_cloud(self):
        """Restore staff data from cloud API following trading service pattern"""
        if not self.cloud_base_url:
            logger.warning("No cloud API URL configured, skipping restore")
            return
            
        try:
            # Get data from cloud API
            restore_endpoint = f"{self.cloud_base_url}/restore_server_data"
            response = requests.get(restore_endpoint, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"No cloud data to restore: {response.status_code}")
                return
                
            backup_data = response.json()
            
            # Restore to local SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM staff_invites')
            cursor.execute('DELETE FROM invite_tracking')
            cursor.execute('DELETE FROM vip_requests')
            
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
                         joined_at, invite_uses_before, invite_uses_after)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row.get('user_id'), row.get('username'), row.get('invite_code'),
                          row.get('inviter_id'), row.get('inviter_username'), row.get('joined_at'),
                          row.get('invite_uses_before'), row.get('invite_uses_after')))
            
            # Restore VIP requests
            if 'vip_requests' in backup_data:
                for row in backup_data['vip_requests']:
                    cursor.execute('''
                        INSERT INTO vip_requests 
                        (id, user_id, username, request_type, staff_id, status, 
                         vantage_email, request_data, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row.get('id'), row.get('user_id'), row.get('username'),
                          row.get('request_type'), row.get('staff_id'), row.get('status'),
                          row.get('vantage_email'), row.get('request_data'), 
                          row.get('created_at'), row.get('updated_at')))
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Successfully restored staff data from cloud API")
            
        except Exception as e:
            logger.error(f"❌ Error restoring from cloud: {e}")
    
    async def periodic_backup(self):
        """Periodic backup every 30 minutes"""
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            await self.backup_to_cloud()