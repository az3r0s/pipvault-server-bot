#!/usr/bin/env python3
"""
Server Bot Test Script
=====================

Test script to validate server bot setup and functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import discord
        print("✅ discord.py imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import discord.py: {e}")
        return False
    
    try:
        from server_bot.utils.database import ServerDatabase
        print("✅ ServerDatabase imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ServerDatabase: {e}")
        return False
    
    try:
        from server_bot.views.vip_upgrade import VIPUpgradeView
        print("✅ VIPUpgradeView imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import VIPUpgradeView: {e}")
        return False
    
    try:
        from server_bot.cogs.vip_upgrade import VIPUpgrade
        print("✅ VIPUpgrade cog imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import VIPUpgrade cog: {e}")
        return False
    
    try:
        from server_bot.cogs.invite_tracker import InviteTracker
        print("✅ InviteTracker cog imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import InviteTracker cog: {e}")
        return False
    
    return True

def test_database():
    """Test database initialization and basic operations"""
    print("\n🗄️ Testing database...")
    
    try:
        from server_bot.utils.database import ServerDatabase
        
        # Initialize database
        db = ServerDatabase("test_server.db")
        print("✅ Database initialized successfully")
        
        # Test recording a user join
        success = db.record_user_join(
            user_id=12345,
            username="TestUser#1234",
            invite_code="test123",
            inviter_id=67890,
            inviter_username="TestInviter#5678",
            uses_before=0,
            uses_after=1
        )
        
        if success:
            print("✅ User join recorded successfully")
        else:
            print("❌ Failed to record user join")
            return False
        
        # Test retrieving user invite info
        invite_info = db.get_user_invite_info(12345)
        if invite_info:
            print(f"✅ User invite info retrieved: {invite_info}")
        else:
            print("❌ Failed to retrieve user invite info")
            return False
        
        # Test staff invite configuration
        success = db.add_staff_invite_config(
            staff_id=67890,
            staff_username="TestInviter#5678",
            invite_code="test123",
            vantage_referral_link="https://vantage.com/ref/test",
            email_template="Test email template for {username}"
        )
        
        if success:
            print("✅ Staff invite config added successfully")
        else:
            print("❌ Failed to add staff invite config")
            return False
        
        # Test creating VIP request
        request_id = db.create_vip_request(
            user_id=12345,
            username="TestUser#1234",
            request_type="existing_account",
            staff_id=67890,
            request_data='{"test": "data"}'
        )
        
        if request_id:
            print(f"✅ VIP request created with ID: {request_id}")
        else:
            print("❌ Failed to create VIP request")
            return False
        
        # Clean up test database
        os.remove("test_server.db")
        print("✅ Test database cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_environment():
    """Test environment variable configuration"""
    print("\n🌍 Testing environment configuration...")
    
    required_vars = [
        'SERVER_BOT_TOKEN',
        'DISCORD_GUILD_ID',
    ]
    
    optional_vars = [
        'VIP_UPGRADE_CHANNEL_ID',
        'VIP_ROLE_ID',
        'STAFF_NOTIFICATION_CHANNEL_ID'
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            print(f"✅ {var} is set")
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
        else:
            print(f"✅ {var} is set")
    
    if missing_required:
        print(f"❌ Missing required environment variables: {missing_required}")
        print("⚠️ Bot will not function without these variables")
        return False
    
    if missing_optional:
        print(f"⚠️ Missing optional environment variables: {missing_optional}")
        print("ℹ️ Some features may be disabled")
    
    return True

def test_file_structure():
    """Test that all required files exist"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "server_bot/main.py",
        "server_bot/utils/database.py",
        "server_bot/views/vip_upgrade.py", 
        "server_bot/cogs/vip_upgrade.py",
        "server_bot/cogs/invite_tracker.py",
        "server_bot/requirements.txt",
        "server_bot/README.md"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = Path(__file__).parent.parent / file_path
        if full_path.exists():
            print(f"✅ {file_path} exists")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path} missing")
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    return True

async def test_bot_initialization():
    """Test bot initialization (without connecting)"""
    print("\n🤖 Testing bot initialization...")
    
    try:
        # Set dummy environment variables for testing
        os.environ.setdefault('SERVER_BOT_TOKEN', 'dummy_token_for_testing')
        os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
        
        from server_bot.main import ZinraiServerBot
        
        # Create bot instance (don't start it)
        bot = ZinraiServerBot()
        print("✅ Bot instance created successfully")
        
        # Test that required attributes exist
        if hasattr(bot, 'db'):
            print("✅ Database instance attached to bot")
        else:
            print("❌ Database instance not attached to bot")
            return False
        
        if hasattr(bot, 'GUILD_ID'):
            print("✅ Guild ID configuration loaded")
        else:
            print("❌ Guild ID configuration not loaded")
            return False
        
        # Clean up
        await bot.close()
        print("✅ Bot instance cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot initialization test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 ZINRAI SERVER BOT TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Database Tests", test_database),
        ("Environment Tests", test_environment),
        ("File Structure Tests", test_file_structure),
        ("Bot Initialization Tests", test_bot_initialization)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print(f"\n📊 TEST RESULTS")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Server bot is ready for deployment.")
        return True
    else:
        print("⚠️ Some tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())