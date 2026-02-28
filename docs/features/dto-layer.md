# DTO-слой: передача данных между слоями приложения

## Описание

DTO (Data Transfer Object) — это простые Pydantic-объекты, которые служат единственным способом передачи данных из базы данных в сервисы и хендлеры. ORM-модели (SQLAlchemy) создаются и уничтожаются строго внутри репозиториев — ни сервисы, ни хендлеры никогда не видят объекты `User`, `Config` или `AdminSession`. Это защищает верхние слои от деталей базы данных и предотвращает случайные обращения к БД за пределами транзакции.

## Использование

### Пример: получить пользователя в хендлере

```python
from bot.dto import UserDTO

# user приходит готовым из AuthMiddleware — репозиторий уже вызван
async def cmd_start(message: Message, user: UserDTO) -> None:
    print(user.telegram_id)  # int
    print(user.is_admin)     # bool
    print(user.username)     # str | None
```

### Пример: получить список конфигов

```python
from bot.db.repositories.config_repo import ConfigRepository
from bot.dto import ConfigDTO

async def list_configs(
    callback: CallbackQuery,
    user: UserDTO,
    db_session: AsyncSession,
) -> None:
    repo = ConfigRepository(db_session)
    configs: list[ConfigDTO] = await repo.get_by_user_id(user.id)

    for config in configs:
        print(config.email, config.protocol, config.created_at)
```

### Пример конвертации ORM-модели в DTO внутри репозитория

```python
# bot/db/repositories/config_repo.py
from bot.db.models import Config      # ORM-модель, живёт только здесь
from bot.dto import ConfigDTO         # DTO, уходит наружу

async def get_by_id(self, config_id: int) -> ConfigDTO | None:
    stmt = select(Config).where(Config.id == config_id)
    result = await self._session.execute(stmt)
    config = result.scalar_one_or_none()   # <-- ORM-объект
    if config is None:
        return None
    return ConfigDTO.model_validate(config)  # <-- конвертация и возврат DTO
```

`model_validate` читает атрибуты ORM-объекта по именам полей DTO. Это работает благодаря `model_config = ConfigDict(from_attributes=True)` в классе DTO.

### Пример для Telegram

```
Пользователь: /start
Бот: Привет, ivan!
     Я помогу управлять VPN-конфигурациями.
     Выберите действие:  [Мои конфиги] [Создать]

Пользователь: нажимает "Мои конфиги"
Бот: Ваши конфиги:
     [home-vpn] [work-vpn]
```

В обоих хендлерах параметр `user: UserDTO` появляется автоматически через `AuthMiddleware` — хендлер не знает ничего про БД.

## API

### `UserDTO`

```python
class UserDTO(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    is_admin: bool
    created_at: datetime
```

Используется в `AuthMiddleware`, `start.py`, `config.py`. Инжектируется в каждый хендлер как аргумент `user`.

### `ConfigDTO`

```python
class ConfigDTO(BaseModel):
    id: int
    user_id: int
    inbound_id: int
    client_id: str
    email: str
    protocol: str
    created_at: datetime
```

Возвращается из всех методов `ConfigRepository`. Используется в хендлерах `config.py`.

- `email` — идентификатор клиента в панели 3x-ui, уникальный на inbound
- `client_id` — UUID клиента в панели

### `ConfigSummaryDTO`

```python
class ConfigSummaryDTO(BaseModel):
    id: int
    email: str
```

Облегчённый вариант для отображения списков, когда полные данные конфига не нужны. Не содержит `from_attributes=True` — конструируется вручную.

### `AdminSessionRepository.get_first_credentials() -> tuple[str, str] | None`

Метод, который не возвращает DTO, но и не возвращает ORM-модель. Вместо этого он возвращает кортеж `(panel_url, encrypted_credentials)`.

- Возвращает: `tuple[str, str]` — URL панели и зашифрованные учётные данные
- Возвращает `None`, если ни одной сессии не существует
- Использование: хендлер `config.py` / `_get_xui_client()` вызывает этот метод, чтобы получить данные подключения без доступа к полю `AdminSession`

## Правила

**Что живёт где:**

| Что | Где живёт |
|-----|-----------|
| ORM-модели (`User`, `Config`, `AdminSession`) | только `bot/db/models.py` и `bot/db/repositories/` |
| DTO-классы | `bot/dto.py` |
| Конвертация ORM -> DTO | внутри метода репозитория, перед `return` |
| Использование DTO | сервисы, хендлеры, мидлвари |

**Что запрещено:**

- Импортировать `bot.db.models` в хендлерах или сервисах
- Возвращать ORM-объект из метода репозитория
- Делать `session.execute()` в хендлере напрямую (только через репозиторий)
- Создавать DTO с изменяемыми полями ради "удобства" мутации — DTO только для чтения

## Связанные файлы

- `bot/dto.py` — все DTO-классы проекта
- `bot/db/repositories/user_repo.py` — возвращает `UserDTO`
- `bot/db/repositories/config_repo.py` — возвращает `ConfigDTO`
- `bot/db/repositories/admin_session_repo.py` — возвращает `tuple` вместо ORM-модели
- `bot/middlewares/auth.py` — получает `UserDTO` из репозитория и кладёт в `data["user"]`
- `bot/handlers/config.py` — использует `UserDTO` и `ConfigDTO`
- `bot/handlers/start.py` — использует `UserDTO`
- `bot/db/models.py` — ORM-модели, которые не должны покидать db-слой

---

## Разбор для изучения

### Архитектурные решения

**Конвертация в репозитории, а не снаружи**

- **Что** использовано: `ConfigDTO.model_validate(config)` вызывается в последней строке каждого метода репозитория, до `return`
- **Зачем** именно так: репозиторий — единственное место, которое знает про ORM-модели. Если завтра модель изменится (переименуется поле, добавится computed property), менять нужно только репозиторий, а не все хендлеры
- **Альтернатива**: конвертировать в хендлере — тогда хендлер должен знать про SQLAlchemy-объекты, что создаёт скрытую связанность: хендлер начинает зависеть от деталей БД

**`from_attributes=True` в Pydantic v2**

- **Что** использовано: `model_config = ConfigDict(from_attributes=True)` в каждом DTO
- **Зачем** именно так: по умолчанию Pydantic ожидает словарь. Этот флаг говорит ему читать данные через атрибуты объекта (`obj.id`, `obj.email`), что нужно для SQLAlchemy-моделей, которые являются обычными Python-объектами с атрибутами
- **Альтернатива**: передавать `ConfigDTO(id=config.id, email=config.email, ...)` вручную — многословно и ломается при добавлении поля, если забыть добавить его в конструктор

**`get_first_credentials` возвращает tuple, а не DTO**

- **Что** использовано: `tuple[str, str]` вместо отдельного `AdminSessionDTO`
- **Зачем** именно так: для `AdminSession` нет публичного API — его данные нужны только в одном месте (`_get_xui_client`), и только два поля из пяти. Создавать полноценный DTO ради одного use-case — избыточно
- **Альтернатива**: `AdminSessionDTO` — разумно, если понадобится второй потребитель этих данных; пока преждевременно

**Инжекция `UserDTO` через мидлварь**

- **Что** использовано: `AuthMiddleware` кладёт `UserDTO` в `data["user"]`, aiogram передаёт его как аргумент хендлера
- **Зачем** именно так: каждый хендлер получает готового пользователя без единой строки работы с БД. Нет дублирования `user_repo.get_or_create()` в каждом хендлере
- **Альтернатива**: вызывать репозиторий в каждом хендлере — 20+ хендлеров, 20 одинаковых блоков, любое изменение логики авторизации надо менять везде

### Словарь терминов

**DTO (Data Transfer Object)** — объект, единственная задача которого — перевезти данные из одного места в другое. Как курьерская коробка: внутри лежат данные, никакой логики, никаких методов для работы с БД. Pydantic-класс идеально подходит на эту роль, потому что умеет валидировать данные при создании и запрещает случайные изменения.

**ORM-модель** — Python-класс, который связан с таблицей в базе данных. Объект `User` — это не просто данные, это "живой" объект с открытым соединением к БД внутри. Если передать его за пределы транзакции, обращение к `user.configs` вызовет запрос в закрытую сессию и упадёт с ошибкой `DetachedInstanceError`. DTO — это "слепок" данных, безопасный для передачи куда угодно.

**`model_validate`** — метод Pydantic v2, который создаёт DTO из любого объекта с атрибутами. Аналог `dict()`, но для объектов: `ConfigDTO.model_validate(orm_config)` читает `orm_config.id`, `orm_config.email` и кладёт их в новый `ConfigDTO`.

**Dependency Injection (DI)** — паттерн, при котором объект не создаёт свои зависимости сам, а получает их снаружи. `AuthMiddleware` создаёт `UserDTO` и кладёт его в словарь `data`. Aiogram достаёт его оттуда и передаёт в аргумент `user` хендлера. Хендлер не знает, откуда взялся `user` — он просто его использует. Это как заказать доставку: вы получаете пиццу, не зная маршрут курьера.

**Слой (layer)** — логическая граница в архитектуре. В этом проекте три слоя: `db` (репозитории + ORM), `services` (бизнес-логика), `handlers` (Telegram-интерфейс). Данные пересекают границу между слоями только в виде DTO.

### Разбор кода

**Конвертация ORM -> DTO в репозитории:**

```python
async def get_by_user_id(self, user_id: int) -> list[ConfigDTO]:
    # select(Config) — строим SQL-запрос через SQLAlchemy
    stmt = select(Config).where(Config.user_id == user_id).order_by(Config.created_at.desc())
    # await — запрос к БД, ждём ответа
    result = await self._session.execute(stmt)
    # result.scalars().all() — достаём список ORM-объектов Config
    # [ConfigDTO.model_validate(c) for c in ...] — конвертируем каждый в DTO
    # Список ORM-объектов создан и сразу преобразован, наружу уходят только DTO
    return [ConfigDTO.model_validate(c) for c in result.scalars().all()]
```

**Инжекция пользователя через мидлварь:**

```python
async def __call__(self, handler, event, data):
    # data — словарь, который aiogram передаёт вместе с событием
    async with async_session_factory() as session, session.begin():
        user_repo = UserRepository(session)
        # get_or_create возвращает UserDTO (не ORM-модель!)
        user = await user_repo.get_or_create(
            telegram_id=tg_user.id,
            username=tg_user.username,
        )
        # Кладём UserDTO в словарь под ключом "user"
        data["user"] = user
        # Aiogram видит, что хендлер просит аргумент user: UserDTO,
        # достаёт его из data["user"] и передаёт автоматически
        result = await handler(event, data)
```

**Использование DTO в хендлере с проверкой владельца:**

```python
async def show_config_detail(callback, user: UserDTO, db_session):
    config_id = int(callback.data.split(":")[1])
    config_repo = ConfigRepository(db_session)
    # get_by_id возвращает ConfigDTO | None
    config = await config_repo.get_by_id(config_id)

    # config.user_id — поле DTO (int), не JOIN к ORM
    # user.id — поле DTO (int), не обращение к БД
    # Простое сравнение двух чисел — быстро и безопасно
    if config is None or config.user_id != user.id:
        await callback.answer("Конфиг не найден.", show_alert=True)
        return
```

### Что изучить дальше

1. **Pydantic v2: validators и computed fields** — как добавить вычисляемые поля в DTO без обращения к БД. Документация: https://docs.pydantic.dev/latest/concepts/validators/
2. **SQLAlchemy `DetachedInstanceError`** — что происходит, если ORM-объект уходит за пределы сессии и почему DTO решает эту проблему. Статья в документации: https://docs.sqlalchemy.org/en/20/errors.html#error-bhk3
3. **Repository Pattern** — архитектурный паттерн, на котором построен db-слой. Martin Fowler, "Patterns of Enterprise Application Architecture", глава 10.

### Вопросы для самопроверки

1. Почему нельзя вернуть объект `User` (ORM) из `UserRepository.get_by_telegram_id()` напрямую в хендлер? Что произойдёт, если обратиться к `user.configs` после закрытия транзакции?

2. `ConfigSummaryDTO` не имеет `model_config = ConfigDict(from_attributes=True)`. Как тогда его создать из ORM-объекта `Config`? Напишите строку кода.

3. В каком слое должен быть такой код и почему: `config = Config(user_id=user.id, email="test")`?

4. `AuthMiddleware` создаёт `UserDTO` и кладёт его в `data["user"]`. Как хендлер получает его в виде аргумента `user: UserDTO`? Кто за это отвечает?

5. Представьте, что нужно добавить поле `expires_at: datetime | None` в конфиги. Перечислите все файлы, которые нужно изменить, начиная от миграции БД до хендлера.
