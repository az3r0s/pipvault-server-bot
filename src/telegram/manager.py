#!/usr/bin/env python3
"""
Telegram Manager for VIP Chat System
====================================

This module manages the pool of dummy Telegram accounts used for VIP private chats.
It handles account authentication, session management, and message routing.

Key Features:
- Dummy account pool management
- Session file encryption and storage
- Automatic reconnection and health monitoring
- Message forwarding between Discord and Telegram
- Account rotation for load balancing
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiofiles
from cryptography.fernet import Fernet

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    FloodWaitError
)

logger = logging.getLogger(__name__)

class TelegramAccount:
    """Represents a single dummy Telegram account"""
    
    def __init__(self, phone: str, session_name: str, active: bool = True, session_string: Optional[str] = None):
        self.phone = phone
        self.session_name = session_name
        self.active = active
        self.session_string = session_string  # StringSession for Railway compatibility
        self.client: Optional[TelegramClient] = None
        self.current_user_id: Optional[str] = None
        self.session_started_at: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None
        self.is_connected = False
        
    def __repr__(self):
        status = "🟢 Connected" if self.is_connected else "🔴 Disconnected"
        user_status = f" (User: {self.current_user_id})" if self.current_user_id else " (Available)"
        return f"TelegramAccount({self.phone}{user_status}) - {status}"

class TelegramAccountManager:
    """Manages the pool of dummy Telegram accounts for VIP chats"""
    
    def __init__(self, api_id: int, api_hash: str, session_dir: str = "data/telegram_sessions"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Account pool
        self.accounts: List[TelegramAccount] = []
        self.active_sessions: Dict[str, TelegramAccount] = {}  # discord_user_id -> account
        
        # Encryption for session files
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Configuration
        self.max_concurrent_sessions = int(os.getenv('MAX_CONCURRENT_SESSIONS', '10'))
        self.session_timeout_hours = int(os.getenv('VIP_SESSION_TIMEOUT_HOURS', '24'))
        self.va_username = os.getenv('TELEGRAM_VA_USERNAME', '')
        
        logger.info(f"🔐 Telegram Account Manager initialized")
        logger.info(f"📂 Session directory: {self.session_dir}")
        logger.info(f"⚡ Max concurrent sessions: {self.max_concurrent_sessions}")
        logger.info(f"👤 VA Username: @{self.va_username}" if self.va_username else "⚠️ VA Username not configured")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for session files"""
        key_file = self.session_dir / "encryption.key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info("🔑 Generated new encryption key for session files")
            return key
    
    async def load_accounts_from_config(self) -> None:
        """Load dummy accounts from environment configuration using StringSession approach"""
        try:
            account_count = 0
            
            # Look for TELEGRAM_ACCOUNT_X_* environment variables
            for i in range(1, 11):  # Support up to 10 accounts
                phone_key = f'TELEGRAM_ACCOUNT_{i}_PHONE'
                session_key = f'TELEGRAM_ACCOUNT_{i}_SESSION'
                name_key = f'TELEGRAM_ACCOUNT_{i}_NAME'
                
                phone = os.getenv(phone_key)
                session_string = os.getenv(session_key)
                name = os.getenv(name_key, f'vip_account_{i}')
                
                if phone and session_string:
                    # Create account with session string
                    account = TelegramAccount(
                        phone=phone,
                        session_name=name,
                        active=True,
                        session_string=session_string  # Pass directly to constructor
                    )
                    
                    self.accounts.append(account)
                    account_count += 1
                    logger.info(f"📱 Loaded account: {phone} ({name}) with StringSession")
            
            if account_count == 0:
                logger.warning("⚠️ No Telegram accounts configured with StringSession format")
                logger.info("💡 Add environment variables: TELEGRAM_ACCOUNT_1_PHONE, TELEGRAM_ACCOUNT_1_SESSION, TELEGRAM_ACCOUNT_1_NAME")
                
                # Fallback to old JSON format for backward compatibility
                logger.info("🔄 Trying legacy JSON format...")
                await self._load_legacy_json_format()
            else:
                logger.info(f"✅ Loaded {account_count} dummy accounts from StringSession configuration")
            
        except Exception as e:
            logger.error(f"❌ Failed to load accounts from configuration: {e}")
    
    async def _load_legacy_json_format(self):
        """Fallback to legacy JSON format (for backward compatibility)"""
        try:
            accounts_json = os.getenv('TELEGRAM_DUMMY_ACCOUNTS', '[]')
            accounts_config = json.loads(accounts_json)
            
            for config in accounts_config:
                account = TelegramAccount(
                    phone=config['phone'],
                    session_name=config['session_name'],
                    active=config.get('active', True)
                )
                self.accounts.append(account)
                logger.info(f"📱 Loaded account (legacy): {account.phone} ({account.session_name})")
            
            if len(self.accounts) > 0:
                logger.info(f"✅ Loaded {len(self.accounts)} dummy accounts from legacy JSON configuration")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse TELEGRAM_DUMMY_ACCOUNTS JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to load legacy accounts: {e}")
    
    async def initialize_account(self, account: TelegramAccount) -> bool:
        """Initialize and authenticate a single Telegram account"""
        try:
            # Check if account has StringSession
            if hasattr(account, 'session_string') and account.session_string:
                # Use StringSession (preferred method for Railway)
                client = TelegramClient(
                    StringSession(account.session_string),
                    self.api_id,
                    self.api_hash,
                    device_model="VIP Chat Bot",
                    system_version="1.0",
                    app_version="1.0"
                )
                logger.info(f"🔗 Using StringSession for account {account.phone}")
            else:
                # Fallback to file session (legacy method)
                session_file = self.session_dir / f"{account.session_name}.session"
                client = TelegramClient(
                    str(session_file),
                    self.api_id,
                    self.api_hash,
                    device_model="VIP Chat Bot",
                    system_version="1.0",
                    app_version="1.0"
                )
                logger.info(f"📁 Using file session for account {account.phone}")
            
            account.client = client
            
            # Connect and authenticate
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error(f"❌ Account {account.phone} session is invalid or expired")
                return False
            
            # Test connection
            me = await client.get_me()
            account.is_connected = True
            account.session_started_at = datetime.now()
            
            # Set up event handlers for this account
            await self._setup_account_handlers(account)
            
            # Safe access to account name
            account_name = getattr(me, 'first_name', 'Unknown')
            logger.info(f"✅ Account {account.phone} ({account_name}) initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize account {account.phone}: {e}")
            account.is_connected = False
            return False
    
    async def _setup_account_handlers(self, account: TelegramAccount):
        """Set up message handlers for a Telegram account"""
        
        @account.client.on(events.NewMessage(incoming=True))
        async def handle_incoming_message(event):
            """Handle incoming messages from VA to user"""
            try:
                # Only process if this account has an active session
                if account.current_user_id:
                    sender = await event.get_sender()
                    message_text = event.message.message
                    
                    logger.info(f"📨 Received message from {sender.first_name} for user {account.current_user_id}")
                    
                    # Forward to Discord via callback (will be set up later)
                    await self._forward_to_discord(account.current_user_id, sender, message_text, event.message)
                    
                    account.last_activity = datetime.now()
            
            except Exception as e:
                logger.error(f"❌ Error handling incoming message: {e}")
        
        logger.info(f"🔧 Set up message handlers for account {account.phone}")
    
    async def _forward_to_discord(self, discord_user_id: str, sender, message_text: str, telegram_message):
        """Forward Telegram message to Discord thread"""
        try:
            # Check if message is from the configured VA
            if hasattr(sender, 'username') and sender.username == self.va_username:
                logger.info(f"📤 Forwarding VA reply to Discord - User: {discord_user_id}")
                
                # Call Discord callback if set
                if hasattr(self, 'discord_callback') and self.discord_callback:
                    await self.discord_callback(discord_user_id, message_text)
                else:
                    logger.warning("No Discord callback set for forwarding messages")
            else:
                logger.debug(f"Ignoring message from non-VA user: {sender.username if hasattr(sender, 'username') else 'Unknown'}")
                
        except Exception as e:
            logger.error(f"❌ Error forwarding to Discord: {e}")
    
    def set_discord_callback(self, callback):
        """Set callback function for forwarding messages to Discord"""
        self.discord_callback = callback
        logger.info("✅ Discord callback set for message forwarding")
    
    async def get_available_account(self) -> Optional[TelegramAccount]:
        """Get an available account for a new VIP session"""
        for account in self.accounts:
            if account.active and account.is_connected and not account.current_user_id:
                return account
        
        logger.warning("⚠️ No available accounts for new VIP session")
        return None
    
    async def assign_account(self, discord_user_id: str) -> Optional[TelegramAccount]:
        """Assign an account to a Discord user for VIP chat"""
        if len(self.active_sessions) >= self.max_concurrent_sessions:
            logger.warning(f"⚠️ Maximum concurrent sessions reached ({self.max_concurrent_sessions})")
            return None
        
        account = await self.get_available_account()
        if not account:
            return None
        
        # Assign account to user
        account.current_user_id = discord_user_id
        account.session_started_at = datetime.now()
        account.last_activity = datetime.now()
        self.active_sessions[discord_user_id] = account
        
        logger.info(f"✅ Assigned account {account.phone} to Discord user {discord_user_id}")
        return account
    
    async def release_account(self, discord_user_id: str) -> bool:
        """Release an account from VIP session"""
        if discord_user_id not in self.active_sessions:
            return False
        
        account = self.active_sessions[discord_user_id]
        account.current_user_id = None
        account.session_started_at = None
        
        del self.active_sessions[discord_user_id]
        
        logger.info(f"🔓 Released account {account.phone} from Discord user {discord_user_id}")
        return True
    
    async def send_message(self, discord_user_id: str, va_username: str, message: str) -> bool:
        """Send message from dummy account to VA - appears as natural Telegram conversation"""
        if discord_user_id not in self.active_sessions:
            logger.error(f"❌ No active session for Discord user {discord_user_id}")
            return False
        
        account = self.active_sessions[discord_user_id]
        
        try:
            # Find VA user  
            va_user = await account.client.get_entity(va_username)
            
            # Send message FROM the dummy account TO the VA
            # This creates a natural conversation that the VA sees as:
            # "Dummy Account Name: [customer's message]"
            await account.client.send_message(va_user, message)
            
            account.last_activity = datetime.now()
            logger.info(f"📤 Sent message from dummy account {account.phone} to VA {va_username}: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message to VA {va_username}: {e}")
            return False
    
    async def cleanup_expired_sessions(self):
        """Clean up expired VIP sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for discord_user_id, account in self.active_sessions.items():
            if account.session_started_at:
                session_age = current_time - account.session_started_at
                if session_age > timedelta(hours=self.session_timeout_hours):
                    expired_sessions.append(discord_user_id)
        
        for discord_user_id in expired_sessions:
            await self.release_account(discord_user_id)
            logger.info(f"🧹 Cleaned up expired session for user {discord_user_id}")
    
    async def start_all_accounts(self):
        """Initialize and start all configured accounts"""
        logger.info(f"🚀 Starting {len(self.accounts)} Telegram accounts...")
        
        for account in self.accounts:
            if account.active:
                success = await self.initialize_account(account)
                if success:
                    logger.info(f"✅ Account {account.phone} started successfully")
                else:
                    logger.error(f"❌ Failed to start account {account.phone}")
        
        active_count = sum(1 for acc in self.accounts if acc.is_connected)
        logger.info(f"🎯 Started {active_count}/{len(self.accounts)} Telegram accounts")
    
    async def stop_all_accounts(self):
        """Stop all Telegram accounts and cleanup"""
        logger.info("🛑 Stopping all Telegram accounts...")
        
        for account in self.accounts:
            if account.client and account.is_connected:
                try:
                    await account.client.disconnect()
                    account.is_connected = False
                    logger.info(f"🔌 Disconnected account {account.phone}")
                except Exception as e:
                    logger.error(f"❌ Error disconnecting account {account.phone}: {e}")
        
        logger.info("✅ All Telegram accounts stopped")
    
    def get_status(self) -> Dict:
        """Get status of all accounts and active sessions"""
        return {
            'total_accounts': len(self.accounts),
            'connected_accounts': sum(1 for acc in self.accounts if acc.is_connected),
            'active_sessions': len(self.active_sessions),
            'max_sessions': self.max_concurrent_sessions,
            'accounts': [
                {
                    'phone': acc.phone,
                    'session_name': acc.session_name,
                    'connected': acc.is_connected,
                    'assigned_user': acc.current_user_id,
                    'last_activity': acc.last_activity.isoformat() if acc.last_activity else None
                }
                for acc in self.accounts
            ]
        }

# Global manager instance (will be initialized by main bot)
telegram_manager: Optional[TelegramAccountManager] = None

async def initialize_telegram_manager() -> TelegramAccountManager:
    """Initialize the global Telegram account manager"""
    global telegram_manager
    
    api_id = int(os.getenv('TELEGRAM_API_ID', '0'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '')
    
    if not api_id or not api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured")
    
    telegram_manager = TelegramAccountManager(api_id, api_hash)
    await telegram_manager.load_accounts_from_config()
    await telegram_manager.start_all_accounts()
    
    return telegram_manager

async def cleanup_telegram_manager():
    """Cleanup the global Telegram account manager"""
    global telegram_manager
    if telegram_manager:
        await telegram_manager.stop_all_accounts()
        telegram_manager = None