#!/bin/bash

# Interactive County Map - Production Startup Script
# Usage: ./start-production.sh [port]

set -e

PORT=${1:-8000}
WORKERS=${WORKERS:-$(($(nproc) * 2 + 1))}

echo "🗺️  Starting Interactive County Map Server (Production)"
echo "📍 Port: $PORT"
echo "👥 Workers: $WORKERS"
echo "🚀 Starting with Gunicorn..."

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn not found. Installing..."
    pip3 install -r requirements.txt
fi

# Start the server
exec gunicorn \
    --bind "0.0.0.0:$PORT" \
    --workers "$WORKERS" \
    --worker-class sync \
    --timeout 30 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --enable-stdio-inheritance \
    wsgi:application
