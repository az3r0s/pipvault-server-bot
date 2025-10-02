"""
PostgreSQL Database Management for Server Bot
============================================

Handles database operations using Railway's managed PostgreSQL database.
This provides persistent storage that survives deployments.
"""

import psycopg2
import psycopg2.extras
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import os
import json

logger = logging.getLogger(__name__)

class PostgreSQLServerDatabase:
    """PostgreSQL database manager for server bot features"""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv('DATABASE_PRIVATE_URL') or os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "staff_config.json")
        self.init_database()
        self.load_staff_config()
    
    def get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.db_url)
    
    def init_database(self):
        """Initialize PostgreSQL database with required tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Invite tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invite_tracking (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    invite_code TEXT,
                    inviter_id BIGINT,
                    inviter_username TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    invite_uses_before INTEGER,
                    invite_uses_after INTEGER
                )
            ''')
            
            # Staff invite configuration table  
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staff_invites (
                    staff_id BIGINT PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    request_type TEXT,
                    staff_id BIGINT,
                    status TEXT DEFAULT 'pending',
                    vantage_email TEXT,
                    request_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ PostgreSQL Server database initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL database: {e}")
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
                INSERT INTO staff_invites 
                (staff_id, staff_username, invite_code, vantage_referral_link, vantage_ib_code, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (staff_id) DO UPDATE SET
                    invite_code = EXCLUDED.invite_code,
                    updated_at = EXCLUDED.updated_at
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
                    cursor.execute('SELECT invite_code FROM staff_invites WHERE staff_id = %s', (discord_id,))
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
                INSERT INTO invite_tracking 
                (user_id, username, invite_code, inviter_id, inviter_username, 
                 joined_at, invite_uses_before, invite_uses_after)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    invite_code = EXCLUDED.invite_code,
                    inviter_id = EXCLUDED.inviter_id,
                    inviter_username = EXCLUDED.inviter_username,
                    joined_at = EXCLUDED.joined_at,
                    invite_uses_before = EXCLUDED.invite_uses_before,
                    invite_uses_after = EXCLUDED.invite_uses_after
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
                WHERE user_id = %s
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
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (user_id, username, request_type, 0, 'pending', 
                  json.dumps({'attributed_staff': attributed_staff, 'staff_ib_code': staff_ib_code}),
                  datetime.now()))
            
            request_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Created VIP request {request_id} for {attributed_staff}")
            return request_id
            
        except Exception as e:
            logger.error(f"❌ Error creating VIP request: {e}")
            return 0