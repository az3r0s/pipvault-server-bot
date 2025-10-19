"""
Railway Live Database Download
=============================

Download the actual database file from Railway before making any changes.
This ensures we backup your real data that's already stored there.
"""

import subprocess
import os
from datetime import datetime

def download_railway_database():
    """Download the live database from Railway"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"railway_live_database_{timestamp}.db"
    
    print("🔄 Downloading live database from Railway...")
    
    try:
        # Use Railway CLI to run a command that copies the database
        print("📡 Connecting to Railway and copying database...")
        
        # Method 1: Try to cat the database file and save it
        cmd = ["railway", "run", "cat server_management.db"]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0 and result.stdout:
            # Save the database content
            with open(backup_file, 'wb') as f:
                f.write(result.stdout)
            
            if os.path.getsize(backup_file) > 0:
                print(f"✅ Downloaded database: {backup_file}")
                print(f"💾 Size: {os.path.getsize(backup_file):,} bytes")
                
                # Now convert to JSON for safety
                import sqlite3
                import json
                
                json_backup = f"railway_live_backup_{timestamp}.json"
                
                conn = sqlite3.connect(backup_file)
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                backup_data = {
                    "backup_info": {
                        "created_at": datetime.now().isoformat(),
                        "source": "Railway Live Database",
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
                    
                    # Convert to JSON
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
                with open(json_backup, 'w') as f:
                    json.dump(backup_data, f, indent=2)
                
                print(f"\n🎯 BACKUP COMPLETE!")
                print(f"   📁 Binary: {backup_file}")
                print(f"   📁 JSON: {json_backup}")
                print(f"   📊 Tables: {len(tables)}")
                print(f"   📈 Records: {total_records}")
                
                # Clean up binary file
                os.remove(backup_file)
                
                return json_backup
            else:
                print("❌ Downloaded file is empty")
                return None
        else:
            print(f"❌ Railway command failed: {result.stderr.decode()}")
            
            # Method 2: Try alternative approach
            print("🔄 Trying alternative method...")
            
            cmd2 = ["railway", "run", "ls -la server_management.db && head -c 1000 server_management.db"]
            result2 = subprocess.run(cmd2, capture_output=True, text=True)
            
            if result2.returncode == 0:
                print("✅ Database exists on Railway:")
                print(result2.stdout)
                print("\n💡 Database exists but couldn't download via cat method.")
                print("💡 Try using the Discord /export_database command after deploying.")
                return "database_exists_use_discord_command"
            else:
                print("❌ Could not locate database on Railway")
                return None
            
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None

if __name__ == "__main__":
    result = download_railway_database()
    
    if result == "database_exists_use_discord_command":
        print("\n🚨 IMPORTANT: Database exists on Railway but couldn't download directly.")
        print("🛡️ SAFE APPROACH:")
        print("   1. Deploy the bot (with backup cog)")
        print("   2. Use /export_database command in Discord")
        print("   3. This will backup your live data safely")
        print("   4. Then proceed with welcome screen implementation")
    elif result:
        print(f"\n✅ SUCCESS: Your Railway data is safely backed up to {result}")
        print("🚀 You can now deploy the welcome screen changes with confidence!")
    else:
        print("\n❌ Could not create backup. Consider deploying bot first, then using /export_database")