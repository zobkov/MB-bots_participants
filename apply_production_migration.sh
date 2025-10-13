#!/bin/bash

# Script to apply database migration on production server
# This script should be run on zobkov-server.ru where the bot is deployed

set -e  # Exit on any error

echo "🔧 Starting production database migration..."

# Navigate to the project directory (adjust path as needed)
cd /root/MB-bots_participants

# Activate virtual environment
source venv/bin/activate

# Install psycopg2-binary if not already installed (needed for alembic)
echo "📦 Installing psycopg2-binary for alembic..."
pip install psycopg2-binary

# Check current migration status
echo "📋 Current migration status:"
alembic current

# Show migration history
echo "📚 Migration history:"
alembic history

# Apply the migration to fix user ID integer overflow
echo "🚀 Applying migration to change user ID to BIGINT..."
alembic upgrade head

# Verify the migration was applied
echo "✅ Migration completed. Current status:"
alembic current

# Check the database schema to confirm the change
echo "🔍 Verifying database schema..."
python -c "
import asyncio
import asyncpg
from config.config import load_config

async def check_schema():
    config = load_config()
    import urllib.parse as urlparse
    url = urlparse.urlparse(config.database_url)
    
    conn = await asyncpg.connect(
        host=url.hostname,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.path[1:]
    )
    
    query = '''
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'users' AND table_schema = 'public'
    ORDER BY ordinal_position;
    '''
    
    columns = await conn.fetch(query)
    
    print('Users table schema after migration:')
    for column in columns:
        print(f'  {column[\"column_name\"]}: {column[\"data_type\"]}')
    
    # Specifically check the id column
    id_column = next((col for col in columns if col['column_name'] == 'id'), None)
    if id_column and id_column['data_type'] == 'bigint':
        print('✅ SUCCESS: User ID column is now BIGINT - can handle large Telegram user IDs')
    else:
        print('❌ ERROR: User ID column is still not BIGINT')
        
    await conn.close()

asyncio.run(check_schema())
"

echo "🎉 Production migration completed successfully!"
echo "📝 The bot should now handle large Telegram user IDs without errors."