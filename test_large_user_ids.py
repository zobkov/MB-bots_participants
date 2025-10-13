#!/usr/bin/env python3
"""
Test script to verify that large Telegram user IDs work after migration
Run this after applying the database migration
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.infrastructure.database.database import DatabaseManager
from config.config import load_config


async def test_large_user_ids():
    """Test that large Telegram user IDs can be handled"""
    print("🧪 Testing large Telegram user ID support...")
    
    config = load_config()
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    # Test user IDs that caused the original error
    test_user_ids = [
        5188011832,  # Original error user ID
        5003223086,  # Second error user ID
        2147483648,  # Just over 32-bit integer limit
        9999999999,  # Large test ID
    ]
    
    success_count = 0
    
    for user_id in test_user_ids:
        try:
            print(f"Testing user ID: {user_id}")
            
            # Try to get user (this was causing the original error)
            user = await db_manager.get_user(user_id)
            
            if user is None:
                # User doesn't exist, try to create one
                test_username = f"test_user_{user_id}"
                test_visible_name = f"Test User {user_id}"
                
                await db_manager.create_user(user_id, test_username, test_visible_name)
                print(f"  ✅ Created user {user_id} successfully")
                
                # Verify we can retrieve the created user
                created_user = await db_manager.get_user(user_id)
                if created_user and created_user.id == user_id:
                    print(f"  ✅ Retrieved user {user_id} successfully")
                    success_count += 1
                else:
                    print(f"  ❌ Failed to retrieve created user {user_id}")
                
                # Clean up test user
                await db_manager.delete_user(user_id)
                print(f"  🧹 Cleaned up test user {user_id}")
                
            else:
                print(f"  ✅ User {user_id} already exists and can be retrieved")
                success_count += 1
                
        except Exception as e:
            print(f"  ❌ Error with user ID {user_id}: {e}")
    
    print(f"\n📊 Test Results: {success_count}/{len(test_user_ids)} user IDs handled successfully")
    
    if success_count == len(test_user_ids):
        print("🎉 SUCCESS: All large Telegram user IDs are now supported!")
        print("✅ The migration has been applied successfully.")
        return True
    else:
        print("❌ FAILED: Some user IDs still cannot be handled.")
        print("🔧 The migration may not have been applied correctly.")
        return False


async def check_database_schema():
    """Verify the database schema is correct"""
    print("\n🔍 Checking database schema...")
    
    config = load_config()
    
    try:
        import asyncpg
        
        conn = await asyncpg.connect(
            host=config.db.host,
            port=config.db.port,
            user=config.db.user,
            password=config.db.password,
            database=config.db.database
        )
        
        query = '''
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'users' AND table_schema = 'public'
        ORDER BY ordinal_position;
        '''
        
        columns = await conn.fetch(query)
        
        print("Users table schema:")
        for column in columns:
            nullable = "NULL" if column['is_nullable'] == 'YES' else "NOT NULL"
            max_length = f"({column['character_maximum_length']})" if column['character_maximum_length'] else ""
            print(f"  {column['column_name']}: {column['data_type']}{max_length} {nullable}")
        
        # Check if id column is bigint
        id_column = next((col for col in columns if col['column_name'] == 'id'), None)
        if id_column and id_column['data_type'] == 'bigint':
            print("✅ SUCCESS: User ID column is BIGINT - can handle large Telegram user IDs")
            schema_ok = True
        else:
            print("❌ ERROR: User ID column is not BIGINT")
            schema_ok = False
            
        await conn.close()
        return schema_ok
        
    except Exception as e:
        print(f"❌ Error checking database schema: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting Telegram Bot Database Migration Test")
    print("=" * 60)
    
    # Check schema first
    schema_ok = await check_database_schema()
    
    if not schema_ok:
        print("\n❌ Database schema is incorrect. Please apply the migration first.")
        print("Run: alembic upgrade head")
        return False
    
    # Test large user IDs
    test_ok = await test_large_user_ids()
    
    print("\n" + "=" * 60)
    if test_ok:
        print("🎉 ALL TESTS PASSED - Migration successful!")
        print("✅ The bot can now handle large Telegram user IDs.")
    else:
        print("❌ TESTS FAILED - Migration may need to be re-applied.")
    
    return test_ok


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)