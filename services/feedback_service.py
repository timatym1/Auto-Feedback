from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FeedbackReport, FeedbackStatus


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_pending_report(
        self, tenant_id: UUID, client_id: UUID, scheduled_at: datetime
    ) -> FeedbackReport:
        """Создание запланированного отчета NPS."""
        report = FeedbackReport(
            tenant_id=tenant_id,
            client_id=client_id,
            status=FeedbackStatus.PENDING,
            scheduled_at=scheduled_at,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_by_id(self, report_id: UUID) -> Optional[FeedbackReport]:
        """Получение отчета по ID."""
        stmt = select(FeedbackReport).where(FeedbackReport.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_pending_for_client(
        self, tenant_id: UUID, client_id: UUID
    ) -> Optional[FeedbackReport]:
        """Получение последнего отправленного/активного запроса отзыва для клиента."""
        stmt = (
            select(FeedbackReport)
            .where(
                FeedbackReport.tenant_id == tenant_id,
                FeedbackReport.client_id == client_id,
                FeedbackReport.status.in_([FeedbackStatus.SENT, FeedbackStatus.PENDING]),
            )
            .order_by(FeedbackReport.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def record_score(self, report_id: UUID, score: int) -> Optional[FeedbackReport]:
        """Фиксация оценки клиента (1-5)."""
        report = await self.get_by_id(report_id)
        if not report:
            return None

        report.score = score
        if score >= 4:
            report.status = FeedbackStatus.COMPLETED
        else:
            # Для низкой оценки статус 'ESCALATED', ожидает текст причины
            report.status = FeedbackStatus.ESCALATED

        await self.session.flush()
        return report

    async def record_negative_reason(
        self, report_id: UUID, reason: str
    ) -> Optional[FeedbackReport]:
        """Запись подробной причины негативного отзыва."""
        report = await self.get_by_id(report_id)
        if not report:
            return None

        report.negative_reason = reason
        report.status = FeedbackStatus.COMPLETED
        await self.session.flush()
        return report

    async def mark_as_sent(self, report_id: UUID) -> None:
        """Отметка об успешной отправке сообщения пользователю."""
        report = await self.get_by_id(report_id)
        if report:
            report.status = FeedbackStatus.SENT
            report.sent_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def mark_as_failed(self, report_id: UUID) -> None:
        """Отметка об ошибке отправки (например, клиент заблокировал бота)."""
        report = await self.get_by_id(report_id)
        if report:
            report.status = FeedbackStatus.FAILED
            await self.session.flush()