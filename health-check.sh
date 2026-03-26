#!/bin/bash
echo "Supplier Hub Health Check"
echo "========================="
echo ""
cd ~/Supplier-Hub

echo "Container Status:"
docker compose ps
echo ""

echo "Database Check:"
docker compose exec -T db pg_isready -U supplier
echo ""

echo "Web App Check:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/
echo ""

echo "Admin User Status:"
docker compose exec -T web python -c "
import sys; sys.path.insert(0, 'backend')
from models import SessionLocal, InternalUser
db = SessionLocal()
admin = db.query(InternalUser).filter(InternalUser.username == 'admin').first()
if admin:
    print(f'  Username: {admin.username}')
    print(f'  Active: {admin.is_active}')
    print(f'  Has Password: {admin.password_hash is not None}')
    print(f'  Invitation Used: {admin.invitation_used}')
else:
    print('  Admin user NOT FOUND!')
db.close()
"
echo ""
echo "========================="
