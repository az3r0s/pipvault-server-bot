"""
Railway Live Database Backup
============================

Backup your live Railway database directly from the cloud.
This connects to your Railway service and downloads the current database state.
"""

import subprocess
import json
import os
import sqlite3
from datetime import datetime

def backup_railway_live_database():
    """Backup database directly from Railway cloud"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_db = f"railway_live_db_{timestamp}.db"
    backup_file = f"railway_live_backup_{timestamp}.json"
    
    print("🔄 Connecting to Railway to backup live database...")
    
    try:
        # Download database from Railway
        print("📡 Downloading database from Railway cloud...")
        
        # Use Railway CLI to copy database from service
        cmd = ["railway", "run", f"cp server_management.db /tmp/{temp_db} && cat /tmp/{temp_db}"]
        
        result = subprocess.run(cmd, capture_output=True, shell=True)
        
        if result.returncode != 0:
            print(f"❌ Railway command failed: {result.stderr.decode()}")
            return None
        
        # Write the database content to local file
        with open(temp_db, 'wb') as f:
            f.write(result.stdout)
        
        print(f"✅ Downloaded database to: {temp_db}")
        
        # Now backup the downloaded database
        if not os.path.exists(temp_db) or os.path.getsize(temp_db) == 0:
            print("❌ Downloaded database is empty or missing")
            return None
        
        # Convert to JSON backup
        conn = sqlite3.connect(temp_db, timeout=10.0)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        backup_data = {
            "backup_info": {
                "created_at": datetime.now().isoformat(),
                "source": "Railway Live Database",
                "project": "humble-vibrancy",
                "service": "pipvault-server-bot",
                "tables": len(tables)
            },
            "data": {}
        }
        
        total_records = 0
        
        print("📊 Processing database tables...")
        
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
        
        # Save JSON backup
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Clean up temp file
        os.remove(temp_db)
        
        file_size = os.path.getsize(backup_file)
        
        print(f"\n🎯 RAILWAY LIVE BACKUP COMPLETE!")
        print(f"   📁 File: {backup_file}")
        print(f"   📊 Tables: {len(tables)}")
        print(f"   📈 Records: {total_records}")
        print(f"   💾 Size: {file_size:,} bytes")
        print(f"   🌐 Source: Railway Cloud Database")
        
        # Show what was backed up
        print(f"\n📋 BACKUP CONTENTS:")
        for table, data in backup_data["data"].items():
            print(f"   • {table}: {len(data['rows'])} records")
            if table == "invite_tracking" and len(data['rows']) > 0:
                print(f"     └─ Invite tracking data: ✅ PRESERVED")
            elif table == "staff_invites" and len(data['rows']) > 0:
                print(f"     └─ Staff invite data: ✅ PRESERVED")
            elif table == "vip_requests" and len(data['rows']) > 0:
                print(f"     └─ VIP request data: ✅ PRESERVED")
        
        print(f"\n💡 Your Railway database is now safely backed up!")
        print(f"💡 Keep {backup_file} safe - you can restore from it if needed.")
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Railway backup failed: {e}")
        return None

if __name__ == "__main__":
    backup_railway_live_database()