"""
Compliance & Material Intelligence Pipeline — Configuration
"""
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INCOMING_DIR = DATA_DIR / "incoming"
BOMS_DIR = INCOMING_DIR / "boms"
LAB_REPORTS_DIR = INCOMING_DIR / "lab_reports"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"
DB_DIR = BASE_DIR / "db"
LOGS_DIR = BASE_DIR / "logs"

# Database
DB_PATH = DB_DIR / "material_library.db"
DATABASE_URL = os.getenv("PIPELINE_DATABASE_URL", "postgresql://supplier:supplier123@localhost:5432/hti_pipeline")

# ─── API Keys ────────────────────────────────────────────
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# ─── BOM Cleaner Settings ────────────────────────────────
# Column name mappings: messy_name → standard_name
BOM_COLUMN_MAP = {
    # Common variants for Internal Material Code
    "internal_material_code": "material_id",
    "material_code": "material_id",
    "mat_code": "material_id",
    "mat_id": "material_id",
    "item_code": "material_id",
    "part_number": "material_id",
    "internal code": "material_id",
    "code": "material_id",
    # Common variants for Component Name
    "component_name": "component_name",
    "component": "component_name",
    "part_name": "component_name",
    "description": "component_name",
    "material_name": "component_name",
    "item_description": "component_name",
    "material description": "component_name",
    # Common variants for Supplier ID
    "supplier_id": "supplier_id",
    "supplier_code": "supplier_id",
    "supplier": "supplier_id",
    "vendor_id": "supplier_id",
    "vendor_code": "supplier_id",
    "supp_id": "supplier_id",
    # Common variants for SKU
    "sku": "sku",
    "product_sku": "sku",
    "item_sku": "sku",
    "finished_good": "sku",
    "fg_code": "sku",
    "product_code": "sku",
    # Common variants for Quantity
    "quantity": "quantity",
    "qty": "quantity",
    "amount": "quantity",
    "usage": "quantity",
    # Common variants for Unit
    "unit": "unit",
    "uom": "unit",
    "unit_of_measure": "unit",
    # Common variants for Component Role
    "component_role": "component_role",
    "role": "component_role",
    "type": "component_role",
    "category": "component_role",
    # New fields
    "manufacturer_name": "manufacturer_name",
    "manufacturer": "manufacturer_name",
    "mfg_name": "manufacturer_name",
    "manufacturer_code": "manufacturer_code",
    "mfg_code": "manufacturer_code",
    "part_spec_name": "part_spec_name",
    "part_specification": "part_spec_name",
    "part_name": "part_spec_name",
    "specification": "part_spec_name",
    "supplier_material_id": "supplier_material_id",
    "supplier_mat_code": "supplier_material_id",
    "supplier_item_code": "supplier_material_id",
    "is_sub_supplier": "is_sub_supplier",
    "sub_supplier": "is_sub_supplier",
    "from_sub_supplier": "is_sub_supplier",
    "sub_supplier_id": "sub_supplier_id",
    "sub_supplier_code": "sub_supplier_id",
    "material_type": "material_type",
    "mat_type": "material_type",
}

# Required columns for a valid BOM
BOM_REQUIRED_COLUMNS = ["material_id", "material_name", "manufacturer_name", "supplier_id", "sku"]

# ─── Compliance Rules ────────────────────────────────────
EN71_3_MIGRATION_LIMITS = {
    "I": 60.0,    # Category I: mg/kg (dry, brittle, powder-like)
    "II": 300.0,  # Category II: mg/kg (liquid, sticky)
    "III": 15.0,  # Category III: mg/kg (scraped-off)
}

TEST_VALIDITY_MONTHS = 12  # Test results valid for 12 months

# ─── Risk Alert Severities ───────────────────────────────
ALERT_SEVERITY = {
    "material_not_in_bom": "high",
    "no_test_history": "high",
    "expired_test": "medium",
    "failed_test": "high",
}

# ─── Logging ─────────────────────────────────────────────
LOG_FILE = LOGS_DIR / "pipeline.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
