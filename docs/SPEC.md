# VPN Bot — Project Specification

## Overview
Telegram bot for managing VPN configurations via 3x-ui panel API.
Two roles: admin and regular user.

## 3x-ui Panel API Reference

Base URL: configurable, e.g. `http://212.34.139.158:2053`

### Authentication
```
POST /login
Body: {"username": "...", "password": "..."}
Response: session cookie (use for all subsequent requests)
```

### Inbound endpoints (base path: /panel/api/inbounds)
| Method | Path | Description |
|--------|------|-------------|
| GET | /list | Get all inbounds |
| GET | /get/:id | Get inbound by ID |
| POST | /add | Add new inbound |
| POST | /del/:id | Delete inbound |
| POST | /update/:id | Update inbound |
| POST | /addClient | Add client to inbound |
| POST | /updateClient/:clientId | Update client |
| POST | /:id/delClient/:clientId | Delete client |
| GET | /getClientTraffics/:email | Get client traffic stats |
| POST | /clientIps/:email | Get client IPs |
| POST | /:id/resetClientTraffic/:email | Reset client traffic |

### API response format
```json
{
  "success": true,
  "msg": "",
  "obj": { ... }
}
```

### Important notes
- Session cookie must be stored and reused across requests
- Client email must be unique per protocol
- Client ID (uuid for vless/vmess, password for trojan) is auto-generated or manual
- Inbound settings contain clients array in JSON format

---

## Bot Features

### 1. Admin initialization
**Command:** `/admin`
**Flow:**
1. User sends `/admin`
2. Bot asks for 3x-ui panel login
3. User sends login
4. Bot asks for 3x-ui panel password
5. User sends password
6. Bot attempts `POST /login` to the panel
7. If success → save user as admin in DB, store session
8. If fail → show error, ask to retry

**Security:**
- Admin credentials stored encrypted in DB
- Session cookie refreshed automatically on expiry
- Only one admin per Telegram user ID (can re-init)
- Delete password messages after reading for security

### 2. User main menu
After `/start`, regular users see inline keyboard:

```
🔑 Создать конфиг
📋 Мои конфиги
```

### 3. Create config (Создать конфиг)
**Flow:**
1. User taps "Создать конфиг"
2. Bot asks for config name (will be used as email/remark)
3. Bot calls `POST /panel/api/inbounds/addClient` with:
   - Generated UUID
   - User-provided name as email
   - Linked to default inbound (configurable)
4. Bot returns the connection link/config to user

### 4. My configs (Мои конфиги)
**Flow:**
1. User taps "Мои конфиги"
2. Bot fetches inbound list, filters clients belonging to this user
3. Shows list of configs as inline buttons
4. User taps a config → sees detail menu:

```
📊 Трафик
🔄 Обновить конфиг
📎 Получить ссылку
🗑 Удалить конфиг
```

### 5. Config actions

**📊 Трафик (Traffic)**
- Call `GET /panel/api/inbounds/getClientTraffics/:email`
- Show: upload, download, total, limit, expiry date

**🔄 Обновить конфиг (Update/Refresh)**
- Call `GET /panel/api/inbounds/get/:id` to fetch fresh config
- Regenerate connection link with current settings
- Send updated link to user

**📎 Получить ссылку (Get link)**
- Generate vless://, vmess://, or trojan:// link from stored config
- Send as copyable message

**🗑 Удалить конфиг (Delete)**
- Confirm with user ("Вы уверены?")
- Call `POST /panel/api/inbounds/:id/delClient/:clientId`
- Remove from local DB
- Show success message

---

## Technical Requirements

### Database schema (PostgreSQL)
- **users** — telegram_id, username, is_admin, created_at
- **admin_sessions** — user_id, panel_url, encrypted_credentials, session_cookie, cookie_expires_at
- **configs** — user_id, inbound_id, client_id (uuid), email, protocol, created_at

### Architecture
- `bot/services/xui_client.py` — async HTTP client for 3x-ui API (httpx)
- `bot/services/vpn_service.py` — business logic (create/delete/get configs)
- `bot/services/link_generator.py` — generate connection links (vless://, vmess://)
- `bot/handlers/start.py` — /start, main menu
- `bot/handlers/admin.py` — /admin, initialization flow
- `bot/handlers/config.py` — config CRUD operations
- `bot/db/repositories/` — user_repo, config_repo, admin_session_repo
- `bot/keyboards/` — inline keyboards for menus
- `bot/middlewares/auth.py` — inject user into handler context

### Config
All sensitive data via environment variables:
```
BOT_TOKEN=...
DATABASE_URL=postgresql+asyncpg://...
DEFAULT_INBOUND_ID=1
PANEL_URL=http://212.34.139.158:2053
ENCRYPTION_KEY=...  # for encrypting admin credentials
```

### Link generation format examples
```
vless://{uuid}@{server}:{port}?type=tcp&security=reality&...#{remark}
vmess://base64({json_config})
```
