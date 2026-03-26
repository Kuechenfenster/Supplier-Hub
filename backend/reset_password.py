#!/usr/bin/env python3
"""Reset admin password - now uses force_init if needed"""
import subprocess
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
force_init = os.path.join(script_dir, "force_init.py")

if os.path.exists(force_init):
    print("Running force initialization...")
    subprocess.run([sys.executable, force_init])
else:
    print("force_init.py not found, trying direct reset...")
    from models import SessionLocal, InternalUser
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"])
    db = SessionLocal()
    admin = db.query(InternalUser).filter(InternalUser.username == "admin").first()
    
    if admin:
        admin.password_hash = pwd_context.hash("master1312")
        admin.invitation_used = True
        db.commit()
        print("✅ Password reset to: master1312")
    else:
        print("❌ Admin not found! Run force_init.py instead.")
    db.close()
