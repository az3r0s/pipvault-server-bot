"""
Quick Railway Database Backup
============================

Simple script to backup your Railway database before implementing welcome screen.
Run this to create a safety backup of all your invite tracking and other data.
"""

import sqlite3
import json
import os
from datetime import datetime

def backup_railway_database():
    """Create a quick backup of the Railway database"""
    
    db_path = "server_management.db"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"railway_backup_before_welcome_screen_{timestamp}.json"
    
    print("🔄 Creating Railway database backup...")
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("   This is normal if you haven't deployed yet.")
        return None
    
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        backup_data = {
            "backup_info": {
                "created_at": datetime.now().isoformat(),
                "purpose": "Safety backup before welcome screen implementation",
                "tables": len(tables)
            },
            "data": {}
        }
        
        total_records = 0
        
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            # Get column names
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Convert to JSON-friendly format
            table_data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[columns[i]] = str(value) if value is not None else None
                table_data.append(row_dict)
            
            backup_data["data"][table] = {
                "columns": columns,
                "rows": table_data
            }
            
            total_records += len(table_data)
            print(f"   ✅ {table}: {len(table_data)} records")
        
        conn.close()
        
        # Save backup
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        file_size = os.path.getsize(backup_file)
        
        print(f"\n🎯 BACKUP COMPLETE!")
        print(f"   📁 File: {backup_file}")
        print(f"   📊 Tables: {len(tables)}")
        print(f"   📈 Records: {total_records}")
        print(f"   💾 Size: {file_size:,} bytes")
        print(f"\n💡 Keep this file safe! You can restore from it if needed.")
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

if __name__ == "__main__":
    backup_railway_database()