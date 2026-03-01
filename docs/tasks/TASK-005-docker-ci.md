# TASK-005: Docker-сборка и CI/CD деплой через GitHub Actions

**Статус:** ⏳ Ожидает апрува
**Приоритет:** Высокий
**Дата:** 2026-03-01

## Описание
Необходимо контейнеризировать бота и настроить автоматический деплой на продакшен-сервер.
При каждом пуше в ветку `main` GitHub Actions собирает Docker-образ, публикует его в GitHub Container Registry (GHCR) и деплоит на сервер через self-hosted раннер — делает `docker pull` и перезапускает контейнеры.

## Что будет сделано

1. **Dockerfile** — multi-stage сборка: на первом этапе `uv` устанавливает зависимости в виртуальное окружение, на втором этапе копируется только venv и исходный код без build-артефактов.
2. **docker-compose.yml** — продакшен-конфигурация: сервисы `bot` и `postgres`, сеть, named volume для данных PostgreSQL, переменные окружения через `.env`-файл.
3. **`.github/workflows/deploy.yml`** — workflow, который срабатывает на push в `main`:
   - Джоб `build-and-push` (runs-on: ubuntu-latest): билд образа, пуш в `ghcr.io/bananchill/vpn-bot`.
   - Джоб `deploy` (runs-on: self-hosted): зависит от `build-and-push`, делает `docker compose pull` + `docker compose up -d`, затем применяет миграции.
4. **Применение миграций при деплое** — отдельный шаг в джобе `deploy`: запуск `docker compose run --rm bot alembic upgrade head` после поднятия контейнеров.
5. **`.dockerignore`** — исключает `.git`, `__pycache__`, `.env`, `tests/`, `docs/`, `.venv`.
6. **Документация секретов** — список переменных, которые нужно добавить в GitHub Secrets репозитория.

## Какие файлы будут затронуты

- `Dockerfile` — новый файл, multi-stage образ на базе `python:3.12-slim`
- `docker-compose.yml` — новый файл, продакшен-конфигурация бот + PostgreSQL
- `.dockerignore` — новый файл, исключения для Docker build context
- `.github/workflows/deploy.yml` — новый файл, CI/CD pipeline

## Пользовательский сценарий

Это инфраструктурный сценарий, видимого UX для конечного пользователя нет.
Сценарий для разработчика/деплоера:

```
Разработчик: git push origin main
GitHub Actions: запускает workflow deploy.yml
  → Job build-and-push (ubuntu-latest):
      - docker build -t ghcr.io/bananchill/vpn-bot:latest .
      - docker push ghcr.io/bananchill/vpn-bot:latest
  → Job deploy (self-hosted runner на сервере):
      - docker compose pull
      - docker compose up -d
      - docker compose run --rm bot alembic upgrade head
Сервер: бот перезапущен с новым образом, миграции применены
```

## Технические решения

**Dockerfile (multi-stage).**
Этап 1 (`builder`): образ `python:3.12-slim`, установка `uv`, копирование `pyproject.toml` + `uv.lock`, запуск `uv sync --frozen --no-dev` — зависимости устанавливаются в `/app/.venv`.
Этап 2 (`runtime`): чистый `python:3.12-slim`, копирование `/app/.venv` и исходников `bot/`, `alembic/`, `alembic.ini` из этапа builder. Точка входа — `python -m bot`.

**docker-compose.yml.**
Два сервиса: `postgres` (образ `postgres:16-alpine`, volume `pgdata`) и `bot` (образ `ghcr.io/bananchill/vpn-bot:latest`, зависит от `postgres`, env_file: `.env`).
В `.env` на сервере `DATABASE_URL` будет указывать на сервис `postgres`: `postgresql+asyncpg://vpnbot:password@postgres:5432/vpnbot`.

**GitHub Actions.**
Аутентификация в GHCR через `GITHUB_TOKEN` (встроенный секрет, дополнительной настройки не требует).
Остальные переменные (`BOT_TOKEN`, `DATABASE_URL`, `PANEL_URL`, `ENCRYPTION_KEY`, `OWNER_ID`, `DEFAULT_INBOUND_ID`, `POSTGRES_PASSWORD`) хранятся в GitHub Secrets и записываются в `.env`-файл на сервере шагом `echo` перед деплоем, либо `.env` уже лежит на сервере и не трогается workflow.

**Применение миграций.**
`alembic/env.py` читает `DATABASE_URL` из `bot.config.settings` (через `pydantic-settings` из переменных окружения). При запуске `docker compose run --rm bot alembic upgrade head` контейнер получает те же переменные из `.env`-файла — дополнительной настройки не нужно.

**Порядок запуска.**
`docker compose up -d` поднимает `postgres` раньше `bot` благодаря `depends_on`. Миграции запускаются отдельным шагом после `up -d`, когда PostgreSQL уже принимает соединения (healthcheck на postgres).

## Критерии приёмки

- [ ] `docker build .` проходит без ошибок на чистой машине
- [ ] `docker compose up -d` поднимает бота и PostgreSQL, бот стартует и отвечает на `/start`
- [ ] Push в `main` автоматически запускает workflow в GitHub Actions
- [ ] После деплоя на сервере поднимается новая версия образа
- [ ] Миграции применяются автоматически при каждом деплое без ручного вмешательства
- [ ] `.env` с секретами не попадает в Docker-образ и не коммитится в репозиторий
- [ ] Размер финального образа не превышает 300 МБ

## Вне скоупа

- Настройка самого self-hosted раннера на сервере (уже развёрнут)
- Настройка reverse-proxy (nginx/traefik) перед ботом
- Мониторинг и алертинг (Prometheus, Grafana)
- Rollback при неудачном деплое
- Multi-environment конфигурация (staging / production)
- Сборка и пуш образа по тегу/версии (только `latest`)

## Вопросы к заказчику

1. Где должен лежать `.env`-файл на сервере? Предполагается, что он создаётся вручную один раз в директории проекта и не перезаписывается workflow — это устраивает?
2. В какую директорию на сервере workflow должен делать `git pull` или достаточно только `docker compose pull`? (Если `docker-compose.yml` лежит в репозитории, нужен либо `git pull`, либо передача файла через `scp`/артефакт.)
3. Нужна ли проверка healthcheck перед запуском миграций (ждать, пока PostgreSQL полностью готов принимать соединения), или достаточно `depends_on: postgres` с условием `service_healthy`?
