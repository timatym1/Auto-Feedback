from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScheduleFeedbackRequest(BaseModel):
    tenant_id: UUID = Field(..., description="ID Тенанта / Бизнеса")
    client_phone: Optional[str] = Field(None, description="Телефон клиента (опционально)")
    tg_user_id: str = Field(..., description="Telegram ID пользователя")
    delay_minutes: int = Field(default=120, ge=0, le=10080, description="Задержка отправки в минутах")

    @field_validator("tg_user_id")
    def validate_tg_id(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Field 'tg_user_id' must be a valid numeric string.")
        return v


class ScheduleFeedbackResponse(BaseModel):
    status: str = "success"
    task_id: str
    scheduled_at: datetime


class RFC7807Error(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str


class TenantCreateDTO(BaseModel):
    company_name: str
    director_tg_id: str
    review_link_2gis: Optional[str] = None
    review_link_google: Optional[str] = None


class TenantReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str
    director_tg_id: str
    review_link_2gis: Optional[str]
    review_link_google: Optional[str]
    subscription_status: str
    trial_ends_at: datetime
    created_at: datetime