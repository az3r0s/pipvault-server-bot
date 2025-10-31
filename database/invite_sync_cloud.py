"""
Cloud Database Methods for Invite Sync
===================================

Methods for managing invite join history in the cloud database
"""

from datetime import datetime
import json

class InviteSyncCloudDB:
    """Cloud database methods for invite sync"""
    
    @staticmethod
    async def init_cloud_tables(db):
        """Initialize invite sync tables in cloud database"""
        try:
            # Create invite_join_history collection
            await db.create_collection('invite_join_history')
            await db.create_collection('invite_sync_meta')
            
            # Create indexes
            await db.create_index('invite_join_history', 'invite_code')
            await db.create_index('invite_join_history', 'user_id', unique=True)
            
            return True
        except Exception as e:
            print(f"Error initializing cloud tables: {e}")
            return False

    @staticmethod
    async def record_invite_join_cloud(db, user_id: int, username: str, invite_code: str, staff_id: int):
        """Record a user joining through an invite in cloud DB"""
        try:
            doc = {
                'user_id': user_id,
                'username': username,
                'invite_code': invite_code,
                'staff_id': staff_id,
                'joined_at': datetime.now().isoformat(),
            }
            
            await db.insert_one('invite_join_history', doc)
            return True
        except Exception as e:
            print(f"Error recording invite join in cloud: {e}")
            return False

    @staticmethod
    async def get_invite_joins_cloud(db, invite_code: str):
        """Get all members who joined through a specific invite from cloud"""
        try:
            results = await db.find('invite_join_history', {'invite_code': invite_code})
            return [dict(r) for r in results]
        except Exception as e:
            print(f"Error getting invite joins from cloud: {e}")
            return []

    @staticmethod
    async def update_sync_meta_cloud(db, guild_id: int, status: str = 'success'):
        """Update sync metadata for a guild in cloud"""
        try:
            doc = {
                'guild_id': guild_id,
                'last_sync': datetime.now().isoformat(),
                'status': status
            }
            
            await db.update_one('invite_sync_meta', 
                              {'guild_id': guild_id}, 
                              {'$set': doc},
                              upsert=True)
            return True
        except Exception as e:
            print(f"Error updating sync meta in cloud: {e}")
            return False

    @staticmethod
    async def get_sync_meta_cloud(db, guild_id: int):
        """Get sync metadata for a guild from cloud"""
        try:
            result = await db.find_one('invite_sync_meta', {'guild_id': guild_id})
            return dict(result) if result else None
        except Exception as e:
            print(f"Error getting sync meta from cloud: {e}")
            return None

    @staticmethod
    async def clear_invite_history_cloud(db, guild_id: int):
        """Clear invite join history for a guild from cloud"""
        try:
            await db.delete_many('invite_join_history', {})
            await db.delete_one('invite_sync_meta', {'guild_id': guild_id})
            return True
        except Exception as e:
            print(f"Error clearing invite history from cloud: {e}")
            return False

    @staticmethod
    async def sync_local_to_cloud(db, local_db):
        """Sync local invite history to cloud"""
        try:
            # Get all local invite history
            cursor = local_db.cursor()
            cursor.execute('''
                SELECT user_id, username, invite_code, staff_id, joined_at
                FROM invite_join_history
            ''')
            
            for row in cursor.fetchall():
                doc = {
                    'user_id': row[0],
                    'username': row[1],
                    'invite_code': row[2],
                    'staff_id': row[3],
                    'joined_at': row[4]
                }
                
                await db.update_one('invite_join_history',
                                  {'user_id': doc['user_id']},
                                  {'$set': doc},
                                  upsert=True)
            
            return True
        except Exception as e:
            print(f"Error syncing to cloud: {e}")
            return False