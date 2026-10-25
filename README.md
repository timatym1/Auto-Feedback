# AutoFeedback

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white" alt="Telegram Bot" />
  <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/TaskIQ-Async-6C63FF" alt="TaskIQ" />
  <img src="https://img.shields.io/badge/Status-Active%20Prototype-00C853" alt="Status" />
</p>

<p align="center">
  <a href="#-overview"><img src="https://img.shields.io/badge/Overview-Read%20More-0A66C2?style=for-the-badge" alt="Overview" /></a>
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-Run%20Now-FF6B35?style=for-the-badge" alt="Quick Start" /></a>
  <a href="#-api"><img src="https://img.shields.io/badge/API-End%20points-8A2BE2?style=for-the-badge" alt="API" /></a>
</p>

<div align="center">

```text
╔══════════════════════════════════════════════════════════════╗
║                    AUTOFEEDBACK                         ║
║          NPS • Review Automation • Customer Insight      ║
╚══════════════════════════════════════════════════════════════╝
```

</div>

AutoFeedback is a Telegram-first NPS and review automation platform for businesses that want to collect customer feedback, improve service quality, and turn happy customers into public reviews without friction.

Instead of relying on manual follow-ups, the system automatically schedules satisfaction surveys, sends them via Telegram, captures ratings, and guides satisfied customers to Google or 2GIS review pages while escalating negative feedback directly to the business owner.

## Why teams use AutoFeedback

- Collect customer satisfaction in real time after a visit or service interaction
- Reduce manual work with automated survey scheduling
- Turn happy customers into positive reviews on Google and 2GIS
- Handle negative feedback quickly with direct escalation to management
- Monitor subscription health and tenant lifecycle with a clean backend flow
- Keep everything fast and reliable with async processing and background workers

## Demo flow

```text
Customer visit
      ↓
Business schedules feedback trigger
      ↓
AutoFeedback sends Telegram NPS message
      ↓
Customer rates 1–5 stars
      ├─ 4–5 → redirect to review links + discount promo
      └─ 1–3 → capture complaint and alert business owner
```

## Feature highlights

### 📊 NPS survey engine
- Send a 1-to-5 customer satisfaction survey directly to Telegram
- Track survey status: pending, sent, completed, failed, escalated
- Delayed triggers using scheduled response logic

### ⚡ Background automation
- Async task processing through TaskIQ and Redis
- FastAPI API for scheduling review requests
- Long polling and webhook deployment modes supported

### 🏢 Multi-tenant architecture
- Support for multiple companies / tenants
- Independent subscription lifecycle and business ownership mapping
- Clean separation between client records, reports, and tenant logic

### 📍 Review funnel optimization
- High-score responses help customers leave public feedback on Google or 2GIS
- Bonus flow for positive reviews and brand advocacy
- Direct feedback loop for service recovery and reputation improvement

### 🔔 Escalation system
- Negative feedback is captured as a complaint reason
- Alerts are sent to the company director in Telegram
- Enables fast issue handling before problems spread online

## Tech stack

- Python 3.11+
- FastAPI
- Aiogram 3
- SQLAlchemy 2
- PostgreSQL
- Redis
- TaskIQ
- Docker / Docker Compose
- Alembic

## Repository structure

```text
Auto-Feedback/
├── .env.example                # Example environment variables
├── alembic/                    # Database migrations
├── config/
│   └── settings.py             # Application settings and config
├── database/
│   ├── models.py               # SQLAlchemy models
│   ├── session.py              # DB session setup
│   └── unit_of_work.py         # Transaction pattern
├── filters/
├── handlers/
│   ├── client.py               # Customer feedback interaction flow
│   └── creator.py              # Creator / admin commands
├── keyboards/
├── middlewares/
├── schemas/
├── services/
│   ├── client_service.py
│   ├── feedback_service.py
│   ├── taskiq_broker.py
│   ├── tasks.py                # Telegram NPS sender task
│   └── tenant_service.py
├── src/
│   └── app.py                 # FastAPI application + bot startup
├── docker-compose.yml
├── dockerfile
├── main.py                     # Local bot startup entrypoint
├── requirements.txt
├── todo.md
├── README.md
└── .gitignore
```

## Quick start

### 1) Clone the repository

```bash
git clone https://github.com/timatym1/Auto-Feedback.git
cd Auto-Feedback
```

### 2) Configure environment variables

Copy the example environment file and update it with your credentials.

```bash
cp .env.example .env
```

Example values:

```env
ENV=development
DEBUG=true
CREATOR_ID=123456789
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz_123456
USE_WEBHOOK=false
POSTGRES_USER=nps_user
POSTGRES_PASSWORD=nps_password_secure
POSTGRES_DB=nps_engine_db
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4) Run the app locally

#### Long polling mode

```bash
python main.py
```

#### Webhook mode

```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

### 5) Run with Docker Compose

```bash
docker compose up --build -d
```

This starts:
- PostgreSQL
- Redis
- FastAPI app
- TaskIQ worker

## API

The service exposes a feedback scheduling endpoint for triggering future NPS messages.

### Schedule a survey

Endpoint:

```http
POST /api/v1/feedback/schedule
```

Example request:

```json
{
  "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "tg_user_id": 123456789,
  "client_phone": "+77051234567",
  "delay_minutes": 120
}
```

Example response:

```json
{
  "status": "success",
  "task_id": "<task-id>",
  "scheduled_at": "2026-10-25T18:00:00+00:00"
}
```

### Health check

```http
GET /health
```

## Business workflow

```text
1. A tenant is created with company metadata and director Telegram ID
2. A client is linked to the tenant and Telegram user ID
3. The API creates a pending feedback report
4. A background TaskIQ job sends the Telegram NPS survey
5. Customer chooses a score between 1 and 5
6. The app reacts based on the score:
   - 4–5 → redirect to review platforms + offer
   - 1–3 → collect complaint and notify management
```

## Why this project matters

Local businesses often lose repeat customers because they do not get structured feedback at the right moment. AutoFeedback helps close that gap by after-visit automation, clear reputation-building flows, and fast issue resolution. It is built for small and medium businesses that want to improve service quality without expensive enterprise tooling.

## Roadmap

- Add admin dashboard for tenants and analytics
- Expand review destinations and campaign logic
- Add richer reporting and NPS trend charts
- Support multiple languages for customer messaging
- Improve webhook security and deployment hardening

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your improvements
4. Open a pull request with a clear description

## Contact

For questions or collaboration, reach out via the repository owner or the project maintainer.

---

<p align="center">
  <strong>AutoFeedback</strong> — Smart NPS automation for customer experience and reputation growth.
</p>
