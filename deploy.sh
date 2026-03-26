#!/bin/bash
set -e

echo "========================================"
echo "  Supplier Hub - Deployment Script"
echo "========================================"
echo ""

# Check if Docker works
echo "[1/4] Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERROR: Docker is not running!"
    echo "   Run: sudo systemctl start docker"
    exit 1
fi
echo "✅ Docker is running"

# Stop existing containers
echo ""
echo "[2/4] Stopping existing containers..."
docker compose down 2>/dev/null || true
echo "✅ Cleaned up"

# Build and start
echo ""
echo "[3/4] Building containers (this may take a minute)..."
docker compose build --no-cache

echo ""
echo "[4/4] Starting services..."
docker compose up -d

# Wait for health check
echo ""
echo "Waiting for database to be ready..."
sleep 10

# Show status
echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
docker compose ps
echo ""
echo " Web App: http://localhost:8080"
echo "🗄️  Database: localhost:5432"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
