"""In-memory async job manager.

Stem separation and edit rendering are CPU/GPU-bound and take real time (a
few seconds to a couple of minutes), so they run as background jobs: the API
returns a `job_id` immediately, the work runs in a thread-pool executor (kept
off the asyncio event loop and off FastAPI's request/response cycle), and the
frontend either polls `GET /jobs/{job_id}` or subscribes to
`WS /jobs/{job_id}/ws` for live progress.

A single-user local desktop app doesn't need Celery/Redis/etc — this is
intentionally the simplest thing that gives real progress streaming.
"""
from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from .schemas import JobProgress, JobStatus

_executor = ThreadPoolExecutor(max_workers=2)


@dataclass
class _Job:
    id: str
    kind: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    subscribers: list[asyncio.Queue] = field(default_factory=list)

    def snapshot(self) -> JobProgress:
        return JobProgress(
            job_id=self.id,
            kind=self.kind,
            status=self.status,
            progress=self.progress,
            message=self.message,
            result=self.result,
            error=self.error,
        )


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, _Job] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def get(self, job_id: str) -> JobProgress | None:
        job = self._jobs.get(job_id)
        return job.snapshot() if job else None

    def subscribe(self, job_id: str) -> asyncio.Queue | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        q: asyncio.Queue = asyncio.Queue()
        job.subscribers.append(q)
        q.put_nowait(job.snapshot())
        return q

    def start(
        self,
        kind: str,
        work: Callable[[Callable[[float, str], None]], dict[str, Any]],
    ) -> str:
        """Schedules `work` on the thread pool. `work` receives a `report(progress,
        message)` callback it should call periodically; its return value becomes
        `job.result` on success."""
        job_id = uuid.uuid4().hex[:10]
        job = _Job(id=job_id, kind=kind)
        self._jobs[job_id] = job

        loop = self._loop or asyncio.get_event_loop()

        def report(progress: float, message: str = "") -> None:
            job.progress = max(0.0, min(1.0, progress))
            job.message = message
            job.status = JobStatus.RUNNING
            loop.call_soon_threadsafe(self._broadcast, job)

        def run() -> None:
            job.status = JobStatus.RUNNING
            loop.call_soon_threadsafe(self._broadcast, job)
            try:
                result = work(report)
                job.result = result
                job.progress = 1.0
                job.status = JobStatus.DONE
                job.message = "done"
            except Exception as exc:  # noqa: BLE001 - surfaced to the client
                job.status = JobStatus.ERROR
                job.error = f"{exc}\n{traceback.format_exc()}"
            loop.call_soon_threadsafe(self._broadcast, job)

        loop.run_in_executor(_executor, run)
        return job_id

    def _broadcast(self, job: _Job) -> None:
        snapshot = job.snapshot()
        for q in list(job.subscribers):
            q.put_nowait(snapshot)


job_manager = JobManager()
