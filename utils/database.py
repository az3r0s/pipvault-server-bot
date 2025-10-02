"""
Server Bot Database Management
=============================

Handles database operations for server management features including:
- Invite tracking (which invite each user joined through)
- VIP upgrade requests and history
- Staff attribution and referral tracking
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import os
import json

logger = logging.getLogger(__name__)

class ServerDatabase:
    """Database manager for server bot features"""
    
    def __init__(self, db_path: str = "server_management.db"):
        self.db_path = db_path
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "staff_config.json")
        self.init_database()
        self.load_staff_config()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Invite tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_tracking (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                invite_code TEXT,
                inviter_id INTEGER,
                inviter_username TEXT,
                joined_at TIMESTAMP,
                invite_uses_before INTEGER,
                invite_uses_after INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Invite rejoins table (track when users leave and rejoin with different invites)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_rejoins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                invite_code TEXT,
                inviter_id INTEGER,
                inviter_username TEXT,
                rejoined_at TIMESTAMP,
                invite_uses_before INTEGER,
                invite_uses_after INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES invite_tracking(user_id)
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
                request_type TEXT, -- 'existing_account' or 'new_account'
                staff_id INTEGER,  -- Staff member who gets attribution
                status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'cancelled'
                vantage_email TEXT,
                request_data TEXT, -- JSON data for the request
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Server database initialized")
    
    def load_staff_config(self) -> Dict:
        """Load staff configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Staff config file not found: {self.config_path}")
                return {"staff_members": {}, "email_template": {}, "channels": {}, "roles": {}}
        except Exception as e:
            logger.error(f"Failed to load staff config: {e}")
            return {"staff_members": {}, "email_template": {}, "channels": {}, "roles": {}}
    
    def get_staff_by_discord_id(self, discord_id: int) -> Optional[Dict]:
        """Get staff member info by Discord ID"""
        config = self.load_staff_config()
        for staff_key, staff_info in config["staff_members"].items():
            if staff_info["discord_id"] == discord_id:
                return staff_info
        return None
    
    def get_staff_by_invite_code(self, invite_code: str) -> Optional[Dict]:
        """Get staff member info by invite code"""
        config = self.load_staff_config()
        for staff_key, staff_info in config["staff_members"].items():
            if staff_info.get("invite_code") == invite_code:
                return staff_info
        return None
    
    def update_staff_invite_code(self, discord_id: int, invite_code: str) -> bool:
        """Update invite code for a staff member in config file"""
        try:
            config = self.load_staff_config()
            
            for staff_key, staff_info in config["staff_members"].items():
                if staff_info["discord_id"] == discord_id:
                    config["staff_members"][staff_key]["invite_code"] = invite_code
                    
                    with open(self.config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    logger.info(f"Updated invite code for staff {discord_id}: {invite_code}")
                    return True
            
            logger.warning(f"Staff member with Discord ID {discord_id} not found in config")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update staff invite code: {e}")
            return False
    
    def record_user_join(self, user_id: int, username: str, invite_code: str, 
                        inviter_id: int, inviter_username: str, 
                        uses_before: int, uses_after: int) -> bool:
        """Record when a user joins through a specific invite"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Check if user already has a record (preserve original attribution)
            cursor.execute('SELECT user_id FROM invite_tracking WHERE user_id = ?', (user_id,))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # User already exists, just log the rejoin but don't change attribution
                logger.info(f"👥 {username} rejoined via invite {invite_code} by {inviter_username}, but keeping original attribution")
                
                # Optionally, record this as a separate rejoin event
                cursor.execute('''
                    INSERT INTO invite_rejoins 
                    (user_id, username, invite_code, inviter_id, inviter_username, 
                     rejoined_at, invite_uses_before, invite_uses_after)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, invite_code, inviter_id, inviter_username,
                      datetime.now(), uses_before, uses_after))
            else:
                # New user, record normally
                cursor.execute('''
                    INSERT INTO invite_tracking 
                    (user_id, username, invite_code, inviter_id, inviter_username, 
                     joined_at, invite_uses_before, invite_uses_after)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, invite_code, inviter_id, inviter_username,
                      datetime.now(), uses_before, uses_after))
                
                logger.info(f"✅ Recorded new user join: {username} via invite {invite_code}")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error recording user join: {e}")
            return False
    
    def get_user_invite_info(self, user_id: int) -> Optional[Dict]:
        """Get invite information for a user"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT invite_code, inviter_id, inviter_username, joined_at
                FROM invite_tracking 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'invite_code': result[0],
                    'inviter_id': result[1],
                    'inviter_username': result[2],
                    'joined_at': result[3]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user invite info: {e}")
            return None
    
    def add_staff_invite_config(self, staff_id: int, staff_username: str, 
                               invite_code: str, vantage_referral_link: str,
                               vantage_ib_code: str, email_template: str) -> bool:
        """Add or update staff invite configuration"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO staff_invites 
                (staff_id, staff_username, invite_code, vantage_referral_link, 
                 vantage_ib_code, email_template, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (staff_id, staff_username, invite_code, vantage_referral_link,
                  vantage_ib_code, email_template, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Updated staff invite config for {staff_username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating staff invite config: {e}")
            return False
    
    def get_staff_config_by_invite(self, invite_code: str) -> Optional[Dict]:
        """Get staff configuration by invite code"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT staff_id, staff_username, vantage_referral_link, vantage_ib_code, email_template
                FROM staff_invites 
                WHERE invite_code = ?
            ''', (invite_code,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'staff_id': result[0],
                    'staff_username': result[1],
                    'vantage_referral_link': result[2],
                    'vantage_ib_code': result[3],
                    'email_template': result[4]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting staff config: {e}")
            return None
    
    def create_vip_request(self, user_id: int, username: str, request_type: str,
                          staff_id: int, request_data: Optional[str] = None) -> Optional[int]:
        """Create a new VIP upgrade request"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO vip_requests 
                (user_id, username, request_type, staff_id, request_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, request_type, staff_id, request_data))
            
            request_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Created VIP request {request_id} for {username}")
            return request_id
            
        except Exception as e:
            logger.error(f"❌ Error creating VIP request: {e}")
            return None
    
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


    
    def get_staff_vip_stats(self, staff_id: int) -> Dict:
        """Get VIP conversion stats for a staff member"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get total invites and VIP conversions
            cursor.execute('''
                SELECT COUNT(*) FROM invite_tracking WHERE inviter_id = ?
            ''', (staff_id,))
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