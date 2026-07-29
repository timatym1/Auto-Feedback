import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    DateTime,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    director_tg_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_link_2gis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_link_google: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, name="subscription_status_enum"),
        default=SubscriptionStatus.TRIAL,
        nullable=False,
    )
    trial_ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    clients: Mapped[List["Client"]] = relationship(
        "Client", back_populates="tenant", cascade="all, delete-orphan"
    )
    feedback_reports: Mapped[List["FeedbackReport"]] = relationship(
        "FeedbackReport", back_populates="tenant", cascade="all, delete-orphan"
    )


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tg_user_id", name="uq_tenant_tg_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tg_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="clients")
    feedback_reports: Mapped[List["FeedbackReport"]] = relationship(
        "FeedbackReport", back_populates="client", cascade="all, delete-orphan"
    )


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"
    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 5", name="check_score_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    negative_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[FeedbackStatus] = mapped_column(
        SQLEnum(FeedbackStatus, name="feedback_status_enum"),
        default=FeedbackStatus.PENDING,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="feedback_reports"
    )
    client: Mapped["Client"] = relationship(
        "Client", back_populates="feedback_reports"
    )