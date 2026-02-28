# TASK-001: Введение DTO-слоя для фичи "Мои конфиги"

**Статус:** Ожидает апрува
**Приоритет:** Высокий
**Дата:** 2026-02-28

## Описание

Сейчас ORM-модели `User` и `Config` из `bot/db/models.py` передаются напрямую в хендлеры, что нарушает принцип разделения слоёв. Нужно ввести Pydantic DTO между репозиторием, сервисом и хендлером, чтобы хендлеры никогда не видели SQLAlchemy-объектов. Рефакторинг затрагивает всю вертикаль фичи "Мои конфиги": middleware → репозиторий → сервис → хендлер.

## Что будет сделано

1. Создать `bot/dto.py` — Pydantic-модели `UserDTO` и `ConfigDTO` (и `ConfigSummaryDTO` для списков)
2. Изменить `ConfigRepository` — все методы возвращают `ConfigDTO` / `list[ConfigDTO]` вместо ORM-моделей
3. Изменить `UserRepository` — методы `get_or_create`, `get_by_telegram_id`, `set_admin` возвращают `UserDTO`
4. Изменить `AuthMiddleware` — инжектирует `UserDTO` в `data["user"]` вместо ORM `User`
5. Изменить `vpn_service.py` — функции принимают и возвращают DTO; убрать прямое обращение к полям ORM
6. Изменить `bot/handlers/config.py` — заменить аннотацию `user: User` на `user: UserDTO`; убрать импорт ORM-моделей из хендлера
7. Проверить `bot/handlers/admin.py` — при необходимости привести к DTO
8. Обновить тесты под новые сигнатуры

## Какие файлы будут затронуты

- `bot/dto.py` — новый файл, Pydantic DTO: `UserDTO`, `ConfigDTO`, `ConfigSummaryDTO`
- `bot/db/repositories/user_repo.py` — изменение, методы возвращают `UserDTO` вместо ORM `User`
- `bot/db/repositories/config_repo.py` — изменение, методы возвращают `ConfigDTO` вместо ORM `Config`
- `bot/middlewares/auth.py` — изменение, `data["user"]` становится `UserDTO`
- `bot/services/vpn_service.py` — изменение, сигнатуры функций работают с DTO; `delete_config` и `get_config_link` принимают `ConfigDTO` или `config_id: int`
- `bot/handlers/config.py` — изменение, аннотация `user: User` → `user: UserDTO`; убраны импорты ORM
- `bot/handlers/admin.py` — изменение (при необходимости), аналогичная замена
- `tests/` — изменение, моки и фикстуры переведены на DTO

## Пользовательский сценарий

Поведение бота для пользователя не меняется — рефакторинг внутренний:

```
Пользователь: [нажимает "Мои конфиги"]
Бот: показывает список конфигов в виде inline-кнопок

Пользователь: [нажимает на конфиг]
Бот: Конфиг: my-vpn
     Протокол: vless
     Создан: 01.01.2026 12:00
     [Трафик] [Обновить] [Ссылка] [Удалить]

Пользователь: [Удалить]
Бот: Вы уверены, что хотите удалить конфиг «my-vpn»?
     [Да, удалить] [Отмена]

Пользователь: [Да, удалить]
Бот: Конфиг «my-vpn» удалён.
```

## Технические решения

### DTO-модели (bot/dto.py)

```python
from datetime import datetime
from pydantic import BaseModel

class UserDTO(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class ConfigDTO(BaseModel):
    id: int
    user_id: int
    inbound_id: int
    client_id: str
    email: str
    protocol: str
    created_at: datetime

    model_config = {"from_attributes": True}

class ConfigSummaryDTO(BaseModel):
    """Облегчённый DTO для отображения в списке."""
    id: int
    email: str
```

### Конвертация в репозиториях

Репозитории по-прежнему работают с ORM внутри, но на выходе вызывают `ConfigDTO.model_validate(orm_obj)`. Это сохраняет SQLAlchemy внутри db-слоя и не выпускает ORM наружу.

### Сигнатуры сервисных функций

- `create_config(user_id: int, ...) -> str` — не меняется (уже принимает `int`)
- `delete_config(config_id: int, xui: XUIClient, session: AsyncSession) -> None` — не меняется
- `get_config_link(config_id: int, xui: XUIClient, session: AsyncSession) -> str` — не меняется
- Внутри сервиса `config_repo.get_by_id()` теперь вернёт `ConfigDTO`; обращение к полям (`config.inbound_id`, `config.client_id`, `config.email`) сохраняется без изменений, так как DTO имеет те же поля

### Middleware

`AuthMiddleware` получает ORM `User` из `UserRepository.get_or_create()`, конвертирует его в `UserDTO` и кладёт в `data["user"]`. ORM-объект после этого нигде не покидает db-слой.

### Зависимости

Дополнительных зависимостей не требуется — Pydantic v2 уже входит в стек.

## Критерии приёмки

- [ ] Файл `bot/dto.py` создан, содержит `UserDTO`, `ConfigDTO`, `ConfigSummaryDTO` с `model_config = {"from_attributes": True}`
- [ ] `UserRepository` возвращает `UserDTO` во всех публичных методах; ORM-модель `User` не экспортируется за пределы репозитория
- [ ] `ConfigRepository` возвращает `ConfigDTO` / `list[ConfigDTO]` во всех публичных методах; ORM-модель `Config` не экспортируется за пределы репозитория
- [ ] `AuthMiddleware` кладёт в `data["user"]` объект типа `UserDTO`, а не ORM `User`
- [ ] В `bot/handlers/config.py` нет импорта `from bot.db.models import User` (или `Config`)
- [ ] В `bot/handlers/admin.py` нет импорта ORM-моделей в качестве типов хендлеров
- [ ] Все хендлеры аннотируют параметр `user` как `UserDTO`
- [ ] Поведение бота для пользователя не изменилось (список, детали, трафик, ссылка, удаление работают)
- [ ] Тесты проходят (`uv run pytest -x`), покрытие не падает ниже 80%
- [ ] Линтер не даёт ошибок (`uv run ruff check .`)

## Вне скоупа

- Изменение схемы базы данных или миграции Alembic
- Добавление новых полей в DTO сверх того, что есть в ORM-моделях
- Изменение логики генерации ссылок или трафика
- Рефакторинг `admin_session_repo.py` (AdminSession DTO — отдельная задача)
- Кэширование или оптимизация запросов
