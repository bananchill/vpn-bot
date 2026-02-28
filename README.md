# vpn-bot

Telegram-бот для управления VPN-конфигурациями через API панели 3x-ui. Позволяет создавать, просматривать и удалять клиентские конфиги (VLESS/VMess), отслеживать трафик и получать ссылки для подключения.

## Требования

- Python 3.12+
- PostgreSQL
- [3x-ui](https://github.com/MHSanaei/3x-ui) панель с настроенным inbound
- [uv](https://docs.astral.sh/uv/) -- менеджер пакетов

## Установка

Клонируйте репозиторий и установите зависимости:

```bash
git clone https://github.com/your-org/vpn-bot.git
cd vpn-bot
uv sync
```

Для разработки (тесты, линтер):

```bash
uv sync --extra dev
```

### Настройка окружения

Скопируйте шаблон и заполните переменные:

```bash
cp .env.example .env
```

Описание переменных:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота. Получите через [@BotFather](https://t.me/BotFather): создайте нового бота командой `/newbot` и скопируйте токен. |
| `DATABASE_URL` | Строка подключения к PostgreSQL в формате `postgresql+asyncpg://user:password@localhost:5432/vpn-bot`. |
| `PANEL_URL` | URL панели 3x-ui, например `http://212.34.139.158:2053`. |
| `DEFAULT_INBOUND_ID` | ID inbound в 3x-ui, к которому будут привязываться клиенты. По умолчанию `1`. |
| `ENCRYPTION_KEY` | Ключ Fernet для шифрования учетных данных администратора в базе. |
| `OWNER_ID` | Telegram ID владельца бота. Даёт доступ к скрытым командам управления администраторами. Узнать свой ID можно через [@userinfobot](https://t.me/userinfobot). |

Генерация `ENCRYPTION_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Настройка базы данных

Создайте базу данных в PostgreSQL:

```sql
CREATE DATABASE "vpn-bot";
```

Примените миграции:

```bash
alembic upgrade head
```

## Запуск

```bash
uv run bot
```

## Использование бота

После запуска бот принимает следующие команды и действия:

**`/start`** -- главное меню с двумя кнопками:
- **Создать конфиг** -- бот запросит имя конфига, создаст клиента на панели и вернет ссылку для подключения.
- **Мои конфиги** -- список ваших конфигов. По каждому доступны действия: просмотр трафика, получение ссылки, удаление.

**`/admin`** -- настройка подключения к панели 3x-ui. Бот последовательно запросит логин и пароль от панели, проверит подключение и сохранит сессию. Пароль автоматически удаляется из чата после прочтения.

## Разработка

Запуск тестов:

```bash
uv run pytest -x
```

Проверка линтером:

```bash
uv run ruff check .
```

Создание новой миграции после изменения моделей:

```bash
alembic revision --autogenerate -m "описание изменений"
```

## Стек технологий

- **aiogram 3** -- Telegram Bot API
- **SQLAlchemy 2.0** (async) -- ORM
- **PostgreSQL** + **asyncpg** -- база данных
- **Alembic** -- миграции
- **Pydantic v2** -- валидация и настройки
- **httpx** -- асинхронный HTTP-клиент для 3x-ui API
- **cryptography** -- шифрование учетных данных
- **pytest** + **pytest-asyncio** -- тестирование
- **ruff** -- линтер
