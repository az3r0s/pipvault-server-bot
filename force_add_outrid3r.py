"""
EMERGENCY SCRIPT: Force add OUTRID3R directly to cloud API
This bypasses local SQLite and adds OUTRID3R directly to the cloud backup
"""

import requests
import json
from datetime import datetime

# Cloud API endpoint (same as unified trading service)
CLOUD_URL = "https://web-production-1299f.up.railway.app"

def force_add_outrid3r():
    """Add OUTRID3R directly to cloud backup"""
    
    print("🚀 FORCE ADDING OUTRID3R TO CLOUD API...")
    
    # Step 1: Get current cloud backup
    print("\n📥 Step 1: Fetching current cloud backup...")
    response = requests.get(f"{CLOUD_URL}/get_discord_data_backup?t={int(datetime.now().timestamp())}")
    
    if response.status_code != 200:
        print(f"❌ Failed to get cloud backup: {response.status_code}")
        print("Creating fresh backup instead...")
        backup_data = {
            'staff_invites': [],
            'invite_tracking': [],
            'vip_requests': []
        }
    else:
        data = response.json()
        backup_data = data.get('discord_data', {})
        print(f"✅ Got cloud backup with {len(backup_data.get('staff_invites', []))} staff members")
    
    # Step 2: Add OUTRID3R to staff_invites
    print("\n➕ Step 2: Adding OUTRID3R to backup data...")
    
    outrid3r_data = {
        'staff_id': 974994910581256293,  # OUTRID3R Discord ID
        'staff_username': 'outrid3r',
        'invite_code': 'RDwD35HRMt',
        'vantage_referral_link': None,
        'vantage_ib_code': None,
        'email_template': None,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    # Remove OUTRID3R if already exists (to avoid duplicates)
    if 'staff_invites' not in backup_data:
        backup_data['staff_invites'] = []
    
    backup_data['staff_invites'] = [
        staff for staff in backup_data['staff_invites'] 
        if staff.get('staff_id') != 974994910581256293
    ]
    
    # Add OUTRID3R
    backup_data['staff_invites'].append(outrid3r_data)
    print(f"✅ Added OUTRID3R (total staff now: {len(backup_data['staff_invites'])})")
    
    # Step 3: Send updated backup to cloud
    print("\n☁️ Step 3: Sending updated backup to cloud API...")
    
    payload = {'discord_data': backup_data}
    response = requests.post(f"{CLOUD_URL}/backup_discord_data", json=payload, timeout=30)
    
    if response.status_code == 200:
        print("✅ SUCCESS! OUTRID3R added to cloud backup!")
        print(f"\n📊 Current staff in cloud backup ({len(backup_data['staff_invites'])} total):")
        for staff in backup_data['staff_invites']:
            username = staff.get('staff_username', 'unknown')
            invite_code = staff.get('invite_code', 'unknown')
            print(f"   - {username}: {invite_code}")
    else:
        print(f"❌ FAILED to update cloud backup: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return False
    
    # Step 4: Verify by fetching again
    print("\n🔍 Step 4: Verifying update...")
    verify_response = requests.get(f"{CLOUD_URL}/get_discord_data_backup?t={int(datetime.now().timestamp())}")
    
    if verify_response.status_code == 200:
        verify_data = verify_response.json()
        verify_backup = verify_data.get('discord_data', {})
        staff_count = len(verify_backup.get('staff_invites', []))
        
        # Check if OUTRID3R is there
        outrid3r_found = any(
            staff.get('staff_id') == 974994910581256293 
            for staff in verify_backup.get('staff_invites', [])
        )
        
        if outrid3r_found:
            print(f"✅ VERIFICATION PASSED! OUTRID3R found in cloud backup!")
            print(f"   Total staff in backup: {staff_count}")
        else:
            print(f"⚠️ WARNING: OUTRID3R not found in verification (staff count: {staff_count})")
            print("   This might be a cloud caching issue. Try again in 1 minute.")
    else:
        print(f"⚠️ Could not verify: {verify_response.status_code}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🚨 EMERGENCY: ADD OUTRID3R TO CLOUD BACKUP")
    print("=" * 60)
    
    success = force_add_outrid3r()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DONE! Next steps:")
        print("1. Restart the PipVault bot (redeploy on Railway)")
        print("2. Run /list_staff_invites to verify OUTRID3R shows up")
        print("3. If still missing, there may be a cloud caching issue")
        print("   Wait 5 minutes and try redeploying again")
    else:
        print("❌ FAILED! Check the error messages above")
    print("=" * 60)
