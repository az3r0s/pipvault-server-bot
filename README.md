# 🤖 Zinrai Discord Server Management Bot

A specialized Discord bot for managing server features, separated from the trading bot for better reliability and maintainability.

## 🎯 **Features**

### 👑 VIP Upgrade System
- **Invite Tracking**: Automatically tracks which staff invite each user joined through
- **Dynamic Attribution**: Email templates and referral links personalized per staff member
- **Interactive Process**: Button-driven flow for existing vs new Vantage accounts
- **Staff Analytics**: Track conversion rates and invite performance
- **Automated Workflow**: Seamless integration with Vantage account verification

### 🔗 Invite Management
- Real-time invite usage tracking
- Staff member attribution and statistics
- Automatic invite cache updates
- Support for multiple staff referral systems

## 🚀 **Quick Start**

### Prerequisites
1. **Discord Bot Application**: Create a new bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. **Bot Permissions**: Administrator permissions (or specific permissions as needed)
3. **Python 3.8+**: Required for Discord.py
4. **Environment Variables**: Set up as described below

### Installation

1. **Install Dependencies**:
   ```bash
   cd server_bot
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.template .env
   # Edit .env with your bot token and configuration
   ```

3. **Run the Bot**:
   ```bash
   python main.py
   ```

## ⚙️ **Configuration**

### Required Environment Variables

```bash
# Discord Bot Configuration
SERVER_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_server_id

# VIP Upgrade System
VIP_UPGRADE_CHANNEL_ID=channel_id_for_vip_upgrades
VIP_ROLE_ID=role_id_for_vip_members
STAFF_NOTIFICATION_CHANNEL_ID=channel_for_staff_notifications
```

### Optional Configuration

```bash
# Database
DATABASE_URL=sqlite:///server_management.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=server_bot.log

# Bot Settings
BOT_PREFIX=!server
```

## 📋 **Setup Guide**

### 1. Discord Bot Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application and bot
3. Copy bot token to `SERVER_BOT_TOKEN`
4. Invite bot to server with Administrator permissions

### 2. VIP Upgrade Channel Setup
1. Create a dedicated channel for VIP upgrades (e.g., #vip-upgrade)
2. Copy channel ID to `VIP_UPGRADE_CHANNEL_ID`
3. Run `/setup_vip_channel` command in the channel

### 3. Staff Invite Configuration
For each staff member, run:
```
/setup_staff_invite @staff_member invite_code vantage_referral_link "email_template"
```

**Example**:
```
/setup_staff_invite @john abc123 https://vantage.com/ref/john123 "Subject: VIP Upgrade Request from {username}

Hello Vantage Team,

I would like to request VIP access for my Discord account.

Discord Username: {username}
Discord ID: {discord_id}
Staff Member: {staff_name}
Request ID: {request_id}

Please verify my account and grant VIP access.

Best regards"
```

## 🎮 **Commands**

### Admin Commands
- `/setup_vip_channel [channel]` - Set up VIP upgrade system
- `/setup_staff_invite` - Configure staff invite attribution
- `/approve_vip <request_id> <user>` - Approve VIP request
- `/deny_vip <request_id> [reason]` - Deny VIP request
- `/vip_stats` - View VIP upgrade statistics

### Staff Commands
- `/vip_requests [status]` - View VIP requests by status
- `/invite_stats [staff_member]` - View invite statistics

## 🔧 **How It Works**

### VIP Upgrade Flow

1. **User Joins Server**: Invite tracker records which staff invite was used
2. **User Requests VIP**: Clicks "Upgrade to VIP" button in designated channel
3. **Account Type Selection**: User chooses existing account or new account
4. **Existing Account Path**:
   - Shows personalized email template with staff attribution
   - User sends email from Vantage account email
   - Staff verifies and approves
5. **New Account Path**:
   - Shows staff member's personalized Vantage referral link
   - User creates account using that link
   - User provides Vantage email for verification
   - Staff verifies deposit and approves

### Database Schema

#### Invite Tracking
```sql
CREATE TABLE invite_tracking (
    user_id INTEGER PRIMARY KEY,
    invite_code TEXT,
    inviter_id INTEGER,
    inviter_username TEXT,
    joined_at TIMESTAMP
);
```

#### Staff Configuration
```sql
CREATE TABLE staff_invites (
    staff_id INTEGER PRIMARY KEY,
    invite_code TEXT,
    vantage_referral_link TEXT,
    email_template TEXT
);
```

#### VIP Requests
```sql
CREATE TABLE vip_requests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    request_type TEXT,
    staff_id INTEGER,
    status TEXT,
    vantage_email TEXT
);
```

## 🚀 **Railway Deployment**

### Setup Railway Service

1. **Create New Service** in Railway dashboard
2. **Connect GitHub Repository**
3. **Set Environment Variables** in Railway dashboard
4. **Deploy**: Railway will automatically build and deploy

### Environment Variables in Railway

```
SERVER_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_guild_id
VIP_UPGRADE_CHANNEL_ID=your_channel_id
VIP_ROLE_ID=your_vip_role_id
```

### Build Configuration

The `railway.json` file is already configured for Railway deployment:

```json
{
  "build": {
    "commands": [
      "cd server_bot",
      "pip install -r requirements.txt"
    ]
  },
  "start": {
    "command": "cd server_bot && python main.py"
  }
}
```

## 📊 **Monitoring & Analytics**

### Staff Performance Tracking
- Total invites per staff member
- VIP conversion rates
- Pending request volumes
- Monthly/weekly performance trends

### System Health
- Bot uptime and response times
- Database query performance
- Discord API rate limit monitoring
- Error tracking and alerting

## 🔍 **Troubleshooting**

### Common Issues

**Bot Not Responding**:
- Check bot token is correct
- Verify bot has necessary permissions
- Check console logs for errors

**VIP Upgrade Not Working**:
- Verify `VIP_UPGRADE_CHANNEL_ID` is set correctly
- Check if sticky embed exists in channel
- Ensure staff invite configurations are set up

**Database Issues**:
- Check database file permissions
- Verify database initialization completed
- Check logs for database errors

### Logs

Bot logs are written to:
- Console output (real-time)
- `server_bot.log` file
- Railway deployment logs (in Railway dashboard)

## 🤝 **Integration with Trading Bot**

This server bot is designed to work alongside the main trading bot:

- **Shared Database**: Can access same database for signal statistics
- **Independent Operation**: Runs as separate Railway service
- **No Interference**: Server features don't affect trading operations

## 📝 **License**

This project is part of the Zinrai trading system and is proprietary software.

## 📞 **Support**

For issues or questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Contact the development team
4. Check Discord server for community support

---

**🎯 Ready to enhance your Discord server with automated VIP management!**