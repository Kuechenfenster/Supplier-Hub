#!/usr/bin/env python3
"""Initialize database with first admin user"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from models import init_db, SessionLocal, InternalUser, Department
from datetime import datetime, timedelta
import secrets
import string

def generate_invitation_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(12))

def init():
    print("Initializing database...")
    init_db()
    db = SessionLocal()
    
    # Check if admin exists
    admin = db.query(InternalUser).filter(InternalUser.username == "admin").first()
    if not admin:
        invitation_code = generate_invitation_code()
        admin = InternalUser(
            username="admin",
            email="admin@hti.com",
            full_name="System Administrator",
            role="admin",
            invitation_code=invitation_code,
            invitation_used=False,
            invitation_expires=datetime.utcnow() + timedelta(days=365),
            is_active=True
        )
        db.add(admin)
        db.commit()
        print(f"\n✅ Admin user created!")
        print(f"   Username: admin")
        print(f"   Invitation Code: {invitation_code}")
        print(f"   First login: Go to /management/login and use 'Accept Invitation' with this code")
    else:
        print("✅ Admin user already exists")
    
    # Create default departments
    depts = [
        ("QA", "Quality Assurance", "Responsible for product quality and compliance"),
        ("PURCHASE", "Purchasing", "Raw material procurement and supplier relations"),
        ("PROD", "Production", "Manufacturing and production oversight")
    ]
    for code, name, desc in depts:
        if not db.query(Department).filter(Department.code == code).first():
            db.add(Department(code=code, name=name, description=desc))
    db.commit()
    print("✅ Default departments created")
    db.close()

if __name__ == "__main__":
    init()
