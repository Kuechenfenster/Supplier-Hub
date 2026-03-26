#!/bin/bash
set -e

echo "⏳ Waiting for database to be ready..."

# Wait for PostgreSQL to be ready
while ! python -c "import psycopg2; psycopg2.connect('postgresql://supplier:supplier123@db:5432/supplier_hub')" 2>/dev/null; do
    echo "  Database not ready, waiting..."
    sleep 2
done

echo "✅ Database is ready!"
echo "📝 Running database migrations..."
python backend/migrate.py

echo "🔧 Initializing admin user..."
python backend/init_db.py || true

echo "✅ Startup complete! Starting web server..."
exec "$@"
