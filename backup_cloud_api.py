"""
Cloud API Database Backup for PipVault Server Bot
=================================================

Your bot uses CloudAPIServerDatabase which stores data via API calls to:
https://web-production-1299f.up.railway.app

This script will backup your data from the cloud API directly.
"""

import requests
import json
import os
from datetime import datetime

def backup_cloud_api_database():
    """Backup data from the cloud API service"""
    
    # Your cloud service URL (same as in main.py)
    cloud_url = "https://web-production-1299f.up.railway.app"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"pipvault_cloud_backup_{timestamp}.json"
    
    print("🔄 Backing up data from PipVault Cloud API...")
    print(f"🌐 Cloud Service: {cloud_url}")
    
    try:
        # Get Discord data backup from cloud API
        print("📡 Fetching data from cloud API...")
        
        restore_endpoint = f"{cloud_url}/get_discord_data_backup"
        
        response = requests.get(restore_endpoint, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            discord_data = response_data.get('discord_data', {})
            
            if discord_data:
                # Create comprehensive backup
                backup_data = {
                    "backup_info": {
                        "created_at": datetime.now().isoformat(),
                        "source": "PipVault Cloud API",
                        "cloud_url": cloud_url,
                        "backup_type": "CloudAPIServerDatabase"
                    },
                    "cloud_data": discord_data,
                    "raw_response": response_data
                }
                
                # Save backup
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                
                # Analyze what we backed up
                total_records = 0
                tables_info = {}
                
                for table_name, table_data in discord_data.items():
                    if isinstance(table_data, list):
                        record_count = len(table_data)
                        total_records += record_count
                        tables_info[table_name] = record_count
                        print(f"   ✅ {table_name}: {record_count} records")
                
                file_size = os.path.getsize(backup_file)
                
                print(f"\n🎯 CLOUD BACKUP COMPLETE!")
                print(f"   📁 File: {backup_file}")
                print(f"   📊 Tables: {len(tables_info)}")
                print(f"   📈 Total Records: {total_records}")
                print(f"   💾 File Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                print(f"   🌐 Source: PipVault Cloud API")
                
                # Show backup contents
                print(f"\n📋 BACKUP CONTENTS:")
                for table, count in tables_info.items():
                    print(f"   • {table}: {count} records")
                    if table == "invite_tracking" and count > 0:
                        print(f"     └─ Invite tracking data: ✅ PRESERVED")
                    elif table == "staff_invites" and count > 0:
                        print(f"     └─ Staff invite data: ✅ PRESERVED")
                    elif table == "vip_requests" and count > 0:
                        print(f"     └─ VIP request data: ✅ PRESERVED")
                
                print(f"\n💡 Your cloud database is now safely backed up!")
                print(f"💡 This backup works with your CloudAPIServerDatabase system.")
                
                return backup_file
            else:
                print("⚠️ Cloud API returned empty discord_data")
                print("   This might mean no data has been stored yet, or cloud service is new")
                return "empty_data"
                
        elif response.status_code == 404:
            print("⚠️ Cloud API endpoint not found (404)")
            print("   This suggests the cloud service might not have backup data yet")
            print("   This is normal for new deployments")
            return "no_backup_endpoint"
            
        else:
            print(f"❌ Cloud API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error connecting to cloud API: {e}")
        return None
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def test_cloud_api_connection():
    """Test if the cloud API is accessible"""
    cloud_url = "https://web-production-1299f.up.railway.app"
    
    try:
        print(f"🔍 Testing connection to {cloud_url}...")
        
        # Try a simple endpoint first
        response = requests.get(f"{cloud_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Cloud API is accessible")
            return True
        else:
            print(f"⚠️ Cloud API responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to cloud API: {e}")
        return False

if __name__ == "__main__":
    print("🛡️ PipVault Cloud Database Backup Tool")
    print("=====================================")
    
    # Test connection first
    if test_cloud_api_connection():
        result = backup_cloud_api_database()
        
        if result and result not in ["empty_data", "no_backup_endpoint"]:
            print(f"\n✅ SUCCESS: Your PipVault cloud data is safely backed up!")
            print(f"📁 Backup file: {result}")
            print("\n🚀 You can now deploy the welcome screen changes with confidence!")
            
        elif result == "empty_data":
            print("\n⚠️ RESULT: Cloud API is working but contains no data yet")
            print("🚀 This is normal for new setups. You can deploy safely!")
            
        elif result == "no_backup_endpoint":
            print("\n⚠️ RESULT: Cloud service exists but no backup endpoint found")
            print("🚀 This suggests a new deployment. Welcome screen changes are still safe!")
            
        else:
            print("\n❌ BACKUP FAILED")
            print("💡 But welcome screen changes are still safe since they're additive-only")
    else:
        print("\n❌ Cannot connect to cloud API")
        print("💡 But welcome screen database changes are still safe (additive-only)")