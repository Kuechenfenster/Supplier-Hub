#!/bin/bash
# Supplier Hub - Complete Deployment and Fix Script
# Run this on your Docker server

set -e

echo "=========================================="
echo "  SUPPLIER HUB - DEPLOYMENT & FIX SCRIPT"
echo "=========================================="
echo ""

cd ~/Supplier-Hub

# Step 1: Pull latest code
echo "📥 Pulling latest code from GitHub..."
git pull
echo ""

# Step 2: Stop containers
echo "🛑 Stopping containers..."
docker compose down
echo ""

# Step 3: Clean old images
echo "🧹 Cleaning old images..."
docker compose rm -f || true
echo ""

# Step 4: Rebuild with no cache
echo "🔨 Building fresh images (this takes 2-5 minutes)..."
docker compose build --no-cache
echo ""

# Step 5: Start containers
echo "🚀 Starting containers..."
docker compose up -d
echo ""

# Step 6: Wait for database
echo "⏳ Waiting for database to be ready..."
sleep 15

# Step 7: Check container status
echo "📊 Container status:"
docker compose ps
echo ""

# Step 8: Run password reset
echo "🔑 Resetting admin password..."
docker compose exec -T web python backend/reset_password.py
echo ""

# Step 9: Show logs
echo "📋 Last 20 log lines:"
docker compose logs --tail=20 web
echo ""

# Step 10: Verification
echo "=========================================="
echo "  VERIFICATION"
echo "=========================================="
echo ""
echo "✅ Deployment complete!"
echo ""
echo "  Management Portal: http://$(hostname -I | awk '{print $1}'):8080/management"
echo "  Login: admin / master1312"
echo ""
echo "  ⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Open the Management Portal URL in your browser"
echo "2. Login with admin / master1312"
echo "3. Go to Users tab to create team members"
echo ""
