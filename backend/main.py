import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
import uvicorn

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://supplier:supplier123@localhost:5432/supplier_hub")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic schemas
class SupplierCreate(BaseModel):
    name: str
    email: str
    code: str
    password: str

class SupplierResponse(BaseModel):
    id: int
    name: str
    email: str
    code: str
    
    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI(title="Supplier Hub API")

# Mount static files
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes
@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/index.html")
async def index():
    return FileResponse("static/index.html")

@app.post("/api/suppliers", response_model=SupplierResponse)
async def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    # Check if code exists
    existing = db.query(Supplier).filter(Supplier.code == supplier.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier code already exists")
    
    db_supplier = Supplier(
        name=supplier.name,
        email=supplier.email,
        code=supplier.code,
        password=supplier.password  # In production, hash this!
    )
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@app.get("/api/suppliers", response_model=List[SupplierResponse])
async def get_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()

@app.get("/api/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
