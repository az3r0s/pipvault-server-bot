"""
Database Migration Manager
========================

Handles creation and migration of database tables for the server bot
"""

import sqlite3
import logging
from typing import List, Dict
import os

logger = logging.getLogger(__name__)

class MigrationManager:
    """Handles database migrations and schema updates"""
    
    def __init__(self, db_path: str = "server_management.db"):
        self.db_path = db_path
        self._migrations_initialized = False
        
        # Ensure database directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
    def init_migrations(self):
        """Initialize migrations system"""
        if self._migrations_initialized:
            return
            
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Create migrations tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        self._migrations_initialized = True
        
    def get_applied_migrations(self) -> List[str]:
        """Get list of migrations that have been applied"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('SELECT migration_name FROM migrations')
        applied = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return applied
        
    def apply_migration(self, migration_name: str, migration_sql: List[str]) -> bool:
        """Apply a specific migration"""
        try:
            # Initialize migrations system if not done
            self.init_migrations()
            
            # Check if migration already applied
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM migrations WHERE migration_name = ?', (migration_name,))
            if cursor.fetchone():
                logger.info(f"Migration {migration_name} already applied")
                conn.close()
                return True
                
            # Apply migration statements
            for sql in migration_sql:
                cursor.execute(sql)
                
            # Record migration as applied
            cursor.execute('INSERT INTO migrations (migration_name) VALUES (?)', (migration_name,))
            conn.commit()
            
            logger.info(f"✅ Applied migration: {migration_name}")
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration_name}: {e}")
            return False
            
    def create_all_tables(self) -> bool:
        """Create all tables defined in schema"""
        try:
            # Initialize migrations system
            self.init_migrations()
            
            # Run each migration in sequence
            migrations = [
                ("create_invite_tracking", ['''
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
                ''']),
                
                ("create_staff_invites", ['''
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
                ''']),
                
                ("create_vip_requests", ['''
                    CREATE TABLE IF NOT EXISTS vip_requests (
                        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        request_type TEXT,
                        status TEXT,
                        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        notes TEXT
                    )
                ''']),
                
                ("create_onboarding_progress", ['''
                    CREATE TABLE IF NOT EXISTS onboarding_progress (
                        user_id TEXT PRIMARY KEY,
                        username TEXT,
                        steps_completed TEXT,
                        is_completed BOOLEAN DEFAULT 0,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP NULL,
                        last_step_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                '''])
            ]
            
            # Apply each migration
            for name, statements in migrations:
                if not self.apply_migration(name, statements):
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False