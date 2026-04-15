# backend/app/middleware/file_validator.py
"""
Validates uploaded files for security and correctness.
"""
import os
import io
import logging
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/json",
    "text/plain",  # Some systems send CSV as text/plain
    "application/octet-stream",  # Fallback
}


async def validate_upload(file: UploadFile) -> bytes:
    """
    Validate an uploaded file. Returns the file content if valid.
    Raises HTTPException if invalid.
    """
    # 1. Check file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_file_type",
                "detail": f"File type '{ext}' not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
                "status": 400,
            },
        )

    # 2. Read content
    content = await file.read()
    await file.seek(0)  # Reset for downstream use

    # 3. Check file size
    if len(content) > MAX_FILE_SIZE:
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "file_too_large",
                "detail": f"File is {size_mb:.1f}MB. Maximum allowed: {MAX_FILE_SIZE / (1024 * 1024):.0f}MB",
                "status": 400,
            },
        )

    # 4. Check if file is empty
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "empty_file",
                "detail": "Uploaded file is empty",
                "status": 400,
            },
        )

    # 5. Validate content is parseable
    try:
        if ext == ".csv":
            _validate_csv(content)
        elif ext == ".json":
            _validate_json(content)
        elif ext in (".xlsx", ".xls"):
            _validate_excel(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "malformed_file",
                "detail": f"Could not parse file: {str(e)}",
                "status": 400,
            },
        )

    logger.info(f"[FileValidator] File validated: {file.filename} ({len(content)} bytes)")
    return content


def _validate_csv(content: bytes):
    """Check that CSV has valid headers."""
    import csv

    try:
        text = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        if not header:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "malformed_csv",
                    "detail": "CSV file has no header row",
                    "status": 400,
                },
            )
        # Check at least one data row
        first_row = next(reader, None)
        if not first_row:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "empty_csv",
                    "detail": "CSV file has headers but no data rows",
                    "status": 400,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "malformed_csv",
                "detail": f"Invalid CSV format: {str(e)}",
                "status": 400,
            },
        )


def _validate_json(content: bytes):
    """Check that JSON is valid."""
    import json

    try:
        data = json.loads(content)
        if not isinstance(data, (dict, list)):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_json",
                    "detail": "JSON must be an object or array",
                    "status": 400,
                },
            )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "malformed_json",
                "detail": f"Invalid JSON: {str(e)}",
                "status": 400,
            },
        )


def _validate_excel(content: bytes):
    """Basic check that Excel file is readable."""
    # Just check the magic bytes for xlsx (PK zip header)
    if content[:2] != b'PK' and content[:8] != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        raise HTTPException(
            status_code=400,
            detail={
                "error": "malformed_excel",
                "detail": "File does not appear to be a valid Excel file",
                "status": 400,
            },
        )
