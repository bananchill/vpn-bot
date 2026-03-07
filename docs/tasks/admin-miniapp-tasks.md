# Telegram Admin Mini App — Спецификация задач

## Общий контекст

**Проект:** Админ-панель как Telegram Mini App для управления VPN/proxy-сервисом.

**Что уже есть:**
- Клиентский бот (работает, трогать не нужно)
- PostgreSQL база данных (существующая)
- Панель управления конфигами (внешний сервис с API)

**Архитектура:**

```
┌─────────────────────────────────────────────────┐
│  Telegram                                       │
│  ┌───────────────┐                              │
│  │  Admin Bot     │── кнопка "Открыть админку" ─┤
│  │  (aiogram)     │                              │
│  └───────────────┘                              │
│         │                                        │
│  ┌──────▼──────────────────────────────┐        │
│  │  Mini App (WebApp)                   │        │
│  │  Vue 3 + Tailwind + Telegram SDK     │        │
│  │  SPA внутри Telegram                 │        │
│  └──────┬──────────────────────────────┘        │
└─────────┼───────────────────────────────────────┘
          │ REST API (JSON)
          │ Authorization: initData из Telegram
          │
┌─────────▼──────────────────────────────┐
│  Backend (FastAPI)                      │
│  ├── /api/auth      — валидация initData│
│  ├── /api/settings  — настройки бота    │
│  ├── /api/users     — пользователи      │
│  ├── /api/configs   — конфиги VPN       │
│  ├── /api/promos    — промокоды         │
│  ├── /api/stats     — статистика        │
│  ├── /api/logs      — логи действий     │
│  └── /api/admins    — управление админами│
│         │                               │
│  ┌──────▼─────┐   ┌──────────────┐     │
│  │ PostgreSQL  │   │  VPN Panel   │     │
│  │   (БД)      │   │  (внешний)   │     │
│  └────────────┘   └──────────────┘     │
└─────────────────────────────────────────┘
```

---

## Стек

**Бэкенд:**
- Python 3.11+
- FastAPI + uvicorn
- SQLAlchemy 2.x + asyncpg
- alembic (миграции)
- aiohttp (HTTP-клиент к панели)
- aiogram 3.x (минимально — только кнопка открытия Mini App)
- cryptography (Fernet для шифрования)
- pydantic v2 (схемы запросов/ответов)

**Фронтенд:**
- Vue 3 (Composition API, `<script setup>`)
- Vite (сборка)
- Tailwind CSS
- Vue Router (SPA навигация)
- Pinia (стейт-менеджер)
- @twa-dev/sdk (Telegram WebApp SDK)
- axios (HTTP-клиент)
- fsd (Архитектура)

**Конфигурация `.env`** (только для запуска):
```
DATABASE_URL=postgresql+asyncpg://...
ADMIN_BOT_TOKEN=...
FERNET_KEY=...
WEBAPP_URL=https://your-domain.com   # URL где хостится Mini App
```

Все панельные настройки (PANEL_URL, credentials, OWNER_ID, CLIENT_BOT_TOKEN) — **только в БД**, настраиваются через UI Mini App.

---

## Структура проекта

```
admin-mini-app/
├── backend/
│   ├── main.py                    # FastAPI app + uvicorn
│   ├── config.py                  # Загрузка .env
│   ├── requirements.txt
│   ├── alembic/
│   │   └── versions/
│   ├── alembic.ini
│   ├── bot/
│   │   ├── __init__.py
│   │   └── bot.py                 # aiogram — только /start + WebApp кнопка
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py              # async engine + sessionmaker
│   │   ├── models.py              # SQLAlchemy модели
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── user_repo.py
│   │       ├── config_repo.py
│   │       ├── promo_repo.py
│   │       ├── settings_repo.py
│   │       ├── log_repo.py
│   │       ├── admin_repo.py
│   │       └── stats_repo.py
│   ├── panel/
│   │   ├── __init__.py
│   │   └── client.py             # HTTP-клиент VPN панели
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py               # Dependency injection (get_db, get_current_admin)
│   │   ├── auth.py               # Валидация Telegram initData
│   │   ├── router_settings.py
│   │   ├── router_users.py
│   │   ├── router_configs.py
│   │   ├── router_promos.py
│   │   ├── router_stats.py
│   │   ├── router_logs.py
│   │   └── router_admins.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── settings.py           # Pydantic-схемы настроек
│   │   ├── user.py
│   │   ├── config.py
│   │   ├── promo.py
│   │   ├── stats.py
│   │   ├── log.py
│   │   └── admin.py
│   └── utils/
│       ├── __init__.py
│       ├── crypto.py             # Fernet encrypt/decrypt
│       └── scheduler.py          # APScheduler задачи
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── src/
│   │   ├── main.js               # Vue app init + Telegram SDK init
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.js          # Vue Router
│   │   ├── stores/
│   │   │   ├── auth.js           # Pinia: auth стейт + initData
│   │   │   ├── settings.js
│   │   │   ├── users.js
│   │   │   └── promos.js
│   │   ├── api/
│   │   │   └── client.js         # axios instance + initData header
│   │   ├── views/
│   │   │   ├── DashboardView.vue     # Главная / статистика
│   │   │   ├── SettingsView.vue      # Настройки подключения
│   │   │   ├── UsersListView.vue     # Список пользователей
│   │   │   ├── UserDetailView.vue    # Карточка пользователя
│   │   │   ├── PromosListView.vue    # Список промокодов
│   │   │   ├── PromoCreateView.vue   # Создание промокода
│   │   │   ├── PromoDetailView.vue   # Детали промокода
│   │   │   ├── LogsView.vue          # Логи действий
│   │   │   └── AdminsView.vue        # Управление админами
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── AppNavbar.vue         # Нижняя навигация
│   │   │   │   ├── AppHeader.vue         # Верхняя шапка с заголовком + back
│   │   │   │   ├── ToggleSwitch.vue      # Свитчер вкл/выкл
│   │   │   │   ├── StatusBadge.vue       # Бейдж статуса (оплачен/нет)
│   │   │   │   ├── Pagination.vue        # Пагинация
│   │   │   │   ├── SearchInput.vue       # Поле поиска
│   │   │   │   ├── FilterBar.vue         # Панель фильтров
│   │   │   │   ├── EmptyState.vue        # Заглушка "нет данных"
│   │   │   │   ├── LoadingSpinner.vue    # Индикатор загрузки
│   │   │   │   └── ConfirmModal.vue      # Модалка подтверждения
│   │   │   ├── users/
│   │   │   │   ├── UserCard.vue          # Карточка в списке
│   │   │   │   ├── UserInfo.vue          # Блок информации
│   │   │   │   └── ConfigList.vue        # Список конфигов со свитчерами
│   │   │   ├── promos/
│   │   │   │   ├── PromoCard.vue         # Карточка промокода в списке
│   │   │   │   └── PromoForm.vue         # Форма создания
│   │   │   └── settings/
│   │   │       ├── SettingsForm.vue      # Форма настроек
│   │   │       └── ConnectionStatus.vue  # Статус подключения к панели
│   │   └── assets/
│   │       └── styles/
│   │           └── main.css          # Tailwind imports + кастомные стили
│   └── public/
│
├── docker-compose.yml            # backend + frontend + nginx
├── nginx.conf                    # Проксирование /api → backend, / → frontend
└── README.md
```

---

## Авторизация через Telegram initData

**Принцип:** Telegram Mini App при открытии передаёт `initData` — подписанную строку с данными пользователя. Бэкенд валидирует подпись через `ADMIN_BOT_TOKEN`.

**Фронтенд (`api/client.js`):**
```javascript
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use(config => {
  const initData = window.Telegram?.WebApp?.initData
  if (initData) {
    config.headers['X-Telegram-Init-Data'] = initData
  }
  return config
})
```

**Бэкенд (`api/auth.py`):**
```python
import hashlib, hmac, json
from urllib.parse import parse_qs

def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Валидирует initData из Telegram WebApp.
    Возвращает данные пользователя или None если невалидно.
    """
    parsed = dict(parse_qs(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        return None

    # Собрать строку для проверки
    data_check = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )

    # HMAC-SHA256
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        return None

    user_data = json.loads(parsed.get("user", ["{}"])[0])
    return user_data
```

**Бэкенд (`api/deps.py`) — dependency:**
```python
async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Admin:
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    settings = await settings_repo.get_settings(db)
    user_data = validate_init_data(init_data, settings.client_bot_token or BOT_TOKEN)
    if not user_data:
        raise HTTPException(401, "Invalid initData")

    telegram_id = user_data["id"]

    # Проверить, является ли админом
    admin = await admin_repo.get_by_telegram_id(db, telegram_id)
    if not admin:
        # Если первый запуск и нет админов — сделать owner
        admin_count = await admin_repo.count(db)
        if admin_count == 0:
            admin = await admin_repo.create(db, telegram_id, role="owner")
        else:
            raise HTTPException(403, "Not an admin")

    return admin
```

---

## Модели БД

```python
# === Этап 1 ===

class BotSettings(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    panel_url: Mapped[str | None]
    panel_sub_url: Mapped[str | None]
    panel_username: Mapped[str | None]
    panel_password: Mapped[str | None]       # Fernet encrypted
    owner_id: Mapped[int | None] = mapped_column(BigInteger)
    client_bot_token: Mapped[str | None]     # Fernet encrypted
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None]
    first_name: Mapped[str | None]
    photo_url: Mapped[str | None]
    is_paid: Mapped[bool] = mapped_column(default=False)
    subscription_expires: Mapped[datetime | None]
    subscribed_since: Mapped[datetime | None]
    is_blocked: Mapped[bool] = mapped_column(default=False)
    admin_note: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    configs: Mapped[list["VPNConfig"]] = relationship(back_populates="user")


class VPNConfig(Base):
    __tablename__ = "vpn_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    panel_config_id: Mapped[str]
    name: Mapped[str]
    is_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="configs")


# === Этап 2 ===

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    discount_percent: Mapped[int]
    max_activations: Mapped[int]
    current_activations: Mapped[int] = mapped_column(default=0)
    valid_until: Mapped[datetime]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PromoUsage(Base):
    __tablename__ = "promo_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    used_at: Mapped[datetime] = mapped_column(server_default=func.now())


# === Этап 3 ===

class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str]
    target: Mapped[str | None]
    details: Mapped[str | None]               # JSON
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    role: Mapped[str]                         # "owner" | "moderator"
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

---

---

# ЭТАП 1 — Каркас + настройки + пользователи + конфиги

---

## Задача 1.1: Инициализация бэкенда

**Цель:** FastAPI-приложение, подключение к БД, миграции, минимальный Telegram-бот.

**Что сделать:**

1. Создать структуру `backend/` (см. "Структура проекта").
2. `requirements.txt`:
   ```
   fastapi
   uvicorn[standard]
   sqlalchemy[asyncio]
   asyncpg
   alembic
   aiohttp
   aiogram==3.x
   python-dotenv
   cryptography
   pydantic>=2.0
   ```
3. `config.py` — загрузка `DATABASE_URL`, `ADMIN_BOT_TOKEN`, `FERNET_KEY`, `WEBAPP_URL` из `.env`.
4. `db/engine.py` — async engine + sessionmaker.
5. `db/models.py` — модели `BotSettings`, `User`, `VPNConfig`, `Admin`.
6. Alembic: настроить async, первая миграция, применить.
7. `main.py`:
   - FastAPI app с CORS (разрешить origin = `WEBAPP_URL`).
   - Lifespan: при старте запускать aiogram polling в фоновой задаче.
   - Подключение роутеров.
   - Раздача фронтенда как static files (или через nginx).
8. `bot/bot.py`:
   - `/start` — отправляет сообщение с `WebAppInfo` кнопкой:
     ```python
     WebAppInfo(url=f"{WEBAPP_URL}")
     ```
   - Больше ничего. Никаких inline-кнопок, FSM, хэндлеров.
9. `api/deps.py`:
   - `get_db()` — async session dependency.
   - `get_current_admin()` — валидация initData + проверка admin (см. раздел "Авторизация").
10. `api/auth.py` — функция `validate_init_data()`.

**Критерии готовности:**
- `uvicorn main:app` запускается
- Бот отправляет кнопку открытия Mini App при `/start`
- `GET /api/health` возвращает 200
- Миграция применяется
- initData валидация работает (тест с реальным Telegram)

---

## Задача 1.2: Инициализация фронтенда

**Цель:** Vue 3 SPA, подключение Telegram SDK, навигация, базовый layout.

**Что сделать:**

1. Инициализировать проект:
   ```bash
   npm create vite@latest frontend -- --template vue
   cd frontend
   npm install vue-router@4 pinia axios @twa-dev/sdk
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

2. `src/main.js`:
   ```javascript
   import { createApp } from 'vue'
   import { createPinia } from 'pinia'
   import WebApp from '@twa-dev/sdk'
   import App from './App.vue'
   import router from './router'

   WebApp.ready()
   WebApp.expand()  // Развернуть на весь экран

   const app = createApp(App)
   app.use(createPinia())
   app.use(router)
   app.mount('#app')
   ```

3. `src/api/client.js` — axios instance с `X-Telegram-Init-Data` заголовком.

4. `src/router/index.js`:
   ```javascript
   const routes = [
     { path: '/', name: 'dashboard', component: DashboardView },
     { path: '/settings', name: 'settings', component: SettingsView },
     { path: '/users', name: 'users', component: UsersListView },
     { path: '/users/:id', name: 'user-detail', component: UserDetailView },
     { path: '/promos', name: 'promos', component: PromosListView },
     { path: '/promos/create', name: 'promo-create', component: PromoCreateView },
     { path: '/promos/:id', name: 'promo-detail', component: PromoDetailView },
     { path: '/logs', name: 'logs', component: LogsView },
     { path: '/admins', name: 'admins', component: AdminsView },
   ]
   ```

5. `src/App.vue`:
   - `<AppHeader>` сверху (заголовок страницы + кнопка назад через `WebApp.BackButton`).
   - `<router-view>` — основной контент.
   - `<AppNavbar>` снизу — нижняя навигация:
     ```
     [🏠 Главная] [👥 Юзеры] [🏷 Промо] [⚙️ Ещё]
     ```

6. **Telegram WebApp BackButton:**
   ```javascript
   // В router/index.js
   router.afterEach((to, from) => {
     if (to.path === '/') {
       WebApp.BackButton.hide()
     } else {
       WebApp.BackButton.show()
       WebApp.BackButton.onClick(() => router.back())
     }
   })
   ```

7. **Тема Telegram:** использовать CSS-переменные Telegram для цветов:
   ```css
   :root {
     --tg-theme-bg-color: var(--tg-theme-bg-color, #ffffff);
     --tg-theme-text-color: var(--tg-theme-text-color, #000000);
     --tg-theme-hint-color: var(--tg-theme-hint-color, #999999);
     --tg-theme-link-color: var(--tg-theme-link-color, #2481cc);
     --tg-theme-button-color: var(--tg-theme-button-color, #2481cc);
     --tg-theme-button-text-color: var(--tg-theme-button-text-color, #ffffff);
     --tg-theme-secondary-bg-color: var(--tg-theme-secondary-bg-color, #f0f0f0);
   }
   ```
   Tailwind config — подключить эти переменные как цвета:
   ```javascript
   // tailwind.config.js
   module.exports = {
     theme: {
       extend: {
         colors: {
           tg: {
             bg: 'var(--tg-theme-bg-color)',
             text: 'var(--tg-theme-text-color)',
             hint: 'var(--tg-theme-hint-color)',
             link: 'var(--tg-theme-link-color)',
             button: 'var(--tg-theme-button-color)',
             'button-text': 'var(--tg-theme-button-text-color)',
             'secondary-bg': 'var(--tg-theme-secondary-bg-color)',
           }
         }
       }
     }
   }
   ```

8. UI-компоненты (заглушки, стилизовать позже):
   - `LoadingSpinner.vue`
   - `EmptyState.vue`
   - `ConfirmModal.vue`
   - `ToggleSwitch.vue`
   - `StatusBadge.vue`
   - `Pagination.vue`
   - `SearchInput.vue`

**Критерии готовности:**
- Mini App открывается из Telegram
- Навигация между страницами работает
- BackButton Telegram корректно работает (показывается/скрывается)
- Цвета адаптируются под тему Telegram (светлая/тёмная)
- Нижняя навигация отображается и переключает страницы

---

## Задача 1.3: Настройки бота (Settings)

### Бэкенд

**API эндпоинты:**

```
GET    /api/settings              — получить текущие настройки
PUT    /api/settings              — обновить настройки
POST   /api/settings/check        — проверить подключение к панели
```

**Pydantic-схемы (`schemas/settings.py`):**
```python
class SettingsResponse(BaseModel):
    panel_url: str | None
    panel_sub_url: str | None
    panel_username: str | None
    has_password: bool              # True если пароль задан (не показывать сам пароль!)
    owner_id: int | None
    client_bot_token_masked: str | None   # "••••last4"
    updated_at: datetime | None

class SettingsUpdate(BaseModel):
    panel_url: str | None = None
    panel_sub_url: str | None = None
    panel_username: str | None = None
    panel_password: str | None = None       # Открытый текст → бэкенд шифрует
    owner_id: int | None = None
    client_bot_token: str | None = None     # Открытый текст → бэкенд шифрует

class ConnectionCheckResponse(BaseModel):
    success: bool
    message: str
    response_time_ms: int | None
```

**Что сделать:**

1. `api/router_settings.py`:
   - `GET /settings` — вернуть настройки, пароль и токен замаскированы.
   - `PUT /settings` — обновить. Шифровать пароль/токен через Fernet перед сохранением.
   - `POST /settings/check` — создать `PanelClient`, вызвать `check_connection()`, вернуть результат.
   - **Доступ: только role="owner".**

2. `db/repositories/settings_repo.py`:
   - `get_settings(db) -> BotSettings | None`
   - `upsert_settings(db, **kwargs) -> BotSettings`

3. `utils/crypto.py`:
   - `encrypt(value: str) -> str`
   - `decrypt(value: str) -> str`

### Фронтенд

**`views/SettingsView.vue`:**

Форма с полями:
- Panel URL (text input)
- Sub URL (text input)
- Panel Username (text input)
- Panel Password (password input, показывать "••••last4" если задан)
- Owner ID (number input, по умолчанию = текущий admin)
- Client Bot Token (password input, аналогично)
- Кнопка "Проверить подключение" → показать ✅/❌ + время ответа
- Кнопка "Сохранить"

**Компонент `ConnectionStatus.vue`:**
- Индикатор: 🟢 Подключено / 🔴 Ошибка / ⚪ Не проверено
- Время ответа панели

**Критерии готовности:**
- Все настройки сохраняются в БД через API
- Пароль/токен не передаются обратно в открытом виде
- Проверка подключения реально делает запрос к панели
- Форма показывает текущие значения при загрузке
- Только owner видит раздел настроек

---

## Задача 1.4: Клиент панели

**Идентично предыдущей версии.** Класс `PanelClient` в `panel/client.py`.

```python
class PanelClient:
    def __init__(self, base_url: str, username: str, password: str): ...
    async def login(self) -> str: ...
    async def get_users(self) -> list[dict]: ...
    async def get_user_configs(self, user_id: str) -> list[dict]: ...
    async def enable_config(self, config_id: str) -> bool: ...
    async def disable_config(self, config_id: str) -> bool: ...
    async def disable_all_user_configs(self, user_id: str) -> bool: ...
    async def enable_all_user_configs(self, user_id: str) -> bool: ...
    async def check_connection(self) -> tuple[bool, str]: ...
```

- Auto re-login при 401.
- Таймаут 10 секунд.
- Логирование через `logging`.
- Настройки читать из БД (через dependency).

**Примечание:** Эндпоинты зависят от панели (Marzban, 3x-ui и т.д.). Уточнить у заказчика.

**Критерии готовности:**
- Все методы реализованы
- Auto re-login работает
- Ошибки обрабатываются gracefully

---

## Задача 1.5: Список пользователей

### Бэкенд

**API эндпоинты:**

```
GET    /api/users                 — список пользователей (пагинация, поиск)
GET    /api/users/:id             — детали пользователя
PATCH  /api/users/:id/block       — заблокировать/разблокировать
PATCH  /api/users/:id/note        — обновить заметку
PATCH  /api/users/:id/extend      — продлить подписку
```

**Query-параметры для `GET /api/users`:**
```
?page=1
&per_page=20
&search=ivan                      # по username, first_name, telegram_id
&is_paid=true|false
&subscription=active|expired|expiring_7d
&sort_by=created_at|first_name|subscription_expires
&sort_order=asc|desc
```

**Pydantic-схемы (`schemas/user.py`):**
```python
class UserShort(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    photo_url: str | None
    is_paid: bool
    is_blocked: bool
    subscription_expires: datetime | None

class UserDetail(UserShort):
    subscribed_since: datetime | None
    days_subscribed: int | None
    admin_note: str | None
    configs: list[ConfigResponse]
    promo_usages: list[PromoUsageResponse]   # Этап 2, пока пустой список

class UserListResponse(BaseModel):
    items: list[UserShort]
    total: int
    page: int
    per_page: int
    pages: int
```

### Фронтенд

**`views/UsersListView.vue`:**
- Поисковая строка сверху (debounce 300ms).
- Фильтры: чипсы/кнопки (Все / Оплачено / Не оплачено / Истекает).
- Список карточек пользователей — каждая кликабельна.
- Пагинация внизу.
- Pull-to-refresh (Telegram haptic feedback).

**`components/users/UserCard.vue`:**
- Аватар (круглый, fallback — инициалы).
- Имя + @username.
- Бейдж статуса оплаты (зелёный/красный).
- Дата истечения подписки.

**Критерии готовности:**
- Список загружается с пагинацией
- Поиск работает (по username, имени, telegram_id)
- Фильтры комбинируются
- При смене фильтра — сброс на первую страницу
- Пустое состояние отображается корректно

---

## Задача 1.6: Карточка пользователя и управление конфигами

### Бэкенд

**API эндпоинты:**

```
GET    /api/users/:id/configs                — конфиги пользователя (из БД + sync с панелью)
PATCH  /api/configs/:id/toggle               — вкл/выкл конфиг
POST   /api/users/:id/configs/toggle-all     — вкл/выкл все конфиги
```

**Pydantic-схемы (`schemas/config.py`):**
```python
class ConfigResponse(BaseModel):
    id: int
    panel_config_id: str
    name: str
    is_enabled: bool
    created_at: datetime

class ConfigToggle(BaseModel):
    enabled: bool

class ConfigToggleAllRequest(BaseModel):
    enabled: bool

class ConfigToggleAllResponse(BaseModel):
    updated_count: int
    success: bool
```

### Фронтенд

**`views/UserDetailView.vue`:**

Макет:
```
┌─────────────────────────────┐
│  ← Назад      Карточка       │
├─────────────────────────────┤
│  [Аватар]  Иван Иванов      │
│            @ivan             │
│            tg://user?id=...  │
├─────────────────────────────┤
│  💰 Статус: Оплачено  ✅     │
│  📅 До: 15.03.2026          │
│  ⏱ Подписан: 347 дней       │
├─────────────────────────────┤
│  📝 Заметка: VIP клиент     │
│     [Редактировать]          │
├─────────────────────────────┤
│  Конфиги          [ВСЕ 🔄]  │
│  ┌─────────────────────┐    │
│  │ config-1      [🟢]  │    │
│  │ config-2      [🟢]  │    │
│  │ config-3      [🔴]  │    │
│  └─────────────────────┘    │
├─────────────────────────────┤
│  [🚫 Заблокировать]         │
│  [📅 Продлить подписку]     │
└─────────────────────────────┘
```

**Компоненты:**
- `UserInfo.vue` — блок с инфой (аватар, имя, статусы).
- `ConfigList.vue` — список конфигов с `ToggleSwitch` для каждого + общий свитчер.

**Поведение свитчеров:**
1. При нажатии — оптимистичное обновление UI (сразу переключить).
2. Запрос к API → панели.
3. Если ошибка — откатить UI обратно + показать toast с ошибкой.
4. Telegram haptic feedback при переключении.

**Критерии готовности:**
- Вся информация о пользователе отображается
- Свитчеры работают с оптимистичным обновлением
- При ошибке панели — откат + понятное сообщение
- Общий свитчер переключает все конфиги
- Ссылка на Telegram профиль работает
- Блокировка/разблокировка работает
- Заметка редактируется inline
- Продление подписки через модалку с вводом дней

---

## Задача 1.7: Главная страница (Dashboard — заглушка)

**`views/DashboardView.vue`:**

На этом этапе — приветственный экран:
- Имя админа (из Telegram).
- Статус подключения к панели (🟢/🔴).
- Быстрые ссылки: "Пользователи", "Настройки".
- Заглушки для статистики (Этап 3).

При первом входе (нет настроек в БД) — показать onboarding:
```
Добро пожаловать! 👋
Настройте подключение к панели, чтобы начать работу.
[Перейти к настройкам →]
```

**Критерии готовности:**
- Dashboard открывается как главная страница
- Onboarding показывается если настройки пустые
- Статус панели отображается

---

## Задача 1.8: Docker и деплой

**Что сделать:**

1. `backend/Dockerfile`:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. `frontend/Dockerfile`:
   ```dockerfile
   FROM node:20-alpine AS build
   WORKDIR /app
   COPY package*.json .
   RUN npm ci
   COPY . .
   RUN npm run build

   FROM nginx:alpine
   COPY --from=build /app/dist /usr/share/nginx/html
   COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
   ```

3. `docker-compose.yml`:
   ```yaml
   services:
     backend:
       build: ./backend
       env_file: .env
       depends_on:
         - db
       ports:
         - "8000:8000"

     frontend:
       build: ./frontend
       ports:
         - "3000:80"

     nginx:
       image: nginx:alpine
       ports:
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/conf.d/default.conf
         - ./certs:/etc/nginx/certs    # SSL обязателен для Mini App!
       depends_on:
         - backend
         - frontend

     db:
       image: postgres:16-alpine
       environment:
         POSTGRES_DB: admin_bot
         POSTGRES_USER: admin
         POSTGRES_PASSWORD: ${DB_PASSWORD}
       volumes:
         - pgdata:/var/lib/postgresql/data

   volumes:
     pgdata:
   ```

4. `nginx.conf`:
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /etc/nginx/certs/cert.pem;
       ssl_certificate_key /etc/nginx/certs/key.pem;

       location /api/ {
           proxy_pass http://backend:8000/api/;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location / {
           proxy_pass http://frontend:80;
       }
   }
   ```

**ВАЖНО:** Telegram Mini App **требует HTTPS**. SSL-сертификат обязателен.

**Критерии готовности:**
- `docker-compose up` поднимает всё
- Mini App открывается из Telegram по HTTPS
- API доступен через `/api/`
- БД создаётся автоматически

---

---

# ЭТАП 2 — Промокоды

> **Пререквизит:** Этап 1 полностью завершён и протестирован.

---

## Задача 2.1: Миграция БД для промокодов

Добавить модели `PromoCode` и `PromoUsage` → alembic-миграция.

---

## Задача 2.2: API промокодов

**API эндпоинты:**

```
GET    /api/promos                — список (пагинация)
POST   /api/promos                — создать
GET    /api/promos/:id            — детали
PATCH  /api/promos/:id/toggle     — активировать/деактивировать
DELETE /api/promos/:id            — удалить
GET    /api/promos/:id/usages     — кто использовал
POST   /api/promos/generate-code  — сгенерировать уникальный код
```

**Pydantic-схемы (`schemas/promo.py`):**
```python
class PromoCreate(BaseModel):
    code: str = Field(max_length=32, pattern=r'^[A-Z0-9]+$')
    discount_percent: int = Field(ge=1, le=100)
    max_activations: int = Field(ge=1)
    valid_days: int | None = None        # "30 дней" → вычислить valid_until
    valid_until: datetime | None = None  # Или конкретная дата

class PromoResponse(BaseModel):
    id: int
    code: str
    discount_percent: int
    max_activations: int
    current_activations: int
    valid_until: datetime
    is_active: bool
    is_expired: bool                     # computed: valid_until < now
    created_at: datetime

class PromoListResponse(BaseModel):
    items: list[PromoResponse]
    total: int
    page: int
    per_page: int

class PromoUsageResponse(BaseModel):
    user_id: int
    username: str | None
    first_name: str | None
    used_at: datetime

class GenerateCodeResponse(BaseModel):
    code: str
```

**Репозиторий `promo_repo.py`:**
- `use_promo(db, promo_id, user_id)` — **атомарный** (SELECT FOR UPDATE + проверка лимита + инкремент).

---

## Задача 2.3: Фронтенд промокодов

**`views/PromosListView.vue`:**
- Список карточек промокодов.
- Кнопка "+ Создать" (FAB или в хедере).
- Каждая карточка: код, скидка %, использований X/Y, срок, статус.

**`views/PromoCreateView.vue`:**
- Форма:
  - Код: текстовое поле + кнопка "🎲 Сгенерировать" (запрос к `/api/promos/generate-code`).
  - Скидка %: числовой инпут + слайдер.
  - Количество активаций: числовой инпут.
  - Срок: выбор "7 дней / 14 дней / 30 дней / 90 дней / Своя дата".
  - Кнопка "Создать" — валидация на фронте + запрос.

**`views/PromoDetailView.vue`:**
- Полная информация о промокоде.
- Прогресс-бар использований (X/Y).
- Список использовавших пользователей (кликабельные → переход в UserDetail).
- Кнопка "Деактивировать" / "Активировать" (toggle).
- Кнопка "Удалить" → `ConfirmModal`.

**Критерии готовности:**
- Создание с валидацией (код уникален, скидка 1-100, срок в будущем)
- Генератор кодов работает
- Деактивированный промокод отображается серым
- Удаление требует подтверждения
- Список использовавших загружается с пагинацией

---

## Задача 2.4: Расширенный поиск пользователей

Добавить к `UsersListView.vue`:

**`components/ui/FilterBar.vue`:**
- Горизонтальная полоса с чипсами-фильтрами.
- Статус оплаты: Все / Оплачено / Не оплачено.
- Подписка: Все / Активна / Истекла / Истекает в 7 дней.
- Сортировка: dropdown (По дате / По имени / По сроку подписки).

**Поведение:**
- Фильтры передаются как query-параметры в API.
- При смене фильтра — сброс на page=1.
- Состояние фильтров сохраняется в Pinia store (не теряется при навигации).

---

---

# ЭТАП 3 — Дашборд, логи, уведомления, мультиадмин

> **Пререквизит:** Этапы 1 и 2 полностью завершены.

---

## Задача 3.1: Миграция БД

Добавить модель `AdminLog` → alembic-миграция. Модель `Admin` уже создана в Этапе 1.

---

## Задача 3.2: Логирование действий

### Бэкенд

**API:**
```
GET /api/logs?page=1&per_page=20&action=disable_config&admin_id=123
```

**Что логировать:** каждое мутирующее действие (изменение настроек, toggle конфигов, блокировка, промокоды, продление подписки).

**Реализация:** добавить вызов `log_repo.log_action(...)` во все существующие роутеры, где происходят мутации.

### Фронтенд

**`views/LogsView.vue`:**
- Таблица/список логов: дата, админ, действие, цель, детали.
- Фильтр по типу действия (dropdown).
- Пагинация.

---

## Задача 3.3: Дашборд (статистика)

### Бэкенд

**API:**
```
GET /api/stats/dashboard
```

**Response:**
```python
class DashboardStats(BaseModel):
    total_users: int
    paid_users: int
    unpaid_users: int
    expiring_7d: int
    active_configs: int
    active_promos: int
    new_users_30d: int
    panel_status: bool
```

Один SQL-запрос с `func.count` + `case`.

### Фронтенд

Обновить `DashboardView.vue`:
- Карточки со статистикой (сетка 2x2 или 2x4).
- Каждая карточка — число + подпись + иконка.
- Цвета: зелёный для позитивных, красный для проблемных.
- Статус панели: 🟢/🔴 с временем последнего ответа.

---

## Задача 3.4: Автоматические уведомления

**В боте (не в Mini App!)** — потому что уведомления приходят как сообщения в Telegram.

Использовать `apscheduler`:
- `check_expiring_subscriptions` — cron ежедневно 09:00. Отправить сообщение OWNER_ID: "⚠️ У 12 пользователей подписка истекает в ближайшие 3 дня".
- `check_panel_health` — interval каждые 5 мин. Если панель упала — сообщение (не чаще раза в час). Если восстановилась — "✅ Панель снова доступна".
- Дедупликация: таблица `notifications_sent` или in-memory dict.

---

## Задача 3.5: Управление админами

### Бэкенд

**API:**
```
GET    /api/admins              — список админов
POST   /api/admins              — добавить (только owner)
DELETE /api/admins/:id          — удалить (только owner, нельзя удалить себя)
PATCH  /api/admins/:id/role     — изменить роль (только owner)
```

**Роли:**
- `owner` — полный доступ.
- `moderator` — всё кроме настроек и управления админами.

В `get_current_admin()` dependency добавить поле `role` → проверять в роутерах через дополнительный dependency `require_owner`.

### Фронтенд

**`views/AdminsView.vue`:**
- Список админов: имя, @username, роль, дата добавления.
- Кнопка "Добавить модератора" → ввод telegram_id.
- Кнопка удаления (с подтверждением).
- Этот раздел **не показывается** модераторам (скрыть из навигации).

**Навигация:** в `AppNavbar.vue` пункт "⚙️ Ещё" открывает подменю:
- Настройки (только owner)
- Логи
- Админы (только owner)

---

---

# Общие требования

## Бэкенд
- Type hints везде
- Pydantic v2 для всех request/response
- Логирование через `logging`
- Обработка ошибок: HTTPException с понятными сообщениями
- Все секреты шифруются Fernet перед сохранением в БД
- initData валидация на каждый запрос
- Атомарность `use_promo` (SELECT FOR UPDATE)

## Фронтенд
- Composition API + `<script setup>` везде
- Tailwind для стилей, цвета через Telegram CSS-переменные
- Pinia для стейта
- Axios interceptors для авторизации и обработки ошибок
- Оптимистичные обновления для свитчеров
- Telegram haptic feedback (`WebApp.HapticFeedback`) на действиях
- Загрузочные состояния (skeleton/spinner)
- Пустые состояния ("Нет пользователей", "Нет промокодов")
- Обработка ошибок: toast-уведомления при ошибках API
- Адаптация под мобильный экран (Mini App = телефон)

## Деплой
- Docker Compose для всех сервисов
- HTTPS обязателен (Telegram требует)
- nginx как reverse proxy
- Автоматические миграции при старте бэкенда

## Тестирование
- pytest + httpx для API-тестов
- Mocker для PanelClient
- Фронтенд: базовые тесты компонентов (vitest)
