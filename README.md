# 🚌 BusGo API

**BusGo API** သည် Myanmar ရှိ ခရီးသွားလာမှုအတွက် ဘတ်စ်ကား လက်မှတ်ကြိုတင်မှာယူမှုစနစ် (Bus Ticket Booking System) ၏ **Backend REST API** ဖြစ်သည်။

`FastAPI` ကို အခြေခံတည်ဆောက်ထားပြီး **JWT Authentication**, **Role-Based Access Control (RBAC)**, **Rate Limiting**, **Redis Caching** အစရှိသော လုံခြုံရေးနှင့် စွမ်းဆောင်ရည်ဆိုင်ရာ အင်္ဂါရပ်များ အပြည့်အဝပါဝင်ပါသည်။

---

## 📑 Table of Contents

- [🌟 Features](#-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [📁 Project Structure](#-project-structure)
- [✅ Prerequisites](#-prerequisites)
- [🚀 Installation & Setup](#-installation--setup)
  - [Local Setup (venv)](#local-setup-venv)
  - [Docker Setup](#docker-setup)
- [⚙️ Environment Variables](#️-environment-variables)
- [🗄️ Database Migrations](#️-database-migrations)
- [🌱 Database Seeding](#-database-seeding)
- [🔐 Authentication & RBAC](#-authentication--rbac)
- [📚 API Documentation](#-api-documentation)
- [🔗 API Endpoints](#-api-endpoints)
- [🧪 Testing](#-testing)
- [🛡️ Security Features](#️-security-features)
- [📜 License](#-license)

---

## 🌟 Features

| အင်္ဂါရပ် | အသေးစိတ် |
|---|---|
| 🔐 **JWT Authentication** | Access Token (30 min) + Refresh Token (7 days)၊ Logout/Revocation အတွက် Token Blacklist |
| 👥 **RBAC (Role-Based Access Control)** | Dynamic Permissions (`resource:action` ပုံစံ)၊ Default Roles ၄ မျိုး (Super Admin, Manager, Counter Staff, Customer) |
| 🚌 **Bus Management** | Bus Companies, Buses, Bus Types (VIP 2+1, Standard 2+2) |
| 🛣️ **Route Management** | Origin/Destination Unique Constraints၊ Distance & Estimated Hours |
| 🎫 **Trip Management** | ခရီးစဉ်များကို Search/Filter/Paginate လုပ်နိုင်ခြင်း |
| 💰 **Dynamic Pricing** | Local / Foreigner ဈေးနှုန်းနှစ်မျိုး၊ Festival Period (ပွဲတော်ကာလ) ဈေးနှုန်းများ |
| 🪑 **Seat Layout Generation** | Bus Type အလိုက် Seat Template အလိုအလျောက်ထုတ်ပေးခြင်း (2:1, 2:2) |
| ☁️ **Cloudinary Upload** | Bus Company Logo များကို Cloud သို့ Upload လုပ်နိုင်ခြင်း |
| ⏱️ **Rate Limiting** | IP အလိုက် တစ်မိနစ်အတွင်း ကန့်သတ်ချက် (Redis + In-Memory Fallback) |
| 🛡️ **Security Headers** | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy |
| 🗄️ **PostgreSQL + Alembic** | Async SQLAlchemy ORM၊ Migration အပြည့်အဝထောက်ပံ့ |

---

## 🛠️ Tech Stack

### Backend Framework
- **FastAPI** `0.111` — မြန်ဆန်သော Async Python Web Framework
- **Uvicorn** `0.30` — ASGI Server

### Database & ORM
- **PostgreSQL 16** — Primary Database
- **SQLAlchemy 2.0** (Async) — ORM
- **asyncpg** — Async PostgreSQL Driver
- **Alembic** — Database Migration Tool

### Authentication & Security
- **JWT (python-jose)** — Token-Based Authentication
- **Passlib + Bcrypt** — Password Hashing
- **Python-Multipart** — Form Data / File Upload

### Caching & Rate Limiting
- **Redis 7** — Token Blacklist & Rate Limiting
- **In-Memory Fallback** — Redis မရရှိသည့်အခါ Rate Limit အတွက်

### File Upload
- **Cloudinary** — Bus Company Logo Upload

### Monitoring & Testing
- **Sentry SDK** — Error Tracking
- **Pytest + httpx** — Testing

---

## 📁 Project Structure

```
busgo-api/
├── app/
│   ├── api/
│   │   ├── deps.py                    # Dependencies (DB, Auth, Permissions)
│   │   └── v1/
│   │       ├── router.py              # Main API Router
│   │       └── endpoints/
│   │           ├── auth.py            # Register, Login, Refresh, Logout, Me
│   │           ├── users.py           # User CRUD
│   │           ├── roles.py           # Role CRUD + Assign Permissions
│   │           ├── permissions.py     # Permission CRUD
│   │           ├── bus_companies.py   # Company CRUD + Logo Upload
│   │           ├── buses.py           # Bus CRUD
│   │           ├── seats.py           # Seat Template Generate/List
│   │           ├── routes.py          # Route CRUD + Cities
│   │           └── trips.py           # Trip CRUD + Search/Filter
│   │
│   ├── core/
│   │   ├── config.py                  # Settings (Pydantic)
│   │   ├── database.py                # Async DB Engine/Session
│   │   ├── security.py                # JWT & Password Hashing
│   │   ├── rate_limit.py              # Rate Limit Middleware
│   │   ├── redis_client.py            # Redis Client
│   │   └── token_blacklist.py         # JWT Revocation Logic
│   │
│   ├── db/
│   │   ├── base.py                    # Base Metadata
│   │   └── seed.py                    # RBAC + Super Admin Seeder
│   │
│   ├── models/                        # SQLAlchemy Models
│   │   ├── base.py                    # BaseModel (UUID, created_at, updated_at)
│   │   ├── user.py
│   │   ├── rbac.py                    # Role, Permission
│   │   ├── bus.py
│   │   ├── bus_company.py
│   │   ├── route.py
│   │   ├── trip.py
│   │   ├── seat.py
│   │   └── associations.py            # role_permissions, user_roles Tables
│   │
│   ├── schemas/                       # Pydantic Schemas
│   ├── repositories/                  # Data Access Layer
│   ├── services/                      # Business Logic Layer
│   └── utils/
│
├── alembic/                           # Database Migrations
├── scripts/
│   └── entrypoint.sh                  # Docker Entrypoint (Migrate + Seed + Run)
├── tests/                             # Pytest Tests
├── Dockerfile                         # Production Dockerfile (Multi-stage)
├── docker-compose.yml                 # PostgreSQL + Redis + API
├── Makefile                           # Dev Commands
├── requirements.txt
└── .env.example                       # Environment Variables Template
```

### Layered Architecture

```
┌─────────────────────────────────────────────────┐
│                API Endpoints                    │
│         (app/api/v1/endpoints/)                 │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                  Services                       │
│            (app/services/) — Business Logic     │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│               Repositories                      │
│        (app/repositories/) — Data Access        │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                  Models (ORM)                   │
│            (app/models/) — SQLAlchemy           │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                 PostgreSQL 16                    │
└─────────────────────────────────────────────────┘
```

---

## ✅ Prerequisites

- **Python 3.12+**
- **PostgreSQL 16** (သို့မဟုတ် Docker Desktop)
- **Redis 7** (သို့မဟုတ် Docker Desktop)
- **Docker & Docker Compose** (Docker ဖြင့် လုပ်ဆောင်လိုပါက)

---

## 🚀 Installation & Setup

### Local Setup (venv)

```bash
# 1. Clone repository (အသစ်ဆိုလျှင်)
git clone git@github.com:thuta-developer/busgo-api.git
cd busgo-api

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file (template မှ copy)
cp .env.example .env
# ⚠️ .env ထဲရှိ values များကို မိမိ environment နှင့် ကိုက်ညီအောင် ပြင်ဆင်ပါ

# 5. Start PostgreSQL & Redis (Docker ဖြင့်)
docker-compose up -d db redis

# 6. Run database migrations
alembic upgrade head

# 7. Seed RBAC (permissions & roles)
python -m app.db.seed rbac

# 8. Create Super Admin
python -m app.db.seed create-admin --email admin@example.com --password YourStrongPassword123

# 9. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server ကို http://localhost:8000 တွင် ဖွင့်ပြီး
- **API Docs (Swagger UI):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/

### Docker Setup

```bash
# 1. .env file ပြင်ဆင်ပါ
cp .env.example .env

# 2. Build & Start all services (db, redis, api)
docker-compose up --build

# 3. Container များအတွင်းသို့ ဝင်ရောက်ပြီး Super Admin ဖန်တီးပါ
docker exec -it busgo_api python -m app.db.seed create-admin \
  --email admin@example.com \
  --password YourStrongPassword123
```

> **Note:** Docker entrypoint (`scripts/entrypoint.sh`) သည် container စတင်သည့်အခါ migrations + RBAC seed ကို အလိုအလျောက် လုပ်ဆောင်ပေးပါသည်။

### Makefile Commands

```bash
make install     # Install dev dependencies
make dev         # Start dev server (auto-reload)
make run         # Start production server
make migrate     # Run database migrations
make migration   # Create new migration (msg="name")
make test        # Run pytest
make lint        # Check linting (ruff)
make format      # Format code (ruff)
```

---

## ⚙️ Environment Variables

`.env` file တွင် အောက်ပါ variables များ လိုအပ်ပါသည်။

| Variable | Required | Default | Description |
|---|---|---|---|
| `PROJECT_NAME` | ❌ | `BusGo API` | Project Name |
| `VERSION` | ❌ | `1.0.0` | API Version |
| `API_V1_STR` | ❌ | `/api/v1` | API Prefix |
| `ENVIRONMENT` | ❌ | `development` | `development` / `production` |
| `DEBUG` | ❌ | `True` | Production တွင် `False` ဖြစ်ရမည် |
| `SECRET_KEY` | ✅ | — | JWT Secret (min 32 characters) |
| `ALGORITHM` | ❌ | `HS256` | JWT Algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `30` | Access Token Lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | `7` | Refresh Token Lifetime |
| `POSTGRES_SERVER` | ✅ | — | PostgreSQL Host |
| `POSTGRES_PORT` | ❌ | `5432` | PostgreSQL Port |
| `POSTGRES_USER` | ✅ | — | PostgreSQL User |
| `POSTGRES_PASSWORD` | ✅ | — | PostgreSQL Password |
| `POSTGRES_DB` | ✅ | — | PostgreSQL Database Name |
| `REDIS_HOST` | ❌ | `localhost` | Redis Host |
| `REDIS_PORT` | ❌ | `6379` | Redis Port |
| `REDIS_URL` | ✅ | — | Redis Connection URL |
| `ALLOWED_ORIGINS` | ✅ | — | CORS Origins (JSON array or comma-separated) |
| `ALLOWED_HOSTS` | ✅ | — | Allowed Hosts (JSON array or comma-separated) |
| `RATE_LIMIT_PER_MINUTE` | ❌ | `1440` | API Rate Limit |
| `CLOUDINARY_CLOUD_NAME` | ✅ | — | Cloudinary Cloud Name |
| `CLOUDINARY_API_KEY` | ✅ | — | Cloudinary API Key |
| `CLOUDINARY_API_SECRET` | ✅ | — | Cloudinary API Secret |

> **⚠️ Production Warning:** `ENVIRONMENT=production` ဖြစ်ပါက `DEBUG` သည် `False` ဖြစ်ရမည်။ `ALLOWED_ORIGINS` နှင့် `ALLOWED_HOSTS` တွင် `*` ကို ခွင့်မပြုပါ။

---

## 🗄️ Database Migrations

```bash
# Create new migration (auto-generate from model changes)
alembic revision --autogenerate -m "description"

# Apply all migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current version
alembic current

# Show history
alembic history
```

---

## 🌱 Database Seeding

### 1. RBAC Seeding (Permissions & Roles)

```bash
python -m app.db.seed rbac
```

- **Permissions** (40 ခု) — Dynamic ဖြင့် ထုတ်ပေးသည်:
  - Resources: `user`, `role`, `permission`, `bus`, `bus_company`, `route`, `trip`, `booking`, `payment`, `promotion`
  - Actions: `create`, `read`, `update`, `delete`
  - Format: `resource:action` (e.g. `bus:create`)

- **Default Roles** (4 ခု):

| Role | Permissions |
|---|---|
| **Super Admin** | `*` — အရာအားလုံး |
| **Manager** | user, bus, bus_company, route, trip, booking, payment, promotion အားလုံး (role & permission မှလွဲ၍) |
| **Counter Staff** | `bus:read`, `trip:read`, `booking:create`, `booking:read`, `booking:delete` |
| **Customer** | `trip:read`, `booking:create`, `booking:read` |

- Stale roles ရှင်းလင်းရန်: `python -m app.db.seed rbac --sync`

### 2. Create Super Admin

```bash
python -m app.db.seed create-admin \
  --email admin@example.com \
  --password YourStrongPassword123 \
  --name "System Admin" \
  --phone "09123456789"
```

Password ကို Prompt ဖြင့် ထည့်လိုပါက `--password` flag ချန်လှပ်နိုင်ပါသည်။

---

## 🔐 Authentication & RBAC

### Flow

1. **Register** → `/api/v1/auth/register`
2. **Login** → Access Token + Refresh Token ရရှိမည်
3. **Access Protected API** → `Authorization: Bearer <access_token>`
4. **Refresh Token** → Access Token သက်တမ်းကုန်ပါက Refresh Token ဖြင့် အသစ်ယူပါ
5. **Logout** → Token ကို Blacklist ထဲသို့ ထည့်ပြီး Revoke လုပ်ပါ

### Permission System

- Permission များကို `resource:action` ပုံစံဖြင့် သတ်မှတ်သည် (e.g. `trip:create`)
- Role တစ်ခုထဲသို့ Permissions များ Assign လုပ်နိုင်သည်
- User တစ်ဦးထဲသို့ Roles များ Assign လုပ်နိုင်သည်
- Endpoint တစ်ခုချင်းစီတွင် `has_permission("trip:create")` ဖြင့် စစ်ဆေးသည်

---

## 📚 API Documentation

Server စတင်ပြီးနောက် အောက်ပါ documentation များကို browser ဖြင့် ကြည့်ရှုနိုင်သည်:

| URL | Description |
|---|---|
| `http://localhost:8000/docs` | **Swagger UI** — Interactive testing |
| `http://localhost:8000/redoc` | **ReDoc** — Readable documentation |
| `http://localhost:8000/api/v1/openapi.json` | **OpenAPI JSON** — Machine-readable spec |

---

## 🔗 API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/register` | အကောင့်အသစ်ဖွင့်ရန် | ❌ |
| `POST` | `/login` | Login ဝင်ရန် (JWT Tokens) | ❌ |
| `POST` | `/refresh` | Access Token အသစ်ယူရန် | ❌ (Refresh Token) |
| `GET` | `/me` | လက်ရှိ user အချက်အလက် | ✅ |
| `POST` | `/logout` | Logout + Token Revoke | ✅ |

### Users Management (`/api/v1/users`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/` | Users List (Search/Filter/Paginate) | `user:read` |
| `GET` | `/{user_id}` | User Detail + Roles | `user:read` |
| `PUT` | `/{user_id}` | Update User | `user:update` |
| `DELETE` | `/{user_id}` | Delete User | `user:delete` |

### Roles Management (`/api/v1/roles`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `POST` | `/` | Create Role | `role:create` |
| `GET` | `/` | List Roles | `role:read` |
| `GET` | `/{role_id}` | Get Role Detail | `role:read` |
| `POST` | `/{role_id}/permissions` | Assign Permissions to Role | `role:update` |
| `POST` | `/users/{user_id}/assign-roles` | Assign Roles to User | `user:update` |
| `DELETE` | `/{role_id}` | Delete Role | `role:delete` |

### Permissions Management (`/api/v1/permissions`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `POST` | `/` | Create Permission | `permission:create` |
| `GET` | `/` | List Permissions (filter by module) | `permission:read` |
| `PUT` | `/{perm_id}` | Update Permission | `permission:update` |
| `DELETE` | `/{perm_id}` | Delete Permission | `permission:delete` |

### Bus Companies Management (`/api/v1/bus-companies`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/` | List Companies | `bus_company:read` |
| `GET` | `/{company_id}` | Get Company Detail | `bus_company:read` |
| `POST` | `/` | Create Company | `bus_company:create` |
| `PUT` | `/{company_id}` | Update Company | `bus_company:update` |
| `DELETE` | `/{company_id}` | Delete Company | `bus_company:delete` |
| `POST` | `/{company_id}/logo` | Upload Logo (Cloudinary) | `bus_company:update` |

### Buses Management (`/api/v1/buses`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/` | List Buses | `bus:read` |
| `GET` | `/{bus_id}` | Get Bus Detail | `bus:read` |
| `POST` | `/` | Create Bus | `bus:create` |
| `PUT` | `/{bus_id}` | Update Bus | `bus:update` |
| `DELETE` | `/{bus_id}` | Delete Bus | `bus:delete` |

### Seat Templates (`/api/v1/buses`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `POST` | `/{bus_id}/generate-seats` | Seat Layout အလိုအလျောက်ထုတ်ပေးခြင်း | `bus:update` |
| `GET` | `/{bus_id}/seats` | Bus ၏ Seat List | ❌ |

### Routes Management (`/api/v1/routes`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/` | List Routes | `route:read` |
| `GET` | `/cities/origins` | Unique Origins List | ❌ |
| `GET` | `/cities/destinations` | Unique Destinations List | ❌ |
| `GET` | `/{route_id}` | Get Route Detail | `route:read` |
| `POST` | `/` | Create Route | `route:create` |
| `PUT` | `/{route_id}` | Update Route | `route:update` |
| `DELETE` | `/{route_id}` | Delete Route | `route:delete` |

### Trips Management (`/api/v1/trips`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/` | List Trips (Search/Filter/Paginate) | `trip:read` |
| `GET` | `/{trip_id}` | Get Trip Detail | `trip:read` |
| `POST` | `/` | Create Trip | `trip:create` |
| `PUT` | `/{trip_id}` | Update Trip | `trip:update` |
| `DELETE` | `/{trip_id}` | Delete Trip | `trip:delete` |

#### Trip List Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `search` | `string` | Route သို့မဟုတ် Bus ဖြင့် ရှာဖွေခြင်း |
| `is_active` | `boolean` | Active Status Filter |
| `page` | `int` | Page Number (default: 1) |
| `size` | `int` | Page Size (default: 20, max: 100) |
| `include_bookable_only` | `boolean` | Bookable Schedules သာပြရန် (default: true) |
| `route_id` | `UUID` | Route ID Filter |
| `bus_id` | `UUID` | Bus ID Filter |
| `origin` | `string` | မည်သည့်မြို့မှ ထွက်ခွာသည် |
| `destination` | `string` | မည်သည့်မြို့သို့ ရောက်ရှိသည် |
| `travel_date` | `date` | ခရီးသွားမည့်နေ့ |
| `user_type` | `string` | `local` / `foreigner` (Price Type, default: local) |
| `time_of_day` | `string` | `morning` / `afternoon` / `night` |

---

## 🧪 Testing

```bash
# Run tests
pytest -v

# Run tests with coverage
pytest --cov=app --cov-report=html
```

---

## 🛡️ Security Features

1. **JWT Token Security**
   - Access Token: 30 minutes
   - Refresh Token: 7 days
   - Token Blacklist (Redis) — Logout ပြီးနောက် Token ကို Revoke ပြုလုပ်ခြင်း
   - `jti` (JWT ID) — Token တစ်ခုချင်းစီအတွက် Unique ID

2. **Password Security**
   - Bcrypt Hashing (Passlib)
   - Password ကို Plain Text ဖြင့် သိမ်းဆည်းခြင်းမရှိ

3. **HTTP Security Headers**
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy` — Camera, Microphone, Geolocation Blocked
   - `Strict-Transport-Security` (HSTS) — Production တွင်သာ

4. **Rate Limiting**
   - IP အလိုက် တစ်မိနစ် `RATE_LIMIT_PER_MINUTE` ကန့်သတ်ချက်
   - Redis Primary + In-Memory Fallback

5. **CORS & Host Validation**
   - `ALLOWED_ORIGINS` — Frontend Domains သာ ခွင့်ပြုခြင်း
   - `ALLOWED_HOSTS` — Trusted Hosts သာ ခွင့်ပြုခြင်း
   - Production တွင် `*` ခွင့်မပြု

6. **Production Hardening**
   - `DEBUG=False` ဖြစ်ရမည်
   - `SECRET_KEY` — အနည်းဆုံး 32 characters
   - Docker — Non-root user (`busgo`) ဖြင့် လုပ်ဆောင်ခြင်း

7. **GZip Compression**
   - Response size 1000 bytes နှင့်အထက် ကို Compress လုပ်ခြင်း

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 👨‍💻 Author

**Thuta Developer** — [GitHub](https://github.com/thuta-developer)

---

> **BusGo API** — Myanmar Bus Ticket Booking System Backend