# Blood Relay Backend

A production-grade, modular FastAPI backend powering the **Blood Relay Citizen App (React Native)** and **Hospital Dashboard (React)**. Features PostgreSQL database persistence, JWT Authentication, Role-Based Access Control, Geo-Spatial Search (Haversine Formula), and an AI Matching Engine for intelligent donor and inventory recommendations.

---

## 🛠️ Tech Stack

- **Python 3.12+ / 3.13**
- **FastAPI** (Async ASGI Web Framework)
- **SQLAlchemy 2.0** (ORM Engine & Models)
- **PostgreSQL 16** (Primary Relational Database)
- **Pydantic v2 & pydantic-settings** (Validation & Settings Management)
- **python-jose & bcrypt** (JWT Token Authentication & Password Hashing)
- **Uvicorn** (ASGI Web Server)
- **Faker** (Realistic Seeding Engine)

---

## 📁 Folder Structure

```
blood-relay-backend/
│
├── app/
│   ├── main.py                   # FastAPI Application Entry Point & Router Registrations
│   ├── config.py                 # Pydantic Settings loading .env configuration
│   ├── database.py               # PostgreSQL Engine, SessionLocal, & Base class
│   ├── auth.py                   # Password hashing, JWT token encoding, & RBAC dependencies
│   ├── enums.py                  # Domain Enums (RoleEnum, BloodGroupEnum, RequestStatusEnum, MatchStatusEnum)
│   ├── models.py                 # SQLAlchemy 2.0 ORM Entities & Soft Delete Mixins
│   ├── schemas.py                # Pydantic DTO validation & response schemas
│   ├── seed.py                   # Database Seeder script (python -m app.seed)
│   │
│   ├── routes/                   # Modular API Routers
│   │   ├── auth.py               # /auth/register, /auth/login, /auth/me
│   │   ├── donors.py             # /donors CRUD API (Owner-protected)
│   │   ├── hospitals.py          # /hospitals CRUD API
│   │   ├── inventory.py          # /inventory CRUD API (Blood Bank restricted)
│   │   ├── requests.py           # /requests CRUD API (Hospital restricted status updates)
│   │   ├── search.py             # GET /search (Geo-spatial radius radius search)
│   │   └── ai.py                 # POST /ai/match/{request_id} (AI Recommendation Engine)
│   │
│   └── services/
│       └── matching_service.py   # AI Donor Scoring Algorithm & Compatibility Matrix
│
├── requirements.txt              # Production dependency manifest
├── .env.example                  # Environment variable configuration template
├── .gitignore                    # Git tracking ignore rules
└── README.md                     # System documentation & Frontend Handoff Guide
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12+ installed
- PostgreSQL 16 server running locally or via Docker

### 2. Virtual Environment Setup

```bash
cd blood-relay-backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Ensure your PostgreSQL `DATABASE_URL` is configured in `.env`:
```env
DATABASE_URL=postgresql://localhost:5432/blood_relay_db
```

### 5. Seed the Database

Populate PostgreSQL with 50 Users, 35 Donors, 10 Hospitals, 5 Blood Banks, 200 Inventories, and 20 Requests:

```bash
python -m app.seed
```

### 6. Run the Uvicorn Server

```bash
uvicorn app.main:app --reload
```

---

## 🔗 Documentation & API Base URLs

- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
- **OpenAPI JSON Schema**: `http://127.0.0.1:8000/openapi.json`
- **Health Check**: `GET http://127.0.0.1:8000/health`

---

## 🔑 Authentication & Security Flow

1. **Register**: `POST /auth/register`
   - Accepts `full_name`, `email`, `phone_number`, `password`, `role` (`citizen`, `hospital`, `blood_bank`, `admin`).
2. **Login**: `POST /auth/login`
   - Accepts JSON payload OR Form Data (`username`/`password` for Swagger UI compatibility).
   - Returns JWT Bearer `access_token`.
3. **Authenticated Requests**:
   - Pass header: `Authorization: Bearer <access_token>`
4. **Current User Profile**: `GET /auth/me`

---

## 🔍 Geo-Spatial Search API

`GET /search?blood_group=O%2B&latitude=12.9716&longitude=77.5946&radius=10`

- Uses the **Haversine Formula** to compute great-circle distance in kilometers:
  $$d = 2 \cdot 6371 \cdot \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
- Returns matching Blood Bank stock and available Donors sorted by nearest distance (`distance_km` ascending).

---

## 🧠 AI Matching & Recommendation Engine

`POST /ai/match/{request_id}`

1. **Inventory Sufficiency Check**:
   - Evaluates Blood Bank stock matching compatible blood groups.
   - If stock $\ge$ required units: Returns nearest Blood Bank (`recommended_source: "blood_bank"`).
2. **4-Tier Donor Scoring Engine** (Max 100 Points):
   - **Availability**: 40 pts
   - **Proximity**: $<5$km (30 pts), $5-10$km (20 pts), $10-20$km (10 pts), $>20$km (0 pts)
   - **Response Rate**: $\ge 95\%$ (20 pts), $80-95\%$ (15 pts), $60-80\%$ (10 pts), $<60\%$ (5 pts)
   - **Donation Recency**: $>120$ days (10 pts), $90-120$ days (8 pts), $60-90$ days (5 pts), $<60$ days (0 pts)
3. **Medical Compatibility Matrix**:
   - `A+` $\rightarrow$ `['A+', 'A-', 'O+', 'O-']`
   - `AB+` $\rightarrow$ `['AB+', 'AB-', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-']`
4. Returns **Top 5 ranked donors** with detailed bullet point score reason breakdowns.

---

## 💻 Frontend Integration Guide (Handoff)

### Base Configuration
- **Base URL**: `http://127.0.0.1:8000`
- **Headers**:
  ```json
  {
    "Content-Type": "application/json",
    "Authorization": "Bearer <YOUR_JWT_ACCESS_TOKEN>"
  }
  ```

### Key Demo Accounts (Pre-Seeded)
- **Hospital Demo Account**: `email: hosp@test.com`, `password: password123`
- **Blood Bank Demo Account**: `email: bloodbank@test.com`, `password: password123`
- **Citizen Demo Account**: `email: citizen1@test.com`, `password: password123`

### Common HTTP Status Codes
- `200 OK`: Request succeeded.
- `201 Created`: Resource created.
- `400 Bad Request`: Invalid request body or parameter validation error.
- `401 Unauthorized`: Token missing, invalid, or expired.
- `403 Forbidden`: Role permission restriction or non-owner resource edit attempt.
- `404 Not Found`: Resource does not exist or soft-deleted.
- `409 Conflict`: Duplicate email or phone number during registration.
