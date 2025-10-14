#!/usr/bin/env python3
"""
Database Backup Discord Commands
===============================

Discord slash commands for managing database backups in the PipVault bot.
Provides administrative interface for backup and restore operations.

Commands:
- /export_database - Create a backup of all database data
- /import_database - Restore data from a backup file
- /list_backups - Show available backup files
- /backup_status - Display backup system status
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from database_backup import DatabaseBackupManager

logger = logging.getLogger(__name__)

class DatabaseBackupCommands(commands.Cog):
    """
    Discord commands for database backup and restore operations.
    
    Provides secure administrative interface for data management.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the backup commands cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.backup_manager = None
        
        # Admin role/user IDs (customize these)
        self.admin_role_ids = [
            int(os.getenv('ADMIN_ROLE_ID', 0)),
            int(os.getenv('OWNER_ROLE_ID', 0))
        ]
        self.admin_user_ids = [
            int(os.getenv('OWNER_USER_ID', 0))
        ]
        
        logger.info("✅ DatabaseBackupCommands cog initialized")
    
    async def cog_load(self):
        """Initialize backup manager when cog loads."""
        try:
            # Get database path from bot's database instance
            if hasattr(self.bot, 'db') and hasattr(self.bot.db, 'db_path'):
                db_path = self.bot.db.db_path
            else:
                db_path = "data/server.db"  # Default path
            
            self.backup_manager = DatabaseBackupManager(db_path)
            logger.info(f"✅ Backup manager initialized with database: {db_path}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize backup manager: {e}")
    
    def _is_admin(self, interaction: discord.Interaction) -> bool:
        """
        Check if user has admin permissions.
        
        Args:
            interaction: Discord interaction
            
        Returns:
            bool: True if user is admin
        """
        # Check if user ID is in admin list
        if interaction.user.id in self.admin_user_ids:
            return True
        
        # Check if user has admin roles
        if hasattr(interaction.user, 'roles'):
            user_role_ids = [role.id for role in interaction.user.roles]
            if any(role_id in self.admin_role_ids for role_id in user_role_ids):
                return True
        
        # Check if user has administrator permission
        if hasattr(interaction.user, 'guild_permissions'):
            if interaction.user.guild_permissions.administrator:
                return True
        
        return False
    
    @app_commands.command(name="export_database", description="Create a backup of all database data")
    @app_commands.describe(filename="Optional custom filename for the backup")
    async def export_database(self, interaction: discord.Interaction, filename: Optional[str] = None):
        """
        Export all database data to a backup file.
        
        Args:
            interaction: Discord interaction
            filename: Optional custom filename
        """
        # Check permissions
        if not self._is_admin(interaction):
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not self.backup_manager:
            embed = discord.Embed(
                title="❌ Error",
                description="Backup manager not initialized.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Defer response as backup might take time
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate filename if provided
            if filename:
                if not filename.endswith('.json'):
                    filename += '.json'
                # Remove potentially dangerous characters
                filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            
            # Create backup
            backup_path = await self.backup_manager.export_all_data(filename)
            backup_file = Path(backup_path)
            
            # Get file stats
            file_size = backup_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            embed = discord.Embed(
                title="✅ Database Export Completed",
                description="Successfully created database backup.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="📁 Backup File",
                value=f"`{backup_file.name}`",
                inline=False
            )
            
            embed.add_field(
                name="📊 File Size",
                value=f"{file_size_mb:.2f} MB ({file_size:,} bytes)",
                inline=True
            )
            
            embed.add_field(
                name="📍 Location",
                value=f"`{backup_file.parent}`",
                inline=True
            )
            
            embed.set_footer(text="Use /list_backups to see all available backups")
            
            await interaction.followup.send(embed=embed)
            logger.info(f"✅ Database export completed by {interaction.user}: {backup_path}")
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Export Failed",
                description=f"Failed to create database backup:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            logger.error(f"❌ Database export failed for {interaction.user}: {e}")
    
    @app_commands.command(name="import_database", description="Restore data from a backup file")
    @app_commands.describe(
        filename="Name of the backup file to restore from",
        overwrite="Whether to overwrite existing records (default: False)"
    )
    async def import_database(
        self, 
        interaction: discord.Interaction, 
        filename: str, 
        overwrite: bool = False
    ):
        """
        Import data from a backup file.
        
        Args:
            interaction: Discord interaction
            filename: Backup file name
            overwrite: Whether to overwrite existing records
        """
        # Check permissions
        if not self._is_admin(interaction):
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not self.backup_manager:
            embed = discord.Embed(
                title="❌ Error",
                description="Backup manager not initialized.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Defer response as import might take time
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Find backup file
            backup_path = self.backup_manager.backup_dir / filename
            if not backup_path.exists():
                # Try without .json extension
                backup_path = self.backup_manager.backup_dir / f"{filename}.json"
                if not backup_path.exists():
                    embed = discord.Embed(
                        title="❌ File Not Found",
                        description=f"Backup file `{filename}` not found.\nUse `/list_backups` to see available files.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            
            # Confirmation for overwrite mode
            if overwrite:
                embed = discord.Embed(
                    title="⚠️ Confirmation Required",
                    description=f"You are about to restore data from `{backup_path.name}` with **overwrite mode enabled**.\n\n"
                               "This will replace existing records with backup data.\n"
                               "Are you sure you want to continue?",
                    color=discord.Color.orange()
                )
                
                # Add confirmation buttons
                view = ConfirmationView()
                await interaction.followup.send(embed=embed, view=view)
                
                # Wait for confirmation
                await view.wait()
                if not view.confirmed:
                    embed = discord.Embed(
                        title="❌ Import Cancelled",
                        description="Database import was cancelled by user.",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=embed, view=None)
                    return
            
            # Perform import
            stats = await self.backup_manager.import_all_data(str(backup_path), overwrite)
            
            embed = discord.Embed(
                title="✅ Database Import Completed",
                description="Successfully restored data from backup.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="📁 Source File",
                value=f"`{backup_path.name}`",
                inline=False
            )
            
            embed.add_field(
                name="📊 Import Statistics",
                value=f"**Tables Processed:** {stats['tables_processed']}\n"
                      f"**Records Imported:** {stats['records_imported']}\n"
                      f"**Records Skipped:** {stats['records_skipped']}",
                inline=False
            )
            
            if stats['errors']:
                error_text = '\n'.join(stats['errors'][:5])  # Show first 5 errors
                if len(stats['errors']) > 5:
                    error_text += f"\n... and {len(stats['errors']) - 5} more errors"
                
                embed.add_field(
                    name="⚠️ Errors",
                    value=f"```{error_text}```",
                    inline=False
                )
            
            await interaction.edit_original_response(embed=embed, view=None)
            logger.info(f"✅ Database import completed by {interaction.user}: {backup_path}")
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Import Failed",
                description=f"Failed to restore database backup:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            logger.error(f"❌ Database import failed for {interaction.user}: {e}")
    
    @app_commands.command(name="list_backups", description="Show available backup files")
    async def list_backups(self, interaction: discord.Interaction):
        """
        List all available backup files.
        
        Args:
            interaction: Discord interaction
        """
        # Check permissions
        if not self._is_admin(interaction):
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not self.backup_manager:
            embed = discord.Embed(
                title="❌ Error",
                description="Backup manager not initialized.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            backups = self.backup_manager.list_backups()
            
            if not backups:
                embed = discord.Embed(
                    title="📁 No Backups Found",
                    description="No backup files are currently available.",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📁 Available Backup Files",
                description=f"Found {len(backups)} backup file(s)",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Show up to 10 most recent backups
            for i, backup in enumerate(backups[:10]):
                size_mb = backup['size'] / (1024 * 1024)
                created_date = datetime.fromisoformat(backup['created'].replace('Z', '+00:00'))
                
                embed.add_field(
                    name=f"📄 {backup['filename']}",
                    value=f"**Size:** {size_mb:.2f} MB\n"
                          f"**Created:** <t:{int(created_date.timestamp())}:R>",
                    inline=True
                )
            
            if len(backups) > 10:
                embed.set_footer(text=f"Showing 10 of {len(backups)} backup files")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to list backups:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.error(f"❌ Failed to list backups for {interaction.user}: {e}")
    
    @app_commands.command(name="backup_status", description="Display backup system status")
    async def backup_status(self, interaction: discord.Interaction):
        """
        Show backup system status and configuration.
        
        Args:
            interaction: Discord interaction
        """
        # Check permissions
        if not self._is_admin(interaction):
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not self.backup_manager:
            embed = discord.Embed(
                title="❌ Error",
                description="Backup manager not initialized.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            status = self.backup_manager.get_backup_status()
            
            embed = discord.Embed(
                title="🔧 Backup System Status",
                color=discord.Color.green() if not status['backup_in_progress'] else discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Current status
            status_emoji = "🔄" if status['backup_in_progress'] else "✅"
            status_text = "In Progress" if status['backup_in_progress'] else "Ready"
            
            embed.add_field(
                name="📊 Current Status",
                value=f"{status_emoji} {status_text}",
                inline=True
            )
            
            # Last backup
            if status['last_backup_time']:
                last_backup = datetime.fromisoformat(status['last_backup_time'].replace('Z', '+00:00'))
                embed.add_field(
                    name="🕒 Last Backup",
                    value=f"<t:{int(last_backup.timestamp())}:R>",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🕒 Last Backup",
                    value="Never",
                    inline=True
                )
            
            # Available backups
            embed.add_field(
                name="📁 Available Backups",
                value=str(status['available_backups']),
                inline=True
            )
            
            # Configuration
            cloud_status = "✅ Enabled" if status['cloud_configured'] else "❌ Disabled"
            handlers_status = "✅ Registered" if status['shutdown_handlers_registered'] else "❌ Not Registered"
            
            embed.add_field(
                name="⚙️ Configuration",
                value=f"**Cloud Storage:** {cloud_status}\n"
                      f"**Auto Backup:** {handlers_status}",
                inline=False
            )
            
            # Paths
            embed.add_field(
                name="📍 Paths",
                value=f"**Database:** `{status['database_path']}`\n"
                      f"**Backup Dir:** `{status['backup_directory']}`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to get backup status:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.error(f"❌ Failed to get backup status for {interaction.user}: {e}")

class ConfirmationView(discord.ui.View):
    """Simple confirmation view for dangerous operations."""
    
    def __init__(self):
        super().__init__(timeout=60)
        self.confirmed = False
    
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm the operation."""
        self.confirmed = True
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the operation."""
        self.confirmed = False
        self.stop()

async def setup(bot: commands.Bot):
    """Set up the database backup commands cog."""
    await bot.add_cog(DatabaseBackupCommands(bot))
    logger.info("✅ DatabaseBackupCommands cog loaded")