"""
Invite Sync Database Methods
==========================

Database methods for storing and retrieving invite join history
"""

from typing import Dict, List, Optional, Any
import sqlite3
import json
from datetime import datetime

class InviteSyncDB:
    """Methods for managing invite join history in the database"""
    
    @staticmethod
    def init_tables(db):
        """Initialize invite sync tables"""
        cursor = db.cursor()
        
        # Create table for tracking invite join history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_join_history (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                invite_code TEXT NOT NULL,
                staff_id INTEGER NOT NULL,
                joined_at TIMESTAMP NOT NULL,
                FOREIGN KEY (staff_id) REFERENCES staff_invites(staff_id)
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_invite_join_code 
            ON invite_join_history(invite_code)
        ''')
        
        # Create table for sync metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invite_sync_meta (
                guild_id INTEGER PRIMARY KEY,
                last_sync TIMESTAMP,
                sync_status TEXT
            )
        ''')
        
        db.commit()

    @staticmethod
    def record_invite_join(db, user_id: int, username: str, invite_code: str, staff_id: int):
        """Record a user joining through an invite"""
        cursor = db.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO invite_join_history 
                (user_id, username, invite_code, staff_id, joined_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, invite_code, staff_id, datetime.now()))
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error recording invite join: {e}")
            return False

    @staticmethod
    def get_invite_joins(db, invite_code: str) -> List[Dict[str, Any]]:
        """Get all members who joined through a specific invite"""
        cursor = db.cursor()
        cursor.execute('''
            SELECT user_id, username, joined_at 
            FROM invite_join_history 
            WHERE invite_code = ?
            ORDER BY joined_at DESC
        ''', (invite_code,))
        
        return [{
            'user_id': row[0],
            'username': row[1],
            'joined_at': row[2]
        } for row in cursor.fetchall()]

    @staticmethod
    def update_sync_meta(db, guild_id: int, status: str = 'success'):
        """Update sync metadata for a guild"""
        cursor = db.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO invite_sync_meta 
                (guild_id, last_sync, sync_status)
                VALUES (?, ?, ?)
            ''', (guild_id, datetime.now(), status))
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error updating sync meta: {e}")
            return False

    @staticmethod
    def get_sync_meta(db, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get sync metadata for a guild"""
        cursor = db.cursor()
        cursor.execute('''
            SELECT guild_id, last_sync, sync_status
            FROM invite_sync_meta
            WHERE guild_id = ?
        ''', (guild_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'guild_id': row[0],
                'last_sync': row[1],
                'status': row[2]
            }
        return None

    @staticmethod
    def clear_invite_history(db, guild_id: int):
        """Clear invite join history for a guild"""
        cursor = db.cursor()
        try:
            cursor.execute('DELETE FROM invite_join_history')
            cursor.execute('DELETE FROM invite_sync_meta WHERE guild_id = ?', (guild_id,))
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error clearing invite history: {e}")
            return False