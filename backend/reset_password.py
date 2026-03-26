#!/usr/bin/env python3
"""Reset admin password script"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models import SessionLocal, InternalUser
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])
NEW_PASSWORD = "master1312"

db = SessionLocal()
admin = db.query(InternalUser).filter(InternalUser.username == "admin").first()

if admin:
    admin.password_hash = pwd_context.hash(NEW_PASSWORD)
    admin.invitation_used = True
    admin.is_active = True
    db.commit()
    print(f"✅ Admin password reset to: {NEW_PASSWORD}")
    print(f"   Username: admin")
    print(f"   User is active: {admin.is_active}")
else:
    print("❌ Admin user not found!")
db.close()
