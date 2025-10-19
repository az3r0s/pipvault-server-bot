"""
Cloud API Backup Restore System
===============================

Restore PipVault cloud database from backup files.
This uploads your backed-up data back to the cloud API service.

DANGER: This will REPLACE all current data in your cloud database!
Only use this if you need to recover from data loss.
"""

import json
import requests
import sys
from datetime import datetime

def restore_backup_to_cloud(backup_file, confirm=False):
    """Restore backup data to the cloud API"""
    
    if not confirm:
        print("🚨 DANGER: This will REPLACE all current data in your cloud database!")
        print("🚨 Only proceed if you need to recover from data loss.")
        print("🚨 Add --confirm flag if you're absolutely sure.")
        return False
    
    try:
        # Load backup data
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        backup_info = backup_data.get('backup_info', {})
        cloud_data = backup_data.get('cloud_data', {})
        cloud_url = backup_info.get('cloud_url', 'https://web-production-1299f.up.railway.app')
        
        print("🔄 PIPVAULT CLOUD RESTORE")
        print("=" * 40)
        print(f"📁 Backup File: {backup_file}")
        print(f"📅 Backup Date: {backup_info.get('created_at', 'Unknown')}")
        print(f"🌐 Target Cloud: {cloud_url}")
        print()
        
        # Show what will be restored
        total_records = 0
        for table_name, table_data in cloud_data.items():
            if isinstance(table_data, list):
                count = len(table_data)
                total_records += count
                print(f"   📋 {table_name}: {count} records")
        
        print(f"   📈 Total: {total_records} records")
        print()
        
        # Confirm restoration
        print("🚨 This will REPLACE all current cloud data with backup data!")
        user_confirm = input("Type 'RESTORE' to confirm: ")
        
        if user_confirm != 'RESTORE':
            print("❌ Restoration cancelled.")
            return False
        
        print("🔄 Starting restoration...")
        
        # Send data to cloud API backup endpoint
        backup_endpoint = f"{cloud_url}/backup_discord_data"
        payload = {'discord_data': cloud_data}
        
        print(f"📡 Uploading data to {backup_endpoint}...")
        
        response = requests.post(backup_endpoint, json=payload, timeout=60)
        
        if response.status_code == 200:
            print("✅ DATA RESTORATION SUCCESSFUL!")
            print(f"   📊 Restored {total_records} records")
            print(f"   🌐 Target: {cloud_url}")
            print(f"   📅 Backup from: {backup_info.get('created_at', 'Unknown')}")
            
            # Verify restoration by reading back
            print("\n🔍 Verifying restoration...")
            verify_endpoint = f"{cloud_url}/get_discord_data_backup"
            verify_response = requests.get(verify_endpoint, timeout=30)
            
            if verify_response.status_code == 200:
                verify_data = verify_response.json().get('discord_data', {})
                verify_total = sum(len(table) for table in verify_data.values() if isinstance(table, list))
                
                if verify_total == total_records:
                    print(f"✅ Verification successful: {verify_total} records confirmed")
                else:
                    print(f"⚠️ Verification warning: Expected {total_records}, found {verify_total}")
            else:
                print("⚠️ Could not verify restoration (but upload succeeded)")
            
            return True
            
        else:
            print(f"❌ RESTORATION FAILED!")
            print(f"   Status: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except FileNotFoundError:
        print(f"❌ Backup file not found: {backup_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid backup file: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Restoration failed: {e}")
        return False

def test_cloud_api_status():
    """Test current cloud API status and show existing data"""
    cloud_url = "https://web-production-1299f.up.railway.app"
    
    try:
        print("🔍 CURRENT CLOUD STATUS")
        print("=" * 30)
        print(f"🌐 Cloud URL: {cloud_url}")
        
        # Test connection
        health_response = requests.get(f"{cloud_url}/health", timeout=10)
        if health_response.status_code == 200:
            print("✅ Cloud API is accessible")
        else:
            print(f"⚠️ Cloud API status: {health_response.status_code}")
        
        # Get current data
        backup_response = requests.get(f"{cloud_url}/get_discord_data_backup", timeout=30)
        
        if backup_response.status_code == 200:
            current_data = backup_response.json().get('discord_data', {})
            
            if current_data:
                total = sum(len(table) for table in current_data.values() if isinstance(table, list))
                print(f"📊 Current data: {total} records")
                
                for table_name, table_data in current_data.items():
                    if isinstance(table_data, list):
                        print(f"   • {table_name}: {len(table_data)} records")
            else:
                print("📭 No data currently stored in cloud")
        else:
            print(f"⚠️ Could not retrieve current data: {backup_response.status_code}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Cannot connect to cloud API: {e}")
        return False

def list_backup_files():
    """List available backup files"""
    import os
    import glob
    
    backup_files = glob.glob("pipvault_cloud_backup_*.json")
    
    if not backup_files:
        print("📭 No backup files found in current directory.")
        return []
    
    backup_files.sort(key=os.path.getctime, reverse=True)
    
    print("📁 AVAILABLE BACKUP FILES:")
    for i, file in enumerate(backup_files, 1):
        file_size = os.path.getsize(file)
        file_time = datetime.fromtimestamp(os.path.getctime(file))
        
        print(f"{i:2d}. {file}")
        print(f"     Size: {file_size:,} bytes")
        print(f"     Created: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    return backup_files

def main():
    if len(sys.argv) < 2:
        print("🔄 PIPVAULT CLOUD RESTORE SYSTEM")
        print("=" * 40)
        print()
        
        # Show current status
        test_cloud_api_status()
        
        # Show available backups
        backup_files = list_backup_files()
        
        if backup_files:
            print("USAGE:")
            print(f"  python {sys.argv[0]} <backup_file> [--confirm]")
            print()
            print("EXAMPLE:")
            print(f"  python {sys.argv[0]} {backup_files[0]} --confirm")
            print()
            print("⚠️  WARNING: --confirm flag required for actual restoration")
        
        return
    
    backup_file = sys.argv[1]
    confirm = '--confirm' in sys.argv
    
    # Show current status before restore
    print("🔍 BEFORE RESTORATION:")
    test_cloud_api_status()
    print()
    
    # Perform restoration
    success = restore_backup_to_cloud(backup_file, confirm)
    
    if success:
        print("\n🔍 AFTER RESTORATION:")
        test_cloud_api_status()

if __name__ == "__main__":
    main()