from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    name: str
    status: str


class ProductCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")
    name: str = Field(min_length=2, max_length=160)


class SectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    name: str
    description: str


class TeamMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    canonical_name: str
    canonical_role: str
    responsibility: str
    active: bool


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    action: str
    object_type: str
    object_id: str | None
    product_id: str | None
    reason: str | None
    correlation_id: str
    created_at: datetime


class MeOut(BaseModel):
    member_id: str
    name: str
    canonical_role: str
    roles: list[str]
    product_slugs: list[str]
    auth_mode: str


class FeedbackCreate(BaseModel):
    product_slug: str = "nexgrana"
    category: str = Field(default="suggestion", pattern=r"^(bug|error|improvement|suggestion|ux|performance|security|privacy|other)$")
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=10000)
    expected: str | None = Field(default=None, max_length=10000)
    observed: str | None = Field(default=None, max_length=10000)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    human_id: str
    product_id: str
    category: str
    title: str
    description: str
    expected: str | None
    observed: str | None
    severity: str
    priority: str
    status: str
    source: str
    created_at: datetime
    updated_at: datetime


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    human_id: str
    product_id: str
    source_feedback_id: str | None
    title: str
    description: str
    owner_sector: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime


class MonitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product_id: str
    name: str
    local_path: str
    test_command: str
    enabled: bool
    interval_seconds: int
    last_run_at: datetime | None
    next_run_at: datetime | None


class AutomationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    monitor_id: str | None
    product_id: str
    run_type: str
    status: str
    commit_sha: str | None
    command: str
    stdout: str | None
    stderr: str | None
    exit_code: int | None
    duration_ms: int | None
    started_at: datetime
    finished_at: datetime | None
