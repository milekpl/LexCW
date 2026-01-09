# Lexicographic Curation Workbench - Installation Guide

## Quick Start

```bash
git clone https://github.com/your-org/dictionary-workbench.git
cd dictionary-workbench
./setup.sh
python run.py
```

Then open http://localhost:5000

---

## Prerequisites

- **Docker** (20.10+) with Docker Compose (v2+)
- **Python** 3.10+
- **Git**
- **4GB RAM** minimum

Check prerequisites:
```bash
docker --version          # Should be 20.10+
python3 --version         # Should be 3.10+
git --version
```

---

## Installation Modes

### Docker Mode (Recommended)

All services run in containers:
- PostgreSQL, Redis, BaseX, Flask

```bash
# Step 1: Setup (install deps, configure, init databases)
./setup.sh

# Step 2: Start services
docker-compose up -d

# Step 3: Run app
python run.py
```

### Hybrid Mode

- PostgreSQL & Redis via Docker
- BaseX runs locally (for development/debugging)

```bash
# Step 1: Setup
./setup.sh --hybrid

# Step 2: Start PostgreSQL & Redis only
docker-compose up -d postgres redis

# Step 3: Start BaseX locally
./start-services.sh

# Step 4: Run app
python run.py
```

---

## Troubleshooting

### Services won't start

```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs

# Restart services
docker-compose restart
```

### Connection refused

```bash
# Verify services are running
./scripts/verify-setup.sh

# Check ports
netstat -tlnp | grep -E '5432|6379|1984|5000'
```

### PostgreSQL connection issues

See [docs/POSTGRESQL_WSL_SETUP.md](docs/POSTGRESQL_WSL_SETUP.md)

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL server |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `BASEX_HOST` | `localhost` | BaseX server |
| `BASEX_PORT` | `1984` | BaseX port |
| `REDIS_HOST` | `localhost` | Redis server |
| `FLASK_ENV` | `development` | `development` or `production` |

---

## More Information

- Full setup guide: [docs/setup-guide.md](docs/setup-guide.md)
- API documentation: Available at http://localhost:5000/apidocs when app is running
