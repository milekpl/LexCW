# Lexicographic Curation Workbench - Setup Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Modes](#installation-modes)
3. [Docker Mode Setup](#docker-mode-setup)
4. [Hybrid Mode Setup](#hybrid-mode-setup)
5. [Configuration](#configuration)
6. [Initial Data](#initial-data)
7. [Running the Application](#running-the-application)
8. [Testing the Setup](#testing-the-setup)
9. [Production Considerations](#production-considerations)
10. [Maintenance](#maintenance)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Recommended | Check Command |
|----------|-----------------|-------------|---------------|
| Docker | 20.10 | 24+ | `docker --version` |
| Docker Compose | 2.0 | v2+ | `docker-compose --version` |
| Python | 3.10 | 3.11 | `python3 --version` |
| Git | 2.0 | Latest | `git --version` |

### System Requirements

- **RAM:** 4GB minimum (8GB recommended)
- **Disk:** 2GB for application + data volumes
- **CPU:** 64-bit architecture

### Verify Prerequisites

```bash
# All checks
docker --version && echo "Docker OK"
python3 --version && echo "Python OK"
git --version && echo "Git OK"

# Docker daemon running
docker info && echo "Docker daemon OK"
```

---

## Installation Modes

### Docker Mode (Recommended)

All services run in isolated Docker containers:
- **PostgreSQL** - Dictionary analytics and worksets
- **Redis** - Caching and sessions
- **BaseX** - Primary XML dictionary data
- **Flask** - Web application

**Pros:**
- Consistent across environments
- Easy cleanup and restart
- Isolated from host system
- Reproducible deployments

**Cons:**
- More resources used
- Slightly slower on some operations
- Container management overhead

### Hybrid Mode

Services split between Docker and local:
- **PostgreSQL & Redis** - Docker containers
- **BaseX** - Local installation (for debugging, profiling)

**Use when:**
- Developing BaseX itself
- Need to attach debugger to BaseX
- Profiling BaseX performance
- Custom BaseX configuration

---

## Docker Mode Setup

### Step 1: Clone and Enter Repository

```bash
git clone https://github.com/your-org/dictionary-workbench.git
cd dictionary-workbench
```

### Step 2: Run Setup Script

```bash
./setup.sh
```

This script:
- Creates Python virtual environment
- Installs Python dependencies
- Creates `.env` from `.env.example`
- Starts Docker services
- Initializes PostgreSQL database
- Verifies all services

### Step 3: Start Application

```bash
python run.py
```

Access at http://localhost:5000

### Manual Steps (If Needed)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `.\venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start Docker services
docker-compose up -d

# Verify services
./scripts/verify-setup.sh
```

---

## Hybrid Mode Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/dictionary-workbench.git
cd dictionary-workbench
```

### Step 2: Download and Install BaseX

```bash
# Download latest BaseX
./scripts/download-basex.sh

# Verify installation
./basex/bin/version
```

### Step 3: Run Setup Script

```bash
./setup.sh --hybrid
```

This script:
- Creates Python virtual environment
- Installs Python dependencies
- Creates `.env` from `.env.example`
- Starts PostgreSQL & Redis via Docker only
- Downloads and configures BaseX (if not present)
- Verifies all services

### Step 4: Start BaseX Manually

```bash
# In one terminal - start BaseX server
./basex/bin/start

# In another terminal - start application
python run.py
```

Or use the combined script:
```bash
./start-services.sh
python run.py
```

---

## Configuration

### Environment Variables

All configuration is in `.env` file. Copy from template:

```bash
cp .env.example .env
```

#### Core Settings

```bash
# Flask
FLASK_ENV=development          # or production
SECRET_KEY=your-secret-key    # change in production!

# Database Connection (auto-configured by setup.sh)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dictionary_analytics
POSTGRES_USER=dict_user
POSTGRES_PASSWORD=change_me

# BaseX Connection
BASEX_HOST=localhost
BASEX_PORT=1984
BASEX_USERNAME=admin
BASEX_PASSWORD=admin
BASEX_DATABASE=dictionary

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### Production Settings

```bash
FLASK_ENV=production
SECRET_KEY=<generate-secure-random-key>
POSTGRES_PASSWORD=<strong-password>
BASEX_PASSWORD=<strong-password>
```

---

## Initial Data

### Database Structure

The PostgreSQL database includes:
- `dictionary` schema - Core dictionary tables
- `analytics` schema - Statistics and metrics
- `corpus` schema - Corpus integration tables
- Extensions: uuid-ossp, pg_trgm, pg_stat_statements

### Loading Sample Data

```bash
# With seed data (minimal - 1-2 entries for testing)
./scripts/init-postgres.sh --seed

# Structural only (empty database)
./scripts/init-postgres.sh
```

### Importing LIFT Data

```bash
# Import from LIFT file
python -m scripts.import_lift path/to/dictionary.lift [path/to/ranges.lift-ranges]

# Export to LIFT
python -m scripts.export_lift path/to/output.lift
```

---

## Running the Application

### Development Mode

```bash
python run.py
```

Features:
- Auto-reload on code changes
- Debug output
- Detailed error pages

### Production Mode

```bash
FLASK_ENV=production python run.py
```

Or with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

---

## Testing the Setup

### Quick Verification

```bash
./scripts/verify-setup.sh
```

Expected output:
```
PostgreSQL (dictionary_analytics):  ✓ Running
PostgreSQL (dictionary_test):       ✓ Running
BaseX Server:                       ✓ Running
Redis:                              ✓ Running
Flask App:                          ? Not started (run python run.py)
```

### Health Endpoints

When the application is running:

| Endpoint | Description |
|----------|-------------|
| http://localhost:5000/health | Application health |
| http://localhost:5000/ | Main application |
| http://localhost:5000/apidocs | API documentation |

### Manual Checks

```bash
# PostgreSQL
psql -h localhost -U dict_user -d dictionary_analytics -c "\dt"

# BaseX
curl http://localhost:1984/

# Redis
redis-cli ping
```

---

## Production Considerations

### Security

1. **Change all default passwords** in `.env`
2. **Use strong `SECRET_KEY`** (32+ random characters)
3. **Enable SSL/TLS** for production
4. **Restrict database access** by IP
5. **Use secrets management** (Docker secrets, Kubernetes secrets)

### Performance

1. **Increase connection pool:**
   ```bash
   POSTGRES_POOL_SIZE=20
   POSTGRES_MAX_OVERFLOW=40
   ```

2. **BaseX memory:**
   ```bash
   BASEX_JVM=-Xmx4g
   ```

3. **Redis persistence:**
   ```bash
   REDIS_APPENDONLY=yes
   ```

### Backup

See [docs/BACKUP_SYSTEM_IMPLEMENTATION_PLAN.md](BACKUP_SYSTEM_IMPLEMENTATION_PLAN.md)

### Monitoring

1. **Application logs:** `logs/app.log`
2. **Docker logs:** `docker-compose logs -f`
3. **BaseX logs:** `basex/logs/`

---

## Maintenance

### Updating Application

```bash
# Pull latest code
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart services
docker-compose restart flask_app
```

### Updating BaseX (Hybrid Mode)

```bash
./scripts/download-basex.sh
./basex/bin/stop
./basex/bin/start
```

### Database Migrations

```bash
# Apply any pending migrations
alembic upgrade head
```

### Viewing Logs

```bash
# Application logs
tail -f logs/app.log

# Docker container logs
docker-compose logs -f flask_app

# BaseX logs
tail -f basex/logs/basex.log
```

---

## Troubleshooting

### Docker Issues

```bash
# Container won't start
docker-compose logs <service-name>

# Out of disk space
docker system prune -a

# Reset all data
docker-compose down -v
docker-compose up -d
```

### PostgreSQL Connection

```bash
# Check if running
docker ps | grep postgres

# Test connection
docker exec -it dictionary_postgres psql -U dict_user -d dictionary_analytics

# View logs
docker-compose logs postgres
```

### BaseX Issues

```bash
# Check if running
./basex/bin/status

# View logs
cat basex/logs/basex.log

# Restart
./basex/bin/stop
./basex/bin/start
```

### Port Already in Use

```bash
# Find process using port
lsof -i :5432

# Kill process
kill <PID>
```

---

## Getting Help

- Check [docs/POSTGRESQL_WSL_SETUP.md](docs/POSTGRESQL_WSL_SETUP.md) for WSL-specific issues
- Check existing issues on GitHub
- Review application logs for error details
