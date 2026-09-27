"""Lightweight local JobQueue with retries and dead-letter handling."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from app.core.events.idempotency import get_idempotency_store
from app.core.events.schemas import Job, JobStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

JobProcessor = Callable[[Job], Awaitable[None]]


class JobQueue(Protocol):
    async def enqueue(self, job: Job) -> None: ...
    def register_processor(self, job_type: str, processor: JobProcessor) -> None: ...


class LocalJobQueue:
    """Asyncio-backed local job queue supporting retries and dead-lettering."""

    def __init__(self, concurrency: int = 2) -> None:
        self._queue: asyncio.Queue[Job] | None = None
        self._processors: dict[str, JobProcessor] = {}
        self._idempotency = get_idempotency_store()
        self._concurrency = concurrency
        self._workers: list[asyncio.Task[None]] = []
        self._running = False
        self._dead_letter_jobs: list[Job] = []

    @property
    def queue(self) -> asyncio.Queue[Job]:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    def register_processor(self, job_type: str, processor: JobProcessor) -> None:
        self._processors[job_type] = processor
        logger.debug("job processor registered", extra={"job_type": job_type, "processor": processor.__name__})

    async def enqueue(self, job: Job) -> None:
        if job.idempotency_key and not self._idempotency.check_and_set(f"job:{job.idempotency_key}"):
            logger.warning("duplicate job enqueue skipped", extra={"job_id": job.job_id, "key": job.idempotency_key})
            return

        logger.info(
            "enqueuing background job",
            extra={"job_id": job.job_id, "job_type": job.job_type, "complaint_id": job.complaint_id},
        )
        await self.queue.put(job)

    def start(self) -> None:
        if self._running:
            return
        self._queue = asyncio.Queue()
        self._running = True
        for i in range(self._concurrency):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        logger.info("job queue workers started", extra={"concurrency": self._concurrency})

    def stop(self) -> None:
        self._running = False
        for task in self._workers:
            task.cancel()
        self._workers.clear()
        self._queue = None
        logger.info("job queue workers stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        q = self.queue
        while self._running:
            try:
                job = await q.get()
                await self._process_job(job)
                q.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("worker error in job loop", extra={"worker_id": worker_id, "error": str(exc)})
                await asyncio.sleep(0.5)

    async def _process_job(self, job: Job) -> None:
        processor = self._processors.get(job.job_type)
        if not processor:
            logger.error("no processor registered for job type", extra={"job_type": job.job_type, "job_id": job.job_id})
            job.status = JobStatus.FAILED
            job.error_message = f"No processor for {job.job_type}"
            self._dead_letter_jobs.append(job)
            return

        job.status = JobStatus.PROCESSING
        try:
            logger.info("processing job", extra={"job_id": job.job_id, "job_type": job.job_type, "retry": job.retry_count})
            await processor(job)
            job.status = JobStatus.COMPLETED
            logger.info("job completed successfully", extra={"job_id": job.job_id, "job_type": job.job_type})
        except Exception as exc:
            job.retry_count += 1
            job.error_message = str(exc)
            logger.warning(
                "job processing failed",
                extra={
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "retry": job.retry_count,
                    "max_retries": job.max_retries,
                    "error": str(exc),
                },
            )

            if job.retry_count <= job.max_retries:
                # Exponential backoff retry
                backoff_seconds = 0.5 * (2 ** (job.retry_count - 1))
                await asyncio.sleep(backoff_seconds)
                await self._queue.put(job)
            else:
                job.status = JobStatus.DEAD_LETTER
                self._dead_letter_jobs.append(job)
                logger.error("job moved to dead letter queue", extra={"job_id": job.job_id, "error": str(exc)})


# Global job queue singleton
_default_job_queue = LocalJobQueue()


def get_job_queue() -> LocalJobQueue:
    return _default_job_queue
