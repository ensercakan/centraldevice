from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import AccessMethod, DeviceType, JobStatus, JobType, Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str
    role: Role = Role.viewer


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    email: str | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    access_method: AccessMethod
    secret: dict


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    device_id: int | None
    access_method: AccessMethod
    created_at: datetime


class DeviceCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: str = Field(min_length=1, max_length=45)
    mac: str | None = None
    device_type: DeviceType = DeviceType.other
    vendor: str | None = None
    model: str | None = None
    management_url: str | None = None
    site: str | None = None
    notes: str | None = None


class DeviceUpdate(BaseModel):
    hostname: str | None = None
    mac: str | None = None
    device_type: DeviceType | None = None
    vendor: str | None = None
    model: str | None = None
    management_url: str | None = None
    site: str | None = None
    notes: str | None = None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    ip_address: str
    mac: str | None
    device_type: DeviceType
    vendor: str | None
    model: str | None
    serial: str | None
    management_url: str | None
    site: str | None
    notes: str | None
    status: str
    last_seen: datetime | None
    created_at: datetime
    updated_at: datetime


class DeviceWithRelations(DeviceOut):
    credentials: list[CredentialOut] = []


class ConfigPushRequest(BaseModel):
    template: str = Field(min_length=1)
    variables: dict = Field(default_factory=dict)
    access_method: AccessMethod | None = None


class DiscoverRequest(BaseModel):
    subnet: str = Field(min_length=1, max_length=64)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    job_type: JobType
    status: JobStatus
    payload: str | None
    result: str | None
    error: str | None
    created_by: int | None
    created_at: datetime
    finished_at: datetime | None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime


class MetricPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ts: datetime
    metric_key: str
    value: str


class DashboardSummary(BaseModel):
    devices_total: int
    devices_up: int
    devices_down: int
    devices_unknown: int
    by_type: dict[str, int]
    open_alerts: int
    jobs_last_24h: int
    recent_alerts: list[AlertOut]
    recent_jobs: list[JobOut]
