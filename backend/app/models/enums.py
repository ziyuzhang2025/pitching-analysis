"""Shared enumerations (part of the API/database contract)."""

import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


ACTIVE_JOB_STATUSES = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)

THROWING_HANDS = ("right", "left")
CAMERA_VIEWS = ("arm_side", "glove_side", "behind", "rear_oblique", "front", "other")
EVENT_METHODS = ("auto", "manual")
