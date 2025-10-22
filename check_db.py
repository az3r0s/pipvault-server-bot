#!/usr/bin/env python3
"""Check database contents"""

import sqlite3
import os

db_path = "server_management.db"

if os.path.exists(db_path):
    print(f"✅ Database file exists: {db_path}")
    print(f"📁 File size: {os.path.getsize(db_path)} bytes")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📊 Tables: {tables}")
    
    # Check each table
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"📋 {table}: {count} records")
            
            if count > 0 and table == 'staff_invites':
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cursor.fetchall()
                print(f"   Sample data: {rows}")
        except Exception as e:
            print(f"❌ Error checking {table}: {e}")
    
    conn.close()
else:
    print(f"❌ Database file not found: {db_path}")