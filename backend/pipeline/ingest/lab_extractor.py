"""
Lab Report Extractor — Uses Ollama (qwen2:7b) to extract structured data from PDF lab reports.
Extracts: EN 71-3 migration limits, GHS Section 3/14 data, substance breakdown.
"""
import os
import re
import json
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://192.168.8.224:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:7b")


def _call_ollama(prompt: str, temperature: float = 0.1, timeout: int = 120) -> str:
    """Send prompt to Ollama and return response text."""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 2048}
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Ollama request timed out after {timeout}s")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot connect to Ollama at {OLLAMA_HOST}")
    except Exception as e:
        raise RuntimeError(f"Ollama API error: {e}")


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using available tools."""
    # Try pdfplumber first (best quality)
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except ImportError:
        pass

    # Fallback to PyPDF2
    try:
        import PyPDF2
        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n\n".join(text_parts)
    except ImportError:
        pass

    raise RuntimeError("No PDF library available. Install pdfplumber or PyPDF2.")


def _build_extraction_prompt(text: str, report_type: str = "en71_3") -> str:
    """Build prompt for lab report extraction."""
    base = """You are a compliance data extraction assistant. Extract structured data from the following lab report text.

RULES:
- Return ONLY valid JSON. No markdown, no explanations, no code blocks.
- Use null for missing values.
- Concentrations should be numeric (float) in mg/kg.
- Dates should be in ISO format YYYY-MM-DD.

"""
    if report_type == "en71_3":
        base += """EXTRACT the following fields:
{
  "report_number": "string or null",
  "report_date": "YYYY-MM-DD or null",
  "lab_name": "string or null",
  "test_standard": "EN 71-3 or null",
  "sample_description": "string or null",
  "material_id": "string or null — the internal material code if present",
  "sku": "string or null — the product SKU if present",
  "en71_3_category": "I, II, III, or null",
  "migration_results": [
    {
      "element": "string (e.g. Lead, Cadmium, Mercury)",
      "symbol": "string (e.g. Pb, Cd, Hg)",
      "measured_value_mg_kg": "float or null",
      "limit_value_mg_kg": "float or null",
      "result": "Pass, Fail, or null",
      "method": "string or null"
    }
  ],
  "overall_result": "Pass, Fail, or null",
  "notes": "string or null"
}
"""
    elif report_type == "ghs":
        base += """EXTRACT GHS classification data:
{
  "report_number": "string or null",
  "report_date": "YYYY-MM-DD or null",
  "lab_name": "string or null",
  "material_id": "string or null",
  "sku": "string or null",
  "section_3_composition": [
    {
      "substance_name": "string",
      "cas_number": "string or null",
      "concentration_percent": "float or null",
      "concentration_range": "string or null"
    }
  ],
  "section_14_transport": {
    "un_number": "string or null",
    "shipping_name": "string or null",
    "hazard_class": "string or null",
    "packing_group": "string or null"
  },
  "ghs_hazard_codes": ["H315", "H319", ...],
  "ghh_signal_word": "Danger or Warning or null",
  "notes": "string or null"
}
"""
    else:
        base += """EXTRACT all test data you can find:
{
  "report_number": "string or null",
  "report_date": "YYYY-MM-DD or null",
  "lab_name": "string or null",
  "test_standard": "string or null",
  "material_id": "string or null",
  "sku": "string or null",
  "test_results": [
    {
      "test_name": "string",
      "measured_value": "float or null",
      "unit": "string or null",
      "limit_value": "float or null",
      "result": "Pass, Fail, or null"
    }
  ],
  "overall_result": "Pass, Fail, or null",
  "notes": "string or null"
}
"""

    base += f"\n\nLAB REPORT TEXT:\n{'='*60}\n{text[:12000]}\n{'='*60}\n\nJSON OUTPUT:"
    return base


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown fences."""
    # Remove markdown fences
    content = re.sub(r'^```json\s*', '', content.strip(), flags=re.IGNORECASE)
    content = re.sub(r'```\s*$', '', content.strip())
    content = content.strip()

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Try to fix common issues
    content = content.replace("'", '"')  # single quotes
    content = re.sub(r',\s*}', '}', content)  # trailing commas
    content = re.sub(r',\s*]', ']', content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Could not parse JSON from response: {content[:500]}")


def extract_lab_report(pdf_path: str, report_type: str = "auto") -> Dict[str, Any]:
    """
    Extract structured data from a PDF lab report.

    Args:
        pdf_path: Path to PDF file
        report_type: "en71_3", "ghs", or "auto" (detect from content)

    Returns:
        Dict with extracted structured data
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Extract text
    text = _extract_text_from_pdf(pdf_path)
    if not text.strip():
        raise ValueError("No text could be extracted from PDF")

    # Auto-detect report type
    if report_type == "auto":
        text_upper = text.upper()
        if "EN 71" in text_upper or "EN71" in text_upper or "MIGRATION" in text_upper:
            report_type = "en71_3"
        elif "GHS" in text_upper or "SECTION 3" in text_upper or "SECTION 14" in text_upper:
            report_type = "ghs"
        else:
            report_type = "general"

    # Build prompt and call Ollama
    prompt = _build_extraction_prompt(text, report_type)
    response = _call_ollama(prompt)

    # Parse JSON
    data = _parse_json_response(response)
    data["_extraction_meta"] = {
        "source_file": os.path.basename(pdf_path),
        "report_type_detected": report_type,
        "extracted_at": datetime.now().isoformat(),
        "model": OLLAMA_MODEL,
        "raw_text_length": len(text)
    }
    return data


def save_extraction_to_db(data: Dict[str, Any], db_session=None):
    """Save extracted lab report data to the pipeline database."""
    from pipeline.models.database import (
        get_db, TestHistory, SubstanceBreakdown, ComplianceCheck,
        MaterialLibrary, init_db
    )

    if db_session is None:
        init_db()
        db = get_db()
    else:
        db = db_session

    try:
        material_id = data.get("material_id")
        sku = data.get("sku")
        report_number = data.get("report_number", "UNKNOWN")
        report_date = data.get("report_date")
        lab_name = data.get("lab_name", "Unknown Lab")
        overall_result = data.get("overall_result", "Review")

        # Save migration results as TestHistory entries
        for result in data.get("migration_results", []):
            th = TestHistory(
                material_id=material_id or "UNKNOWN",
                report_number=report_number,
                report_date=report_date,
                lab_name=lab_name,
                test_standard="EN 71-3",
                test_type="migration",
                result=result.get("result", "Review"),
                measured_value=result.get("measured_value_mg_kg"),
                unit="mg/kg",
                limit_value=result.get("limit_value_mg_kg"),
                sku=sku,
                notes=f"Element: {result.get('element', 'N/A')}, Method: {result.get('method', 'N/A')}"
            )
            db.add(th)

        # Save substance breakdown from GHS Section 3
        for substance in data.get("section_3_composition", []):
            sb = SubstanceBreakdown(
                material_id=material_id or "UNKNOWN",
                cas_number=substance.get("cas_number"),
                substance_name=substance.get("substance_name", "Unknown"),
                concentration_typical=substance.get("concentration_percent"),
                source="ai_extracted"
            )
            db.add(sb)

        # Save compliance check
        cc = ComplianceCheck(
            material_id=material_id or "UNKNOWN",
            regulation="en71_3" if data.get("test_standard", "").upper().startswith("EN") else "ghs",
            check_type="migration_test" if "migration" in str(data.get("test_standard", "")).lower() else "substance_restrict",
            result=overall_result.lower() if overall_result else "review",
            details=json.dumps(data, default=str),
            source="ai_check"
        )
        db.add(cc)

        db.commit()
        return {"test_history_count": len(data.get("migration_results", [])),
                "substance_count": len(data.get("section_3_composition", [])),
                "compliance_check_id": cc.id}
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Database save failed: {e}")
    finally:
        if db_session is None:
            db.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python lab_extractor.py <pdf_path> [report_type]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    report_type = sys.argv[2] if len(sys.argv) > 2 else "auto"

    print(f"🔬 Extracting lab report: {pdf_path}")
    print(f"🤖 Using Ollama model: {OLLAMA_MODEL} at {OLLAMA_HOST}")

    try:
        result = extract_lab_report(pdf_path, report_type)
        print("\n✅ Extraction successful!")
        print(json.dumps(result, indent=2, default=str))

        # Optionally save to DB
        save_result = save_extraction_to_db(result)
        print(f"\n💾 Saved to database: {save_result}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
