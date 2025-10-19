#!/usr/bin/env python3
"""
Railway Database Backup & Restore System
========================================

Safe backup and restore for Railway cloud persistence database.
Use this before any database schema changes to ensure data safety.

USAGE:
1. Backup: python railway_database_backup.py --backup
2. Restore: python railway_database_backup.py --restore backup_file.json
3. Verify: python railway_database_backup.py --verify
"""

import sqlite3
import json
import argparse
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RailwayDatabaseBackup:
    """Complete backup and restore system for Railway SQLite database"""
    
    def __init__(self, db_path: str = "server_management.db"):
        self.db_path = db_path
        self.backup_dir = "database_backups"
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_complete_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a complete backup of the database with all data and schema"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"railway_db_backup_{timestamp}"
        
        backup_file = os.path.join(self.backup_dir, f"{backup_name}.json")
        
        try:
            logger.info(f"🔄 Starting complete database backup...")
            
            if not os.path.exists(self.db_path):
                logger.error(f"❌ Database file not found: {self.db_path}")
                return None
            
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            backup_data = {
                "backup_info": {
                    "created_at": datetime.now().isoformat(),
                    "database_path": self.db_path,
                    "tables_count": len(tables),
                    "backup_version": "1.0"
                },
                "schema": {},
                "data": {}
            }
            
            total_records = 0
            
            for table in tables:
                logger.info(f"📊 Backing up table: {table}")
                
                # Get table schema
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
                schema_result = cursor.fetchone()
                backup_data["schema"][table] = schema_result[0] if schema_result else None
                
                # Get all data from table
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Convert rows to dictionaries for JSON serialization
                table_data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Handle datetime objects and other non-JSON serializable types
                        if isinstance(value, bytes):
                            row_dict[columns[i]] = value.decode('utf-8', errors='ignore')
                        elif value is None:
                            row_dict[columns[i]] = None
                        else:
                            row_dict[columns[i]] = str(value)
                    table_data.append(row_dict)
                
                backup_data["data"][table] = {
                    "columns": columns,
                    "rows": table_data,
                    "record_count": len(table_data)
                }
                
                total_records += len(table_data)
                logger.info(f"   ✅ {table}: {len(table_data)} records backed up")
            
            conn.close()
            
            # Write backup to file
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Verify backup file
            file_size = os.path.getsize(backup_file)
            
            logger.info(f"🎯 BACKUP COMPLETE!")
            logger.info(f"   📁 File: {backup_file}")
            logger.info(f"   📊 Tables: {len(tables)}")
            logger.info(f"   📈 Total Records: {total_records}")
            logger.info(f"   💾 File Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            
            return backup_file
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    def restore_from_backup(self, backup_file: str, confirm: bool = False) -> bool:
        """Restore database from backup file"""
        try:
            if not os.path.exists(backup_file):
                logger.error(f"❌ Backup file not found: {backup_file}")
                return False
            
            if not confirm:
                logger.warning("🚨 DANGER: This will REPLACE your current database!")
                logger.warning("🚨 Use --confirm flag if you're absolutely sure")
                return False
            
            logger.info(f"🔄 Starting database restore from: {backup_file}")
            
            # Load backup data
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            backup_info = backup_data["backup_info"]
            logger.info(f"📅 Backup created: {backup_info['created_at']}")
            logger.info(f"📊 Tables to restore: {backup_info['tables_count']}")
            
            # Create backup of current database before restore
            current_backup = self.create_complete_backup("pre_restore_backup")
            if current_backup:
                logger.info(f"💾 Current database backed up to: {current_backup}")
            
            # Remove existing database
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"🗑️ Removed existing database: {self.db_path}")
            
            # Create new database and restore
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            total_restored = 0
            
            # Restore schema and data
            for table_name, table_info in backup_data["data"].items():
                # Create table using original schema
                if table_name in backup_data["schema"] and backup_data["schema"][table_name]:
                    cursor.execute(backup_data["schema"][table_name])
                    logger.info(f"📋 Created table: {table_name}")
                
                # Insert data
                columns = table_info["columns"]
                rows = table_info["rows"]
                
                if rows:
                    placeholders = ','.join(['?' for _ in columns])
                    insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
                    
                    for row_dict in rows:
                        values = [row_dict[col] for col in columns]
                        cursor.execute(insert_sql, values)
                    
                    total_restored += len(rows)
                    logger.info(f"   ✅ {table_name}: {len(rows)} records restored")
            
            conn.commit()
            conn.close()
            
            logger.info(f"🎯 RESTORE COMPLETE!")
            logger.info(f"   📊 Total Records Restored: {total_restored}")
            logger.info(f"   📁 Database: {self.db_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Restore failed: {e}")
            return False
    
    def verify_database(self) -> Dict[str, Any]:
        """Verify database integrity and show current state"""
        try:
            if not os.path.exists(self.db_path):
                return {"error": f"Database file not found: {self.db_path}"}
            
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            verification = {
                "database_path": self.db_path,
                "database_size": os.path.getsize(self.db_path),
                "tables": {},
                "total_records": 0
            }
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                verification["tables"][table] = count
                verification["total_records"] += count
            
            conn.close()
            
            logger.info(f"🔍 DATABASE VERIFICATION:")
            logger.info(f"   📁 File: {self.db_path}")
            logger.info(f"   💾 Size: {verification['database_size']:,} bytes")
            logger.info(f"   📊 Tables: {len(tables)}")
            logger.info(f"   📈 Total Records: {verification['total_records']}")
            
            for table, count in verification["tables"].items():
                logger.info(f"      • {table}: {count} records")
            
            return verification
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return {"error": str(e)}
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backup files"""
        backups = []
        
        if not os.path.exists(self.backup_dir):
            return backups
        
        for file in os.listdir(self.backup_dir):
            if file.endswith('.json'):
                file_path = os.path.join(self.backup_dir, file)
                try:
                    with open(file_path, 'r') as f:
                        backup_data = json.load(f)
                    
                    backups.append({
                        "filename": file,
                        "path": file_path,
                        "created_at": backup_data["backup_info"]["created_at"],
                        "tables_count": backup_data["backup_info"]["tables_count"],
                        "file_size": os.path.getsize(file_path)
                    })
                except:
                    continue
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        logger.info(f"📋 AVAILABLE BACKUPS ({len(backups)}):")
        for backup in backups:
            logger.info(f"   📁 {backup['filename']}")
            logger.info(f"      📅 Created: {backup['created_at']}")
            logger.info(f"      📊 Tables: {backup['tables_count']}")
            logger.info(f"      💾 Size: {backup['file_size']:,} bytes")
            logger.info("")
        
        return backups

def main():
    parser = argparse.ArgumentParser(description='Railway Database Backup & Restore System')
    parser.add_argument('--backup', action='store_true', help='Create a complete database backup')
    parser.add_argument('--restore', type=str, help='Restore from backup file')
    parser.add_argument('--verify', action='store_true', help='Verify current database state')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--confirm', action='store_true', help='Confirm destructive operations')
    parser.add_argument('--db-path', type=str, default='server_management.db', help='Database file path')
    
    args = parser.parse_args()
    
    backup_system = RailwayDatabaseBackup(args.db_path)
    
    if args.backup:
        backup_file = backup_system.create_complete_backup()
        if backup_file:
            print(f"\n✅ SUCCESS: Backup created at {backup_file}")
        else:
            print("\n❌ FAILED: Backup creation failed")
            sys.exit(1)
    
    elif args.restore:
        success = backup_system.restore_from_backup(args.restore, args.confirm)
        if success:
            print(f"\n✅ SUCCESS: Database restored from {args.restore}")
        else:
            print(f"\n❌ FAILED: Restore from {args.restore} failed")
            sys.exit(1)
    
    elif args.verify:
        verification = backup_system.verify_database()
        if "error" in verification:
            print(f"\n❌ VERIFICATION FAILED: {verification['error']}")
            sys.exit(1)
        else:
            print(f"\n✅ VERIFICATION COMPLETE")
    
    elif args.list:
        backups = backup_system.list_backups()
        if not backups:
            print("\n📭 No backup files found")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()