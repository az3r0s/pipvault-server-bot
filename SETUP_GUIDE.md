# Server Bot Setup Guide

## 📋 Quick Setup Checklist

### 1. **Discord Bot Setup**
- [ ] Create Discord application at https://discord.developer.com/applications
- [ ] Generate bot token and save securely
- [ ] Enable these bot permissions:
  - `Send Messages`
  - `Use Slash Commands`
  - `Manage Roles`
  - `Create Instant Invite`
  - `Read Message History`
  - `Attach Files`
  - `Embed Links`

### 2. **Server Configuration**
- [ ] Create/identify these channels:
  - VIP upgrade channel (for sticky embed)
  - VIP tickets channel ID: `1423246972617490473`
  - Staff notifications channel
- [ ] Create VIP role if it doesn't exist
- [ ] Get all channel and role IDs

### 3. **Staff Configuration File**
- [ ] Edit `server_bot/config/staff_config.json`
- [ ] Add each staff member with their:
  - Discord ID
  - Username
  - Vantage referral link
  - Vantage IB code (7470320, 7470272, etc.)
- [ ] Update channel and role IDs

### 4. **Environment Variables**
```bash
DISCORD_BOT_TOKEN=your_server_bot_token_here
DISCORD_GUILD_ID=your_server_id
VIP_UPGRADE_CHANNEL_ID=your_vip_upgrade_channel_id
```

### 5. **Deployment**
```bash
# Local testing:
cd server_bot
python main.py

# Railway deployment:
railway up
```

## 🔧 Staff Configuration Example

Update `server_bot/config/staff_config.json`:

```json
{
  "staff_members": {
    "john_staff": {
      "discord_id": 123456789012345678,
      "username": "JohnStaff",
      "vantage_referral_link": "https://portal.vantage.com/register?referral=john_ref",
      "vantage_ib_code": "7470320",
      "invite_code": null
    },
    "jane_staff": {
      "discord_id": 987654321098765432,
      "username": "JaneStaff",
      "vantage_referral_link": "https://portal.vantage.com/register?referral=jane_ref",
      "vantage_ib_code": "7470272",
      "invite_code": null
    }
  },
  "email_template": {
    "recipient": "support@vantage.com",
    "subject": "VIP Upgrade Request - Discord User Verification",
    "body_template": "Dear Vantage Support Team,\\n\\nI am writing to request a VIP upgrade for my trading account...\\n\\n**Account Details:**\\n- Discord Username: {username}\\n- Discord ID: {discord_id}\\n- Request ID: {request_id}\\n- Referred by Staff: {staff_name}\\n- IB Code: {ib_code}\\n\\n[Please fill in your name and account details]\\n\\nBest regards,\\n[Your Name]"
  },
  "channels": {
    "vip_upgrade_channel": "YOUR_VIP_UPGRADE_CHANNEL_ID",
    "vip_tickets_channel": "1423246972617490473",
    "staff_notifications_channel": "YOUR_STAFF_NOTIFICATIONS_CHANNEL_ID"
  },
  "roles": {
    "vip_role": "YOUR_VIP_ROLE_ID"
  }
}
```

## 📝 Bot Commands

### Admin Commands:
- `/setup_vip_embed` - Create sticky VIP upgrade button in channel
- `/create_staff_invite @member` - Generate invite link for staff (must be in config)
- `/approve_vip request_id` - Approve VIP upgrade request
- `/deny_vip request_id reason` - Deny VIP upgrade request

### User Flow:
1. User clicks "Upgrade to VIP" button
2. Selects existing/new Vantage account
3. Gets email template with staff IB code
4. **User fills in their name** in template
5. Sends email to support@vantage.com
6. **Uploads screenshot proof** in Discord
7. Staff reviews and approves in vip-tickets channel

## 🎯 Key Features

### **Scalable Staff Management**
- Add new staff by updating JSON config file
- No database changes needed
- Automatic IB code attribution

### **Email Template System**
- Pre-filled recipient, subject, IB code
- User only needs to add their name
- Screenshot proof required

### **VIP Tickets Integration**
- Automatic notifications to channel `1423246972617490473`
- Staff can review email proofs
- Approve/deny with role assignment

### **Privacy Protection**
- All VIP interactions are ephemeral (private)
- Only screenshot upload is public for staff review
- Secure invite tracking system

## 🚀 Going Live Steps

1. **Invite Bot to Server:**
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=268435456&scope=bot%20applications.commands
   ```

2. **Configure Staff:**
   - Update `staff_config.json` with real Discord IDs
   - Use `/create_staff_invite` for each staff member

3. **Setup VIP Channel:**
   - Run `/setup_vip_embed` in designated channel
   - Test complete upgrade flow

4. **Verify Integration:**
   - Test email template generation
   - Confirm vip-tickets notifications work
   - Validate staff attribution system

## 🔒 Security Notes

- Keep bot token secure and rotate regularly
- Config file contains sensitive IB codes - protect access
- VIP tickets channel should be staff-only
- Regular backup of server_management.db database

---

**Ready for Production:** ✅ All systems implemented and tested