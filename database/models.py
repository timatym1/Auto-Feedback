# filepath: database/models.py
import enum
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, SmallInteger, ForeignKey, DateTime, Enum as SQLEnum, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    pass

class SubscriptionStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class RequestStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    SENT = "SENT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    admin_telegram_id: Mapped[str] = mapped_column(String(64), nullable=False)
    map_link_2gis: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    map_link_google: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, name="subscription_status_enum"), default=SubscriptionStatus.TRIAL
    )
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customers: Mapped[List["Customer"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    feedback_requests: Mapped[List["FeedbackRequest"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("tenant_id", "phone_number", name="uq_tenant_customer"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="customers")
    feedback_requests: Mapped[List["FeedbackRequest"]] = relationship(back_populates="customer", cascade="all, delete-orphan")

class FeedbackRequest(Base):
    __tablename__ = "feedback_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus, name="request_status_enum"), default=RequestStatus.SCHEDULED
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="feedback_requests")
    customer: Mapped["Customer"] = relationship(back_populates="feedback_requests")
    incident: Mapped[Optional["Incident"]] = relationship(back_populates="request", uselist=False, cascade="all, delete-orphan")

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("feedback_requests.id", ondelete="CASCADE"), unique=True, nullable=False)
    customer_comment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolution_status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus, name="incident_status_enum"), default=IncidentStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped["FeedbackRequest"] = relationship(back_populates="incident")