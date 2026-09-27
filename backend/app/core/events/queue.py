"""Lightweight background job queue for autonomous complaint processing."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger(__name__)

JobHandler = Callable[["Job"], Awaitable[None]]


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid4()))
    job_type: str = ""
    complaint_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED


class AsyncJobQueue:
    """In-process background job queue using asyncio.Queue."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._handlers: dict[str, JobHandler] = {}
        self._worker_task: asyncio.Task[None] | None = None
        self._running: bool = False

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    async def enqueue(self, job_type: str, complaint_id: str, payload: dict[str, Any] | None = None) -> Job:
        job = Job(job_type=job_type, complaint_id=complaint_id, payload=payload or {})
        await self._queue.put(job)
        logger.info(
            "Job enqueued",
            extra={"job_id": job.id, "job_type": job.job_type, "complaint_id": job.complaint_id},
        )
        self.ensure_worker_running()
        return job

    def ensure_worker_running(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._worker_task = loop.create_task(self._worker_loop())
            except RuntimeError:
                pass  # Loop not running yet (will start when FastAPI starts)

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                job = await self._queue.get()
                handler = self._handlers.get(job.job_type)
                if not handler:
                    logger.warning("No handler for job type", extra={"job_type": job.job_type})
                    self._queue.task_done()
                    continue

                job.status = "RUNNING"
                job.attempts += 1
                try:
                    await handler(job)
                    job.status = "COMPLETED"
                    logger.info("Job completed", extra={"job_id": job.id, "job_type": job.job_type})
                except Exception as exc:
                    logger.error(
                        "Job execution failed",
                        extra={"job_id": job.id, "job_type": job.job_type, "attempt": job.attempts, "error": str(exc)},
                    )
                    if job.attempts < job.max_retries:
                        job.status = "PENDING"
                        # Exponential backoff retry
                        await asyncio.sleep(0.5 * (2 ** (job.attempts - 1)))
                        await self._queue.put(job)
                    else:
                        job.status = "FAILED"
                        logger.error("Job permanently failed (dead-letter)", extra={"job_id": job.id})

                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected worker queue error", extra={"error": str(exc)})
                await asyncio.sleep(0.5)

    def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()


# Global default instance
job_queue = AsyncJobQueue()
