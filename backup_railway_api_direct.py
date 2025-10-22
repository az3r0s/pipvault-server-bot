#!/usr/bin/env python3
"""
Direct Railway API Backup
=========================

This script directly calls the Railway API endpoints to backup all production data
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

def backup_railway_api_direct():
    print("=" * 80)
    print("🔗 DIRECT RAILWAY API BACKUP")
    print("=" * 80)
    
    railway_url = "https://web-production-1299f.up.railway.app"
    
    print(f"🌐 Connecting to Railway API: {railway_url}")
    
    backup_data = {}
    total_records = 0
    
    # Try to get discord data backup endpoint
    try:
        print("📡 Calling /get_discord_data_backup endpoint...")
        response = requests.get(f"{railway_url}/get_discord_data_backup", timeout=30)
        
        if response.status_code == 200:
            api_data = response.json()
            print(f"✅ Successfully retrieved data from Railway API")
            print(f"📊 Response keys: {list(api_data.keys())}")
            
            if 'discord_data' in api_data:
                discord_data = api_data['discord_data']
                backup_data.update(discord_data)
                
                print("\n📋 Data retrieved from Railway:")
                for table, records in discord_data.items():
                    record_count = len(records) if isinstance(records, list) else 1
                    total_records += record_count
                    print(f"  ✅ {table}: {record_count} records")
                    
                    # Show sample for verification
                    if isinstance(records, list) and len(records) > 0:
                        sample = dict(records[0])
                        # Truncate long values
                        for key in sample:
                            if len(str(sample[key])) > 50:
                                sample[key] = str(sample[key])[:50] + "..."
                        print(f"     Sample: {sample}")
                        
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None, 0
            
    except Exception as e:
        print(f"❌ Error calling Railway API: {e}")
        return None, 0
    
    # Also try other potential endpoints
    try:
        print(f"\n🔍 Trying alternative endpoints...")
        
        # Try staff invites endpoint
        staff_response = requests.get(f"{railway_url}/staff_invites", timeout=30)
        if staff_response.status_code == 200:
            print(f"✅ Found /staff_invites endpoint")
            staff_data = staff_response.json()
            backup_data['staff_api_response'] = staff_data
            
        # Try invite tracking endpoint  
        invite_response = requests.get(f"{railway_url}/invite_tracking", timeout=30)
        if invite_response.status_code == 200:
            print(f"✅ Found /invite_tracking endpoint")
            invite_data = invite_response.json()
            backup_data['invite_api_response'] = invite_data
            
    except Exception as e:
        print(f"⚠️ Alternative endpoints not available: {e}")
    
    # Create timestamped backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"railway_api_backup_{timestamp}.json"
    
    # Save comprehensive backup
    with open(backup_filename, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)
    
    print(f"\n✅ Railway API backup completed!")
    print(f"💾 Backup saved to: {backup_filename}")
    print(f"📊 Total records backed up: {total_records}")
    
    # Show summary
    if total_records > 0:
        print(f"\n🛡️ Your {total_records} production records are safely backed up!")
        print("🔍 Review the backup file to verify all data is captured")
    else:
        print("\n⚠️ No data retrieved from Railway API")
        print("🔍 This might indicate the API endpoint is different or protected")
    
    return backup_data, total_records

if __name__ == "__main__":
    backup_railway_api_direct()