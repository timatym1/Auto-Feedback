from aiogram import Router, Command
from aiogram.filters import CommandObject
from aiogram.types import Message
from loguru import logger

from database.unit_of_work import UnitOfWork
from filters.is_creator import IsCreatorFilter
from schemas.dto import TenantCreateDTO
from services.tenant_service import TenantService

router = Router(name="creator_router")
router.message.filter(IsCreatorFilter())


@router.message(Command("add_tenant"))
async def cmd_add_tenant(message: Message, command: CommandObject) -> None:
    """
    Создание нового тенанта напрямую Создателем.
    Формат: /add_tenant <Company Name> | <Director TG ID>
    """
    if not command.args or "|" not in command.args:
        await message.answer("Использование: `/add_tenant Название Компании | Director_TG_ID`", parse_mode="Markdown")
        return

    parts = command.args.split("|")
    company_name = parts[0].strip()
    director_tg_id = parts[1].strip()

    dto = TenantCreateDTO(
        company_name=company_name,
        director_tg_id=director_tg_id,
    )

    async with UnitOfWork() as uow:
        tenant_service = TenantService(uow.session)
        tenant = await tenant_service.create_tenant(dto)
        await uow.commit()

        response = (
            f"✅ **Тенант успешно создан!**\n\n"
            f"**UUID:** `{tenant.id}`\n"
            f"**Компания:** {tenant.company_name}\n"
            f"**Директор TG ID:** `{tenant.director_tg_id}`\n"
            f"**Триал до:** {tenant.trial_ends_at.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        await message.answer(response, parse_mode="Markdown")