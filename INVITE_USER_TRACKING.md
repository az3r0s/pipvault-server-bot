# Invite User Tracking Commands 👥

## New Commands Added

### 1. `/list_invite_users` - Show Users by Staff Member
**Usage:** `/list_invite_users staff_member:@Username`

**What it does:**
- Shows all users who joined through a specific staff member's invite
- Displays their current status (active in server, has VIP role, etc.)
- Provides conversion statistics and IB attribution

### 2. `/list_users_by_code` - Show Users by Invite Code  
**Usage:** `/list_users_by_code invite_code:abc123def`

**What it does:**
- Shows all users who joined through a specific invite code
- Useful for debugging or when you have the code but not the staff member
- Includes join dates and detailed statistics

## Command Features

### User Information Displayed:
- ✅ **User Mention/Username** - Active users show as mentions, left users are crossed out
- ✅ **Server Status** - 🟢 Active in server or 🔴 Left server
- ✅ **VIP Status** - 👑 Has VIP role or blank if not VIP
- ✅ **Join Date** - When they joined through the invite (in `/list_users_by_code`)

### Statistics Provided:
- **Total Joins** - How many users joined through this invite
- **Active Count** - Users still in the server
- **VIP Count** - Users who have VIP role
- **VIP Conversion Rate** - Percentage of joins that became VIP

### Staff Attribution:
- **Staff Member** - Who created the invite
- **IB Code** - Their Vantage IB code for attribution  
- **Referral Link** - Link to their Vantage referral

## Example Output

### `/list_invite_users staff_member:@Cyril`
```
👥 Users from Cyril's Invite
All users who joined through invite code F82HtFnC6X

📊 Summary
Staff Member: @Cyril
Invite Code: F82HtFnC6X
Total Joins: 15

👥 Users (Showing 15/15)
1. 🟢 @User1 👑
2. 🟢 @User2
3. 🔴 ~~User3~~
4. 🟢 @User4 👑
...

📈 Statistics
🟢 Active in Server: 12/15
👑 VIP Members: 4/15
📊 VIP Conversion Rate: 26.7%

💼 IB Attribution  
IB Code: 1234567
Referral Link: [View](https://vantage.com/...)
```

### `/list_users_by_code invite_code:F82HtFnC6X`
```
👥 Users from Invite Code F82HtFnC6X
All users who joined through this invite

👤 Staff Attribution
Staff Member: @Cyril
IB Code: 1234567
Total Joins: 15

👥 Users (Showing 15/15)
1. 🟢 @User1 👑 (10/01/25)
2. 🟢 @User2 (10/02/25)
3. 🔴 ~~User3~~ (10/03/25)
...
```

## Use Cases

### For Staff Management:
- **Track Performance** - See how many users each staff member brings in
- **Monitor Conversions** - Check VIP conversion rates per staff member
- **Verify Attribution** - Ensure IB codes are working correctly

### For Analytics:
- **Retention Analysis** - See how many invited users stay in server
- **VIP Conversion Tracking** - Monitor which invites convert to VIP
- **Historical Data** - Track invite performance over time

### For Support:
- **Debug Issues** - Look up specific invite codes when users have problems
- **Verify Claims** - Check if users actually joined through claimed invites
- **Attribution Disputes** - Resolve conflicts about who referred whom

## Technical Implementation

### Database Integration:
- Uses existing `invite_tracking` table
- New `get_users_by_invite_code()` method added
- Integrates with staff configuration system

### Smart User Display:
- **Active users**: Show as Discord mentions
- **Left users**: Show as crossed out text
- **VIP members**: Show crown emoji 👑
- **Join dates**: Formatted as MM/DD/YY

### Pagination Support:
- Limits display to 25 users per page
- Shows "X of Y users" for larger lists
- Footer indicates if more users available

## Permissions

- **Administrator Only** - Both commands require administrator permissions
- **Ephemeral Responses** - All output is private (only command user sees it)
- **Staff Privacy** - Respects staff configuration privacy

## Commands Available Now:

```
/list_invite_users @StaffMember - Show users by staff member
/list_users_by_code abc123def - Show users by invite code
/create_staff_invite @StaffMember - Create new staff invite
/delete_staff_invite @StaffMember - Delete staff invite  
/delete_invite_by_code abc123def - Delete by specific code
/list_staff_invites - Show all staff invites
/test_dm @User - Test DM capability
```

## Status: ✅ READY FOR USE

Both new commands are fully implemented and ready for production use:
- Complete user tracking with status indicators
- Detailed statistics and conversion rates  
- Staff attribution with IB codes
- Professional formatting with pagination
- Full error handling and validation

Perfect for managing your staff invite system and tracking VIP conversions! 🚀