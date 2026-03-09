# TASK-018: Унификация системы администраторов

**Статус:** ⏳ Ожидает апрува
**Приоритет:** Высокий
**Дата:** 2026-03-07
**Зоны:** Бот / Shared / Админ-бэк

---

## Описание

Сейчас в проекте два независимых источника правды об администраторах: таблица
`admins` (admin-mini-app) и флаг `User.is_admin` (бот). При входе администратора
в мини-апп бот об этом не знает. Кроме того, `BotSettings` содержит единые
настройки панели для всех, тогда как каждый админ должен подключить свою 3x-ui
панель и своего config-бота.

Задача объединяет две системы через общую PostgreSQL: оба сервиса читают и
пишут напрямую в одну БД без промежуточного HTTP API. Таблица `admins`
становится единственным источником правды, каждый admin получает поля для
персональных credentials панели и токен собственного config-бота.

---

## Контекст и текущее состояние

### Проблема 1 — Дублирование источников правды

| Место | Сущность | Назначение |
|---|---|---|
| `bot/db/models.py` | `User.is_admin` | Проверка прав в боте |
| `bot/db/models.py` | `AdminSession` | Credentials 3x-ui панели (per-admin) |
| `admin-mini-app/backend/db/models.py` | `Admin` (таблица `admins`) | Права доступа в мини-апп |

Когда мини-апп добавляет нового администратора — в `admins` запись есть, но
`User.is_admin = false` и `AdminSession` отсутствует. Бот про такого admin
ничего не знает.

### Проблема 2 — Единые настройки панели

`BotSettings` — одна строка (id=1) на весь сервис. Каждый admin должен
управлять своими конфигурациями в своей 3x-ui панели. `AdminSession` уже
хранит per-admin credentials, но мини-апп об этом не знает и всегда читает
`bot_settings`.

### Проблема 3 — Per-admin config-бот

Каждый admin использует собственного Telegram-бота для управления
конфигурациями клиентов (config-бот, не путать с admin-ботом для мини-апп).
Токен config-бота должен храниться per-admin в зашифрованном виде.

### Проблема 4 — Команды бота

`/setadmin` / `/rmadmin` — команды owner'а в боте для управления ролями.
После унификации управление переходит в мини-апп, эти команды устаревают.
Команда `/admin` (FSM ввод credentials панели) — оставить как запасной способ.

---

## Архитектурное решение — Синхронизация через общую БД

Оба сервиса (бот на aiogram + admin-mini-app на FastAPI) работают с одной
PostgreSQL. **Internal HTTP API между ними не нужен.**

- **Бот** при проверке прав — читает таблицу `admins` напрямую (или проверяет
  `User.is_admin` как денормализованный кэш).
- **Admin-mini-app** при сохранении настроек — пишет в поля `Admin` напрямую.
  При первом входе нового owner — обновляет `User.is_admin = true` в таблице
  `users` напрямую.
- Синхронизация `AdminSession` (таблица бота): admin-mini-app при сохранении
  панельных настроек пишет напрямую в `admin_sessions`.

Это убирает целый слой сложности: нет FastAPI-сервера в боте, нет
`INTERNAL_API_KEY`, нет HTTP-клиента в мини-апп.

---

## Пайплайн выполнения

| # | Агент | Что делает | Зависит от |
|---|---|---|---|
| 1 | `developer` | Добавляет поля в `Admin`, обновляет `AdminSession`, мигрирует БД; обновляет бот-репозитории и хендлеры | — |
| 2 | `admin-api` | Переключает `router_settings.py` на поля `Admin`; добавляет прямую запись в `admin_sessions` и `users`; обновляет `deps.py` | Шаг 1 |
| 3 | `qa-bot` | Тестирует бот-логику проверки прав через таблицу `admins` | Шаг 1 |
| 4 | `qa-admin` | Тестирует обновлённые settings-эндпоинты и прямую запись в БД | Шаг 2 |
| 5 | `review-backend` | Ревью всех изменений бэка | Шаги 3, 4 |

> Дизайн и фронт не затронуты. Страница Settings в мини-апп уже существует;
> форма совместима с новыми полями. Страница "Administrators" — вне скоупа
> этой задачи (отдельная задача в будущем).
>
> Шаги 3 и 4 могут выполняться параллельно.

---

## Что будет сделано

### Shared — модели и БД (developer)

1. **Расширить модель `Admin`** (таблица `admins`, файл
   `admin-mini-app/backend/db/models.py`):
   - `panel_url: str | None` — URL 3x-ui панели этого администратора
   - `panel_username: str | None` — логин в панели
   - `panel_password_encrypted: str | None` — пароль, зашифрованный Fernet
   - `panel_sub_url: str | None` — base URL для subscription links
   - `config_bot_token_encrypted: str | None` — зашифрованный токен
     собственного config-бота данного admin
   - `username: str | None` — Telegram username (для логов; заполняется из
     initData при первом входе)

2. **Миграция Alembic**: добавить новые nullable-поля в таблицу `admins`.
   Существующие записи не затрагиваются (все поля nullable).

3. **`User.is_admin`**: оставить как денормализованный флаг для быстрой
   проверки в боте без JOIN. Устанавливается напрямую из admin-mini-app при
   первом входе owner.

4. **`AdminSession`** (таблица бота): admin-mini-app при сохранении панельных
   credentials пишет напрямую в `admin_sessions`, используя тот же
   `FERNET_KEY`.

### Бот (developer)

1. **Проверка прав в боте**: при проверке `is_admin` — читать таблицу `admins`
   напрямую через репозиторий (или синхронизировать `User.is_admin` при
   старте через startup-reconciler как вспомогательный механизм).

2. **Убрать/упростить команды**:
   - `/admin` — FSM-флоу ручного ввода credentials: оставить как запасной
     способ, добавить информационное сообщение о том, что настройки теперь
     доступны через мини-апп
   - `/setadmin`, `/rmadmin`, `/admins` — **устаревают**: выводить сообщение
     "Управление администраторами перенесено в мини-апп" и ничего не делать

3. **Убрать** из `bot/config.py` любые упоминания `INTERNAL_API_KEY`,
   `INTERNAL_API_PORT`, `INTERNAL_API_URL` (если они были добавлены ранее).
   Не создавать `bot/internal_api.py`.

### Админ-бэк (admin-api)

1. **`deps.py` — обогатить `get_current_admin`**: при авто-создании owner
   сохранять `username` из initData в поле `Admin.username`. При каждом входе
   обновлять `username`, если он изменился.

2. **`router_settings.py` — per-admin настройки панели**:
   - `GET /api/settings` — возвращать настройки текущего администратора из
     полей `Admin` (не из `BotSettings`)
   - `PUT /api/settings` — обновлять поля `Admin` текущего администратора;
     одновременно писать в `admin_sessions` напрямую через DB-сессию
   - `POST /api/settings/check` — тест соединения по credentials из полей
     `Admin` текущего admin

3. **`GET /api/settings/global`** и **`PUT /api/settings/global`** — только
   для owner. Хранит глобальный `owner_id` и `client_bot_token` (токен
   admin-бота). Остаётся в `BotSettings` (таблицу не удаляем).

4. **Прямая запись в `admin_sessions`**: при `PUT /api/settings` admin-mini-app
   пишет в таблицу `admin_sessions` (таблица бота) через ту же PostgreSQL.
   Для этого нужен репозиторий `admin_sessions` в admin-mini-app, который
   использует ту же модель (или raw SQL / отражённую таблицу).

5. **Прямая запись в `users.is_admin`**: при первом входе owner — установить
   `User.is_admin = true` в таблице `users`.

6. **Убрать**: `services/bot_sync.py`, `schemas/admin.py`, `router_admins.py`
   — не создавать эти файлы.

---

## Какие файлы будут затронуты

### Shared / Бот

- `admin-mini-app/backend/db/models.py` — изменение `Admin`: добавить поля
  `panel_url`, `panel_username`, `panel_password_encrypted`, `panel_sub_url`,
  `config_bot_token_encrypted`, `username`
- `admin-mini-app/backend/db/repositories/admin_repo.py` — добавить методы:
  `update_panel_settings`, `update_username`, `get_by_telegram_id`
  (уже есть — проверить)
- `admin-mini-app/backend/alembic/versions/XXXX_add_admin_panel_fields.py` —
  миграция для новых полей таблицы `admins`
- `bot/handlers/admin.py` — обновить сообщения `/admin` (добавить подсказку
  про мини-апп)
- `bot/handlers/owner.py` — `/setadmin`, `/rmadmin`, `/admins` → deprecated-
  сообщения
- `bot/services/` или `bot/middlewares/` — проверка `is_admin` через таблицу
  `admins` (если сейчас использует только `User.is_admin`)

### Adminsessions репозиторий в admin-mini-app

- `admin-mini-app/backend/db/repositories/admin_session_repo.py` — **новый**:
  upsert в таблицу `admin_sessions` (таблица создана ботом). Используется при
  `PUT /api/settings` для записи credentials панели.
- `admin-mini-app/backend/db/models.py` — добавить отражённую модель
  `AdminSession` (или использовать `text()`-запросы, если модели конфликтуют)

### Админ-бэк

- `admin-mini-app/backend/api/deps.py` — сохранять `username` из initData при
  авто-создании owner; обновлять `username` при каждом входе
- `admin-mini-app/backend/api/router_settings.py` — переключить `GET/PUT`
  с `BotSettings` на поля `Admin`; добавить вызов `admin_session_repo.upsert`
  при `PUT`
- `admin-mini-app/backend/schemas/settings.py` — обновить `SettingsResponse`
  и `SettingsUpdate` под поля `Admin` (убрать глобальные поля из personal-схем)
- `admin-mini-app/backend/config.py` — убрать любые переменные
  `INTERNAL_API_URL`, `INTERNAL_API_KEY` (если были добавлены)

---

## Пользовательские сценарии

### Сценарий 1: Первый вход owner в мини-апп

```
Owner открывает мини-апп впервые
Мини-апп: валидирует initData, находит 0 admin-записей
Мини-апп: создаёт Admin(telegram_id, role="owner", username="...") в таблице admins
Мини-апп: устанавливает User.is_admin = true в таблице users (прямая запись в БД)
Owner: переходит на страницу Settings
UI: форма с полями panel_url, panel_username, panel_password, panel_sub_url, config_bot_token
Owner: заполняет и сохраняет
API: PUT /api/settings → обновляет поля Admin, пишет в admin_sessions напрямую
Бот: при следующем запросе видит актуальные данные в admin_sessions
```

### Сценарий 2: Бот проверяет права администратора

```
Пользователь отправляет команду, требующую прав admin
Бот: делает SELECT из таблицы admins WHERE telegram_id = ...
Если запись есть → разрешить
Если нет → отказать (или проверить User.is_admin как fallback)
```

### Сценарий 3: Admin обновляет credentials панели

```
Admin: открывает Settings в мини-апп, вводит panel_url/username/password
API: PUT /api/settings
Мини-апп:
  1. Шифрует пароль через Fernet (FERNET_KEY)
  2. Обновляет поля Admin в таблице admins
  3. Upsert в admin_sessions (telegram_id, panel_url, encrypted_credentials)
  4. Записывает в audit log
Бот: при следующем запросе к панели читает свежие данные из admin_sessions
```

### Сценарий 4: Admin сохраняет токен config-бота

```
Admin: вводит токен своего config-бота в поле "Config Bot Token" на странице Settings
API: PUT /api/settings { config_bot_token: "..." }
Мини-апп: шифрует токен, сохраняет в Admin.config_bot_token_encrypted
Config-бот этого admin: при старте читает свой токен из Admin-записи
```

---

## API-контракт

### `GET /api/settings` — личные настройки текущего администратора

**Response 200:**
```json
{
  "panel_url": "https://panel.example.com",
  "panel_sub_url": "https://panel.example.com:2096",
  "panel_username": "admin",
  "has_panel_password": true,
  "has_config_bot_token": false,
  "updated_at": "2026-03-07T12:00:00Z"
}
```

### `PUT /api/settings` — обновить личные настройки

**Request:**
```json
{
  "panel_url": "https://...",
  "panel_sub_url": "https://...",
  "panel_username": "...",
  "panel_password": "plaintext",
  "config_bot_token": "plaintext_token"
}
```

**Response 200:** аналогично GET

**Errors:**
- `400` — нет полей для обновления
- `403` — не авторизован

### `POST /api/settings/check` — тест подключения к панели

Берёт credentials из текущего `Admin` (не из `BotSettings`).

**Response 200:**
```json
{
  "success": true,
  "message": "Connected successfully",
  "response_time_ms": 142
}
```

### `GET /api/settings/global` — глобальные настройки (только owner)

**Response 200:**
```json
{
  "owner_id": 123456789,
  "client_bot_token_masked": "****abcd",
  "updated_at": "2026-03-07T12:00:00Z"
}
```

### `PUT /api/settings/global` — обновить глобальные настройки (только owner)

**Request:**
```json
{
  "owner_id": 123456789,
  "client_bot_token": "plaintext_token"
}
```

**Response 200:** аналогично GET

---

## Технические решения

### Синхронизация через общую БД (без internal HTTP API)

Оба сервиса подключены к одной PostgreSQL через один `DATABASE_URL` и один
`FERNET_KEY`. Admin-mini-app при `PUT /api/settings` пишет в `admin_sessions`
напрямую через ту же async-сессию SQLAlchemy. Это атомарно (одна транзакция)
и не требует дополнительной инфраструктуры.

### Модель AdminSession в admin-mini-app

Таблица `admin_sessions` создана ботом. Admin-mini-app нужно либо:
- Добавить зеркальную SQLAlchemy-модель `AdminSession` в
  `admin-mini-app/backend/db/models.py` (без `__table_args__` с
  `extend_existing`), либо
- Использовать `Table` через `MetaData` (reflected), либо
- Использовать `text()` запросы.

Рекомендуется: добавить полноценную модель `AdminSession` в models.py
admin-mini-app (она читает существующую таблицу, не создаёт новую — Alembic
`autogenerate` не будет её трогать, так как таблица уже существует).

### Шифрование credentials в Admin

Используется тот же `FERNET_KEY`, что и в `AdminSession` бота. Функции
`encrypt`/`decrypt` из `admin-mini-app/backend/utils/crypto.py`.

### Обратная совместимость BotSettings

Таблицу `bot_settings` **не удаляем** — она хранит глобальные настройки
(`client_bot_token` admin-бота, `owner_id`). Личные настройки панели
переносятся в `Admin`. `GET /api/settings` теперь читает `Admin`, а не
`BotSettings`.

### `User.is_admin` как денормализованный флаг

Флаг обновляется один раз при первом входе owner. Бот может использовать его
для быстрой проверки без JOIN с `admins`. Полноценный reconciler при старте
бота — вне скоупа этой задачи.

---

## Критерии приёмки

### Бот
- [ ] Бот проверяет права через таблицу `admins` (прямой SELECT)
- [ ] `/setadmin`, `/rmadmin`, `/admins` выводят deprecated-сообщение
- [ ] `/admin` (FSM) работает как запасной способ с подсказкой про мини-апп
- [ ] `bot/config.py` не содержит `INTERNAL_API_KEY`, `INTERNAL_API_PORT`
- [ ] `bot/internal_api.py` не создан

### Админ-бэк
- [ ] `GET /api/settings` читает из полей `Admin`, а не `BotSettings`
- [ ] `PUT /api/settings` обновляет поля `Admin` и пишет в `admin_sessions`
      в одной транзакции
- [ ] `POST /api/settings/check` тестирует credentials из `Admin`
- [ ] `GET/PUT /api/settings/global` читает/пишет `BotSettings`, только owner
- [ ] `username` сохраняется/обновляется в `Admin` при каждом входе из initData
- [ ] `router_admins.py` не создан (управление admin-пользователями — вне скоупа)

### Shared / Миграции
- [ ] Миграция применяется без потери данных
- [ ] Существующие `Admin`-записи корректны (новые поля nullable)
- [ ] `Admin` содержит поля: `panel_url`, `panel_username`,
      `panel_password_encrypted`, `panel_sub_url`,
      `config_bot_token_encrypted`, `username`

---

## Вне скоупа

- Страница "Administrators" в мини-апп и CRUD администраторов через API
  (`router_admins.py`) — отдельная задача в будущем
- Startup-reconciler (сверка `admins` vs `User.is_admin` при старте бота)
- Удаление таблицы `bot_settings`
- Перенос управления подпиской/конфигами на per-admin панель
- Internal HTTP API в боте (`bot/internal_api.py`, `INTERNAL_API_KEY`)
- `schemas/admin.py` и CRUD-эндпоинты для admin-пользователей
