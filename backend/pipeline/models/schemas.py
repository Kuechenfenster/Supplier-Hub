"""
Compliance & Material Intelligence Pipeline — Pydantic Validation Schemas
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# Manufacturer
# ═══════════════════════════════════════════════════════════
class ManufacturerBase(BaseModel):
    manufacturer_id: Optional[str] = Field(None, max_length=50)
    manufacturer_name: str = Field(..., min_length=1, max_length=200)
    manufacturer_code: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerRead(ManufacturerBase):
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# Supplier
# ═══════════════════════════════════════════════════════════
class SupplierBase(BaseModel):
    supplier_id: Optional[str] = Field(None, max_length=50)
    supplier_name: Optional[str] = Field(None, max_length=200)
    supplier_material_id: Optional[str] = Field(None, max_length=100)
    manufacturer_id: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = Field("active", pattern=r"^(active|inactive|pending)$")


class SupplierCreate(SupplierBase):
    pass


class SupplierRead(SupplierBase):
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# Material Library
# ═══════════════════════════════════════════════════════════
class MaterialLibraryBase(BaseModel):
    material_id: str = Field(..., min_length=1, max_length=50)
    material_name: str = Field(..., min_length=1, max_length=200)
    component_name: Optional[str] = None
    supplier_id: str = Field(..., min_length=1, max_length=50)
    part_spec_name: Optional[str] = Field(None, max_length=200, description="Part specification name")
    material_type: Optional[str] = Field(None, pattern=r"^(substance|mixture|article)$")
    category: Optional[str] = None
    cas_number: Optional[str] = None
    ghs_classification: Optional[str] = None
    en71_3_category: Optional[str] = Field(None, pattern=r"^(I|II|III)$")
    migration_limit_mg_kg: Optional[float] = Field(None, ge=0)
    reach_regulation: Optional[str] = None
    internal_status: Optional[str] = Field("pending_review", pattern=r"^(approved|conditional|rejected|pending_review)$")
    sub_supplier_id: Optional[str] = None
    notes: Optional[str] = None


class MaterialLibraryCreate(MaterialLibraryBase):
    pass


class MaterialLibraryRead(MaterialLibraryBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# BOM Record
# ═══════════════════════════════════════════════════════════
class BOMRecordBase(BaseModel):
    bom_id: str = Field(..., min_length=1, max_length=50)
    sku: str = Field(..., min_length=1, max_length=50)
    product_name: Optional[str] = None
    version: Optional[str] = None
    material_id: str = Field(..., min_length=1, max_length=50)
    component_name: Optional[str] = None
    supplier_id: Optional[str] = None
    quantity: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = None
    component_role: Optional[str] = None
    is_sub_supplier: bool = False
    source_file: Optional[str] = None


class BOMRecordCreate(BOMRecordBase):
    # Extended fields for BOM processing (not in DB, used for manufacturer/supplier creation)
    manufacturer_name: Optional[str] = None
    manufacturer_code: Optional[str] = None
    supplier_material_id: Optional[str] = None
    part_spec_name: Optional[str] = None
    material_type: Optional[str] = None
    sub_supplier_id: Optional[str] = None


class BOMRecordRead(BOMRecordBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# Substance Breakdown
# ═══════════════════════════════════════════════════════════
class SubstanceBreakdownBase(BaseModel):
    material_id: str = Field(..., min_length=1, max_length=50)
    cas_number: str = Field(..., min_length=1, max_length=50)
    substance_name: str = Field(..., min_length=1, max_length=200)
    concentration_min: Optional[float] = None
    concentration_max: Optional[float] = None
    concentration_typical: Optional[float] = None
    is_impurity: bool = False
    source: Optional[str] = Field(None, pattern=r"^(sds|tds|supplier_declaration|ai_extracted)$")
    reach_status: Optional[str] = None
    svhc: bool = False
    reach_annex_xvii_restricted: bool = False
    toy_safety_compliant: Optional[bool] = None
    migration_limit_mg_kg: Optional[float] = None
    internal_limit_mg_kg: Optional[float] = None
    notes: Optional[str] = None


class SubstanceBreakdownCreate(SubstanceBreakdownBase):
    pass


class SubstanceBreakdownRead(SubstanceBreakdownBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# Compliance Check
# ═══════════════════════════════════════════════════════════
class ComplianceCheckBase(BaseModel):
    material_id: str = Field(..., min_length=1, max_length=50)
    cas_number: Optional[str] = None
    regulation: str = Field(..., pattern=r"^(reach|eu_toy_directive|en71_3|internal)$")
    check_type: str = Field(..., pattern=r"^(svhc_screening|annex_xvii|migration_test|substance_restrict|internal_standard)$")
    result: str = Field(..., pattern=r"^(pass|fail|review|exempt)$")
    limit_value: Optional[float] = None
    measured_value: Optional[float] = None
    unit: Optional[str] = None
    details: Optional[str] = None
    source: Optional[str] = Field(None, pattern=r"^(ai_check|manual|test_report)$")
    reference: Optional[str] = None


class ComplianceCheckCreate(ComplianceCheckBase):
    pass


class ComplianceCheckRead(ComplianceCheckBase):
    id: int
    checked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# Risk Alert
# ═══════════════════════════════════════════════════════════
class RiskAlertBase(BaseModel):
    material_id: Optional[str] = None
    cas_number: Optional[str] = None
    sku: Optional[str] = None
    alert_type: str = Field(..., pattern=r"^(svhc_found|reach_violation|toy_directive_fail|no_sds|expired_test|internal_standard_fail)$")
    severity: str = Field(..., pattern=r"^(high|medium|low)$")
    description: Optional[str] = None
    regulation_reference: Optional[str] = None
    resolved: bool = False


class RiskAlertCreate(RiskAlertBase):
    pass


class RiskAlertRead(RiskAlertBase):
    alert_id: int
    resolved_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# BOM Clean Result
# ═══════════════════════════════════════════════════════════
class BOMCleanResult(BaseModel):
    source_file: str
    bom_id: str
    sku: str
    product_name: Optional[str] = None
    version: Optional[str] = None
    total_rows: int
    valid_rows: int
    skipped_rows: int
    materials: list[BOMRecordCreate]
    warnings: list[str] = []
    errors: list[str] = []
