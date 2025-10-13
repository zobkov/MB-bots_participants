#!/bin/bash

# Quick migration fix for production server
# Run this on zobkov-server.ru to fix the integer overflow issue

echo "🚀 Applying database migration to fix Telegram user ID integer overflow..."

# Navigate to project directory
cd /root/MB-bots_participants

# Activate virtual environment
source venv/bin/activate

# Install psycopg2-binary (needed for alembic)
pip install psycopg2-binary

# Apply the migration
echo "📥 Applying migration..."
alembic upgrade head

# Check migration status
echo "✅ Migration status:"
alembic current

echo "🎉 Migration completed! The bot should now handle large Telegram user IDs."
echo "📝 Please restart the bot service and monitor logs for confirmation."