import os
import secrets
import string
import sys
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
import uvicorn

from models import init_db, get_db, InternalUser, Department, Supplier, SessionLocal
from auth_helpers import (
    hash_password, verify_password, create_jwt_token, decode_jwt_token,
    get_current_user, log_audit, security, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY
)

from bom_routes import router as bom_router

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://supplier:supplier123@localhost:5432/supplier_hub")
INVITATION_EXPIRY_DAYS = 7

# FastAPI app
app = FastAPI(title="Supplier Hub API", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

# Register BOM router
app.include_router(bom_router)

# Initialize database
init_db()

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    department_id: Optional[int] = None
    role: str = "viewer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class DepartmentCreate(BaseModel):
    name: str
    code: str

class SupplierCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    code: str

class PasswordReset(BaseModel):
    email: EmailStr
    new_password: str

class SupplierInvite(BaseModel):
    email: EmailStr
    name: str
    department: str = "General"

class InvitationResponse(BaseModel):
    token: str
    expires_at: str

# Routes
@app.get("/")
async def root():
    return {"message": "Supplier Hub API", "version": "2.0"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# Authentication
@app.post("/api/auth/login")
async def login(data: UserLogin, db: SessionLocal = Depends(get_db)):
    user = db.query(InternalUser).filter(InternalUser.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_jwt_token({"sub": str(user.id), "email": user.email, "role": user.role})
    log_audit(db, user.id, "login", "user", user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role}}

@app.get("/api/auth/me")
async def me(current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name, "role": current_user.role}

# User Management
@app.get("/api/admin/users")
async def list_users(current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    users = db.query(InternalUser).all()
    return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role, "is_active": u.is_active} for u in users]

@app.post("/api/admin/users")
async def create_user(data: UserCreate, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if db.query(InternalUser).filter(InternalUser.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = InternalUser(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        department_id=data.department_id,
        role=data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(db, current_user.id, "create", "user", user.id)
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}

@app.put("/api/admin/users/{user_id}")
async def update_user(user_id: int, data: dict, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update users")
    user = db.query(InternalUser).filter(InternalUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if "name" in data:
        user.name = data["name"]
    if "role" in data:
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    db.commit()
    db.refresh(user)
    log_audit(db, current_user.id, "update", "user", user_id)
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role, "is_active": user.is_active}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete users")
    user = db.query(InternalUser).filter(InternalUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    log_audit(db, current_user.id, "delete", "user", user_id)
    return {"message": "User deleted"}

# Departments
@app.get("/api/admin/departments")
async def list_departments(current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    depts = db.query(Department).filter(Department.is_active == True).all()
    return [{"id": d.id, "name": d.name, "code": d.code} for d in depts]

@app.post("/api/admin/departments")
async def create_department(data: DepartmentCreate, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if db.query(Department).filter(Department.code == data.code).first():
        raise HTTPException(status_code=400, detail="Department code already exists")
    dept = Department(name=data.name, code=data.code)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_audit(db, current_user.id, "create", "department", dept.id)
    return {"id": dept.id, "name": dept.name, "code": dept.code}

# Suppliers
@app.get("/api/suppliers")
async def list_suppliers(db: SessionLocal = Depends(get_db)):
    suppliers = db.query(Supplier).all()
    return [{"id": s.id, "name": s.name, "email": s.email, "code": s.code, "status": s.status} for s in suppliers]

@app.post("/api/suppliers")
async def create_supplier(data: SupplierCreate, db: SessionLocal = Depends(get_db)):
    if db.query(Supplier).filter(Supplier.email == data.email).first():
        raise HTTPException(status_code=400, detail="Supplier email already exists")
    if db.query(Supplier).filter(Supplier.code == data.code).first():
        raise HTTPException(status_code=400, detail="Supplier code already exists")
    supplier = Supplier(name=data.name, email=data.email, code=data.code, password=hash_password(data.password))
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return {"id": supplier.id, "name": supplier.name, "code": supplier.code, "status": supplier.status}

# Dashboard
@app.get("/api/admin/dashboard/stats")
async def dashboard_stats(current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    total_suppliers = db.query(Supplier).count()
    active_suppliers = db.query(Supplier).filter(Supplier.status == "active").count()
    pending_suppliers = db.query(Supplier).filter(Supplier.status == "pending").count()
    total_users = db.query(InternalUser).count()
    active_users = db.query(InternalUser).filter(InternalUser.is_active == True).count()
    total_departments = db.query(Department).filter(Department.is_active == True).count()
    return {
        "total_suppliers": total_suppliers,
        "active_suppliers": active_suppliers,
        "pending_suppliers": pending_suppliers,
        "total_users": total_users,
        "active_users": active_users,
        "total_departments": total_departments
    }

@app.get("/api/admin/dashboard/activity")
async def dashboard_activity(limit: int = 10, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    from models import AuditLog
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [{"id": l.id, "user_id": l.user_id, "action": l.action, "entity_type": l.entity_type, "created_at": l.created_at.isoformat()} for l in logs]

print("✅ Backend API initialized with Management Portal + BOM Pipeline!")
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=False)
