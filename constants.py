# Create a simple constants file for the server bot
# This replaces the shared.constants import

import discord

class Colors:
    """Discord embed colors"""
    GREEN = discord.Color.green()
    RED = discord.Color.red()
    BLUE = discord.Color.blue()
    ORANGE = discord.Color.orange()
    GOLD = discord.Color.gold()
    PURPLE = discord.Color.purple()

class Emojis:
    """Discord emojis"""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    MONEY = "💰"
    CHART = "📈"
    BELL = "🔔"