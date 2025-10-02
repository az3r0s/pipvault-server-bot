# 🔗 **Staff Invite Management Guide**

This guide explains how to set up and manage permanent invite links for staff members in the VIP upgrade system.

---

## 🎯 **Overview**

Each staff member gets their own permanent Discord invite link that:
- ✅ **Never expires** and has **unlimited uses**
- ✅ **Tracks all users** who join through their link
- ✅ **Attributes VIP upgrades** to the correct staff member
- ✅ **Uses their personal Vantage referral link** for new accounts
- ✅ **Includes their name** in email templates for existing accounts

---

## 🚀 **Quick Setup Process**

### **Method 1: Automated Creation (Recommended)**

Use the bot command to automatically create and configure invite links:

```
/create_staff_invite @staff_member https://vantage.com/ref/their_code "email_template_here"
```

**Example**:
```
/create_staff_invite @john_trader https://vantage.com/ref/john123 "Subject: VIP Upgrade Request from {username}

Hello Vantage Team,

I would like to request VIP access for my Discord account.

Discord Username: {username}
Discord ID: {discord_id}
Staff Member: {staff_name}
Request ID: {request_id}

Please verify my account and grant VIP access.

Best regards"
```

### **Method 2: Manual Creation**

1. **Create Discord Invite**:
   - Right-click server name → "Invite People"
   - Click "Edit invite link"
   - Set: **Never expires**, **No limit** uses, **Permanent membership**
   - Copy invite code (e.g., `abc123` from `https://discord.gg/abc123`)

2. **Configure in Bot**:
   ```
   /setup_staff_invite @staff_member abc123 https://vantage.com/ref/staff123 "email_template"
   ```

---

## 📋 **Email Template Guidelines**

### **Required Placeholders**:
- `{username}` - Discord display name
- `{discord_id}` - Discord user ID
- `{staff_name}` - Staff member's name
- `{request_id}` - Unique request ID for tracking

### **EGN/Vantage Template Example**:
```
Subject: EGN

Hi I am a member of EGN,

Please move my account under IB {ib_code}.

Name: {username}
Email: [User will fill this in]
Live vantage acc number: [User will fill this in]

Kind regards,
{username}
```

### **Staff-Specific Setup Examples**:

**Staff Member 1 (IB: 7470320)**:
```
/create_staff_invite @staff1 https://www.vantagemarkets.com/open-live-account/?affid=NzQ3MDMyMA== "Subject: EGN

Hi I am a member of EGN,

Please move my account under IB 7470320.

Name: {username}
Email: [Please enter your Vantage account email]
Live vantage acc number: [Please enter your live account number]

Kind regards,
{username}"
```

**Staff Member 2 (IB: 7470272)**:
```
/create_staff_invite @staff2 https://www.vantagemarkets.com/open-live-account/?affid=NzQ3MDI3Mg== "Subject: EGN

Hi I am a member of EGN,

Please move my account under IB 7470272.

Name: {username}
Email: [Please enter your Vantage account email]
Live vantage acc number: [Please enter your live account number]

Kind regards,
{username}"
```

---

## 🛠️ **Management Commands**

### **Administrative Commands**

| Command | Description | Usage |
|---------|-------------|-------|
| `/create_staff_invite` | Create permanent invite + configure | `/create_staff_invite @user vantage_link "template"` |
| `/setup_staff_invite` | Configure existing invite | `/setup_staff_invite @user code vantage_link "template"` |
| `/list_staff_invites` | View all configured staff invites | `/list_staff_invites` |
| `/approve_vip` | Approve VIP request | `/approve_vip 123 @user` |
| `/deny_vip` | Deny VIP request | `/deny_vip 123 "reason"` |

### **Analytics Commands**

| Command | Description | Usage |
|---------|-------------|-------|
| `/invite_stats` | View staff performance | `/invite_stats @staff_member` |
| `/vip_stats` | View system statistics | `/vip_stats` |
| `/vip_requests` | View pending requests | `/vip_requests pending` |

---

## 📊 **How Staff Attribution Works**

### **User Journey**:
1. **User joins** via staff invite (`https://discord.gg/john123`)
2. **System records**: User X joined via John's invite
3. **User requests VIP**: Goes to #vip-upgrade channel
4. **System retrieves**: John's configuration (Vantage link + email template)
5. **Dynamic content**: Shows John's Vantage referral or John's email template
6. **Staff gets credit**: VIP conversion attributed to John

### **Database Tracking**:
```
User #12345 → Invite "john123" → Staff John → Vantage Referral: john_ref_123
```

---

## 🔧 **Staff Member Setup Checklist**

### **For Each Staff Member**:

- [ ] **Get Vantage Referral Link**
  - Staff member provides their personal Vantage referral URL
  - Format: `https://vantage.com/ref/their_unique_code`

- [ ] **Create Email Template**
  - Include all required placeholders
  - Personalize with staff member's name
  - Keep professional tone

- [ ] **Generate Invite Link**
  - Use `/create_staff_invite` command
  - Verify invite is permanent and unlimited

- [ ] **Test the Flow**
  - Staff member tests their invite link
  - Verify VIP upgrade process works
  - Check attribution is correct

- [ ] **Share with Staff**
  - Staff member receives DM with their invite link
  - Provide instructions on how to share
  - Explain commission/attribution system

---

## 📈 **Performance Tracking**

### **Key Metrics per Staff Member**:
- **Total Invites**: How many users joined via their link
- **VIP Conversions**: How many became VIP members
- **Conversion Rate**: VIP conversions / Total invites × 100
- **Pending Requests**: Current VIP requests awaiting approval

### **View Staff Performance**:
```
/invite_stats @john_trader
```

### **System Overview**:
```
/vip_stats
```

---

## ⚠️ **Important Notes**

### **Invite Link Security**:
- ✅ Invite links are **permanent** - don't delete unless necessary
- ✅ Each staff member should have **only one** active invite
- ✅ **Don't share** invite codes between staff members
- ✅ **Track performance** regularly to optimize attribution

### **Vantage Referral Links**:
- ✅ Each staff member **must have their own** Vantage referral
- ✅ **Test referral links** before configuring in bot
- ✅ **Update immediately** if referral links change
- ✅ **Coordinate with Vantage** for proper commission tracking

### **Email Templates**:
- ✅ **Keep templates professional** and consistent
- ✅ **Include all required placeholders** for proper attribution
- ✅ **Test email flow** with Vantage support team
- ✅ **Update templates** if Vantage requirements change

---

## 🚨 **Troubleshooting**

### **Common Issues**:

**Invite Not Tracking Users**:
- ✅ Check invite hasn't expired or reached use limit
- ✅ Verify invite is configured in bot database
- ✅ Check bot has necessary permissions

**VIP Attribution Wrong**:
- ✅ Verify user joined via correct invite link
- ✅ Check staff configuration in database
- ✅ Review invite tracking logs

**Email Template Not Working**:
- ✅ Check all placeholders are included
- ✅ Verify template is saved in database
- ✅ Test with sample VIP request

**Vantage Referral Issues**:
- ✅ Test referral link manually
- ✅ Coordinate with Vantage support
- ✅ Update link in bot configuration

---

## 📞 **Support**

For technical issues:
1. Check bot logs for error messages
2. Use `/list_staff_invites` to verify configuration
3. Test invite tracking with dummy accounts
4. Contact bot administrator for database issues

**Ready to set up your staff invite system!** 🚀