"""
Railway Database Export Command
==============================

Add this as a slash command to your bot to export database directly from Railway.
This runs on Railway and outputs the backup data that you can copy.
"""

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseExportCommands(commands.Cog):
    """Database export and backup commands for Railway"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "server_management.db"
    
    @app_commands.command(
        name="export_database",
        description="[ADMIN] Export complete database backup (Railway safe)"
    )
    @app_commands.default_permissions(administrator=True)
    async def export_database(self, interaction: discord.Interaction):
        """Export complete database for backup purposes"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            if not os.path.exists(self.db_path):
                await interaction.followup.send("❌ Database file not found. This might be a new deployment.")
                return
            
            # Create backup data
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            backup_data = {
                "backup_info": {
                    "created_at": datetime.now().isoformat(),
                    "source": "Railway Production Database",
                    "exported_by": f"{interaction.user.name}#{interaction.user.discriminator}",
                    "tables": len(tables)
                },
                "data": {}
            }
            
            total_records = 0
            
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Convert to JSON-friendly format
                table_data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[columns[i]] = str(value) if value is not None else None
                    table_data.append(row_dict)
                
                backup_data["data"][table] = {
                    "columns": columns,
                    "rows": table_data
                }
                
                total_records += len(table_data)
            
            conn.close()
            
            # Create backup file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"railway_backup_{timestamp}.json"
            
            with open(backup_filename, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            file_size = os.path.getsize(backup_filename)
            
            # Create summary
            summary = f"""🎯 **Railway Database Export Complete**
            
📁 **File**: `{backup_filename}`
📊 **Tables**: {len(tables)}
📈 **Total Records**: {total_records:,}
💾 **File Size**: {file_size:,} bytes ({file_size/1024:.1f} KB)
🌐 **Source**: Railway Production Database

📋 **Table Breakdown**:"""
            
            for table, data in backup_data["data"].items():
                record_count = len(data['rows'])
                summary += f"\n• **{table}**: {record_count:,} records"
                
                if table == "invite_tracking" and record_count > 0:
                    summary += " ✅ (Invite data preserved)"
                elif table == "staff_invites" and record_count > 0:
                    summary += " ✅ (Staff data preserved)"
                elif table == "vip_requests" and record_count > 0:
                    summary += " ✅ (VIP data preserved)"
            
            summary += f"""
            
🛡️ **Usage**: Keep this file safe! You can restore from it if needed.
⏰ **Created**: {backup_data["backup_info"]["created_at"]}"""
            
            # Send the backup file
            with open(backup_filename, 'rb') as f:
                file = discord.File(f, filename=backup_filename)
                await interaction.followup.send(content=summary, file=file)
            
            # Clean up
            os.remove(backup_filename)
            
            logger.info(f"Database export completed by {interaction.user} - {total_records} records backed up")
            
        except Exception as e:
            logger.error(f"Database export failed: {e}")
            await interaction.followup.send(f"❌ Export failed: {str(e)}")
    
    @app_commands.command(
        name="verify_database",
        description="[ADMIN] Check current database status and integrity"
    )
    @app_commands.default_permissions(administrator=True)
    async def verify_database(self, interaction: discord.Interaction):
        """Verify current database state"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            if not os.path.exists(self.db_path):
                await interaction.followup.send("❌ Database file not found.")
                return
            
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            verification = f"""🔍 **Railway Database Verification**
            
📁 **Database**: `{self.db_path}`
💾 **File Size**: {os.path.getsize(self.db_path):,} bytes
📊 **Tables**: {len(tables)}

📋 **Table Status**:"""
            
            total_records = 0
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_records += count
                verification += f"\n• **{table}**: {count:,} records"
            
            verification += f"\n\n📈 **Total Records**: {total_records:,}"
            verification += f"\n✅ **Status**: Database is accessible and intact"
            
            conn.close()
            
            await interaction.followup.send(verification)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Verification failed: {str(e)}")

async def setup(bot):
    await bot.add_cog(DatabaseExportCommands(bot))