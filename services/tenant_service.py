from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SubscriptionStatus, Tenant
from schemas.dto import TenantCreateDTO


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_tenant(self, dto: TenantCreateDTO, trial_days: int = 14) -> Tenant:
        """Создание нового тенанта с триальным периодом."""
        trial_ends_at = datetime.now(timezone.utc) + timedelta(days=trial_days)
        tenant = Tenant(
            company_name=dto.company_name,
            director_tg_id=dto.director_tg_id,
            review_link_2gis=dto.review_link_2gis,
            review_link_google=dto.review_link_google,
            subscription_status=SubscriptionStatus.TRIAL,
            trial_ends_at=trial_ends_at,
        )
        self.session.add(tenant)
        await self.session.flush()
        return tenant

    async def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Получение тенанта по UUID."""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_director_tg_id(self, director_tg_id: str) -> Optional[Tenant]:
        """Получение тенанта по Telegram ID директора."""
        stmt = select(Tenant).where(Tenant.director_tg_id == director_tg_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_links(
        self, tenant_id: UUID, review_link_2gis: Optional[str], review_link_google: Optional[str]
    ) -> Optional[Tenant]:
        """Обновление ссылок на 2GIS и Google Maps."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None
        if review_link_2gis is not None:
            tenant.review_link_2gis = review_link_2gis
        if review_link_google is not None:
            tenant.review_link_google = review_link_google
        await self.session.flush()
        return tenant

    async def is_subscription_active(self, tenant: Tenant) -> bool:
        """Проверка активности подписки с учетом триального периода."""
        if tenant.subscription_status == SubscriptionStatus.ACTIVE:
            return True
        if tenant.subscription_status == SubscriptionStatus.TRIAL:
            return datetime.now(timezone.utc) < tenant.trial_ends_at
        return False