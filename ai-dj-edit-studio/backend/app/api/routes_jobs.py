"""GET /jobs/{job_id} — poll a job's current status.
WS  /jobs/{job_id}/ws — subscribe for live progress push (used by the
frontend's JobProgress component instead of polling)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ..jobs import job_manager
from ..schemas import JobProgress, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobProgress)
def get_job(job_id: str) -> JobProgress:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id")
    return job


@router.websocket("/{job_id}/ws")
async def job_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    queue = job_manager.subscribe(job_id)
    if queue is None:
        await websocket.send_json({"error": "unknown job id"})
        await websocket.close()
        return

    try:
        while True:
            snapshot = await queue.get()
            await websocket.send_json(snapshot.model_dump(mode="json"))
            if snapshot.status in (JobStatus.DONE, JobStatus.ERROR):
                break
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
