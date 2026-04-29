"""
BOM Template Download, Upload & Document API Routes
"""
import os
import shutil
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse

from pipeline.ingest.bom_cleaner import clean_bom, save_to_database
from pipeline.models.database import (
    init_db as pipeline_init_db, get_db as pipeline_get_db,
    MaterialLibrary, BOMRecord, Manufacturer, Supplier, MaterialDocument
)
from auth_helpers import get_current_user, log_audit
from models import InternalUser, SessionLocal

router = APIRouter(prefix="/api/bom", tags=["BOM"])

BASE_DIR = os.path.dirname(__file__)
BOM_TEMPLATE_DIR = os.path.join(BASE_DIR, "data")
BOM_UPLOAD_DIR = os.path.join(BASE_DIR, "data", "incoming", "boms")
DOCUMENT_UPLOAD_DIR = os.path.join(BASE_DIR, "data", "documents")

# Ensure directories exist
os.makedirs(BOM_TEMPLATE_DIR, exist_ok=True)
os.makedirs(BOM_UPLOAD_DIR, exist_ok=True)
os.makedirs(DOCUMENT_UPLOAD_DIR, exist_ok=True)


@router.get("/template")
async def download_bom_template(format: str = "xlsx"):
    if format.lower() == "csv":
        path = os.path.join(BOM_TEMPLATE_DIR, "bom_template.csv")
        return FileResponse(path, media_type="text/csv", filename="bom_template.csv")
    elif format.lower() == "xlsx":
        path = os.path.join(BOM_TEMPLATE_DIR, "bom_template.xlsx")
        return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="bom_template.xlsx")
    else:
        raise HTTPException(status_code=400, detail="Format must be 'xlsx' or 'csv'")


@router.post("/upload")
async def upload_bom(
    file: UploadFile = File(...),
    bom_id: Optional[str] = None,
    sku: Optional[str] = None,
    product_name: Optional[str] = None,
    version: Optional[str] = None,
    current_user: InternalUser = Depends(get_current_user)
):
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be .xlsx, .xls, or .csv")
    
    save_path = os.path.join(BOM_UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        result = clean_bom(save_path, bom_id=bom_id, sku=sku, product_name=product_name, version=version)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        records = save_to_database(result)
        
        db = SessionLocal()
        log_audit(db, current_user.id, "upload", "bom", result.get("bom_id", "unknown"))
        db.close()
        
        return {
            "message": "BOM processed successfully",
            "bom_id": result.get("bom_id"),
            "sku": result.get("sku"),
            "total_rows": result.get("total_rows", 0),
            "valid_rows": result.get("valid_rows", 0),
            "skipped": result.get("skipped", 0),
            "warnings": result.get("warnings", []),
            "materials_count": records.get("materials_count", 0),
            "bom_records_count": records.get("bom_records_count", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/records")
async def list_bom_records(
    bom_id: Optional[str] = None,
    sku: Optional[str] = None,
    current_user: InternalUser = Depends(get_current_user)
):
    db = pipeline_get_db()
    try:
        query = db.query(BOMRecord)
        if bom_id:
            query = query.filter(BOMRecord.bom_id == bom_id)
        if sku:
            query = query.filter(BOMRecord.sku == sku)
        records = query.all()
        return {
            "count": len(records),
            "records": [{
                "id": r.id,
                "bom_id": r.bom_id,
                "sku": r.sku,
                "product_name": r.product_name,
                "version": r.version,
                "material_id": r.material_id,
                "quantity": r.quantity,
                "unit": r.unit,
                "component_role": r.component_role,
                "created_at": r.created_at.isoformat() if r.created_at else None
            } for r in records]
        }
    finally:
        db.close()


@router.get("/materials")
async def list_materials(current_user: InternalUser = Depends(get_current_user)):
    db = pipeline_get_db()
    try:
        materials = db.query(MaterialLibrary).all()
        return {
            "count": len(materials),
            "materials": [{
                "material_id": m.material_id,
                "material_name": m.material_name,
                "supplier_id": m.supplier_id,
                "category": m.category,
                "part_spec_name": m.part_spec_name,
                "material_type": m.material_type,
                "sub_supplier_id": m.sub_supplier_id,
                "reach_regulation": m.reach_regulation,
                "toy_directive_compliant": m.toy_directive_compliant,
                "internal_status": m.internal_status,
                "ai_verification_status": m.ai_verification_status
            } for m in materials]
        }
    finally:
        db.close()


@router.get("/manufacturers")
async def list_manufacturers(current_user: InternalUser = Depends(get_current_user)):
    db = pipeline_get_db()
    try:
        manufacturers = db.query(Manufacturer).all()
        return {
            "count": len(manufacturers),
            "manufacturers": [{
                "manufacturer_id": m.manufacturer_id,
                "manufacturer_name": m.manufacturer_name,
                "manufacturer_code": m.manufacturer_code,
                "country": m.country
            } for m in manufacturers]
        }
    finally:
        db.close()


@router.get("/suppliers")
async def list_suppliers(current_user: InternalUser = Depends(get_current_user)):
    db = pipeline_get_db()
    try:
        suppliers = db.query(Supplier).all()
        return {
            "count": len(suppliers),
            "suppliers": [{
                "supplier_id": s.supplier_id,
                "supplier_name": s.supplier_name,
                "supplier_material_id": s.supplier_material_id,
                "manufacturer_id": s.manufacturer_id
            } for s in suppliers]
        }
    finally:
        db.close()


@router.post("/documents/upload")
async def upload_document(
    material_id: str,
    document_type: str,
    file: UploadFile = File(...),
    version: Optional[str] = None,
    valid_until: Optional[str] = None,
    current_user: InternalUser = Depends(get_current_user)
):
    allowed_types = {"sds", "tds", "coa", "part_drawing", "test_report", "declaration", "other"}
    if document_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Type must be one of: {allowed_types}")
    
    material_dir = os.path.join(DOCUMENT_UPLOAD_DIR, material_id)
    os.makedirs(material_dir, exist_ok=True)
    
    file_path = os.path.join(material_dir, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    db = pipeline_get_db()
    try:
        doc = MaterialDocument(
            material_id=material_id,
            document_type=document_type,
            file_name=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            uploaded_by=current_user.username,
            version=version or "1.0",
            valid_until=valid_until
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return {"message": "Document uploaded", "document_id": doc.id, "file_name": file.filename}
    finally:
        db.close()


# Lab Report Extraction

@router.post("/lab-reports/extract")
async def extract_lab_report_endpoint(
    file: UploadFile = File(...),
    report_type: str = "auto",
    material_id: Optional[str] = None,
    sku: Optional[str] = None,
    current_user: InternalUser = Depends(get_current_user)
):
    """Upload a PDF lab report and extract structured data using Ollama LLM."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    from pipeline.ingest.lab_extractor import extract_lab_report, save_extraction_to_db

    save_path = os.path.join(DOCUMENT_UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = extract_lab_report(save_path, report_type=report_type)

        if material_id:
            result["material_id"] = material_id
        if sku:
            result["sku"] = sku

        db_result = save_extraction_to_db(result)

        return {
            "message": "Lab report extracted successfully",
            "extraction": result,
            "database": db_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.get("/lab-reports")
async def list_lab_reports(
    material_id: Optional[str] = None,
    sku: Optional[str] = None,
    current_user: InternalUser = Depends(get_current_user)
):
    """List extracted lab reports from TestHistory."""
    db = pipeline_get_db()
    try:
        from pipeline.models.database import TestHistory
        query = db.query(TestHistory)
        if material_id:
            query = query.filter(TestHistory.material_id == material_id)
        if sku:
            query = query.filter(TestHistory.sku == sku)
        reports = query.order_by(TestHistory.created_at.desc()).all()
        return {
            "count": len(reports),
            "reports": [{
                "id": r.id,
                "material_id": r.material_id,
                "report_number": r.report_number,
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "lab_name": r.lab_name,
                "test_standard": r.test_standard,
                "test_type": r.test_type,
                "result": r.result,
                "measured_value": r.measured_value,
                "limit_value": r.limit_value,
                "sku": r.sku,
                "created_at": r.created_at.isoformat() if r.created_at else None
            } for r in reports]
        }
    finally:
        db.close()
