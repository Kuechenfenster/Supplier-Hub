#!/usr/bin/env python3
"""Force initialize database with admin user - BULLETPROOF"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text, inspect
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Import models
from models import init_db, SessionLocal, engine, Base, InternalUser, Department, Supplier, AuditLog

pwd_context = CryptContext(schemes=["bcrypt"])
ADMIN_PASSWORD = "master1312"

def main():
    print("="*50)
    print("  FORCE DATABASE INITIALIZATION")
    print("="*50)
    print()
    
    # Step 1: Create all tables
    print("📊 Creating database tables...")
    try:
        init_db()  # Creates all tables from models
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # Step 2: Verify tables exist
    print("\n📋 Verifying tables...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"   Found tables: {tables}")
    
    required = ['internal_users', 'departments', 'audit_log', 'suppliers']
    for table in required:
        if table in tables:
            print(f"   ✅ {table}")
        else:
            print(f"   ❌ {table} MISSING!")
            return False
    
    # Step 3: Create or update admin user
    print("\n👤 Setting up admin user...")
    db = SessionLocal()
    
    try:
        admin = db.query(InternalUser).filter(InternalUser.username == "admin").first()
        
        if admin:
            print(f"   Found existing admin: {admin.username}")
            admin.password_hash = pwd_context.hash(ADMIN_PASSWORD)
            admin.invitation_used = True
            admin.invitation_expires = datetime.utcnow() + timedelta(days=365)
            admin.is_active = True
            admin.role = "admin"
            print("   ✅ Admin password updated")
        else:
            admin = InternalUser(
                username="admin",
                email="admin@hti.com",
                full_name="System Administrator",
                password_hash=pwd_context.hash(ADMIN_PASSWORD),
                role="admin",
                invitation_code="INITIAL",
                invitation_used=True,
                invitation_expires=datetime.utcnow() + timedelta(days=365),
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("   ✅ Admin user created")
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"   ❌ Error: {e}")
        db.close()
        return False
    
    # Step 4: Create default departments
    print("\n🏛️  Creating default departments...")
    depts = [
        ("QA", "Quality Assurance", "Product quality and compliance"),
        ("PURCHASE", "Purchasing", "Procurement and supplier relations"),
        ("PROD", "Production", "Manufacturing oversight")
    ]
    
    for code, name, desc in depts:
        if not db.query(Department).filter(Department.code == code).first():
            db.add(Department(code=code, name=name, description=desc))
            print(f"   ✅ Created {code}")
        else:
            print(f"   ✓ {code} exists")
    db.commit()
    
    # Step 5: Verify admin
    print("\n🔍 Final verification...")
    admin = db.query(InternalUser).filter(InternalUser.username == "admin").first()
    if admin:
        # Test password verification
        match = pwd_context.verify(ADMIN_PASSWORD, admin.password_hash)
        print(f"   Username: {admin.username}")
        print(f"   Active: {admin.is_active}")
        print(f"   Has password: {admin.password_hash is not None}")
        print(f"   Password matches '{ADMIN_PASSWORD}': {match}")
        
        if match:
            print("\n" + "="*50)
            print("  ✅ INITIALIZATION COMPLETE!")
            print("="*50)
            print(f"\n  Login: admin / {ADMIN_PASSWORD}")
            print("  ⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!")
            print("="*50)
            db.close()
            return True
        else:
            print("\n   ❌ Password hash verification failed!")
            db.close()
            return False
    else:
        print("\n   ❌ Admin user not found after creation!")
        db.close()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
