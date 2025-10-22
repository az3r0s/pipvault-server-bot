#!/usr/bin/env python3
"""
Debug and Fix Live Data Extraction
=================================

This script will debug exactly what data we're getting and fix the parsing
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.cloud_database import CloudAPIServerDatabase

def debug_live_data():
    print("=" * 80)
    print("🔍 DEBUGGING LIVE DATA EXTRACTION")
    print("=" * 80)
    
    db = CloudAPIServerDatabase()
    
    print("1️⃣ Raw staff configuration data:")
    staff_config = db.load_staff_config()
    print(f"Type: {type(staff_config)}")
    print(f"Content: {json.dumps(staff_config, indent=2, default=str)}")
    
    print("\n2️⃣ Raw staff invite status data:")
    invite_status = db.get_staff_invite_status()
    print(f"Type: {type(invite_status)}")
    print(f"Content: {json.dumps(invite_status, indent=2, default=str)}")
    
    print("\n3️⃣ Trying individual methods:")
    
    # Try get_all_staff_invite_codes
    if hasattr(db, 'get_all_staff_invite_codes'):
        try:
            invite_codes = db.get_all_staff_invite_codes()
            print(f"All invite codes: {invite_codes}")
        except Exception as e:
            print(f"get_all_staff_invite_codes failed: {e}")
    
    # Try get_staff_vip_stats for each known staff ID
    known_staff_ids = [
        1143692972253266012,  # 𝑬𝒅𝒛
        243819020040536065,   # Aidan
        316652790560587776,   # Travis Pennington - 6481
        968961696133705749,   # CyCy227
        1315386250542317732,  # Fin
        1346142502587076702   # LT Business
    ]
    
    for staff_id in known_staff_ids:
        if hasattr(db, 'get_staff_vip_stats'):
            try:
                stats = db.get_staff_vip_stats(staff_id)
                print(f"Staff {staff_id} VIP stats: {stats}")
            except Exception as e:
                print(f"get_staff_vip_stats({staff_id}) failed: {e}")
    
    print("\n4️⃣ Trying database direct access:")
    try:
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Available tables: {tables}")
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} records")
            
            if count > 0 and count < 10:  # Show small tables
                cursor.execute(f"SELECT * FROM {table}")
                rows = [dict(row) for row in cursor.fetchall()]
                print(f"    Sample data: {rows}")
        
        conn.close()
        
    except Exception as e:
        print(f"Database access failed: {e}")
    
    print("\n5️⃣ Trying to find where the real data is stored:")
    
    # Check if there are other database files
    current_dir = Path(__file__).parent
    print(f"Checking directory: {current_dir}")
    
    for file_path in current_dir.glob("*"):
        if file_path.is_file():
            file_size = file_path.stat().st_size
            if file_size > 0:
                print(f"  📁 {file_path.name}: {file_size} bytes")
                
                # Check if it might be a database
                if file_path.suffix.lower() in ['.db', '.sqlite', '.sqlite3']:
                    try:
                        conn = sqlite3.connect(str(file_path))
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = [row[0] for row in cursor.fetchall()]
                        if tables:
                            print(f"    📊 Tables: {tables}")
                        conn.close()
                    except:
                        pass
                        
                # Check if it might be JSON data
                elif file_path.suffix.lower() == '.json':
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        if isinstance(data, dict) and len(data) > 0:
                            print(f"    📋 JSON keys: {list(data.keys())}")
                    except:
                        pass
    
    print("\n6️⃣ Checking environment and config:")
    print(f"CLOUD_API_URL: {os.getenv('CLOUD_API_URL', 'Not set')}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Database path: {db.db_path}")
    print(f"Config path: {db.config_path}")
    
    # Check if config file exists
    if os.path.exists(db.config_path):
        print(f"Config file exists: {db.config_path}")
        try:
            with open(db.config_path, 'r') as f:
                config_content = json.load(f)
            print(f"Config content: {json.dumps(config_content, indent=2, default=str)}")
        except Exception as e:
            print(f"Could not read config: {e}")
    else:
        print(f"Config file does not exist: {db.config_path}")

if __name__ == "__main__":
    debug_live_data()