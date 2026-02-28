# vpn-bot

Telegram bot for managing VPN configs via 3x-ui panel API.

## Stack
Python 3.12, aiogram 3, SQLAlchemy 2.0 async, PostgreSQL, Alembic, Pydantic v2, pytest, httpx

## Commands
- `uv run bot` — start bot
- `uv run pytest -x` — tests
- `uv run ruff check .` — linter
- `alembic revision --autogenerate -m "desc"` — new migration
- `alembic upgrade head` — apply migrations

## Key docs
- Project spec & API reference: docs/SPEC.md
- Task files: docs/tasks/TASK-NNN-*.md
- Feature docs: docs/features/

## Agents
| Agent | Model | Role |
|-------|-------|------|
| task-manager | sonnet | Requirements → task file in Russian → wait for user approval |
| developer | opus | Production-grade code, SOLID, clean architecture |
| qa | sonnet | Write tests + code review in one pass |
| docs | sonnet | Documentation + learning explanations in Russian |
| git-committer | haiku | Stage, commit, push (via `/project:commit`) |

## Workflow — FOLLOW THIS ORDER

### For new features or unclear tasks:
1. Delegate to **task-manager** → creates docs/tasks/TASK-NNN-*.md
2. **STOP. Wait for user to approve the task file.**
3. After approval → delegate to **developer** with: task file path, constraints
4. After developer → delegate to **qa** with: task file path, new/modified files
5. If qa requests changes → send back to developer with specific issues
6. If new patterns/features (not bugfix) → delegate to **docs** with: file list
7. Tell user to run `/project:commit`

### For bugfixes and small changes (< 30 lines):
1. Delegate directly to **developer**
2. Delegate to **qa** (review only, skip heavy testing for trivial fixes)
3. Skip docs
4. Tell user to run `/project:commit`

### For git operations:
User runs `/project:commit` manually. Do not commit yourself.

## Session management
- New unrelated task → tell user: "Новая задача. Выполните /clear и повторите запрос."
- Continuation of recent work → proceed with current context
- Unclear → ask: "Это новая задача или продолжение?"

## Token saving
- Use built-in **Explore** agent (haiku) for file lookups, not sonnet/opus agents
- Keep delegation prompts under 200 words — file paths + spec, no dumps
- Never re-read files already in context
- Skip docs for bugfixes, config changes, minor tweaks
- Skip qa heavy testing for trivial one-line fixes

## Code rules
- Async everywhere, no sync I/O
- Type hints on all signatures, no `Any`
- Business logic in services, not handlers
- DTOs between layers, never pass ORM models to handlers
- Tests for new features (min 80% coverage)
- Russian for user-facing bot messages and documentation
- English for code, comments, commit messages
