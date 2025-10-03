# Invite DM Issue Troubleshooting Guide 🔧

## Issue Summary
Sub-IB members (Cyril and Fin G) added to staff config and given invite links, but they're not receiving DM notifications from the bot.

## Root Cause Analysis

### Possible Reasons for Missing DMs:

1. **Discord Privacy Settings** (Most Common)
   - User has "Allow direct messages from server members" disabled
   - User has blocked the bot
   - User's privacy settings restrict DMs

2. **Server Permissions**
   - Bot lacks permission to send DMs
   - User is not in the server when DM is attempted

3. **Configuration Issues**
   - User not properly added to staff_config.json
   - Discord ID mismatch

## Enhanced Error Handling

I've improved the invite creation system to provide better feedback:

### Before:
```python
except discord.Forbidden:
    logger.warning(f"Couldn't send invite DM to {staff_member.name}")
# Silent failure - no user feedback
```

### After:
```python
except discord.Forbidden:
    logger.warning(f"Couldn't send invite DM to {staff_member.name} - DMs disabled")
    await interaction.followup.send(
        f"⚠️ **Could not send DM** to {staff_member.mention}\n"
        f"They may have DMs disabled from server members.\n"
        f"Please share the invite link with them manually:\n{invite.url}", 
        ephemeral=True
    )
```

## New Debug Tools

### 1. Enhanced `/create_staff_invite` Command
- Now shows success/failure status for DMs
- Provides manual invite link if DM fails
- Detailed error reporting

### 2. New `/test_dm` Command
```
/test_dm user:@Cyril
```
- Tests if bot can send DMs to specific user
- Identifies exact reason for DM failure
- Useful for troubleshooting before creating invites

## Troubleshooting Steps

### Step 1: Verify Staff Config
Check that Cyril and Fin G are properly configured in `staff_config.json`:

```json
{
  "staff_members": {
    "cyril": {
      "discord_id": 123456789012345678,
      "username": "cyril",
      "vantage_ib_code": "1234567",
      "vantage_referral_link": "https://vantage.com/...",
      "permissions": ["create_invites"]
    },
    "fin_g": {
      "discord_id": 987654321098765432,
      "username": "fin g", 
      "vantage_ib_code": "7654321",
      "vantage_referral_link": "https://vantage.com/...",
      "permissions": ["create_invites"]
    }
  }
}
```

### Step 2: Test DM Capability
```
/test_dm user:@Cyril
/test_dm user:@FinG
```

This will tell you exactly why DMs are failing.

### Step 3: Check Discord Privacy Settings
Ask Cyril and Fin G to check:
1. User Settings → Privacy & Safety
2. "Allow direct messages from server members" should be **ON**
3. Make sure they haven't blocked the bot

### Step 4: Manual Verification
If DMs still fail, you'll get the invite links directly and can share them manually.

## Common Discord Privacy Settings Issues

### Default Server Member DM Settings:
- **New users**: Often have DMs disabled by default
- **Privacy-conscious users**: May disable server member DMs
- **High-activity servers**: Users often disable to avoid spam

### Solutions:
1. **Ask users to enable DMs** temporarily for bot setup
2. **Manual link sharing** as fallback
3. **Use `/test_dm`** before creating invites

## Updated Workflow

### For Sub-IB Setup:
1. Add to `staff_config.json` with correct Discord ID
2. Run `/test_dm user:@SubIB` to verify DM capability
3. If DM test passes: Run `/create_staff_invite @SubIB`
4. If DM test fails: Enable DMs, then create invite
5. Bot provides manual link if automated DM fails

## Commands Available

### Administrator Commands:
- `/create_staff_invite @user` - Create invite with DM notification
- `/test_dm @user` - Test DM capability before invite creation
- `/list_staff_invites` - Show all configured staff invites

### Enhanced Feedback:
- ✅ Success notifications when DMs work
- ⚠️ Warning with manual link when DMs fail  
- ❌ Detailed error messages for troubleshooting

## Next Steps

1. **Test DM functionality** with Cyril and Fin G using `/test_dm`
2. **Check their Discord privacy settings** if DMs fail
3. **Re-run invite creation** once DM capability is confirmed
4. **Use manual link sharing** as backup if needed

The system now provides comprehensive feedback about why DMs might fail and gives you the tools to diagnose and resolve the issue! 🔧