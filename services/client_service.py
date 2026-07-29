from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Client


class ClientService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_client(
        self, tenant_id: UUID, tg_user_id: str, phone_number: Optional[str] = None
    ) -> Client:
        """Атомарный поиск или создание клиента в рамках конкретного тенанта."""
        stmt = select(Client).where(
            Client.tenant_id == tenant_id,
            Client.tg_user_id == tg_user_id
        )
        result = await self.session.execute(stmt)
        client = result.scalar_one_or_none()

        if not client:
            client = Client(
                tenant_id=tenant_id,
                tg_user_id=tg_user_id,
                phone_number=phone_number,
            )
            self.session.add(client)
            await self.session.flush()
        elif phone_number and client.phone_number != phone_number:
            client.phone_number = phone_number
            await self.session.flush()

        return client