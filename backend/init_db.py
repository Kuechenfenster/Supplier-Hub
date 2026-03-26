#!/usr/bin/env python3
"""Initialize database with first admin user"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from models import init_db, SessionLocal, InternalUser, Department
from datetime import datetime, timedelta
import secrets
import string
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default admin password - CHANGE AFTER FIRST LOGIN!
DEFAULT_ADMIN_PASSWORD = "master1312"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

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
        admin = InternalUser(
            username="admin",
            email="admin@hti.com",
            full_name="System Administrator",
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            role="admin",
            invitation_code="INITIAL-SETUP",
            invitation_used=True,  # Already set up
            invitation_expires=datetime.utcnow() + timedelta(days=1),
            is_active=True
        )
        db.add(admin)
        db.commit()
        print(f"\n{'='*50}")
        print(f"✅ ADMIN USER CREATED!")
        print(f"{'='*50}")
        print(f"   Username: admin")
        print(f"   Password: {DEFAULT_ADMIN_PASSWORD}")
        print(f"{'='*50}")
        print(f"   ⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!")
        print(f"{'='*50}\n")
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
