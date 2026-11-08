import enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class DeviceType(str, enum.Enum):
    router = "router"
    switch = "switch"
    access_point = "access_point"
    repeater = "repeater"
    modem = "modem"
    other = "other"


class AccessMethod(str, enum.Enum):
    snmp = "snmp"
    ssh = "ssh"
    tr069 = "tr069"
    rest = "rest"


class JobType(str, enum.Enum):
    poll = "poll"
    config_push = "config_push"
    firmware = "firmware"
    reboot = "reboot"
    discover = "discover"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.viewer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship(back_populates="created_by_user")


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True)
    access_method: Mapped[AccessMethod] = mapped_column(SAEnum(AccessMethod))
    encrypted_secret: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

    device: Mapped["Device | None"] = relationship(back_populates="credentials")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, index=True)
    mac: Mapped[str | None] = mapped_column(String(17), nullable=True)
    device_type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType), default=DeviceType.other)
    vendor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial: Mapped[str | None] = mapped_column(String(128), nullable=True)
    management_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    site: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="unknown")
    last_seen: Mapped[object] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    credentials: Mapped[list["Credential"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    metrics: Mapped[list["DeviceMetric"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True)
    job_type: Mapped[JobType] = mapped_column(SAEnum(JobType))
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.queued)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[object] = mapped_column(DateTime, nullable=True)

    device: Mapped["Device | None"] = relationship(back_populates="jobs")
    created_by_user: Mapped["User | None"] = relationship(back_populates="jobs")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="warning")
    message: Mapped[str] = mapped_column(Text)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

    device: Mapped["Device | None"] = relationship(back_populates="alerts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class DeviceMetric(Base):
    __tablename__ = "device_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    ts: Mapped[object] = mapped_column(DateTime, server_default=func.now(), index=True)
    metric_key: Mapped[str] = mapped_column(String(128), index=True)
    value: Mapped[str] = mapped_column(String(255))

    device: Mapped["Device"] = relationship(back_populates="metrics")
