# TASK-017: Логи, промокоды и статистика использования в Admin Mini App

**Статус:** ⏳ Ожидает апрува
**Приоритет:** Высокий
**Дата:** 2026-03-05
**Зоны:** Shared — модели БД / Админ-бэк / Админ-фронт

---

## Описание

Реализовать три функциональных блока в Admin Mini App, которые сейчас существуют только как заглушки в `admin-mini-app/frontend/src/views/`:

1. **Логи** — журнал действий администраторов (блокировки, продления подписок, изменения настроек, операции с конфигами). Нужна модель `AdminLog`, API-эндпоинт с фильтрацией и страница `LogsView.vue`.
2. **Промокоды** — полный CRUD: создание со скидкой в процентах и ограничением активаций, список, детальная страница с историей применений, удаление. Нужны модели `PromoCode` + `PromoUsage`, API и три view-заглушки.
3. **Статистика использования** — расширить дашборд дополнительными метриками: новые пользователи за 30 дней, активные промокоды, распределение по статусам подписки.

---

## Пайплайн выполнения

| # | Агент | Что делает | Зависит от |
|---|---|---|---|
| 1 | `developer` | Добавляет модели `PromoCode`, `PromoUsage`, `AdminLog` в `db/models.py`; создаёт миграцию | — |
| 2 | `admin-api` | Реализует роутеры: `router_logs.py`, `router_promos.py`; расширяет `router_dashboard.py` и `router_users.py`; добавляет логирование в существующие роутеры | Шаг 1 |
| 3 | `designer` | Рисует макеты в Figma: страницы Логов, Промокодов (список, создание, детали) | — (параллельно с шагами 1-2) |
| 4 | `vue-senior` | Реализует `LogsView.vue`, `PromosListView.vue`, `PromoCreateView.vue`, `PromoDetailView.vue`; расширяет `DashboardView.vue`; создаёт stores и компоненты | Шаги 2, 3 |
| 5 | `qa-admin` | Тестирует API: logs, promos, dashboard stats | Шаг 2 |
| 6 | `review-backend` | Ревью всего бэкенда | Шаг 5 |
| 7 | `review-frontend` | Ревью фронтенда | Шаг 4 |

> Шаги 1 и 3 выполняются параллельно. Шаги 5, 6, 7 можно запустить параллельно.

---

## Что будет сделано

### Shared — модели и БД (developer)

1. Добавить в `admin-mini-app/backend/db/models.py` модели `PromoCode`, `PromoUsage`, `AdminLog` (см. схемы ниже).
2. Создать миграцию Alembic: `alembic revision --autogenerate -m "add promo_codes promo_usages admin_logs"`.
3. Применить миграцию.

### Админ-бэк (admin-api)

1. Создать `admin-mini-app/backend/schemas/promo.py` со схемами `PromoCreate`, `PromoResponse`, `PromoListResponse`, `PromoUsageResponse`, `GenerateCodeResponse`.
2. Создать `admin-mini-app/backend/schemas/log.py` со схемами `LogEntry`, `LogListResponse`.
3. Создать `admin-mini-app/backend/db/repositories/promo_repo.py` с методами CRUD и атомарным `use_promo`.
4. Создать `admin-mini-app/backend/db/repositories/log_repo.py` с методами `log_action` и `get_logs`.
5. Создать `admin-mini-app/backend/api/router_promos.py` — 7 эндпоинтов (см. API-контракт).
6. Создать `admin-mini-app/backend/api/router_logs.py` — 1 эндпоинт `GET /api/logs`.
7. Расширить `admin-mini-app/backend/schemas/dashboard.py` — добавить поля `new_users_30d`, `active_promos`, `unpaid_users` в `DashboardStatsResponse`.
8. Обновить `admin-mini-app/backend/db/repositories/dashboard_repo.py` — добавить запросы для новых метрик.
9. Обновить `admin-mini-app/backend/api/router_dashboard.py` — возвращать расширенную статистику.
10. Добавить вызовы `log_repo.log_action(...)` во все мутирующие эндпоинты: `router_users.py` (block, note, extend), `router_settings.py` (update), `router_configs.py` (toggle, toggle-all), `router_promos.py` (create, toggle, delete).
11. Зарегистрировать новые роутеры в `admin-mini-app/backend/main.py`.

### Дизайн (designer)

1. Страница Логов: список строк (иконка действия, имя/ID админа, текст действия, таргет, дата). Фильтр по типу действия — выпадающий список.
2. Список промокодов: карточки с кодом, скидкой, прогресс-баром использований, статусом, сроком.
3. Создание промокода: форма с полями кода, скидки (слайдер + число), лимита активаций, срока действия (пресеты + свободный ввод), кнопка генерации кода.
4. Детальная страница промокода: полная информация + прогресс-бар + список пользователей, применивших промокод.

### Админ-фронт (vue-senior)

1. Создать `admin-mini-app/frontend/src/stores/promos.js` — стейт списка промокодов, детали, создание, удаление.
2. Создать `admin-mini-app/frontend/src/stores/logs.js` — стейт журнала с пагинацией и фильтром.
3. Создать `admin-mini-app/frontend/src/components/promos/PromoCard.vue` — карточка промокода в списке.
4. Создать `admin-mini-app/frontend/src/components/promos/PromoForm.vue` — форма создания промокода.
5. Реализовать `admin-mini-app/frontend/src/views/PromosListView.vue` — список + кнопка создания.
6. Реализовать `admin-mini-app/frontend/src/views/PromoCreateView.vue` — форма с генератором кода.
7. Реализовать `admin-mini-app/frontend/src/views/PromoDetailView.vue` — детали + история применений + действия.
8. Реализовать `admin-mini-app/frontend/src/views/LogsView.vue` — журнал с фильтром и пагинацией.
9. Расширить `admin-mini-app/frontend/src/stores/dashboard.js` — добавить `new_users_30d`, `active_promos`, `unpaid_users`.
10. Расширить `admin-mini-app/frontend/src/views/DashboardView.vue` — показать новые метрики в сетке карточек.
11. Обновить `admin-mini-app/frontend/src/views/UserDetailView.vue` — блок `promo_usages` (список промокодов, которые применил пользователь).

---

## Какие файлы будут затронуты

### Бэк / Shared

- `admin-mini-app/backend/db/models.py` — изменение: добавить `PromoCode`, `PromoUsage`, `AdminLog`
- `admin-mini-app/backend/alembic/versions/XXXX_add_promo_codes_promo_usages_admin_logs.py` — новая миграция
- `admin-mini-app/backend/db/repositories/promo_repo.py` — новый репозиторий
- `admin-mini-app/backend/db/repositories/log_repo.py` — новый репозиторий
- `admin-mini-app/backend/db/repositories/dashboard_repo.py` — изменение: новые агрегаты
- `admin-mini-app/backend/db/repositories/__init__.py` — изменение: экспорт новых репозиториев
- `admin-mini-app/backend/schemas/promo.py` — новый файл схем
- `admin-mini-app/backend/schemas/log.py` — новый файл схем
- `admin-mini-app/backend/schemas/dashboard.py` — изменение: новые поля в `DashboardStatsResponse`
- `admin-mini-app/backend/api/router_promos.py` — новый роутер
- `admin-mini-app/backend/api/router_logs.py` — новый роутер
- `admin-mini-app/backend/api/router_dashboard.py` — изменение: расширенные метрики
- `admin-mini-app/backend/api/router_users.py` — изменение: добавить `log_repo.log_action` в block/note/extend
- `admin-mini-app/backend/api/router_settings.py` — изменение: добавить `log_repo.log_action` в update
- `admin-mini-app/backend/api/router_configs.py` — изменение: добавить `log_repo.log_action` в toggle/toggle-all
- `admin-mini-app/backend/main.py` — изменение: подключить `promos_router`, `logs_router`

### Фронт

- `admin-mini-app/frontend/src/stores/promos.js` — новый store
- `admin-mini-app/frontend/src/stores/logs.js` — новый store
- `admin-mini-app/frontend/src/stores/dashboard.js` — изменение: новые поля
- `admin-mini-app/frontend/src/components/promos/PromoCard.vue` — новый компонент
- `admin-mini-app/frontend/src/components/promos/PromoForm.vue` — новый компонент
- `admin-mini-app/frontend/src/views/PromosListView.vue` — реализация (сейчас заглушка)
- `admin-mini-app/frontend/src/views/PromoCreateView.vue` — реализация (сейчас заглушка)
- `admin-mini-app/frontend/src/views/PromoDetailView.vue` — реализация (сейчас заглушка)
- `admin-mini-app/frontend/src/views/LogsView.vue` — реализация (сейчас заглушка)
- `admin-mini-app/frontend/src/views/DashboardView.vue` — изменение: новые метрики
- `admin-mini-app/frontend/src/views/UserDetailView.vue` — изменение: блок promo_usages

---

## Пользовательские сценарии

### Промокоды — создание

```
Админ: Открывает раздел "Промокоды"
UI: Список промокодов (пустой или с существующими)
Админ: Нажимает кнопку "+ Создать"
UI: Форма создания промокода
Админ: Нажимает "🎲 Сгенерировать"
API: GET /api/promos/generate-code → { code: "SUMMER25" }
UI: Поле кода заполняется автоматически
Админ: Устанавливает скидку 25%, лимит 100 активаций, срок 30 дней
Админ: Нажимает "Создать"
API: POST /api/promos { code: "SUMMER25", discount_percent: 25, max_activations: 100, valid_days: 30 }
UI: Редирект на список, тост "Промокод создан"
```

### Промокоды — детальная страница

```
Админ: Открывает промокод "SUMMER25"
UI: Карточка с деталями
    Скидка: 25%
    Использований: 12/100
    Прогресс-бар: 12%
    Срок до: 04.04.2026
    Статус: Активен
    Список применений:
    - @ivan  •  2026-03-04 14:23
    - @maria  •  2026-03-03 09:11
Админ: Нажимает "Деактивировать"
API: PATCH /api/promos/1/toggle { is_active: false }
UI: Статус → "Неактивен", кнопка меняется на "Активировать"
Админ: Нажимает "Удалить"
UI: Модальное окно подтверждения "Удалить промокод SUMMER25?"
Админ: Подтверждает
API: DELETE /api/promos/1
UI: Редирект на список, тост "Промокод удалён"
```

### Логи действий

```
Админ: Открывает раздел "Логи"
UI: Список последних действий (20 строк, пагинация)
    - 2026-03-05 15:42  @admin_user  block_user  target: @ivan
    - 2026-03-05 14:20  @admin_user  extend_subscription  target: @maria (+30 days)
    - 2026-03-05 11:05  @admin_user  create_promo  target: SUMMER25
Админ: Выбирает фильтр "block_user" из выпадающего списка
UI: Список обновляется, показаны только события блокировки
```

### Статистика на дашборде

```
Админ: Открывает главную страницу
UI: Сетка карточек со статистикой:
    [Пользователей: 1 245]  [Платных: 834]
    [Истекают скоро: 47]    [Активных конфигов: 2 103]
    [Новых за 30 дней: 89]  [Активных промо: 3]
    [Без подписки: 411]
```

---

## API-контракт

### Промокоды

#### `GET /api/promos`

**Query-параметры:**
- `page` (int, default: 1)
- `per_page` (int, default: 20, max: 100)
- `is_active` (bool | null) — фильтр по статусу

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "code": "SUMMER25",
      "discount_percent": 25,
      "max_activations": 100,
      "current_activations": 12,
      "valid_until": "2026-04-04T00:00:00Z",
      "is_active": true,
      "is_expired": false,
      "created_at": "2026-03-05T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

#### `POST /api/promos`

**Request:**
```json
{
  "code": "SUMMER25",
  "discount_percent": 25,
  "max_activations": 100,
  "valid_days": 30
}
```
Либо вместо `valid_days` — `valid_until: "2026-04-04T00:00:00Z"`. Оба поля необязательны, но хотя бы одно должно быть указано.

**Response 201:**
```json
{
  "id": 1,
  "code": "SUMMER25",
  "discount_percent": 25,
  "max_activations": 100,
  "current_activations": 0,
  "valid_until": "2026-04-04T00:00:00Z",
  "is_active": true,
  "is_expired": false,
  "created_at": "2026-03-05T10:00:00Z"
}
```

**Errors:**
- `400` — `valid_until` в прошлом; не указан ни `valid_days`, ни `valid_until`
- `409` — код уже существует

---

#### `GET /api/promos/{id}`

**Response 200:** `PromoResponse` (см. выше)

**Errors:**
- `404` — промокод не найден

---

#### `PATCH /api/promos/{id}/toggle`

**Request:**
```json
{ "is_active": false }
```

**Response 200:** `PromoResponse`

**Errors:**
- `404` — промокод не найден

---

#### `DELETE /api/promos/{id}`

**Response 204:** пустой body

**Errors:**
- `404` — промокод не найден

---

#### `GET /api/promos/{id}/usages`

**Query-параметры:**
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Response 200:**
```json
{
  "items": [
    {
      "user_id": 42,
      "username": "ivan",
      "first_name": "Иван",
      "used_at": "2026-03-04T14:23:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 20
}
```

---

#### `GET /api/promos/generate-code`

**Response 200:**
```json
{ "code": "SUMMER25" }
```

Генерирует случайный уникальный код из 8 символов `[A-Z0-9]`, проверяет уникальность в БД, при коллизии — повторяет (не более 5 попыток, затем 409).

---

### Логи

#### `GET /api/logs`

**Query-параметры:**
- `page` (int, default: 1)
- `per_page` (int, default: 20, max: 100)
- `action` (str | null) — фильтр по типу действия
- `admin_id` (int | null) — фильтр по ID админа

**Response 200:**
```json
{
  "items": [
    {
      "id": 101,
      "admin_telegram_id": 123456789,
      "admin_username": "admin_user",
      "action": "block_user",
      "target": "@ivan",
      "details": "{\"reason\": \"spam\"}",
      "created_at": "2026-03-05T15:42:00Z"
    }
  ],
  "total": 347,
  "page": 1,
  "per_page": 20,
  "available_actions": ["block_user", "unblock_user", "extend_subscription", "update_note", "toggle_config", "toggle_all_configs", "update_settings", "create_promo", "toggle_promo", "delete_promo"]
}
```

---

### Дашборд — расширенная статистика

#### `GET /api/dashboard/stats` (обновлённый ответ)

**Response 200:**
```json
{
  "total_users": 1245,
  "paid_users": 834,
  "unpaid_users": 411,
  "expiring_soon": 47,
  "active_configs": 2103,
  "new_users_30d": 89,
  "active_promos": 3
}
```

Поля `unpaid_users`, `new_users_30d`, `active_promos` — новые.

---

### Промо-применения в деталях пользователя

#### `GET /api/users/{id}` (обновлённый ответ)

Поле `promo_usages` в `UserDetail` теперь возвращает реальные данные:

```json
{
  "promo_usages": [
    {
      "code": "SUMMER25",
      "discount_percent": 25,
      "used_at": "2026-03-04T14:23:00Z"
    }
  ]
}
```

---

## Модели БД

### PromoCode

```python
class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    discount_percent: Mapped[int] = mapped_column(nullable=False)
    max_activations: Mapped[int] = mapped_column(nullable=False)
    current_activations: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    usages: Mapped[list["PromoUsage"]] = relationship(back_populates="promo", cascade="all, delete-orphan")
```

### PromoUsage

```python
class PromoUsage(Base):
    __tablename__ = "promo_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    promo: Mapped["PromoCode"] = relationship(back_populates="usages")
    user: Mapped["User"] = relationship()
```

### AdminLog

```python
class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    admin_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(nullable=True)  # JSON-строка
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
```

Индекс на `created_at` для быстрой сортировки. Индекс на `action` для фильтрации.

---

## Технические решения

- **Атомарность `use_promo`:** SELECT FOR UPDATE на строке `PromoCode` + проверка `current_activations < max_activations` + INCREMENT в одной транзакции. Предотвращает race condition при одновременных применениях.
- **Логирование:** синхронный вызов `await log_repo.log_action(session, ...)` в конце каждого мутирующего роутера — в той же транзакции. Если основное действие успешно, лог записывается вместе с ним.
- **`promo_usages` в `UserDetail`:** загружается отдельным запросом в `user_repo.get_user_by_id` через `selectinload` или явным JOIN.
- **Генерация кода:** `secrets.token_hex(4).upper()` даёт 8 hex-символов `[0-9A-F]`, уникальность проверяется SELECT перед INSERT.
- **`is_expired` в `PromoResponse`:** вычисляемое поле Pydantic (`@computed_field`), не хранится в БД.
- **Фронтенд:** компонент `PromoCard.vue` показывает прогресс-бар `current_activations / max_activations` через inline-style width.
- **Типизация фронта:** хранится как `.js` (Composition API + `<script setup>`) в соответствии с существующим стилем проекта — не TypeScript.

---

## Критерии приёмки

### Логи
- [ ] Таблица `admin_logs` создана и миграция применена
- [ ] Каждое мутирующее действие записывает лог (block/unblock, extend, note, toggle config, toggle-all, update settings, create/toggle/delete promo)
- [ ] `GET /api/logs` возвращает список с пагинацией
- [ ] Фильтр по `action` работает
- [ ] `LogsView.vue` отображает журнал: дата, кто сделал, что сделал, таргет
- [ ] Пагинация работает

### Промокоды
- [ ] Таблицы `promo_codes` и `promo_usages` созданы и миграция применена
- [ ] `POST /api/promos` создаёт промокод, валидация кода `[A-Z0-9]` max 32 символа
- [ ] `GET /api/promos` возвращает список с пагинацией
- [ ] `GET /api/promos/{id}` возвращает детали
- [ ] `PATCH /api/promos/{id}/toggle` переключает активность
- [ ] `DELETE /api/promos/{id}` удаляет промокод
- [ ] `GET /api/promos/{id}/usages` возвращает историю применений с пагинацией
- [ ] `GET /api/promos/generate-code` генерирует уникальный код
- [ ] `PromosListView.vue` — список карточек с прогресс-баром и статусом
- [ ] `PromoCreateView.vue` — форма с генератором, валидация на фронте
- [ ] `PromoDetailView.vue` — детали, история применений, кнопки деактивации и удаления
- [ ] Удаление требует подтверждения через `ConfirmModal`
- [ ] Деактивированный промокод показывается серым

### Дашборд — расширенная статистика
- [ ] `DashboardStatsResponse` содержит поля `unpaid_users`, `new_users_30d`, `active_promos`
- [ ] `DashboardView.vue` отображает новые карточки метрик
- [ ] `UserDetailView.vue` показывает список применённых промокодов

---

## Вне скоупа

Что НЕ входит в эту задачу:
- Применение промокода пользователем через бот (только создание и просмотр в админке)
- Интеграция скидки с платёжной системой — промокоды хранятся в БД, но логика применения скидки к оплате реализуется позже
- Управление администраторами (AdminsView.vue) — отдельная задача
- Экспорт логов в CSV/Excel
- Push-уведомления при применении промокода
- Графики и диаграммы на дашборде (только числовые карточки)
