Ручная проверка INFRA-пунктов (выполнить на вашей стороне)
bash
# 1. Логи сервиса (замени <container_name>)
docker logs --tail 200 -f <container_name>
# или, если через systemd:
journalctl -u <service_name> -n 200 -f

# 2. Статус вебхука
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | jq '.result | {url, has_custom_certificate, last_error_date, last_error_message, pending_update_count}'

# 3. Валидность токена
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | jq

Ключевое: если docker logs покажет ImportError: cannot import name 'broker' from 'services.taskiq_broker' (или AttributeError) — это подтверждает п.1 выше.

[x] services/taskiq_broker.py — восстановление реального TaskIQ broker
🛠 Что сделано: Полностью заменено содержимое файла. Удалены дублирующие Pydantic-схемы (ScheduleFeedbackRequest/Response, RFC7807Error, TenantCreateDTO/ReadDTO), которые уже существуют в schemas/dto.py. Восстановлен реальный AsyncBroker на базе RedisStreamBroker с RedisAsyncResultBackend.
💡 Какая польза: Исправлена критическая ошибка ImportError/AttributeError при импорте broker из services.taskiq_broker. Теперь модуль корректно экспортирует broker для использования в services/tasks.py и src/app.py.
⚠️ Радиус влияния: Затронуты services/tasks.py (строки 12, 29) и src/app.py (строки 20, 41-42, 83-84) — все потребители broker.
🔄 Откат (Rollback): git checkout services/taskiq_broker.py (восстановит предыдущее состояние с Pydantic-схемами).

[x] services/tasks.py — безопасная отправка + разделение ошибок
🛠 Что сделано: Добавлены импорты TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter из aiogram.exceptions и escape_md из aiogram.utils.markdown. Реализована детализированная обработка исключений при отправке сообщений: escape_md для безопасного экранирования company_name, разделение TelegramRetryAfter (retryable, rollback + raise для TaskIQ ретраев), TelegramForbiddenError (BOT_BLOCKED_BY_USER, mark_as_failed), TelegramBadRequest (невалидные данные, mark_as_failed).
💡 Какая польза: Улучшена безопасность (защита от Markdown-инъекций), повышена точность обработки ошибок (разделение retryable и fatal ошибок), добавлено корректное логирование с причинами.
⚠️ Радиус влияния: Только services/tasks.py. Зависимости: services/taskiq_broker.py (broker), services/feedback_service.py (mark_as_sent/mark_as_failed), database/unit_of_work.py (uow.rollback/commit).
🔄 Откат (Rollback): git checkout services/tasks.py.

[x] config/settings.py — обязательность секретов вне DEVELOPMENT
🛠 Что сделано: Добавлен field_validator forbid_default_secrets_in_prod для полей JWT_SECRET и WEBHOOK_SECRET. Валидатор проверяет, что в production (ENV=production) не используются дефолтные секреты-заглушки ("super-secret-jwt-key", "secret-webhook-key").
💡 Какая польза: Повышена безопасность — предотвращено использование слабых секретов в production среде. Валидатор работает только при ENV=production, не затрагивая development/staging.
⚠️ Радиус влияния: config/settings.py. Зависимости: pydantic (field_validator, SecretStr), os (getenv). Все модули, импортирующие settings, получают защиту.
🔄 Откат (Rollback): git checkout config/settings.py.

[x] src/app.py — исправление недостающих импортов
🛠 Что сделано: Добавлены недостающие импорты: timedelta (для расчета scheduled_at), HTTPException (для обработки ошибок в schedule_feedback).
💡 Какая польза: Исправлены NameError при использовании timedelta и HTTPException в эндпоинте /api/v1/feedback/schedule.
⚠️ Радиус влияния: src/app.py. Зависимости: fastapi (HTTPException), datetime (timedelta).
🔄 Откат (Rollback): git checkout src/app.py.

[ ] Ручная проверка INFRA-пунктов (выполнить на вашей стороне)
