#!/bin/bash

echo "🚀 Starting Hungry Bird Backend..."

# Check Redis only if explicitly enabled (default: disabled for MVP)
if [ "${ENABLE_REDIS_CHECK:-false}" = "true" ]; then
    echo "⏳ Waiting for Redis..."
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if timeout 1 bash -c "cat < /dev/null > /dev/tcp/${REDIS_HOST:-127.0.0.1}/${REDIS_PORT:-6379}" 2>/dev/null; then
            echo "✅ Redis is ready"
            break
        fi
        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            echo "   Attempt $attempt/$max_attempts..."
            sleep 2
        fi
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "⚠️  Redis not accessible, continuing anyway..."
    fi
else
    echo "⏭️  Redis check disabled (set ENABLE_REDIS_CHECK=true to enable)"
fi

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput 2>&1 || echo "⚠️  Migration failed, continuing..."

# Collect static files (production only)
if [ "${DEBUG:-False}" = "False" ]; then
    echo "📦 Collecting static files..."
    python manage.py collectstatic --noinput 2>&1 || echo "⚠️  Static files collection failed, continuing..."
fi

# Start web server
echo "🌐 Starting web server on port ${PORT:-8000}..."
exec daphne -b 0.0.0.0 -p ${PORT:-8000} hungryBird.asgi:application
