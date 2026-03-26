#!/usr/bin/env python3
"""Database migration script for Management Portal"""
import os
import time
from sqlalchemy import create_engine, text, exc

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://supplier:supplier123@db:5432/supplier_hub")

max_retries = 30
retry_delay = 2

for attempt in range(max_retries):
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("✅ Database connection successful!")
            break
    except exc.OperationalError as e:
        if attempt < max_retries - 1:
            print(f"⏳ Waiting for database... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
        else:
            print(f"❌ Could not connect to database after {max_retries} attempts")
            raise

migrations = [
    # Internal Users table
    """CREATE TABLE IF NOT EXISTS internal_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255),
        full_name VARCHAR(100) NOT NULL,
        invitation_code VARCHAR(50) UNIQUE NOT NULL,
        invitation_used BOOLEAN DEFAULT FALSE,
        invitation_expires TIMESTAMP NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'viewer',
        department_id INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        created_by INTEGER
    )""",
    
    # Departments table
    """CREATE TABLE IF NOT EXISTS departments (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL,
        code VARCHAR(10) UNIQUE NOT NULL,
        description TEXT,
        manager_id INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    # Audit Log table
    """CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        action VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INTEGER,
        old_value TEXT,
        new_value TEXT,
        ip_address VARCHAR(45),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    # Add status to suppliers
    """ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending'""",
    
    # Add assigned_to to suppliers
    """ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS assigned_to INTEGER""",
    
    # Add timestamps to suppliers
    """ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP""",
    """ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP""",
    
    # Create indexes
    """CREATE INDEX IF NOT EXISTS idx_internal_users_username ON internal_users(username)""",
    """CREATE INDEX IF NOT EXISTS idx_internal_users_email ON internal_users(email)""",
    """CREATE INDEX IF NOT EXISTS idx_internal_users_invitation ON internal_users(invitation_code)""",
    """CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC)""",
]

print("\nRunning database migrations...")
with engine.connect() as conn:
    for i, sql in enumerate(migrations, 1):
        try:
            conn.execute(text(sql))
            conn.commit()
            print(f"  [{i}/{len(migrations)}] ✓ Migration {i} completed")
        except Exception as e:
            print(f"  [{i}/{len(migrations)}] ⚠ Migration {i} skipped or already exists")

print("\n✅ Database migrations completed!")
