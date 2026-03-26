import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://supplier:supplier123@db:5432/supplier_hub")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    qa = "qa"
    viewer = "viewer"

class SupplierStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"
    archived = "archived"

# Internal Users (Company Admin/Staff)
class InternalUser(Base):
    __tablename__ = "internal_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # NULL until password set
    full_name = Column(String(100), nullable=False)
    invitation_code = Column(String(50), unique=True, nullable=False, index=True)
    invitation_used = Column(Boolean, default=False)
    invitation_expires = Column(DateTime, nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    department_id = Column(Integer, ForeignKey("departments.id"))
    is_active = Column(Boolean, default=True)  # Soft delete flag
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("internal_users.id"))
    
    department = relationship("Department", back_populates="users")
    created_by_user = relationship("InternalUser", remote_side=[id])

# Departments
class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    description = Column(Text)
    manager_id = Column(Integer, ForeignKey("internal_users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    users = relationship("InternalUser", back_populates="department")

# Suppliers (extended)
class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    status = Column(String(20), default="pending")
    assigned_to = Column(Integer, ForeignKey("internal_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Audit Log
class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("internal_users.id"))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer)
    old_value = Column(Text)  # JSON string
    new_value = Column(Text)  # JSON string
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
