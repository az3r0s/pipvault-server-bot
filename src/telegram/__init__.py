"""
Telegram Integration Module
==========================

This module provides Telegram integration for the VIP chat system.
It manages dummy Telegram accounts and handles message routing between
Discord threads and Telegram chats with VAs.

Components:
- TelegramAccountManager: Manages pool of dummy accounts
- Session management and encryption
- Message forwarding and routing
- Account health monitoring
"""

from .manager import (
    TelegramAccount,
    TelegramAccountManager,
    telegram_manager,
    initialize_telegram_manager,
    cleanup_telegram_manager
)

__all__ = [
    'TelegramAccount',
    'TelegramAccountManager', 
    'telegram_manager',
    'initialize_telegram_manager',
    'cleanup_telegram_manager'
]