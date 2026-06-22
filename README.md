# Job Scout

A self-service job search agent. Admin creates user accounts, users go through an AI-powered onboarding interview, and the system automatically finds jobs via SerpAPI, ranks them, tailors resumes using Claude, and saves outputs to Google Drive.

## Architecture

- **Frontend**: React + Tailwind CSS (Vite)
- **Backend**: Python FastAPI
- **Database**: PostgreSQL
- **Queue**: Redis + Celery + Celery Beat
- **Containers**: Docker Compose

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### 3. Create the admin account

```bash
docker compose exec backend python -m app.cli create-admin
```

### 4. Log in

Open http://localhost:3000 and log in with the admin credentials.

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start PostgreSQL and Redis locally, then:
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `localhost:8000`.

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### CLI Commands

```bash
# Create admin user
python -m app.cli create-admin

# Initialize database tables
python -m app.cli init-db
```

## API Keys Setup

### Anthropic API
1. Get an API key from https://console.anthropic.com
2. Set `ANTHROPIC_API_KEY` in `.env`

### SerpAPI
1. Sign up at https://serpapi.com
2. Set `SERPAPI_KEY` in `.env`

### Google APIs (Gmail + Drive)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable **Gmail API** and **Google Drive API**
4. Create OAuth 2.0 credentials (Desktop app type)
5. Download the credentials JSON
6. Run the initial OAuth flow locally to get a refresh token
7. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` in `.env`

## Deployment (Hostinger KVM VPS)

### Server Setup

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone the repo
git clone https://github.com/your-user/jobscout.git /opt/jobscout
cd /opt/jobscout
cp .env.example .env
# Edit .env with production values

# Start
docker compose up -d --build

# Create admin
docker compose exec backend python -m app.cli create-admin
```

### SSL with Certbot

```bash
apt install certbot
certbot certonly --standalone -d your-domain.com
# Copy deploy/nginx.conf to /etc/nginx/sites-available/ and update domain
```

### Firewall

```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable
```

### Nightly Backups

```bash
chmod +x deploy/backup.sh
crontab -e
# Add: 0 2 * * * /opt/jobscout/deploy/backup.sh
```

### Deploy Updates

```bash
ssh root@your-vps-ip /opt/jobscout/deploy/deploy.sh
```

## Project Status

- [x] Phase 1: Foundation (auth, user management, DB, Docker, UI skeleton)
- [ ] Phase 2: Onboarding (resume upload, AI interview, criteria)
- [ ] Phase 3: Job Scanner (SerpAPI integration)
- [ ] Phase 4: Resume Tailor (Anthropic API + docx generation)
- [ ] Phase 5: Email Notifications (Gmail API)
- [ ] Phase 6: Feedback Loop (preference profiling)
- [ ] Phase 7: Production Deployment & CI
