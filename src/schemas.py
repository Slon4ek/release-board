from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ReleaseStatus(StrEnum):
    PLANNED = "planned"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ReleaseEnvironment(StrEnum):
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


# SemVer: MAJOR.MINOR.PATCH с optional prerelease и build metadata
SEMVER_PATTERN = (
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class ReleaseCreate(BaseModel):
    service: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., pattern=SEMVER_PATTERN, description="SemVer, например 1.2.3")
    environment: ReleaseEnvironment

    @field_validator("service")
    @classmethod
    def service_must_not_be_empty_or_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("service must not be empty or whitespace")
        return v.strip()


class ReleaseResponse(BaseModel):
    id: UUID
    service: str
    version: str
    environment: ReleaseEnvironment
    status: ReleaseStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ReleaseStatusUpdate(BaseModel):
    status: ReleaseStatus


class VersionResponse(BaseModel):
    version: str
    git_sha: str


VALID_TRANSITIONS: dict[ReleaseStatus, set[ReleaseStatus]] = {
    ReleaseStatus.PLANNED: {ReleaseStatus.DEPLOYED, ReleaseStatus.FAILED},
    ReleaseStatus.DEPLOYED: {ReleaseStatus.ROLLED_BACK},
    ReleaseStatus.FAILED: set(),
    ReleaseStatus.ROLLED_BACK: set(),
}
