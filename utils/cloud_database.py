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
            # Only create directory if db_path contains a directory
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
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
            
            # Onboarding progress table (welcome system)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS onboarding_progress (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    step INTEGER DEFAULT 1,
                    completed BOOLEAN DEFAULT FALSE,
                    welcome_reacted BOOLEAN DEFAULT FALSE,
                    rules_reacted BOOLEAN DEFAULT FALSE, 
                    faq_reacted BOOLEAN DEFAULT FALSE,
                    chat_introduced BOOLEAN DEFAULT FALSE,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    last_step_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Onboarding analytics table (welcome system)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS onboarding_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    event_type TEXT, -- 'member_joined', 'step_completed', 'onboarding_completed'
                    step_name TEXT, -- 'welcome_react', 'rules_react', 'faq_react', 'chat_intro'
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT -- JSON data for additional context
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
        """
        Update invite code for a staff member using clean architecture:
        - Only stores dynamic data (invite_code) in database
        - Static data comes from config file
        """
        try:
            # Verify staff exists in config first
            config = self.load_staff_config()
            staff_info = None
            
            for staff_key, info in config["staff_members"].items():
                if info["discord_id"] == discord_id:
                    staff_info = info
                    break
            
            if not staff_info:
                logger.warning(f"Staff member with Discord ID {discord_id} not found in config")
                return False
            
            # Store only dynamic data in database, set static columns to NULL
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO staff_invites 
                (staff_id, staff_username, invite_code, vantage_referral_link, vantage_ib_code, updated_at)
                VALUES (?, NULL, ?, NULL, NULL, ?)
            ''', (discord_id, invite_code, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Updated invite code for {staff_info['username']} (Discord ID: {discord_id}) with clean architecture")
            
            # Trigger immediate cloud backup
            self.trigger_backup()
            
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
    
    def record_user_join_manual(self, user_id: int, username: str, invite_code: str, 
                               inviter_id: int, inviter_username: str, joined_at=None) -> bool:
        """Manually record when a user joined through a specific invite"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            join_time = joined_at if joined_at else datetime.now()
            
            cursor.execute('''
                INSERT OR REPLACE INTO invite_tracking 
                (user_id, username, invite_code, inviter_id, inviter_username, 
                 joined_at, invite_uses_before, invite_uses_after)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1)
            ''', (user_id, username, invite_code, inviter_id, inviter_username, join_time))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Manually recorded user join: {username} via invite {invite_code}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error manually recording user join: {e}")
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
    
    def remove_user_invite_tracking(self, user_id: int) -> bool:
        """Remove invite tracking data when a user leaves the server"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user exists first
            cursor.execute('SELECT user_id FROM invite_tracking WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Remove from invite tracking
                cursor.execute('DELETE FROM invite_tracking WHERE user_id = ?', (user_id,))
                conn.commit()
                logger.info(f"✅ Removed invite tracking for user {user_id}")
                result = True
            else:
                logger.info(f"ℹ️ No invite tracking found for user {user_id}")
                result = False
                
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"❌ Error removing user invite tracking: {e}")
            return False
    
    def create_vip_request(self, user_id: int, username: str, request_type: str, 
                          staff_id: int, request_data: str) -> int:
        """Create a new VIP upgrade request"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO vip_requests (user_id, username, request_type, staff_id, status, request_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, request_type, staff_id, 'pending', request_data, datetime.now()))
            
            request_id = cursor.lastrowid or 0
            conn.commit()
            conn.close()
            
            # Trigger immediate cloud backup
            self.trigger_backup()
            
            logger.info(f"✅ Created VIP request {request_id} for staff ID {staff_id}")
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
            
            # Onboarding progress (new welcome system)
            try:
                cursor.execute('SELECT * FROM onboarding_progress')
                onboarding_progress = [dict(row) for row in cursor.fetchall()]
                backup_data['onboarding_progress'] = onboarding_progress
            except sqlite3.OperationalError:
                # Table doesn't exist yet
                backup_data['onboarding_progress'] = []
            
            # Onboarding analytics (new welcome system)
            try:
                cursor.execute('SELECT * FROM onboarding_analytics')
                onboarding_analytics = [dict(row) for row in cursor.fetchall()]
                backup_data['onboarding_analytics'] = onboarding_analytics
            except sqlite3.OperationalError:
                # Table doesn't exist yet
                backup_data['onboarding_analytics'] = []
            
            conn.close()
            
            # CRITICAL: Also backup invite cache from JSON file for complete persistence
            try:
                import os
                cache_path = "data/invite_cache_backup.json"
                if os.path.exists(cache_path):
                    with open(cache_path, 'r') as f:
                        invite_cache_data = json.load(f)
                    backup_data['invite_cache'] = invite_cache_data
                    logger.info("📦 Added invite cache to cloud backup")
            except Exception as cache_error:
                logger.warning(f"⚠️ Could not add invite cache to backup: {cache_error}")
            
            # Send to cloud API using discord_data format
            backup_endpoint = f"{self.cloud_base_url}/backup_discord_data"
            payload = {'discord_data': backup_data}
            response = requests.post(backup_endpoint, json=payload, timeout=30)
            
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
            # Get data from cloud API with cache-busting to force fresh data
            import time
            cache_buster = int(time.time())
            restore_endpoint = f"{self.cloud_base_url}/get_discord_data_backup?t={cache_buster}"
            logger.info(f"🌐 Restoring from cloud with cache-buster: t={cache_buster}")
            response = requests.get(restore_endpoint, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"No cloud data to restore: {response.status_code}")
                return
                
            response_data = response.json()
            backup_data = response_data.get('discord_data', {})
            
            # Validate backup timestamp to detect stale data
            if 'invite_cache' in backup_data and isinstance(backup_data['invite_cache'], dict):
                cache_timestamp = backup_data['invite_cache'].get('last_updated')
                if cache_timestamp:
                    try:
                        from datetime import datetime, timedelta
                        backup_time = datetime.fromisoformat(cache_timestamp.replace('Z', '+00:00'))
                        age_seconds = (datetime.now(backup_time.tzinfo) - backup_time).total_seconds()
                        age_minutes = age_seconds / 60
                        
                        logger.info(f"📅 Cloud backup age: {age_minutes:.1f} minutes (from {cache_timestamp})")
                        
                        if age_minutes > 60:  # Warn if backup is over 1 hour old
                            logger.warning(f"⚠️ Cloud backup is {age_minutes:.1f} minutes old - may be stale!")
                        elif age_minutes > 1440:  # Error if over 24 hours
                            logger.error(f"🔴 Cloud backup is {age_minutes/60:.1f} HOURS old - likely stale data!")
                    except Exception as ts_error:
                        logger.warning(f"Could not parse backup timestamp: {ts_error}")
            
            # Restore to local SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM staff_invites')
            cursor.execute('DELETE FROM invite_tracking')
            cursor.execute('DELETE FROM vip_requests')
            
            # Clear onboarding tables if they exist
            try:
                cursor.execute('DELETE FROM onboarding_progress')
            except sqlite3.OperationalError:
                pass  # Table doesn't exist yet
            try:
                cursor.execute('DELETE FROM onboarding_analytics')
            except sqlite3.OperationalError:
                pass  # Table doesn't exist yet
            
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
            
            # Restore onboarding progress (new welcome system)
            try:
                cursor.execute('DELETE FROM onboarding_progress')
                if 'onboarding_progress' in backup_data:
                    for row in backup_data['onboarding_progress']:
                        cursor.execute('''
                            INSERT INTO onboarding_progress 
                            (user_id, current_step, started_at, completed_at, last_updated)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (row.get('user_id'), row.get('current_step'), row.get('started_at'),
                              row.get('completed_at'), row.get('last_updated')))
            except sqlite3.OperationalError:
                # Table doesn't exist yet, skip
                pass
            
            # Restore onboarding analytics (new welcome system)
            try:
                cursor.execute('DELETE FROM onboarding_analytics')
                if 'onboarding_analytics' in backup_data:
                    for row in backup_data['onboarding_analytics']:
                        cursor.execute('''
                            INSERT INTO onboarding_analytics 
                            (id, user_id, event_type, step_name, timestamp, metadata)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (row.get('id'), row.get('user_id'), row.get('event_type'),
                              row.get('step_name'), row.get('timestamp'), row.get('metadata')))
            except sqlite3.OperationalError:
                # Table doesn't exist yet, skip
                pass
            
            conn.commit()
            conn.close()
            
            # CRITICAL: Also restore invite cache from cloud backup
            try:
                import os
                if 'invite_cache' in backup_data:
                    cache_path = "data/invite_cache_backup.json"
                    os.makedirs(os.path.dirname(cache_path) if os.path.dirname(cache_path) else "data", exist_ok=True)
                    
                    with open(cache_path, 'w') as f:
                        json.dump(backup_data['invite_cache'], f, indent=2)
                    
                    logger.info("✅ Restored invite cache from cloud backup")
            except Exception as cache_error:
                logger.warning(f"⚠️ Could not restore invite cache from cloud: {cache_error}")
            
            logger.info("✅ Successfully restored staff data from cloud API")
            
        except Exception as e:
            logger.error(f"❌ Error restoring from cloud: {e}")
    
    def get_staff_by_discord_id(self, discord_id: int) -> Optional[Dict]:
        """
        Get staff member info by Discord ID using clean architecture:
        - Static data (discord_id, username, vantage_referral_link, vantage_ib_code) from config file
        - Dynamic data (invite_code) from database
        """
        try:
            # First get static data from config file
            config = self.load_staff_config()
            staff_static_data = None
            
            for staff_key, staff_info in config["staff_members"].items():
                if staff_info["discord_id"] == discord_id:
                    staff_static_data = {
                        'discord_id': staff_info["discord_id"],
                        'username': staff_info["username"],
                        'vantage_referral_link': staff_info["vantage_referral_link"],
                        'vantage_ib_code': staff_info["vantage_ib_code"]
                    }
                    break
            
            if not staff_static_data:
                return None  # Staff member not found in config
            
            # Now get dynamic data (invite_code) from database
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT invite_code
                FROM staff_invites 
                WHERE staff_id = ?
            ''', (discord_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            # Combine static and dynamic data
            combined_data = staff_static_data.copy()
            if result:
                combined_data['invite_code'] = result[0]
            else:
                combined_data['invite_code'] = None  # No invite code generated yet
                
            return combined_data
            
        except Exception as e:
            logger.error(f"❌ Error getting staff by Discord ID {discord_id}: {e}")
            return None

    def get_staff_config_by_invite(self, invite_code: str) -> Optional[Dict]:
        """
        Get staff member info by invite code using clean architecture:
        - Get Discord ID from database using invite code
        - Get static data from config file using Discord ID
        - Combine with invite code
        """
        try:
            # First get Discord ID from database using invite code
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT staff_id
                FROM staff_invites 
                WHERE invite_code = ?
            ''', (invite_code,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None  # Invite code not found
                
            discord_id = row[0]
            
            # Now get static data from config file
            config = self.load_staff_config()
            for staff_key, staff_info in config["staff_members"].items():
                if staff_info["discord_id"] == discord_id:
                    return {
                        'discord_id': staff_info["discord_id"],
                        'username': staff_info["username"],
                        'vantage_referral_link': staff_info["vantage_referral_link"],
                        'vantage_ib_code': staff_info["vantage_ib_code"],
                        'invite_code': invite_code
                    }
            
            # If we reach here, invite code exists in DB but Discord ID not in config
            logger.warning(f"⚠️ Invite code {invite_code} found in DB but Discord ID {discord_id} not in config")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting staff config by invite: {e}")
            return None

    def add_staff_invite_config(self, staff_id: int, invite_code: str, email_template: str) -> bool:
        """
        Add or update staff invite configuration using clean architecture:
        - Only stores dynamic data (invite_code, email_template) in database
        - Static data (username, vantage links) comes from config file
        - Sets redundant columns to NULL for clean separation
        """
        try:
            # Verify staff exists in config first
            config = self.load_staff_config()
            staff_exists = False
            staff_username = None
            
            for staff_key, staff_info in config["staff_members"].items():
                if staff_info["discord_id"] == staff_id:
                    staff_exists = True
                    staff_username = staff_info["username"]
                    break
            
            if not staff_exists:
                logger.error(f"❌ Staff member with Discord ID {staff_id} not found in config file")
                return False
            
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Store only dynamic data, set static data columns to NULL for clean architecture
            cursor.execute('''
                INSERT OR REPLACE INTO staff_invites 
                (staff_id, staff_username, invite_code, vantage_referral_link, 
                 vantage_ib_code, email_template, updated_at)
                VALUES (?, NULL, ?, NULL, NULL, ?, ?)
            ''', (staff_id, invite_code, email_template, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Updated invite code for {staff_username} (Discord ID: {staff_id}) with clean architecture")
            
            # Trigger immediate cloud backup
            self.trigger_backup()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating staff invite config: {e}")
            return False

    def update_vip_request_status(self, request_id: int, status: str, 
                                 vantage_email: Optional[str] = None) -> bool:
        """Update VIP request status"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            if vantage_email:
                cursor.execute('''
                    UPDATE vip_requests 
                    SET status = ?, vantage_email = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, vantage_email, datetime.now(), request_id))
            else:
                cursor.execute('''
                    UPDATE vip_requests 
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, datetime.now(), request_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Updated VIP request {request_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating VIP request: {e}")
            return False

    def get_vip_requests_by_status(self, status: Optional[str] = None) -> List[Dict]:
        """Get VIP requests filtered by status"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            if status and status != 'all':
                cursor.execute('''
                    SELECT id, user_id, username, request_type, staff_id, status, 
                           vantage_email, created_at, updated_at
                    FROM vip_requests 
                    WHERE status = ?
                    ORDER BY created_at DESC
                ''', (status,))
            else:
                cursor.execute('''
                    SELECT id, user_id, username, request_type, staff_id, status, 
                           vantage_email, created_at, updated_at
                    FROM vip_requests 
                    ORDER BY created_at DESC
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            requests = []
            for row in results:
                requests.append({
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'request_type': row[3],
                    'staff_id': row[4],
                    'status': row[5],
                    'vantage_email': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            
            return requests
            
        except Exception as e:
            logger.error(f"❌ Error getting VIP requests: {e}")
            return []

    def get_user_vip_requests(self, user_id: int) -> List[Dict]:
        """Get all VIP requests for a specific user"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, username, request_type, staff_id, status, 
                       vantage_email, created_at, updated_at
                FROM vip_requests 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            requests = []
            for row in results:
                requests.append({
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'request_type': row[3],
                    'staff_id': row[4],
                    'status': row[5],
                    'vantage_email': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            
            return requests
            
        except Exception as e:
            logger.error(f"❌ Error getting user VIP requests: {e}")
            return []

    def get_staff_vip_stats(self, staff_id: int) -> Dict:
        """Get VIP conversion stats for a staff member"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # First get the staff member's invite code
            cursor.execute('''
                SELECT invite_code FROM staff_invites WHERE staff_id = ?
            ''', (staff_id,))
            
            invite_row = cursor.fetchone()
            if not invite_row or not invite_row[0]:
                conn.close()
                return {'total_invites': 0, 'vip_conversions': 0, 'pending_requests': 0, 'conversion_rate': 0}
            
            invite_code = invite_row[0]
            
            # Get total invites using invite code instead of inviter_id
            cursor.execute('''
                SELECT COUNT(*) FROM invite_tracking WHERE invite_code = ?
            ''', (invite_code,))
            total_invites = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM vip_requests WHERE staff_id = ? AND status = 'completed'
            ''', (staff_id,))
            vip_conversions = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM vip_requests WHERE staff_id = ? AND status = 'pending'
            ''', (staff_id,))
            pending_requests = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_invites': total_invites,
                'vip_conversions': vip_conversions,
                'pending_requests': pending_requests,
                'conversion_rate': (vip_conversions / total_invites * 100) if total_invites > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting staff stats: {e}")
            return {'total_invites': 0, 'vip_conversions': 0, 'pending_requests': 0, 'conversion_rate': 0}

    def get_all_staff_configs(self) -> List[Dict]:
        """Get all staff invite configurations"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT staff_id, staff_username, invite_code, vantage_referral_link, created_at
                FROM staff_invites 
                ORDER BY created_at DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            staff_configs = []
            for row in results:
                staff_configs.append({
                    'staff_id': row[0],
                    'staff_username': row[1],
                    'invite_code': row[2],
                    'vantage_referral_link': row[3],
                    'created_at': row[4]
                })
            
            return staff_configs
            
        except Exception as e:
            logger.error(f"❌ Error getting all staff configs: {e}")
            return []

    def get_users_by_invite_code(self, invite_code: str) -> List[Dict]:
        """Get all users who joined through a specific invite code"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, invite_code, inviter_id, inviter_username, 
                       joined_at, invite_uses_before, invite_uses_after
                FROM invite_tracking 
                WHERE invite_code = ?
                ORDER BY joined_at DESC
            ''', (invite_code,))
            
            results = cursor.fetchall()
            conn.close()
            
            users = []
            for row in results:
                users.append({
                    'user_id': row[0],
                    'username': row[1],
                    'invite_code': row[2],
                    'inviter_id': row[3],
                    'inviter_username': row[4],
                    'joined_at': row[5],
                    'invite_uses_before': row[6],
                    'invite_uses_after': row[7]
                })
            
            return users
            
        except Exception as e:
            logger.error(f"❌ Error getting users by invite code: {e}")
            return []

    def update_staff_discord_id(self, old_discord_id: int, new_discord_id: int) -> bool:
        """Update Discord ID for a staff member (fixes ID mismatches)"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Update staff_invites table
            cursor.execute('''
                UPDATE staff_invites 
                SET staff_id = ?
                WHERE staff_id = ?
            ''', (new_discord_id, old_discord_id))
            
            # Update any VIP requests that reference this staff member
            cursor.execute('''
                UPDATE vip_requests 
                SET staff_id = ?
                WHERE staff_id = ?
            ''', (new_discord_id, old_discord_id))
            
            # Update invite tracking if the staff member was an inviter
            cursor.execute('''
                UPDATE invite_tracking 
                SET inviter_id = ?
                WHERE inviter_id = ?
            ''', (new_discord_id, old_discord_id))
            
            conn.commit()
            conn.close()
            
            # Trigger backup to sync changes
            self.trigger_backup()
            
            logger.info(f"✅ Updated Discord ID: {old_discord_id} → {new_discord_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating staff Discord ID: {e}")
            return False

    def trigger_backup(self):
        """Trigger immediate backup (non-blocking)"""
        try:
            # Create a simple backup using requests (synchronous)
            if not self.cloud_base_url:
                return
                
            # Get all data from local SQLite
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
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
            
            # CRITICAL: Also include invite cache in immediate backup
            try:
                import os
                cache_path = "data/invite_cache_backup.json"
                if os.path.exists(cache_path):
                    with open(cache_path, 'r') as f:
                        invite_cache_data = json.load(f)
                    backup_data['invite_cache'] = invite_cache_data
            except Exception as cache_error:
                logger.debug(f"No invite cache to backup: {cache_error}")
            
            # Send to cloud API using discord_data format
            backup_endpoint = f"{self.cloud_base_url}/backup_discord_data"
            payload = {'discord_data': backup_data}
            response = requests.post(backup_endpoint, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Immediate backup to cloud API successful")
            else:
                logger.warning(f"⚠️ Backup warning: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ Backup failed: {e}")

    def update_staff_username(self, staff_id: int, username: str) -> bool:
        """Update staff username in the database"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE staff_invites 
                SET staff_username = ? 
                WHERE staff_id = ?
            ''', (username, staff_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Updated staff username for ID {staff_id} to {username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating staff username: {e}")
            return False

    # ========================================
    # ONBOARDING SYSTEM METHODS  
    # ========================================
    
    async def init_onboarding_progress(self, user_id: str, username: str) -> bool:
        """Initialize onboarding progress for a new user"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO onboarding_progress 
                (user_id, username, step, completed, welcome_reacted, rules_reacted, faq_reacted, chat_introduced, started_at, last_step_at)
                VALUES (?, ?, 1, 0, 0, 0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, username))
            
            conn.commit()
            conn.close()
            
            # Trigger backup to cloud
            await self.backup_to_cloud()
            
            logger.info(f"✅ Initialized onboarding progress for {username} ({user_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize onboarding progress: {e}")
            return False
    
    async def update_onboarding_step(self, user_id: str, step_name: str) -> bool:
        """Update user's onboarding progress"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Update the specific step
            if step_name == "welcome_react":
                cursor.execute('''
                    UPDATE onboarding_progress 
                    SET welcome_reacted = 1, step = 2, last_step_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            elif step_name == "rules_react":
                cursor.execute('''
                    UPDATE onboarding_progress 
                    SET rules_reacted = 1, step = 3, last_step_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            elif step_name == "faq_react":
                cursor.execute('''
                    UPDATE onboarding_progress 
                    SET faq_reacted = 1, step = 4, last_step_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            elif step_name == "chat_intro":
                cursor.execute('''
                    UPDATE onboarding_progress 
                    SET chat_introduced = 1, completed = 1, completed_at = CURRENT_TIMESTAMP, last_step_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            # Trigger backup to cloud
            await self.backup_to_cloud()
            
            logger.info(f"✅ Updated onboarding step {step_name} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update onboarding step: {e}")
            return False
    
    async def log_onboarding_event(self, user_id: str, event_type: str, step_name: str, metadata: Optional[dict] = None) -> bool:
        """Log onboarding analytics event"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute('''
                INSERT INTO onboarding_analytics (user_id, event_type, step_name, metadata)
                VALUES (?, ?, ?, ?)
            ''', (user_id, event_type, step_name, metadata_json))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to log onboarding event: {e}")
            return False
    
    def get_onboarding_stats(self) -> dict:
        """Get onboarding completion statistics"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get completion stats
            cursor.execute('SELECT COUNT(*) FROM onboarding_progress')
            total_started = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM onboarding_progress WHERE completed = 1')
            total_completed = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM onboarding_progress WHERE step = 2')
            step2_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM onboarding_progress WHERE step = 3')
            step3_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM onboarding_progress WHERE step = 4')
            step4_count = cursor.fetchone()[0]
            
            conn.close()
            
            completion_rate = (total_completed / total_started * 100) if total_started > 0 else 0
            
            return {
                'total_started': total_started,
                'total_completed': total_completed,
                'completion_rate': completion_rate,
                'step_breakdown': {
                    'step_1_welcome': total_started - step2_count - step3_count - step4_count - total_completed,
                    'step_2_rules': step2_count,
                    'step_3_faq': step3_count,
                    'step_4_chat': step4_count,
                    'completed': total_completed
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting onboarding stats: {e}")
            return {'total_started': 0, 'total_completed': 0, 'completion_rate': 0, 'step_breakdown': {}}

    async def periodic_backup(self):
        """Periodic backup every 30 minutes"""
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            await self.backup_to_cloud()