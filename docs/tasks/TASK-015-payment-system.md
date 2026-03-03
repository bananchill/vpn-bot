# TASK-015: Система оплаты подписки

**Статус:** Ожидает апрува
**Приоритет:** Высокий
**Дата:** 2026-03-02

## Описание

Добавить систему подписки: создание конфига становится доступным только после оплаты.
Поддерживаются два способа оплаты — Telegram Stars (120 звёзд, фиксировано) и TON (цена
рассчитывается в реальном времени по курсу TON/RUB через публичный API, целевая стоимость —
200 рублей). Помимо оплаты, доступ можно получить через промокод. Подписка действует 30 дней
с момента активации; после истечения бот снова предлагает оплатить. 

## Что будет сделано

1. **БД — новые таблицы** — добавить модели `Subscription` и `PromoCode` в `bot/db/models.py`.

2. **Миграция Alembic** — создать `alembic/versions/XXXX_add_subscriptions_and_promo_codes.py`
   с командами `CREATE TABLE subscriptions` и `CREATE TABLE promo_codes`.

3. **DTO** — добавить `SubscriptionDTO` и `PromoCodeDTO` в `bot/dto.py`.

4. **Репозитории** — создать `bot/db/repositories/subscription_repo.py` (CRUD подписок)
   и `bot/db/repositories/promo_code_repo.py` (поиск, создание, пометка использованного).

5. **Сервис курса TON** — создать `bot/services/ton_price_service.py`: функция
   `get_ton_price_rub() -> Decimal`, которая обращается к CoinGecko Free API
   (`https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=rub`)
   без API-ключа. Кэш результата на 5 минут в памяти процесса (простой `dict` с timestamp).

6. **Сервис подписки** — создать `bot/services/subscription_service.py`:
   - `get_active_subscription(user_id, session) -> SubscriptionDTO | None`
   - `activate_subscription(user_id, session, source: str) -> SubscriptionDTO`
     (source = `"stars"` / `"ton"` / `"promo"`)
   - `activate_promo_code(user_id, code: str, session) -> SubscriptionDTO` — проверяет
     промокод, помечает использованным, активирует подписку
   - `calculate_ton_amount() -> str` — возвращает сумму в TON (например `"1.23"`) через
     `ton_price_service`; при ошибке API выбрасывает `TonPriceUnavailableError`

7. **Middleware проверки подписки** — создать `bot/middlewares/subscription.py`:
   `SubscriptionMiddleware` — inner-middleware на уровне роутера конфигов; если пользователь
   пытается создать конфиг без активной подписки, прерывает обработку и показывает меню оплаты.

8. **Хендлер оплаты** — создать `bot/handlers/payment.py` с FSM-потоком:
   - `show_payment_menu` — показывает меню выбора способа оплаты (Stars / TON / промокод)
   - `pay_stars` — генерирует invoice через `bot.send_invoice(...)` на 120 Stars
   - `pre_checkout_stars` — обработчик `PreCheckoutQuery`, подтверждает платёж
   - `successful_payment_stars` — обработчик `SuccessfulPayment`, вызывает
     `activate_subscription(..., source="stars")`
   - `pay_ton` — рассчитывает сумму в TON, генерирует invoice через встроенные платежи
     Telegram (провайдер `"XTR"` не подходит для TON; используем `"STARS"` только для Stars;
     для TON — внешний invoice через `bot.send_invoice` с `provider_token=""` и валютой `"TON"`)
   - `pre_checkout_ton` и `successful_payment_ton` — аналогично Stars
   - `enter_promo_code` — FSM-состояние ожидания ввода промокода
   - `process_promo_code` — проверяет промокод через `subscription_service`

9. **Хендлер промокодов для admins** — добавить в `bot/handlers/owner.py` команду `/promo`:
   - `/promo create <code>` — создать новый промокод (только owner)
   - `/promo list` — список активных промокодов

10. **Изменение `bot/handlers/config.py`** — в `start_create_config` и `reply_create_config`
    добавить вызов `subscription_service.get_active_subscription(user.id, db_session)`;
    если подписки нет — не входить в FSM, показать меню оплаты.

11. **Клавиатуры** — добавить в `bot/keyboards/menus.py`:
    - `payment_menu()` — кнопки: "Оплатить Stars (120)", "Оплатить TON", "У меня есть промокод"
    - `promo_cancel_menu()` — кнопка "Отмена" для FSM ввода промокода

12. **Конфигурация** — добавить в `bot/config.py`:
    - `SUBSCRIPTION_PRICE_RUB: int = 200`
    - `SUBSCRIPTION_STARS: int = 120`
    - `SUBSCRIPTION_DAYS: int = 30`
    - `TON_PRICE_CACHE_TTL: int = 300` (секунды)
    - `PAYMENTS_PROVIDER_TOKEN: str = ""` (пустой для Telegram Stars, нужен для TON через
      сторонние провайдеры — если используем native Telegram TON, токен не нужен)

## Какие файлы будут затронуты

### Новые файлы
- `bot/db/repositories/subscription_repo.py` — репозиторий подписок
- `bot/db/repositories/promo_code_repo.py` — репозиторий промокодов
- `bot/services/ton_price_service.py` — получение курса TON/RUB через CoinGecko
- `bot/services/subscription_service.py` — бизнес-логика подписок и промокодов
- `bot/middlewares/subscription.py` — middleware проверки активной подписки
- `bot/handlers/payment.py` — хендлеры оплаты (Stars, TON, промокод)
- `alembic/versions/XXXX_add_subscriptions_and_promo_codes.py` — миграция БД

### Изменяемые файлы
- `bot/db/models.py` — добавить модели `Subscription` и `PromoCode`
- `bot/dto.py` — добавить `SubscriptionDTO`, `PromoCodeDTO`
- `bot/config.py` — добавить новые env-переменные подписки
- `bot/keyboards/menus.py` — добавить `payment_menu()`, `promo_cancel_menu()`
- `bot/handlers/config.py` — добавить проверку подписки перед созданием конфига
- `bot/handlers/owner.py` — добавить команду `/promo`
- `bot/__main__.py` — зарегистрировать новый роутер `payment.router`

## Изменения в БД

### Новая таблица `subscriptions`
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | SERIAL PK | — |
| user_id | INTEGER FK → users.id CASCADE | — |
| started_at | TIMESTAMP WITH TZ | Момент активации |
| expires_at | TIMESTAMP WITH TZ | `started_at + 30 дней` |
| source | VARCHAR(20) | `"stars"` / `"ton"` / `"promo"` |
| promo_code | VARCHAR(64) NULLABLE | Код, которым активировано (для защиты от повторного использования) |
| created_at | TIMESTAMP WITH TZ | `server_default=func.now()` |

Индекс: `(user_id, expires_at DESC)` — для быстрого поиска активной подписки.

### Новая таблица `promo_codes`
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | SERIAL PK | — |
| code | VARCHAR(64) UNIQUE | Сам промокод (хранится в нижнем регистре) |
| is_active | BOOLEAN DEFAULT TRUE | Активен ли (owner может деактивировать) |
| use_count | INTEGER DEFAULT 0 | Счётчик активаций |
| created_at | TIMESTAMP WITH TZ | `server_default=func.now()` |

Промокоды — **многоразовые**: один код могут активировать несколько пользователей.
Один пользователь не может использовать один промокод дважды — проверяется через поле
`promo_code` в таблице `subscriptions`. Деактивировать можно через `/promo disable <code>`.

## Пользовательский сценарий

**Сценарий 1: новый пользователь пытается создать конфиг**
```
Пользователь: [нажимает "Создать конфиг"]
Бот: Для создания конфига требуется активная подписка.
     Стоимость: 200 ₽ / 30 дней.
     [кнопка: Оплатить Telegram Stars (120)]
     [кнопка: Оплатить TON (~1.23 TON)]
     [кнопка: У меня есть промокод]
```

**Сценарий 2: оплата через Telegram Stars**
```
Пользователь: [нажимает "Оплатить Telegram Stars (120)"]
Бот: [отправляет invoice — 120 Telegram Stars]
Telegram: [показывает нативный экран оплаты]
Пользователь: [подтверждает оплату]
Бот: Подписка активирована! Действует 30 дней до 01.04.2026.
     [кнопки главного меню]
Пользователь: [нажимает "Создать конфиг"]
Бот: Введите название для нового конфига: ...
```

**Сценарий 3: оплата через TON**
```
Пользователь: [нажимает "Оплатить TON (~1.23 TON)"]
Бот: [отправляет invoice — 1.23 TON]
Telegram: [показывает нативный экран оплаты TON]
Пользователь: [подтверждает оплату]
Бот: Подписка активирована! Действует 30 дней до 01.04.2026.
```

**Сценарий 4: промокод**
```
Пользователь: [нажимает "У меня есть промокод"]
Бот: Введите промокод:
     [кнопка: Отмена]
Пользователь: MYFREEPROMO
Бот: Промокод принят! Подписка активирована на 30 дней.
```

**Сценарий 5: неверный промокод**
```
Пользователь: WRONGCODE
Бот: Промокод не найден или уже использован. Попробуйте другой:
     [кнопка: Отмена]
```

**Сценарий 6: истёкшая подписка**
```
Пользователь: [нажимает "Создать конфиг" — подписка истекла]
Бот: Ваша подписка истекла 28.02.2026. Продлите подписку, чтобы создавать конфиги.
     [кнопки меню оплаты — те же]
```

**Сценарий 7: создание промокода owner-ом**
```
Owner: /promo create MYFREEPROMO
Бот: Промокод MYFREEPROMO создан.

Owner: /promo list
Бот: Активные промокоды:
     - MYFREEPROMO (не использован)
```

## Технические решения

### Telegram Stars (XTR)
`bot.send_invoice(currency="XTR", prices=[LabeledPrice(label="VPN 30 дней", amount=120)])`.
Для Stars `provider_token` должен быть пустой строкой `""`. Обработка: `PreCheckoutQuery`
(нужно вызвать `bot.answer_pre_checkout_query(ok=True)`) + `SuccessfulPayment`.

### TON через Telegram Invoice
Telegram поддерживает нативные TON-платежи через `currency="TON"` и `provider_token=""`.
Сумма передаётся в **нано-TON** (1 TON = 1_000_000_000). Курс берётся из CoinGecko:
`GET https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=rub`
→ `json["the-open-network"]["rub"]`. Сумма в TON = `ceil(200 / rate * 1e9)` (нано-TON),
округлённая до двух знаков для отображения. При недоступности CoinGecko показываем
сообщение "Сервис временно недоступен, попробуйте позже" и не показываем кнопку TON
(или показываем с деактивированным состоянием через alert).

### Промокоды
Хранятся в нижнем регистре. При вводе пользователь может вводить в любом регистре —
нормализуем к нижнему перед поиском. Один промокод — одно использование (`is_used=True`
после активации). Создаёт только owner через `/promo create`.

### Проверка подписки
В `start_create_config` и `reply_create_config` — прямой вызов `get_active_subscription()`.
Middleware не используем (избыточно для одного хендлера), чтобы не усложнять архитектуру.

**Admins всегда имеют бесплатный доступ**: если `user.is_admin == True`, проверка подписки
пропускается — admin может создавать конфиги без оплаты.

### Промокоды — многоразовые
Один промокод может быть активирован неограниченным числом пользователей. Ограничения:
- Один пользователь не может активировать один и тот же промокод дважды (проверяем наличие
  записи в `subscriptions` с `promo_code = code` и `user_id = user.id`)
- Owner может деактивировать промокод (`is_active=False`) — после этого он перестаёт работать
- Создаёт промокоды только owner (`OWNER_ID`) через `/promo create <code>`
- `/promo list` показывает все промокоды (активные и деактивированные) с `use_count`
- `/promo disable <code>` — деактивировать промокод

### Кэш курса TON
Простой in-process кэш: `_cache: dict = {"price": None, "fetched_at": None}`.
Время жизни — `TON_PRICE_CACHE_TTL` секунд (по умолчанию 300). Асинхронный запрос
через `httpx.AsyncClient`. При ошибке HTTP/таймауте выбрасывает `TonPriceUnavailableError`.

### FSM состояния для промокода
`PromoCodeStates.waiting_for_code` — добавляется в `bot/handlers/payment.py`.

## Критерии приёмки

- [ ] Нажатие "Создать конфиг" у пользователя без подписки показывает меню оплаты, не входит в FSM
- [ ] Нажатие "Создать конфиг" у пользователя с активной подпиской работает как раньше
- [ ] Нажатие "Создать конфиг" у пользователя с истёкшей подпиской показывает меню оплаты с датой истечения
- [ ] Оплата Stars: invoice создаётся на 120 XTR, после `SuccessfulPayment` подписка активируется в БД
- [ ] Оплата TON: invoice создаётся с суммой, рассчитанной через CoinGecko; после `SuccessfulPayment` подписка активируется
- [ ] При недоступности CoinGecko кнопка TON показывает `show_alert` с сообщением об ошибке
- [ ] Валидный промокод активирует подписку, помечается `is_used=True`, `used_by_user_id` заполняется
- [ ] Уже использованный промокод показывает сообщение "уже использован"
- [ ] Несуществующий промокод показывает сообщение "не найден"
- [ ] Owner может создать промокод командой `/promo create <code>`
- [ ] Owner может посмотреть список промокодов командой `/promo list`
- [ ] `/promo create` и `/promo list` недоступны не-owner пользователям
- [ ] Новые таблицы создаются миграцией Alembic без ошибок
- [ ] Тесты покрывают: проверку активной подписки, активацию через Stars/TON/promo, расчёт курса TON, кэш курса

## Вне скоупа

- Автоматическое продление подписки (recurring payments)
- Уведомление пользователя за N дней до истечения подписки
- Рефанд / отмена оплаты
- Несколько промокодов на одного пользователя одновременно
- Промокоды с ограниченным сроком действия
- Промокоды с частичной скидкой (не бесплатный доступ, а скидка)
- Поддержка других криптовалют (только TON)
- Admin-панель в Telegram для управления подписками
- Ограничение количества использований промокода (только one-time)
- Проверка подписки при просмотре/удалении существующих конфигов (только при создании)

## Уточнения от заказчика

- Промокоды **многоразовые**: один код могут использовать несколько пользователей
  (но каждый — только один раз)
- **Admins всегда бесплатны**: `is_admin == True` → проверка подписки пропускается
- Промокоды создаёт только **owner** через `/promo create`

## Уточнения по UI

- В `/start` показывать статус подписки: `✅ Подписка до 01.04.2026` (или
  `❌ Подписка не активна` если нет активной).
- Кэш курса TON — **5 минут** приемлемо.
