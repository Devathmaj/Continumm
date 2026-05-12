from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    ip_address = Column(String(64), nullable=False, index=True)
    mac_address = Column(String(64), nullable=True, unique=True, index=True)
    hostname = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)

    ports = relationship("DevicePort", back_populates="device", cascade="all, delete-orphan")
    statuses = relationship("DeviceStatus", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("AlertEvent", back_populates="device", cascade="all, delete-orphan")


class DevicePort(Base):
    __tablename__ = "device_ports"
    __table_args__ = (
        UniqueConstraint("device_id", "port", "protocol", name="uq_device_port"),
    )

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(16), nullable=False, default="tcp")
    service = Column(String(255), nullable=True)
    state = Column(String(32), nullable=True)
    last_seen = Column(DateTime, nullable=False)

    device = relationship("Device", back_populates="ports")


class DeviceStatus(Base):
    __tablename__ = "device_status"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    observed_at = Column(DateTime, nullable=False, index=True)
    online = Column(Boolean, nullable=False, default=False)
    latency_ms = Column(Float, nullable=True)
    packet_loss_percent = Column(Float, nullable=True)
    jitter_ms = Column(Float, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    uptime_percent = Column(Float, nullable=True)

    device = relationship("Device", back_populates="statuses")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    alert_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)
    message = Column(String(512), nullable=False)
    observed_at = Column(DateTime, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="alerts")


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True)
    subnet = Column(String(64), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False)
    devices_found = Column(Integer, nullable=False, default=0)
    error_message = Column(String(1024), nullable=True)
