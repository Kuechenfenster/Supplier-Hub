#!/usr/bin/env python3
"""Initialize admin user - compatible bcrypt"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text, inspect
from datetime import datetime, timedelta

# Import models
from models import init_db, SessionLocal, engine, Base, InternalUser, Department

# Use bcrypt directly (passlib has version issues)
import bcrypt

ADMIN_PASSWORD = "master1312"

def hash_password(password: str) -> str:
    """Hash password using bcrypt directly"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def main():
    print("="*50)
    print("  ADMIN USER INITIALIZATION")
    print("="*50)
    print()
    
    # Step 1: Ensure tables exist
    print("📊 Checking database tables...")
    try:
        init_db()
        print("✅ Tables ready!")
    except Exception as e:
        print(f"   Warning: {e}")
    
    # Step 2: Verify tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"   Tables: {tables}")
    
    if 'internal_users' not in tables:
        print("   ❌ internal_users table missing!")
        return False
    
    # Step 3: Create/update admin
    print("\n👤 Setting up admin user...")
    db = SessionLocal()
    
    try:
        password_hash = hash_password(ADMIN_PASSWORD)
        print(f"   Generated password hash")
        
        admin = db.query(InternalUser).filter(InternalUser.username == "admin").first()
        
        if admin:
            print(f"   Updating existing admin: {admin.username}")
            admin.password_hash = password_hash
            admin.invitation_used = True
            admin.invitation_expires = datetime.utcnow() + timedelta(days=365)
            admin.is_active = True
            admin.role = "admin"
        else:
            print(f"   Creating new admin user")
            admin = InternalUser(
                username="admin",
                email="admin@hti.com",
                full_name="System Administrator",
                password_hash=password_hash,
                role="admin",
                invitation_code="INITIAL",
                invitation_used=True,
                invitation_expires=datetime.utcnow() + timedelta(days=365),
                is_active=True
            )
            db.add(admin)
        
        db.commit()
        db.refresh(admin)
        print("   ✅ Admin saved to database")
        
    except Exception as e:
        db.rollback()
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return False
    
    # Step 4: Verify
    print("\n🔍 Verification...")
    admin = db.query(InternalUser).filter(InternalUser.username == "admin").first()
    if admin:
        match = verify_password(ADMIN_PASSWORD, admin.password_hash)
        print(f"   Username: {admin.username}")
        print(f"   Active: {admin.is_active}")
        print(f"   Password verification: {match}")
        
        if match:
            print("\n" + "="*50)
            print("  ✅ SUCCESS!")
            print("="*50)
            print(f"\n  Login: admin / {ADMIN_PASSWORD}")
            print("  ⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!")
            print("="*50)
            db.close()
            return True
        else:
            print("\n   ❌ Password verification failed!")
            db.close()
            return False
    else:
        print("   ❌ Admin not found!")
        db.close()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
