"""Research API — POST /api/research, GET /api/jobs/{job_id}."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from memoria.api.store import create_job, get_job
from memoria.api.job_runner import run_research_job

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str


@router.post("/research", status_code=202)
async def start_research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    job_id = await create_job(req.query)
    # Fire and forget — don't await
    asyncio.create_task(run_research_job(job_id, req.query))
    return {"job_id": job_id, "status": "pending", "message": "Research job started"}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = None
    if job.get("result_json"):
        import json
        result = json.loads(job["result_json"])
    return {
        "job_id": job["id"],
        "query": job["query"],
        "status": job["status"],
        "progress": job["progress_msg"],
        "created_at": job["created_at"],
        "result": result
    }
