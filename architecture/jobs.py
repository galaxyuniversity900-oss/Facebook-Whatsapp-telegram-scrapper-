from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

@dataclass(slots=True)
class Job:
    kind: str
    payload: dict
    id: str = None
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 0
    error: str | None = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        now = datetime.now(timezone.utc)
        self.id = self.id or str(uuid4())
        self.created_at = self.created_at or now
        self.updated_at = self.updated_at or now

    def start(self): self.status = JobStatus.RUNNING; self.updated_at = datetime.now(timezone.utc)
    def succeed(self): self.status = JobStatus.SUCCEEDED; self.updated_at = datetime.now(timezone.utc)
    def fail(self, error: str): self.status = JobStatus.FAILED; self.error = error[:2000]; self.updated_at = datetime.now(timezone.utc)
