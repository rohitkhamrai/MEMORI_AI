"""SQLite store for reports and background jobs."""
import os
import json
import uuid
import aiosqlite
from datetime import datetime, timezone
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "memoria.db")



async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                created_at TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                progress_msg TEXT NOT NULL DEFAULT 'Queued',
                result_json TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def create_job(query: str) -> str:
    job_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO jobs (id, query, status, progress_msg, created_at) VALUES (?,?,?,?,?)",
            (job_id, query, "pending", "Queued...", now)
        )
        await db.commit()
    return job_id


async def update_job(job_id: str, status: str, progress_msg: str, result_json: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET status=?, progress_msg=?, result_json=? WHERE id=?",
            (status, progress_msg, result_json, job_id)
        )
        await db.commit()


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return dict(row)


async def save_report(query: str, report_data: dict) -> str:
    report_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reports (id, query, created_at, report_json) VALUES (?,?,?,?)",
            (report_id, query, now, json.dumps(report_data))
        )
        await db.commit()
    return report_id


async def list_reports(limit: int = 20) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, query, created_at FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_report(report_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reports WHERE id=?", (report_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["report_json"] = json.loads(d["report_json"])
            return d
