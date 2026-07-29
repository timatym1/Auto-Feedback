from typing import Self
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import AsyncSessionFactory


class UnitOfWork:
    """Паттерн Unit of Work для обеспечения атомарности транзакций."""

    def __init__(self) -> None:
        self.session_factory = AsyncSessionFactory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session:
            if exc_type:
                await self.rollback()
            await self.session.close()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()