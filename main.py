import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import aiofiles

from database import init_db, get_db
from models import Addon, Report, FileRecord, User
from extractor import extract_addon, scan_file_tree
from scanner import scan_addon
from fix_engine import apply_fixes

# Directory config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "..", "reports")
FIXED_DIR = os.path.join(BASE_DIR, "..", "fixed_addons")

for d in [UPLOADS_DIR, REPORTS_DIR, FIXED_DIR]:
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="Minecraft Addon Analyzer AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Minecraft Addon Analyzer AI", "status": "running"}


@app.post("/upload-addon")
async def upload_addon(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate extension
    allowed = {".zip", ".mcaddon", ".mcpack"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'. Allowed: {', '.join(allowed)}")

    # Get or create anonymous user
    user = db.query(User).filter(User.username == "anonymous").first()
    if not user:
        user = User(username="anonymous")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Save uploaded file
    addon_uid = str(uuid.uuid4())
    upload_path = os.path.join(UPLOADS_DIR, f"{addon_uid}{ext}")
    async with aiofiles.open(upload_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Create addon record
    addon = Addon(
        user_id=user.id,
        filename=file.filename,
        original_path=upload_path,
        status="analyzing"
    )
    db.add(addon)
    db.commit()
    db.refresh(addon)

    # Extract
    extract_path = os.path.join(UPLOADS_DIR, f"{addon_uid}_extracted")
    extract_result = extract_addon(upload_path, extract_path)

    if not extract_result["success"]:
        addon.status = "error"
        db.commit()
        raise HTTPException(status_code=422, detail=f"Extraction failed: {extract_result['error']}")

    addon.extracted_path = extract_path
    db.commit()

    # Run full scan
    scan_result = scan_addon(extract_path)

    # Save file records
    for f_info in scan_result["files"]:
        fr = FileRecord(
            addon_id=addon.id,
            file_path=f_info["relative_path"],
            file_type=f_info["type"],
            file_size=f_info["size"],
            error_count=0,
            warning_count=0,
        )
        db.add(fr)

    # Save all reports
    file_error_counts = {}
    file_warning_counts = {}
    for issue in scan_result["all_issues"]:
        fp = issue.get("file_path", "")
        sev = issue.get("severity", "info")
        if sev == "error":
            file_error_counts[fp] = file_error_counts.get(fp, 0) + 1
        elif sev == "warning":
            file_warning_counts[fp] = file_warning_counts.get(fp, 0) + 1

        rpt = Report(
            addon_id=addon.id,
            report_type=issue.get("report_type", "general"),
            severity=sev,
            message=issue.get("message", ""),
            file_path=fp,
            fix_suggestion=issue.get("fix_suggestion", ""),
            auto_fixable=issue.get("auto_fixable", False),
        )
        db.add(rpt)

    # Update file record counts
    db.flush()
    file_records = db.query(FileRecord).filter(FileRecord.addon_id == addon.id).all()
    for fr in file_records:
        fr.error_count = file_error_counts.get(fr.file_path, 0)
        fr.warning_count = file_warning_counts.get(fr.file_path, 0)

    addon.score = scan_result["score"]
    addon.status = "done"
    db.commit()

    return {
        "addon_id": addon.id,
        "filename": file.filename,
        "score": scan_result["score"],
        "stats": scan_result["stats"],
        "files_scanned": len(scan_result["files"]),
        "total_issues": len(scan_result["all_issues"]),
    }


@app.get("/addon/{addon_id}")
def get_addon(addon_id: int, db: Session = Depends(get_db)):
    addon = db.query(Addon).filter(Addon.id == addon_id).first()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")

    reports = db.query(Report).filter(Report.addon_id == addon_id).all()
    files = db.query(FileRecord).filter(FileRecord.addon_id == addon_id).all()

    # Group reports by type
    by_type = {}
    for r in reports:
        rt = r.report_type
        if rt not in by_type:
            by_type[rt] = []
        by_type[rt].append({
            "id": r.id,
            "severity": r.severity,
            "message": r.message,
            "file_path": r.file_path,
            "fix_suggestion": r.fix_suggestion,
            "auto_fixable": r.auto_fixable,
            "fixed": r.fixed,
        })

    # Severity counts
    errors = sum(1 for r in reports if r.severity == "error")
    warnings = sum(1 for r in reports if r.severity == "warning")
    info = sum(1 for r in reports if r.severity == "info")

    # By-type counts for charts
    type_counts = {}
    for r in reports:
        type_counts[r.report_type] = type_counts.get(r.report_type, 0) + 1

    return {
        "id": addon.id,
        "filename": addon.filename,
        "score": addon.score,
        "status": addon.status,
        "upload_time": addon.upload_time.isoformat() if addon.upload_time else None,
        "stats": {
            "files_scanned": len(files),
            "total_issues": len(reports),
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "by_type": type_counts,
        },
        "reports_by_type": by_type,
        "files": [
            {
                "id": f.id,
                "path": f.file_path,
                "type": f.file_type,
                "size": f.file_size,
                "errors": f.error_count,
                "warnings": f.warning_count,
            }
            for f in files
        ],
    }


@app.get("/addon/{addon_id}/file-reports")
def get_file_reports(addon_id: int, file_path: str, db: Session = Depends(get_db)):
    reports = db.query(Report).filter(
        Report.addon_id == addon_id,
        Report.file_path == file_path
    ).all()
    return [
        {
            "id": r.id,
            "severity": r.severity,
            "message": r.message,
            "fix_suggestion": r.fix_suggestion,
            "auto_fixable": r.auto_fixable,
            "report_type": r.report_type,
        }
        for r in reports
    ]


@app.post("/addon/{addon_id}/fix")
def fix_addon(addon_id: int, db: Session = Depends(get_db)):
    addon = db.query(Addon).filter(Addon.id == addon_id).first()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if not addon.extracted_path or not os.path.isdir(addon.extracted_path):
        raise HTTPException(status_code=400, detail="Addon files not found for fixing")

    result = apply_fixes(addon.extracted_path, FIXED_DIR, addon_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Fix failed: {result['error']}")

    # Mark fixable reports as fixed
    auto_fixable_reports = db.query(Report).filter(
        Report.addon_id == addon_id,
        Report.auto_fixable == True
    ).all()
    for r in auto_fixable_reports:
        r.fixed = True
    db.commit()

    return {
        "success": True,
        "fixes_applied": result["fixes_applied"],
        "download_url": f"/addon/{addon_id}/download-fixed",
    }


@app.get("/addon/{addon_id}/download-fixed")
def download_fixed(addon_id: int):
    zip_path = os.path.join(FIXED_DIR, f"fixed_addon_{addon_id}.zip")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Fixed addon not found. Run fix first.")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"fixed_addon_{addon_id}.zip"
    )


@app.get("/addons")
def list_addons(db: Session = Depends(get_db)):
    addons = db.query(Addon).order_by(Addon.upload_time.desc()).limit(20).all()
    return [
        {
            "id": a.id,
            "filename": a.filename,
            "score": a.score,
            "status": a.status,
            "upload_time": a.upload_time.isoformat() if a.upload_time else None,
        }
        for a in addons
    ]


@app.delete("/addon/{addon_id}")
def delete_addon(addon_id: int, db: Session = Depends(get_db)):
    addon = db.query(Addon).filter(Addon.id == addon_id).first()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    # Cleanup files
    for path in [addon.original_path, addon.extracted_path]:
        if path and os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
    db.query(Report).filter(Report.addon_id == addon_id).delete()
    db.query(FileRecord).filter(FileRecord.addon_id == addon_id).delete()
    db.delete(addon)
    db.commit()
    return {"deleted": True}
