"""Reports API — GET /api/reports, GET /api/reports/{id}."""
from fastapi import APIRouter, HTTPException
from memoria.api.store import list_reports, get_report

router = APIRouter()


@router.get("/reports")
async def get_reports():
    reports = await list_reports(limit=50)
    return {"reports": reports, "count": len(reports)}


@router.get("/reports/{report_id}")
async def get_report_by_id(report_id: str):
    report = await get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
