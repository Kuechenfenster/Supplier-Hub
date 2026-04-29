"""
Compliance & Material Intelligence Pipeline — BOM Cleaner

Processes messy Excel BOM files into a unified, standardized format.
- Auto-detects and maps column names using fuzzy matching
- Validates required fields
- Writes to Material_Library + BOM_Records tables in SQLite
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from pipeline.config import BOM_COLUMN_MAP, BOM_REQUIRED_COLUMNS, BOMS_DIR, PROCESSED_DIR
from pipeline.models.database import (
    init_db, get_db, MaterialLibrary, BOMRecord
)
from pipeline.models.database import Manufacturer, Supplier
from pipeline.models.schemas import BOMCleanResult, BOMRecordCreate

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Column Detection & Mapping
# ═══════════════════════════════════════════════════════════
def normalize_column_name(col: str) -> str:
    """Normalize a column name for matching: lowercase, strip, replace spaces/dashes with underscores."""
    col = str(col).strip().lower()
    col = re.sub(r"[\s\-\\/]+", "_", col)
    col = re.sub(r"[^a-z0-9_]", "", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def map_columns(df: pd.DataFrame) -> tuple[dict, list[str]]:
    """
    Map messy DataFrame column names to standardized names.
    Returns (mapping_dict, unmapped_columns).
    """
    mapping = {}
    unmapped = []
    standard_names = set(BOM_COLUMN_MAP.values())
    
    for col in df.columns:
        normalized = normalize_column_name(col)
        
        # Already a standard name? Map to itself
        if normalized in standard_names:
            mapping[col] = normalized
            continue
        
        # Direct match in BOM_COLUMN_MAP
        if normalized in BOM_COLUMN_MAP:
            mapping[col] = BOM_COLUMN_MAP[normalized]
            continue
        
        # Try partial match (column name contains a known key)
        matched = False
        for key, value in BOM_COLUMN_MAP.items():
            if key in normalized or normalized in key:
                mapping[col] = value
                matched = True
                break
        
        if not matched:
            unmapped.append(col)
    
    return mapping, unmapped


def validate_bom(df: pd.DataFrame, mapping: dict) -> tuple[list[str], list[str]]:
    """
    Check that all required columns are present after mapping.
    Returns (missing_required, warnings).
    """
    mapped_names = set(mapping.values())
    missing = [col for col in BOM_REQUIRED_COLUMNS if col not in mapped_names]
    warnings = []
    
    if missing:
        warnings.append(f"Missing required columns: {missing}")
    
    # Check for duplicate mappings (two source columns → same target)
    seen = {}
    for src, tgt in mapping.items():
        if tgt in seen:
            warnings.append(f"Duplicate mapping: '{src}' and '{seen[tgt]}' both map to '{tgt}'")
        seen[tgt] = src
    
    return missing, warnings


# ═══════════════════════════════════════════════════════════
# Data Cleaning
# ═══════════════════════════════════════════════════════════
def clean_value(val):
    """Clean a single cell value: strip whitespace, handle NaN."""
    if pd.isna(val):
        return None
    if isinstance(val, str):
        return val.strip() or None
    return val


def clean_material_id(val) -> Optional[str]:
    """Standardize material ID format: uppercase, remove extra spaces."""
    if val is None:
        return None
    val = str(val).strip().upper()
    # Filter out NaN/None string representations
    if val in ("NAN", "NONE", "", "N/A"):
        return None
    val = re.sub(r"\s+", "-", val)
    return val if val else None


def clean_sku(val) -> Optional[str]:
    """Standardize SKU format: uppercase, remove extra spaces."""
    if val is None:
        return None
    val = str(val).strip().upper()
    val = re.sub(r"\s+", "-", val)
    return val if val else None


def clean_supplier_id(val) -> Optional[str]:
    """Standardize supplier ID: uppercase, consistent format."""
    if val is None:
        return None
    val = str(val).strip().upper()
    return val if val else None


# ═══════════════════════════════════════════════════════════
# Main BOM Cleaning Pipeline
# ═══════════════════════════════════════════════════════════
def clean_bom(
    file_path: str | Path,
    bom_id: Optional[str] = None,
    sku: Optional[str] = None,
    product_name: Optional[str] = None,
    version: str = "v1.0",
    sheet_name: Optional[str | int] = 0,
    header_row: int = 0,
) -> BOMCleanResult:
    """
    Process a messy Excel BOM file into a standardized format.
    
    Args:
        file_path: Path to the Excel file
        bom_id: BOM identifier (auto-generated if not provided)
        sku: Default SKU for all items (if not in file)
        product_name: Product name override
        version: BOM version string
        sheet_name: Sheet name or index (default: first sheet)
        header_row: Row number containing headers (0-indexed)
    
    Returns:
        BOMCleanResult with standardized materials and metadata
    """
    file_path = Path(file_path)
    logger.info(f"Processing BOM: {file_path.name}")
    
    errors = []
    warnings = []
    
    # ─── Read Excel ─────────────────────────────────────
    try:
        ext = file_path.suffix.lower()
        if ext == '.csv':
            df = pd.read_csv(file_path, header=header_row)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
    except Exception as e:
        errors.append(f"Failed to read file: {e}")
        return BOMCleanResult(
            source_file=file_path.name, bom_id="ERROR", sku="ERROR",
            total_rows=0, valid_rows=0, skipped_rows=0,
            materials=[], errors=errors
        )
    
    total_rows = len(df)
    logger.info(f"  Read {total_rows} rows, {len(df.columns)} columns")
    
    # ─── Map Columns ────────────────────────────────────
    mapping, unmapped = map_columns(df)
    logger.info(f"  Column mapping: {mapping}")
    if unmapped:
        logger.warning(f"  Unmapped columns: {unmapped}")
        warnings.append(f"Unmapped columns ignored: {unmapped}")
    
    # ─── Validate ───────────────────────────────────────
    missing, val_warnings = validate_bom(df, mapping)
    warnings.extend(val_warnings)
    
    if missing:
        errors.append(f"Cannot process BOM — missing required columns: {missing}")
        return BOMCleanResult(
            source_file=file_path.name, bom_id="ERROR", sku=sku or "UNKNOWN",
            total_rows=total_rows, valid_rows=0, skipped_rows=total_rows,
            materials=[], warnings=warnings, errors=errors
        )
    
    # ─── Apply Mapping ──────────────────────────────────
    df_clean = df.rename(columns=mapping)
    
    # ─── Clean Values ───────────────────────────────────
    # Material ID
    df_clean["material_id"] = df_clean["material_id"].apply(clean_material_id)
    # Supplier ID
    df_clean["supplier_id"] = df_clean["supplier_id"].apply(clean_supplier_id)
    # SKU (use default if not in file)
    if "sku" in df_clean.columns:
        df_clean["sku"] = df_clean["sku"].apply(clean_sku)
    if sku:
        df_clean["sku"] = df_clean["sku"].fillna(sku.upper())
    # Component Name
    df_clean["component_name"] = df_clean["component_name"].apply(clean_value)
    # Manufacturer name (required)
    if "manufacturer_name" in df_clean.columns:
        df_clean["manufacturer_name"] = df_clean["manufacturer_name"].apply(clean_value)
    # Manufacturer code
    if "manufacturer_code" in df_clean.columns:
        df_clean["manufacturer_code"] = df_clean["manufacturer_code"].apply(clean_value)
    # Part spec name
    if "part_spec_name" in df_clean.columns:
        df_clean["part_spec_name"] = df_clean["part_spec_name"].apply(clean_value)
    # Supplier material ID
    if "supplier_material_id" in df_clean.columns:
        df_clean["supplier_material_id"] = df_clean["supplier_material_id"].apply(clean_value)
    # Material type
    if "material_type" in df_clean.columns:
        df_clean["material_type"] = df_clean["material_type"].apply(lambda v: str(v).strip().lower() if clean_value(v) else None)
    # Sub-supplier fields
    if "is_sub_supplier" in df_clean.columns:
        df_clean["is_sub_supplier"] = df_clean["is_sub_supplier"].apply(lambda v: str(v).strip().lower() in ("true", "1", "yes", "x") if isinstance(v, (str, int, float)) and not (isinstance(v, float) and pd.isna(v)) else False)
    if "sub_supplier_id" in df_clean.columns:
        df_clean["sub_supplier_id"] = df_clean["sub_supplier_id"].apply(clean_value)
    # Quantity
    if "quantity" in df_clean.columns:
        df_clean["quantity"] = pd.to_numeric(df_clean["quantity"], errors="coerce")
    # Unit
    if "unit" in df_clean.columns:
        df_clean["unit"] = df_clean["unit"].apply(lambda v: str(v).strip().lower() if clean_value(v) else None)
    
    # ─── Drop invalid rows ─────────────────────────────
    required_present = [c for c in BOM_REQUIRED_COLUMNS if c in df_clean.columns]
    mask_valid = df_clean[required_present].notna().all(axis=1)
    # Also filter out rows where material_id is empty/whitespace
    mask_valid = mask_valid & df_clean["material_id"].apply(lambda x: x is not None and isinstance(x, str) and len(x) > 0)
    
    df_valid = df_clean[mask_valid].copy()
    df_skipped = df_clean[~mask_valid].copy()
    skipped_rows = len(df_skipped)
    valid_rows = len(df_valid)
    
    if skipped_rows > 0:
        warnings.append(f"Skipped {skipped_rows} rows with missing required fields")
        logger.warning(f"  Skipped {skipped_rows} rows:")
        for _, row in df_skipped.head(5).iterrows():
            logger.warning(f"    {row.to_dict()}")
    
    # ─── Generate BOM ID ────────────────────────────────
    if not bom_id:
        date_str = datetime.now().strftime("%Y%m%d")
        bom_id = f"BOM-{date_str}-{file_path.stem[:10]}"
    
    # ─── Determine SKU ──────────────────────────────────
    if not sku and "sku" in df_valid.columns:
        sku = df_valid["sku"].mode().iloc[0] if len(df_valid) > 0 else "UNKNOWN"
    sku = sku or "UNKNOWN"
    
    # ─── Build BOM Records ──────────────────────────────
    def safe_get(row, key, default=None):
        """Get value from row, converting NaN to None."""
        val = row.get(key, default)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        if isinstance(val, str) and val.strip() == "":
            return None
        return val

    materials = []
    for _, row in df_valid.iterrows():
        record = BOMRecordCreate(
            bom_id=bom_id,
            sku=safe_get(row, "sku", sku),
            product_name=product_name or safe_get(row, "product_name"),
            version=version,
            material_id=row["material_id"],
            component_name=safe_get(row, "component_name"),
            supplier_id=safe_get(row, "supplier_id"),
            quantity=safe_get(row, "quantity"),
            unit=safe_get(row, "unit"),
            component_role=safe_get(row, "component_role"),
            manufacturer_name=safe_get(row, "manufacturer_name"),
            manufacturer_code=safe_get(row, "manufacturer_code"),
            supplier_material_id=safe_get(row, "supplier_material_id"),
            part_spec_name=safe_get(row, "part_spec_name"),
            material_type=safe_get(row, "material_type"),
            is_sub_supplier=bool(safe_get(row, "is_sub_supplier", False)),
            sub_supplier_id=safe_get(row, "sub_supplier_id"),
            source_file=file_path.name,
        )
        materials.append(record)
    
    logger.info(f"  ✅ Cleaned: {valid_rows} valid, {skipped_rows} skipped")
    
    return BOMCleanResult(
        source_file=file_path.name,
        bom_id=bom_id,
        sku=sku,
        product_name=product_name,
        version=version,
        total_rows=total_rows,
        valid_rows=valid_rows,
        skipped_rows=skipped_rows,
        materials=materials,
        warnings=warnings,
        errors=errors,
    )


# ═══════════════════════════════════════════════════════════
# Database Persistence
# ═══════════════════════════════════════════════════════════
def save_to_database(result: BOMCleanResult) -> dict:
    """
    Persist cleaned BOM data to Material_Library and BOM_Records tables.
    - Creates Manufacturer records if not exists
    - Creates Supplier records if not exists
    - Upserts materials into Material_Library
    - Inserts all BOM records
    
    Returns summary dict with counts.
    """
    init_db()
    db = get_db()
    
    materials_added = 0
    materials_updated = 0
    bom_records_added = 0
    manufacturers_added = 0
    suppliers_added = 0
    seen_materials = set()
    seen_manufacturers = set()
    seen_suppliers = set()
    
    try:
        for rec in result.materials:
            # ─── Create Manufacturer if provided ────────
            if rec.manufacturer_name and rec.manufacturer_name not in seen_manufacturers:
                mfg_id = "MFG-" + re.sub(r'[^A-Z0-9]', '', rec.manufacturer_name.upper())[:8]
                existing_mfg = db.query(Manufacturer).filter(
                    Manufacturer.manufacturer_name == rec.manufacturer_name
                ).first()
                if not existing_mfg:
                    manufacturer = Manufacturer(
                        manufacturer_id=mfg_id,
                        manufacturer_name=rec.manufacturer_name,
                        manufacturer_code=rec.manufacturer_code,
                    )
                    db.add(manufacturer)
                    db.flush()
                    manufacturers_added += 1
                    logger.info(f"  Created manufacturer: {mfg_id} - {rec.manufacturer_name}")
                seen_manufacturers.add(rec.manufacturer_name)
            
            # ─── Create/Update Supplier if provided ────
            if rec.supplier_id and rec.supplier_id not in seen_suppliers:
                existing_sup = db.query(Supplier).filter(
                    Supplier.supplier_id == rec.supplier_id
                ).first()
                if not existing_sup:
                    mfg_id = None
                    if rec.manufacturer_name:
                        mfg = db.query(Manufacturer).filter(
                            Manufacturer.manufacturer_name == rec.manufacturer_name
                        ).first()
                        if mfg:
                            mfg_id = mfg.manufacturer_id
                    supplier = Supplier(
                        supplier_id=rec.supplier_id,
                        supplier_name=rec.supplier_id,
                        supplier_material_id=rec.supplier_material_id,
                        manufacturer_id=mfg_id,
                        status="active",
                    )
                    db.add(supplier)
                    db.flush()
                    suppliers_added += 1
                    logger.info(f"  Created supplier: {rec.supplier_id}")
                seen_suppliers.add(rec.supplier_id)
            
            # ─── Upsert Material Library ─────────────
            if rec.material_id not in seen_materials:
                existing = db.query(MaterialLibrary).filter(
                    MaterialLibrary.material_id == rec.material_id
                ).first()
                
                if existing:
                    if rec.component_role:
                        existing.category = rec.component_role
                    if rec.part_spec_name:
                        existing.part_spec_name = rec.part_spec_name
                    if rec.material_type:
                        existing.material_type = rec.material_type
                    if rec.sub_supplier_id:
                        existing.sub_supplier_id = rec.sub_supplier_id
                    existing.updated_at = datetime.utcnow()
                    materials_updated += 1
                else:
                    material = MaterialLibrary(
                        material_id=rec.material_id,
                        material_name=rec.component_name or rec.material_id,
                        component_name=rec.component_name or rec.material_id,
                        supplier_id=rec.supplier_id or "UNKNOWN",
                        part_spec_name=rec.part_spec_name,
                        material_type=rec.material_type,
                        category=rec.component_role,
                        sub_supplier_id=rec.sub_supplier_id,
                    )
                    db.add(material)
                    db.flush()
                    materials_added += 1
                
                seen_materials.add(rec.material_id)
            
            # ─── Insert BOM Record ───────────────────
            bom_record = BOMRecord(
                bom_id=rec.bom_id,
                sku=rec.sku,
                product_name=rec.product_name,
                version=rec.version,
                material_id=rec.material_id,
                quantity=rec.quantity,
                unit=rec.unit,
                component_role=rec.component_role,
                is_sub_supplier=rec.is_sub_supplier,
                source_file=rec.source_file,
            )
            db.add(bom_record)
            bom_records_added += 1
        
        db.commit()
        logger.info(f"  Saved: {manufacturers_added} manufacturers, {suppliers_added} suppliers, {materials_added} new materials, {materials_updated} updated, {bom_records_added} BOM records")
        
    except Exception as e:
        db.rollback()
        logger.error(f"  Database error: {e}")
        raise
    finally:
        db.close()
    
    return {
        "manufacturers_added": manufacturers_added,
        "suppliers_added": suppliers_added,
        "materials_added": materials_added,
        "materials_updated": materials_updated,
        "bom_records_added": bom_records_added,
    }


# ═══════════════════════════════════════════════════════════
# Process Folder
# ═══════════════════════════════════════════════════════════
def process_bom_folder(folder_path: str | Path = None, **kwargs) -> list[BOMCleanResult]:
    """
    Process all Excel files in the BOMs incoming folder.
    Moves processed files to the processed/ directory after successful import.
    """
    folder = Path(folder_path) if folder_path else BOMS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for ext in ["*.xlsx", "*.xls", "*.csv"]:
        for file_path in sorted(folder.glob(ext)):
            # Skip temp files (e.g. ~$filename.xlsx)
            if file_path.name.startswith("~$"):
                continue
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing: {file_path.name}")
            
            result = clean_bom(file_path, **kwargs)
            results.append(result)
            
            if not result.errors:
                # Save to database
                save_summary = save_to_database(result)
                logger.info(f"  Database: {save_summary}")
                
                # Move to processed folder
                dest = PROCESSED_DIR / file_path.name
                PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
                file_path.rename(dest)
                logger.info(f"  Moved to: {dest}")
            else:
                logger.error(f"  Errors: {result.errors}")
    
    return results


# ═══════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════
def main():
    """Process all BOMs in the incoming folder."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean Excel BOM files")
    parser.add_argument("file", nargs="?", help="Single BOM file to process")
    parser.add_argument("--folder", help="Folder containing BOM files")
    parser.add_argument("--bom-id", help="BOM identifier override")
    parser.add_argument("--sku", help="Default SKU for all items")
    parser.add_argument("--product", help="Product name override")
    parser.add_argument("--version", default="v1.0", help="BOM version")
    parser.add_argument("--sheet", default=0, help="Sheet name or index")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    if args.file:
        # Process single file
        result = clean_bom(
            args.file,
            bom_id=args.bom_id,
            sku=args.sku,
            product_name=args.product,
            version=args.version,
            sheet_name=args.sheet,
        )
        
        print(f"\n{'='*60}")
        print(f"  BOM Clean Result: {result.source_file}")
        print(f"{'='*60}")
        print(f"  BOM ID:      {result.bom_id}")
        print(f"  SKU:         {result.sku}")
        print(f"  Total rows:  {result.total_rows}")
        print(f"  Valid rows:  {result.valid_rows}")
        print(f"  Skipped:     {result.skipped_rows}")
        
        if result.warnings:
            print(f"\n  ⚠️  Warnings:")
            for w in result.warnings:
                print(f"     - {w}")
        
        if result.errors:
            print(f"\n  ❌ Errors:")
            for e in result.errors:
                print(f"     - {e}")
        else:
            print(f"\n  ✅ Materials found:")
            for m in result.materials[:10]:
                print(f"     {m.material_id:20s} | {m.sku:15s} | {m.component_role or '-':10s} | qty={m.quantity}")
            if len(result.materials) > 10:
                print(f"     ... and {len(result.materials)-10} more")
        
        if not args.dry_run and not result.errors:
            save_summary = save_to_database(result)
            print(f"\n  💾 Saved to database: {save_summary}")
    
    else:
        # Process folder
        results = process_bom_folder(
            folder_path=args.folder,
            bom_id=args.bom_id,
            sku=args.sku,
            product_name=args.product,
            version=args.version,
        )
        
        print(f"\n{'='*60}")
        print(f"  Processed {len(results)} BOM file(s)")
        print(f"{'='*60}")
        for r in results:
            status = "✅" if not r.errors else "❌"
            print(f"  {status} {r.source_file}: {r.valid_rows} valid / {r.total_rows} total")


if __name__ == "__main__":
    main()
