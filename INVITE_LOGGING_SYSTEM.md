# 🔒 Persistent Invite Logging System

## Overview

This system ensures **ZERO data loss** for invite tracking by maintaining immutable log files of every member join event. Even if the database is corrupted, reset, or the bot crashes, you can always recover exactly which staff member referred each user.

## 🎯 Critical Features

### 1. **Dual Logging System**
- **JSON Log** (`invite_logs/invite_joins.json`) - Structured data with full details
- **CSV Log** (`invite_logs/invite_joins.csv`) - Excel-compatible format for easy viewing

### 2. **Append-Only Architecture**
- Logs are **never overwritten**
- Each join is permanently recorded
- Chronological history of all events

### 3. **Failsafe Design**
- Logs written **BEFORE** database update
- If database fails, log file still contains the data
- Can rebuild database from log files if needed

## 📁 Log File Structure

### JSON Format
```json
[
  {
    "timestamp": "2025-10-31T14:30:45.123456",
    "user_id": "123456789012345678",
    "username": "john_doe",
    "display_name": "John Doe",
    "discriminator": "1234",
    "invite_code": "abc123XYZ",
    "staff_id": "987654321098765432",
    "staff_username": "TravisP#0001",
    "uses_before": 5,
    "uses_after": 6,
    "guild_id": "111222333444555666",
    "guild_name": "PipVault"
  }
]
```

### CSV Format
```
Timestamp,User ID,Username,Display Name,Invite Code,Staff ID,Staff Username,Uses Before,Uses After,Guild ID,Guild Name
2025-10-31T14:30:45.123456,123456789012345678,john_doe,John Doe,abc123XYZ,987654321098765432,TravisP#0001,5,6,111222333444555666,PipVault
```

## 🤖 Commands

### `/lookup_user_invite <user>`
**Purpose:** Find exactly which invite code a specific user joined with

**Example:**
```
/lookup_user_invite @JohnDoe
```

**Output:**
```
✅ User Join Details Found

👤 User Info
Username: john_doe#1234
Display Name: John Doe
User ID: 123456789012345678

🔗 Invite Details
Invite Code: abc123XYZ
Joined On: October 31, 2025 at 02:30 PM
Uses Before: 5
Uses After: 6

👨‍💼 Referring Staff Member
Staff: TravisP#0001
Staff ID: 987654321098765432
IB Link: https://vantage.com/ref/travis
IB Code: TRAVIS123

💾 Data Source: Persistent JSON log (immutable record)
```

### `/view_invite_logs [user_id] [invite_code]`
**Purpose:** View all join events (optionally filtered)

**Examples:**
```
/view_invite_logs                           # Show all recent joins
/view_invite_logs user_id:123456789        # Show joins for specific user
/view_invite_logs invite_code:abc123XYZ    # Show all joins via specific invite
```

### `/export_invite_logs`
**Purpose:** Download complete CSV file of all joins

**Example:**
```
/export_invite_logs
```

Downloads: `invite_logs_20251031.csv`

### `/sync_member_invites`
**Purpose:** Compare Discord invite counts vs database tracking

**Example:**
```
/sync_member_invites
```

## 🔧 Use Cases

### VIP Upgrade Attribution
When a user requests VIP upgrade:
1. Run `/lookup_user_invite @user`
2. See exactly which staff member referred them
3. Assign them to correct IB automatically
4. Credit the referral to the right staff member

### Data Recovery
If database is corrupted:
1. Logs are still intact
2. Can rebuild entire tracking database from logs
3. Zero data loss

### Dispute Resolution
If there's a question about who referred someone:
1. Check persistent logs (immutable)
2. Shows exact timestamp and invite code used
3. Definitive proof of referral source

### Analytics & Reporting
1. Export CSV file
2. Open in Excel
3. Create pivot tables for staff performance
4. Track referral trends over time

## 📊 Data Flow

```
Member Joins Server
       ↓
Bot Detects Join
       ↓
Identify Invite Code Used
       ↓
┌─────────────────────────┐
│ 1. Write to JSON Log    │ ← FIRST (Critical)
└─────────────────────────┘
       ↓
┌─────────────────────────┐
│ 2. Write to CSV Log     │ ← Backup Format
└─────────────────────────┘
       ↓
┌─────────────────────────┐
│ 3. Update Database      │ ← Can fail safely
└─────────────────────────┘
       ↓
┌─────────────────────────┐
│ 4. Backup to Cloud      │ ← Additional safety
└─────────────────────────┘
```

## 🛡️ Reliability Features

### File Locking
- JSON writes are atomic
- CSV appends are thread-safe
- No race conditions

### Error Handling
- If JSON write fails, CSV still written
- If database fails, logs still written
- Never loses data even with failures

### Backup Strategy
- **Primary:** JSON log (structured data)
- **Secondary:** CSV log (human-readable)
- **Tertiary:** SQLite database
- **Quaternary:** Cloud backup

## 📍 File Locations

```
pipvault-server-bot/
├── invite_logs/
│   ├── invite_joins.json  ← Primary log (DO NOT DELETE)
│   └── invite_joins.csv   ← Backup log (DO NOT DELETE)
└── cogs/
    └── invite_tracker.py  ← Main cog
```

## 🔐 Data Integrity

### Immutability
- Logs are append-only
- Previous entries never modified
- Complete audit trail

### Verification
- Each entry has timestamp
- User IDs are permanent
- Can cross-reference with Discord API

### Compliance
- Complete history for audits
- Transparent attribution
- Verifiable referral tracking

## 🚨 Important Notes

### DO NOT DELETE
- **Never delete** `invite_logs/invite_joins.json`
- **Never delete** `invite_logs/invite_joins.csv`
- These are your source of truth

### Backup Regularly
- Copy log files to external storage
- Commit to git repository
- Keep multiple backups

### Testing
- Check logs after each new join
- Verify CSV exports work
- Test lookup commands regularly

## 📈 Future Enhancements

Planned features:
- [ ] Automatic daily backups to cloud storage
- [ ] Log rotation (archive old logs, keep recent accessible)
- [ ] Search by date range
- [ ] Export filtered subsets
- [ ] Automatic database rebuild from logs
- [ ] Real-time log streaming dashboard

## 🆘 Troubleshooting

### "No invite logs found"
- First member hasn't joined yet
- Logs will be created automatically on first join

### "User not found in logs"
- User joined before logging system was active
- Check database as fallback (shown in command output)

### CSV won't open in Excel
- Ensure UTF-8 encoding support in Excel
- Try opening with Google Sheets
- Or use any text editor

## 💡 Best Practices

1. **Check logs weekly** - Ensure they're growing correctly
2. **Export monthly** - Keep historical snapshots
3. **Test commands** - Verify lookup works for recent joins
4. **Monitor file size** - Logs grow over time (normal)
5. **Never edit manually** - Preserve data integrity

---

**This system guarantees you will NEVER lose invite attribution data again.**
