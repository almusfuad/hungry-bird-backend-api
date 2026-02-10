#!/bin/bash
set -e

echo "🚀 Starting Hungry Bird Backend..."

# Wait for PostgreSQL
if [ "${DEBUG:-False}" != "True" ]; then
    echo "⏳ Waiting for PostgreSQL..."
    while ! timeout 1 bash -c "cat < /dev/null > /dev/tcp/${DATABASE_HOST:-localhost}/${DATABASE_PORT:-5432}" 2>/dev/null; do
        sleep 2
    done
    echo "✅ PostgreSQL is ready"
fi

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! timeout 1 bash -c "cat < /dev/null > /dev/tcp/${REDIS_HOST:-127.0.0.1}/${REDIS_PORT:-6379}" 2>/dev/null; do
    sleep 2
done
echo "✅ Redis is ready"

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Collect static files (production only)
if [ "${DEBUG:-False}" = "False" ]; then
    echo "📦 Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Start web server
echo "🌐 Starting web server on port ${PORT:-8000}..."
exec daphne -b 0.0.0.0 -p ${PORT:-8000} hungryBird.asgi:application
