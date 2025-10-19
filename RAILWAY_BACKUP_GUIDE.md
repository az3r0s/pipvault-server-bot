# 🛡️ Railway Database Backup & Restore Guide

## 🎯 THREE Ways to Backup Railway Database

### Option 1: In-Discord Backup (Easiest - NEW!)

**Deploy the bot first, then use Discord commands:**
```
/export_database
```
This command (admin-only) will:
- ✅ Run directly on Railway  
- ✅ Export your live database
- ✅ Send you the backup file via Discord
- ✅ Include all invite tracking data

### Option 2: Quick Local Backup
```bash
cd pipvault-server-bot
python quick_railway_backup.py
```

### Option 3: Railway CLI Method (You're already connected!)
```bash
# You're already linked! Just run:
railway run 'python quick_railway_backup.py'
```

## 📊 How to Export from Railway Cloud

### Method 1: Local Development Backup (Easiest)
1. **Run bot locally** with same database file
2. **Execute backup script** - it will backup whatever data Railway has synced
3. **Data exports to JSON** file with all your invite tracking data

### Method 2: Railway CLI Backup
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Connect to your project
railway link

# Download database file
railway run --service=your-bot-service 'cp server_management.db /tmp/backup.db'
```

### Method 3: Add Backup Command to Bot (Safest)
Add this admin command to your bot to backup from Railway directly.

## 🔄 How Restore Works

### If Something Goes Wrong:
```bash
# List available backups
python railway_database_backup.py --list

# Restore from backup (DANGEROUS - only if needed)
python railway_database_backup.py --restore backup_file.json --confirm
```

## 🚀 Railway-Specific Backup Strategy

### Before Welcome Screen Implementation:

1. **Create local backup** (quick_railway_backup.py)
2. **Deploy welcome screen changes**
3. **Verify data integrity** on Railway
4. **Keep backup file safe** for 30 days

### Railway Cloud Persistence Behavior:
- ✅ Database file persists across deployments
- ✅ New tables get added to existing file
- ✅ Existing data remains untouched
- ✅ `CREATE TABLE IF NOT EXISTS` is 100% safe

## 📋 Backup Verification

Check your backup contains:
```json
{
  "backup_info": {
    "created_at": "timestamp",
    "tables": 3
  },
  "data": {
    "invite_tracking": {
      "rows": [...your invite data...]
    },
    "staff_invites": {
      "rows": [...your staff data...]
    },
    "vip_requests": {
      "rows": [...your vip data...]
    }
  }
}
```

## 🆘 Emergency Restore Process

**Only if welcome screen implementation somehow corrupts data:**

1. **Stop Railway service**
2. **Download corrupted database**
3. **Run restore locally:**
   ```bash
   python railway_database_backup.py --restore your_backup.json --confirm
   ```
4. **Upload restored database to Railway**
5. **Restart service**

## ✅ Safety Checklist

Before deploying welcome screen:
- [ ] Backup created successfully
- [ ] Backup file contains your invite data
- [ ] Backup file size looks reasonable (should have data)
- [ ] File saved in safe location
- [ ] Team knows where backup is stored

## 🎯 Why This is Overkill (But Good Practice)

The welcome screen database changes are:
- ✅ **Additive only** - just adding new tables
- ✅ **Zero risk** to existing data
- ✅ **Tested and verified** safe

But having a backup is always smart for:
- Peace of mind
- Protection against other future changes
- General best practices
- Railway deployment safety

## 🚀 Ready to Deploy

Once backup is complete, you're ready to:
1. Deploy welcome screen implementation
2. Test new onboarding system
3. Verify existing invite tracking still works
4. Celebrate successful deployment! 🎉