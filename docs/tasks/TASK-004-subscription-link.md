# TASK-004: Subscription URL — ссылка-подписка для всех конфигов клиента

**Статус:** Ожидает апрува
**Приоритет:** Средний
**Дата:** 2026-03-01

## Описание
Помимо индивидуальной ссылки `vless://` бот должен показывать пользователю subscription URL вида
`{PANEL_URL}/sub/{client_uuid}`. По этой ссылке V2Ray/Xray-клиенты получают сразу все конфиги,
привязанные к данному UUID на панели. Это решает задачу пользователя, у которого несколько конфигов
на разных inbound-ах и который хочет одной ссылкой подписаться на все сразу.

## Что будет сделано

1. Добавить функцию `generate_subscription_url(panel_url: str, client_uuid: str) -> str`
   в `bot/services/link_generator.py` — собирает URL по шаблону `{panel_url}/sub/{client_uuid}`.

2. Изменить `create_config` в `bot/services/vpn_service.py` — вместо одной строки-ссылки
   возвращать датакласс `ConfigLinks(vless_link: str, subscription_url: str)`.

3. Изменить `get_config_link` в `bot/services/vpn_service.py` — тоже возвращать `ConfigLinks`.

4. Обновить хендлер `process_config_name` в `bot/handlers/config.py` — отображать обе ссылки
   после создания конфига.

5. Обновить хендлеры `show_link` и `refresh_config` в `bot/handlers/config.py` — отображать
   обе ссылки при просмотре и обновлении конфига.

## Какие файлы будут затронуты

- `bot/services/link_generator.py` — добавление функции `generate_subscription_url`
- `bot/services/vpn_service.py` — новый датакласс `ConfigLinks`, изменение сигнатур
  `create_config` и `get_config_link`
- `bot/handlers/config.py` — обновление трёх хендлеров: `process_config_name`, `show_link`,
  `refresh_config`
- `tests/test_link_generator.py` — новые юнит-тесты для `generate_subscription_url`
- `tests/test_vpn_service.py` — обновление тестов `create_config` и `get_config_link`
  под новый возвращаемый тип

## Пользовательский сценарий

```
Пользователь: [вводит название конфига "myvpn"]
Бот: Конфиг «myvpn» создан!

Ссылка для подключения (один конфиг):
<code>vless://uuid@server:443?type=tcp&...#myvpn</code>

Ссылка-подписка (все ваши конфиги сразу):
<code>http://212.34.139.158:2053/sub/uuid</code>

[Импортируйте subscription URL в V2Ray/Xray, чтобы получить все конфиги автоматически]
```

---

```
Пользователь: [нажимает "Получить ссылку" для конфига "myvpn"]
Бот: Ссылка для «myvpn»:

Прямая ссылка (один конфиг):
<code>vless://uuid@server:443?type=tcp&...#myvpn</code>

Ссылка-подписка (все конфиги):
<code>http://212.34.139.158:2053/sub/uuid</code>
```

## Технические решения

- `generate_subscription_url` — чистая функция без I/O, просто конкатенация строк.
  Не требует нового HTTP-запроса к панели; UUID уже хранится в `Config.client_id` в БД.
- `ConfigLinks` — frozen dataclass (по аналогии с `TrafficInfo` в том же файле),
  чтобы не ломать типизацию и держать слой сервисов чистым.
- `settings.PANEL_URL` уже доступен в `bot/config.py` и подтягивается в хендлерах
  через `from bot.config import settings` — новых env-переменных не нужно.
- Ссылки в сообщениях оборачиваются в `<code>...</code>` (HTML parse_mode уже используется
  в хендлерах) — пользователь может скопировать одним касанием.

## Критерии приёмки

- [ ] `generate_subscription_url("http://host:2053", "gy2hpqt5zvyizs3x")` возвращает
  `"http://host:2053/sub/gy2hpqt5zvyizs3x"`
- [ ] При создании конфига генерируется `sub_id` (16 hex символов), передаётся в 3x-ui как `subId` и сохраняется в БД
- [ ] После создания конфига бот показывает оба блока: прямую ссылку и subscription URL
- [ ] При нажатии "Получить ссылку" бот показывает оба блока
- [ ] При нажатии "Обновить конфиг" бот показывает оба блока
- [ ] Subscription URL строится из `settings.PANEL_URL` и `config.sub_id` — без обращения
  к панели
- [ ] Типы в сервисном слое строгие: везде `ConfigLinks`, не `str`
- [ ] Новые и изменённые функции покрыты тестами

## Вне скоупа

- Проверка доступности subscription URL (HTTP-запрос к панели)
- Отдельная кнопка "Subscription URL" в меню конфига (ссылки выводятся в тех же сообщениях,
  что и сейчас, — просто добавляется второй блок)
- Поддержка нескольких PANEL_URL или нескольких панелей
- QR-код для subscription URL
