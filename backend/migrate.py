#!/usr/bin/env python3
"""Database migration script for Management Portal"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://supplier:supplier123@localhost:5432/supplier_hub")

engine = create_engine(DATABASE_URL)

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

print("Running database migrations...")
with engine.connect() as conn:
    for i, sql in enumerate(migrations, 1):
        try:
            conn.execute(text(sql))
            conn.commit()
            print(f"  [{i}/{len(migrations)}] ✓ Migration {i} completed")
        except Exception as e:
            print(f"  [{i}/{len(migrations)}] ⚠ Migration {i} skipped or already exists: {str(e)[:50]}")

print("\n✅ Database migrations completed!")
