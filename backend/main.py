import os
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
import bcrypt
from jose import jwt, JWTError
import uvicorn

from models import init_db, get_db, InternalUser, Department, Supplier, AuditLog, SessionLocal

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://supplier:supplier123@localhost:5432/supplier_hub")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = int(os.getenv("JWT_EXPIRY", "3600"))
INVITATION_EXPIRY_DAYS = 7

# Security
security = HTTPBearer(auto_error=False)

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

# Initialize database
init_db()

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    role: str = "viewer"
    department_id: Optional[int] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

class PasswordReset(BaseModel):
    new_password: str

class UserLogin(BaseModel):
    username: str
    password: str

class InvitationAccept(BaseModel):
    invitation_code: str
    new_password: str

class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class SupplierCreate(BaseModel):
    name: str
    email: str
    code: str
    password: str

class SupplierUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[int] = None

# Helper functions
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def generate_invitation_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(12))

def create_jwt_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(seconds=JWT_EXPIRY)
    payload = {"user_id": user_id, "username": username, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: SessionLocal = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_jwt_token(credentials.credentials)
    user = db.query(InternalUser).filter(InternalUser.id == payload["user_id"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

def log_audit(db: SessionLocal, user_id: int, action: str, entity_type: str, entity_id: int = None, old_value: dict = None, new_value: dict = None, ip_address: str = None):
    audit = AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, old_value=str(old_value) if old_value else None, new_value=str(new_value) if new_value else None, ip_address=ip_address)
    db.add(audit)
    db.commit()

# Routes
@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/index.html")
async def index():
    return FileResponse("static/index.html")

@app.get("/management")
async def management_portal():
    return FileResponse("static/management.html")

@app.get("/management/login")
async def management_login():
    return FileResponse("static/management-login.html")

# Authentication
@app.post("/api/admin/auth/login")
async def login(data: UserLogin, request: Request, db: SessionLocal = Depends(get_db)):
    user = db.query(InternalUser).filter(InternalUser.username == data.username).first()
    if not user or not user.is_active or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_jwt_token(user.id, user.username, user.role)
    log_audit(db, user.id, "login", "internal_user", user.id, ip_address=request.client.host)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role}}

@app.post("/api/admin/auth/logout")
async def logout(current_user: InternalUser = Depends(get_current_user), request: Request = None, db: SessionLocal = Depends(get_db)):
    log_audit(db, current_user.id, "logout", "internal_user", current_user.id, ip_address=request.client.host if request else None)
    return {"message": "Logged out successfully"}

@app.get("/api/admin/auth/me")
async def get_me(current_user: InternalUser = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "full_name": current_user.full_name, "role": current_user.role, "department_id": current_user.department_id}

# Invitation & Password Setup
@app.post("/api/admin/users/accept-invitation")
async def accept_invitation(data: InvitationAccept, db: SessionLocal = Depends(get_db)):
    user = db.query(InternalUser).filter(InternalUser.invitation_code == data.invitation_code).first()
    if not user: raise HTTPException(status_code=404, detail="Invalid invitation code")
    if user.invitation_used: raise HTTPException(status_code=400, detail="Invitation already used")
    if user.invitation_expires < datetime.utcnow(): raise HTTPException(status_code=400, detail="Invitation expired")
    user.password_hash = hash_password(data.new_password)
    user.invitation_used = True
    db.commit()
    return {"message": "Password set successfully. You can now login."}

@app.post("/api/admin/auth/reset-password")
async def reset_password(data: PasswordReset, user_id: int, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if current_user.role != "admin": raise HTTPException(status_code=403, detail="Only admins can reset passwords")
    user = db.query(InternalUser).filter(InternalUser.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    log_audit(db, current_user.id, "password_reset", "internal_user", user_id)
    return {"message": "Password reset successfully"}

# Internal Users CRUD
@app.get("/api/admin/users")
async def list_users(include_inactive: bool = False, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    query = db.query(InternalUser)
    if not include_inactive: query = query.filter(InternalUser.is_active == True)
    users = query.all()
    return [{"id": u.id, "username": u.username, "email": u.email, "full_name": u.full_name, "role": u.role, "department_id": u.department_id, "is_active": u.is_active, "invitation_used": u.invitation_used, "created_at": u.created_at.isoformat(), "last_login": u.last_login.isoformat() if u.last_login else None} for u in users]

@app.post("/api/admin/users")
async def create_user(data: UserCreate, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if db.query(InternalUser).filter(InternalUser.username == data.username).first(): raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(InternalUser).filter(InternalUser.email == data.email).first(): raise HTTPException(status_code=400, detail="Email already exists")
    invitation_code = generate_invitation_code()
    invitation_expires = datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS)
    user = InternalUser(username=data.username, email=data.email, full_name=data.full_name, role=data.role, department_id=data.department_id, invitation_code=invitation_code, invitation_expires=invitation_expires, created_by=current_user.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(db, current_user.id, "create", "internal_user", user.id, None, {"username": user.username, "email": user.email})
    return {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role, "invitation_code": invitation_code, "invitation_expires": invitation_expires.isoformat(), "message": "User created. Send invitation code to user."}

@app.put("/api/admin/users/{user_id}")
async def update_user(user_id: int, data: UserUpdate, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    user = db.query(InternalUser).filter(InternalUser.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    if data.full_name: user.full_name = data.full_name
    if data.role: user.role = data.role
    if data.department_id is not None: user.department_id = data.department_id
    if data.is_active is not None: user.is_active = data.is_active
    user.updated_at = datetime.utcnow()
    db.commit()
    log_audit(db, current_user.id, "update", "internal_user", user_id)
    return {"message": "User updated"}

# Departments
@app.get("/api/admin/departments")
async def list_departments(current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    depts = db.query(Department).filter(Department.is_active == True).all()
    return [{"id": d.id, "name": d.name, "code": d.code, "description": d.description} for d in depts]

@app.post("/api/admin/departments")
async def create_department(data: DepartmentCreate, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if db.query(Department).filter(Department.code == data.code).first(): raise HTTPException(status_code=400, detail="Department code already exists")
    dept = Department(name=data.name, code=data.code, description=data.description)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_audit(db, current_user.id, "create", "department", dept.id)
    return {"id": dept.id, "name": dept.name, "code": dept.code}

# Dashboard
@app.get("/api/admin/dashboard/stats")
async def dashboard_stats(current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    total_suppliers = db.query(Supplier).count()
    active_suppliers = db.query(Supplier).filter(Supplier.status == "active").count()
    pending_suppliers = db.query(Supplier).filter(Supplier.status == "pending").count()
    total_users = db.query(InternalUser).count()
    active_users = db.query(InternalUser).filter(InternalUser.is_active == True).count()
    total_departments = db.query(Department).filter(Department.is_active == True).count()
    return {"total_suppliers": total_suppliers, "active_suppliers": active_suppliers, "pending_suppliers": pending_suppliers, "total_users": total_users, "active_users": active_users, "total_departments": total_departments}

@app.get("/api/admin/dashboard/activity")
async def dashboard_activity(limit: int = 10, current_user: InternalUser = Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [{"id": l.id, "user_id": l.user_id, "action": l.action, "entity_type": l.entity_type, "created_at": l.created_at.isoformat()} for l in logs]

@app.get("/api/admin/users/{user_id}")
async def create_admin_on_first_run(user_id: int = 999, db: SessionLocal = Depends(get_db)):
    # Auto-create admin if no users exist
    if db.query(InternalUser).count() == 0:
        from init_db import init
        init()
    return {"message": "Check /api/admin/users for list"}

print("✅ Backend API initialized with Management Portal!")
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
