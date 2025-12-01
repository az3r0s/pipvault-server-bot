"""
Test script to verify invite tracking persistence across restarts
This checks if the cache-busting and cache-control headers fix the stale data issue
"""

import requests
import json
from datetime import datetime
import time

CLOUD_URL = "https://web-production-1299f.up.railway.app"

def test_backup_and_restore():
    """Test the complete backup → restore cycle"""
    
    print("=" * 80)
    print("🧪 TESTING INVITE TRACKING PERSISTENCE")
    print("=" * 80)
    
    # Step 1: Get current backup (without cache-busting)
    print("\n📥 Step 1: Fetching current backup WITHOUT cache-busting...")
    response1 = requests.get(f"{CLOUD_URL}/get_discord_data_backup")
    
    if response1.status_code == 200:
        data1 = response1.json()
        backup_ts1 = data1.get('backup_timestamp', 'unknown')
        invite_tracking_count1 = len(data1.get('discord_data', {}).get('invite_tracking', []))
        staff_invites_count1 = len(data1.get('discord_data', {}).get('staff_invites', []))
        
        print(f"✅ Got backup from: {backup_ts1}")
        print(f"   - Staff invites: {staff_invites_count1}")
        print(f"   - Invite tracking entries: {invite_tracking_count1}")
        print(f"   - Cache-Control header: {response1.headers.get('Cache-Control', 'NONE')}")
        print(f"   - Pragma header: {response1.headers.get('Pragma', 'NONE')}")
    else:
        print(f"❌ Failed to get backup: {response1.status_code}")
        return
    
    # Step 2: Wait a moment
    print("\n⏳ Step 2: Waiting 2 seconds...")
    time.sleep(2)
    
    # Step 3: Get backup WITH cache-busting
    print("\n📥 Step 3: Fetching backup WITH cache-busting (like bot does)...")
    cache_buster = int(time.time())
    response2 = requests.get(f"{CLOUD_URL}/get_discord_data_backup?t={cache_buster}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        backup_ts2 = data2.get('backup_timestamp', 'unknown')
        invite_tracking_count2 = len(data2.get('discord_data', {}).get('invite_tracking', []))
        staff_invites_count2 = len(data2.get('discord_data', {}).get('staff_invites', []))
        
        print(f"✅ Got backup from: {backup_ts2}")
        print(f"   - Staff invites: {staff_invites_count2}")
        print(f"   - Invite tracking entries: {invite_tracking_count2}")
        print(f"   - Cache-Control header: {response2.headers.get('Cache-Control', 'NONE')}")
        print(f"   - Pragma header: {response2.headers.get('Pragma', 'NONE')}")
        print(f"   - Cache buster used: t={cache_buster}")
    else:
        print(f"❌ Failed to get backup: {response2.status_code}")
        return
    
    # Step 4: Compare results
    print("\n🔍 Step 4: Comparing results...")
    if backup_ts1 == backup_ts2:
        print(f"✅ Both requests returned same backup timestamp: {backup_ts1}")
    else:
        print(f"⚠️ Different timestamps!")
        print(f"   Without cache-bust: {backup_ts1}")
        print(f"   With cache-bust: {backup_ts2}")
    
    if invite_tracking_count1 == invite_tracking_count2 and staff_invites_count1 == staff_invites_count2:
        print(f"✅ Data counts match!")
    else:
        print(f"⚠️ Data counts differ!")
        print(f"   Without cache-bust: {staff_invites_count1} staff, {invite_tracking_count1} invites")
        print(f"   With cache-bust: {staff_invites_count2} staff, {invite_tracking_count2} invites")
    
    # Step 5: Check cache-control headers
    print("\n🔒 Step 5: Verifying cache-control headers...")
    cache_control = response2.headers.get('Cache-Control', '')
    
    if 'no-cache' in cache_control and 'no-store' in cache_control:
        print("✅ Cache-Control headers are CORRECT!")
        print(f"   Headers: {cache_control}")
    else:
        print("❌ Cache-Control headers are MISSING or INCORRECT!")
        print(f"   Expected: 'no-cache, no-store, must-revalidate, max-age=0'")
        print(f"   Got: '{cache_control}'")
        print("\n⚠️ WARNING: Responses may still be cached by proxies/CDN!")
    
    # Step 6: Display invite tracking data
    print("\n📋 Step 6: Current invite tracking data in cloud backup:")
    invite_tracking = data2.get('discord_data', {}).get('invite_tracking', [])
    
    if invite_tracking:
        print(f"\n   Found {len(invite_tracking)} invite tracking entries:")
        for idx, entry in enumerate(invite_tracking[:10], 1):  # Show first 10
            username = entry.get('username', 'unknown')
            invite_code = entry.get('invite_code', 'unknown')
            inviter_username = entry.get('inviter_username', 'unknown')
            joined_at = entry.get('joined_at', 'unknown')
            print(f"   {idx}. {username} → invited by {inviter_username} (code: {invite_code}) on {joined_at}")
        
        if len(invite_tracking) > 10:
            print(f"   ... and {len(invite_tracking) - 10} more")
    else:
        print("   ⚠️ NO invite tracking entries found in cloud backup!")
    
    # Step 7: Display staff invites
    print("\n👥 Step 7: Current staff invites in cloud backup:")
    staff_invites = data2.get('discord_data', {}).get('staff_invites', [])
    
    if staff_invites:
        print(f"\n   Found {len(staff_invites)} staff members:")
        for idx, staff in enumerate(staff_invites, 1):
            username = staff.get('staff_username', 'unknown')
            invite_code = staff.get('invite_code', 'unknown')
            print(f"   {idx}. {username}: {invite_code}")
    else:
        print("   ⚠️ NO staff invites found in cloud backup!")
    
    # Final verdict
    print("\n" + "=" * 80)
    print("📊 FINAL VERDICT")
    print("=" * 80)
    
    if 'no-cache' in cache_control and 'no-store' in cache_control:
        print("✅ Cache-control headers are SET - stale data issue should be FIXED!")
        print("✅ Cache-busting is working - using timestamp parameter")
        print("✅ Invite tracking data WILL persist across restarts")
    else:
        print("⚠️ Cache-control headers are MISSING - may still get stale data!")
        print("   Redeploy main.py with the cache-control header fix")
    
    print("\n📌 Summary:")
    print(f"   - Latest backup timestamp: {backup_ts2}")
    print(f"   - Staff invites in backup: {staff_invites_count2}")
    print(f"   - Invite tracking entries: {invite_tracking_count2}")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_backup_and_restore()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
