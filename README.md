# DSMI Agent - Deep Search Market Intelligence

A sophisticated multi-agent AI system for deep market research, competitive analysis, and strategic intelligence gathering.

## 🎯 Overview

DSMI Agent combines multiple specialized AI agents (Researcher, Planner, Analyst, Critic, Publisher) with advanced tools to conduct comprehensive market research and generate actionable insights.
**Deployment Options**: 
- **Google Cloud Platform** (Cloud Run, App Engine, Compute Engine)
- **100% Free Stack** (Vercel, Render, Neon, Upstash, Qdrant Cloud)
## 📊 Key Features

- 🤖 **Multi-Agent Architecture**: Researcher, Planner, Analyst, Critic, Publisher agents working in concert
- 🔍 **Deep Research Capabilities**: Web scraping, PDF analysis, vector search, competitive intelligence
- 📈 **Real-time Progress Streaming**: Server-Sent Events (SSE) for live updates
- 🔐 **Enterprise Security**: API key auth, JWT tokens, rate limiting
- ⚡ **Async-First Design**: Built with FastAPI and asyncio for high performance
- 🌩️ **Cloud-Native**: Serverless deployment on Google Cloud with auto-scaling
- 📊 **Production Ready**: Health checks, monitoring, structured logging

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Account (with billing enabled)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- PostgreSQL 15+ (Cloud SQL or self-managed)
- Redis 7.0+ (Memorystore or self-managed)
- Qdrant vector database

### Local Development

1. **Clone and setup**:
   ```bash
   git clone YOUR_REPO
   cd dsmi_agent
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Start services** (PostgreSQL, Redis, Qdrant):
   ```bash
   # Ensure these are running on localhost
   # PostgreSQL: localhost:5432
   # Redis: localhost:6379
   # Qdrant: localhost:6333
   ```

5. **Run the API**:
   ```bash
   uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Test the API**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

## 🌐 Cloud Deployment

### Option 1: 100% Free Stack (Recommended for Hobbyists)

**No credit card required. Hosted on Vercel, Render, Neon, Upstash, and Qdrant.**

See [FREE_DEPLOYMENT.md](FREE_DEPLOYMENT.md) for detailed step-by-step instructions on setting up this completely free architecture.

---

### Option 2: Google Cloud Run (Enterprise - Serverless)

**Fastest to deploy on GCP, auto-scales, scales to zero when idle.**

```bash
# 1. Setup infrastructure
./setup-gcp.sh  # macOS/Linux
setup-gcp.bat   # Windows

# 2. Build Docker image
docker build -f Dockerfile.cloudrun -t gcr.io/PROJECT_ID/dsmi-api:latest .

# 3. Push to Cloud Registry
docker push gcr.io/PROJECT_ID/dsmi-api:latest

# 4. Deploy to Cloud Run
gcloud run deploy dsmi-api \
  --image gcr.io/PROJECT_ID/dsmi-api:latest \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --allow-unauthenticated
```

See [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) for detailed instructions on all GCP deployment options.

### Option 3: App Engine

```bash
gcloud app deploy
```

### Option 4: Compute Engine (VMs)

```bash
gcloud compute instances create dsmi-vm \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-standard-2
```

### Option 5: Google Kubernetes Engine (GKE)

```bash
kubectl apply -f gcp-deploy.yaml
```

## 📚 API Documentation

### Base URL

```
https://dsmi-api-xxx.run.app/
```

### Authentication

Generate an API key:
```bash
curl -X POST https://dsmi-api-xxx.run.app/api/v1/auth/api-key \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-integration",
    "expires_in_days": 365
  }'
```

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/research` | Start new research task |
| `GET` | `/api/v1/research/{id}` | Get research status |
| `GET` | `/api/v1/research/{id}/report` | Get completed report |
| `GET` | `/api/v1/research/{id}/stream` | Stream progress (SSE) |
| `DELETE` | `/api/v1/research/{id}` | Cancel research |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/health/live` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe |

### Example: Start Research

```bash
curl -X POST https://dsmi-api-xxx.run.app/api/v1/research \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze the AI safety landscape in Europe",
    "max_iterations": 3,
    "depth": 2,
    "format": "markdown"
  }'
```

Response:
```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_time_seconds": 180,
  "stream_url": "/api/v1/research/550e.../stream"
}
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│           Google Cloud Platform                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────┐      │
│  │  Cloud Run (FastAPI)                     │      │
│  │  • Auto-scales 0→100+ instances          │      │
│  │  • Pay per request                       │      │
│  │  • Managed containers                    │      │
│  └──────────────────────────────────────────┘      │
│                      │                              │
│       ┌──────────────┼──────────────┐               │
│       │              │              │               │
│  ┌────▼───┐   ┌─────▼─────┐   ┌───▼────┐          │
│  │ Cloud  │   │ Memorystore│   │ Qdrant │          │
│  │  SQL   │   │  (Redis)   │   │(Vector)│          │
│  └────────┘   └────────────┘   └────────┘          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 📝 Configuration

All configuration via environment variables in `.env`:

```bash
# Deployment
ENV=production
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dsmi

# Cache
REDIS_URL=redis://user:pass@host:6379/0

# Vector DB
QDRANT_URL=http://host:6333

# Security
JWT_SECRET_KEY=your-secret-key-min-32-chars
ADMIN_API_KEY=your-admin-key

# CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

See [.env.example](.env.example) for all options.

## 🔍 Monitoring & Logging

### Google Cloud Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 50 \
  --format json

# Real-time logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 50 \
  --follow
```

### Metrics & Alerts

Monitor performance:
- Request count, latency, error rate
- Memory and CPU utilization
- Database connection pool status
- Redis cache hit rate

Set up alerts for:
- Error rate > 5%
- Latency p95 > 5s
- Database connection errors
- Out of memory

## 🧪 Testing

```bash
# Unit tests (Add your tests to the tests/ directory)
pytest tests/

# Integration tests
pytest tests/ -v --tb=short

# Load testing
locust -f tests/load_test.py --host=https://dsmi-api-xxx.run.app/
```

## 📊 Project Structure

```
dsmi_agent/
├── api/                      # FastAPI backend application
│   ├── server.py             # FastAPI app entry point
│   ├── auth.py               # Authentication logic
│   └── schemas.py            # API models
├── frontend/                 # Next.js web interface
├── agents/                   # LLM agents (Researcher, Planner, Analyst, etc.)
├── tools/                    # Research tools (Scraper, Search, Vector DB)
├── database/                 # PostgreSQL database layer
├── graph/                    # Workflow definitions and state management
├── schemas/                  # Shared data schemas
├── app.yaml                  # App Engine config
├── cloudbuild.yaml           # Cloud Build CI/CD
├── Dockerfile.cloudrun       # Serverless container
├── gcp-deploy.yaml           # GKE/Kubernetes
├── setup-gcp.sh              # Setup script (macOS/Linux)
├── setup-gcp.bat             # Setup script (Windows)
├── CLOUD_DEPLOYMENT.md       # Detailed deployment guide for GCP
├── FREE_DEPLOYMENT.md        # Detailed deployment guide for Free Stack
└── requirements.txt          # Python dependencies
```

## 🔐 Security

- **API Key Authentication**: Issue and revoke API keys
- **JWT Tokens**: 24-hour expiry with refresh
- **Rate Limiting**: 100 requests/minute per API key
- **CORS Protection**: Configurable allowed origins
- **Secret Management**: Google Cloud Secret Manager
- **HTTPS/TLS**: Automatic with Cloud Run
- **Audit Logging**: Structured request/response logs

## 🚨 Troubleshooting

### Cloud Run container won't start
```bash
# Check error logs
gcloud run services describe dsmi-api --format='value(status.conditions[0].message)'

# Test locally first
docker build -f Dockerfile.cloudrun -t dsmi-api:test .
docker run -p 8080:8080 dsmi-api:test
```

### Database connection issues
```bash
# Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT_ID:us-central1:dsmi-postgres &
```

### See [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) for more troubleshooting

## 📈 Cost Optimization

- **Cloud Run**: Free tier includes 2M requests/month
- **Cloud SQL**: Micro instances start at ~$10/month
- **Redis**: 1GB instance ~$12/month
- **Set spending alerts** to prevent surprises

```bash
gcloud billing budgets create \
  --billing-account ACCOUNT_ID \
  --display-name "DSMI Agent Budget" \
  --budget-amount 200
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes in the respective directories (`api/`, `frontend/`, `agents/`, etc.)
3. Run tests: `pytest`
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file

## 📞 Support

- **Documentation**: See [FREE_DEPLOYMENT.md](FREE_DEPLOYMENT.md) or [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)
- **Issues**: GitHub Issues
- **GCP Docs**: https://cloud.google.com/docs

---

**Last Updated**: March 2025
**Status**: Production Ready
**Deployment**: Google Cloud Platform ☁️
