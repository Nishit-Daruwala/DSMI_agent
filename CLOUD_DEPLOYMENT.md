# 🚀 Google Cloud Deployment Guide

This document covers deploying the DSMI Agent API to **Google Cloud Platform** using multiple options.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Option 1: Cloud Run (Recommended - Serverless)](#option-1-cloud-run-recommended---serverless)
- [Option 2: App Engine](#option-2-app-engine)
- [Option 3: Compute Engine (VM)](#option-3-compute-engine-vm)
- [Option 4: Kubernetes Engine (GKE)](#option-4-kubernetes-engine-gke)
- [Infrastructure Setup](#infrastructure-setup)
- [Environment Variables](#environment-variables)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and configured
   ```bash
   # Install gcloud: https://cloud.google.com/sdk/docs/install
   gcloud init
   gcloud auth login
   ```
3. **Docker** installed locally (for building and testing)
4. **Project created in GCP**:
   ```bash
   gcloud projects create dsmi-agent --name="DSMI Agent"
   gcloud config set project dsmi-agent
   ```

---

## Option 1: Cloud Run (Recommended - Serverless)

**Cloud Run** is ideal for API workloads with variable traffic. It's fastest to deploy and scales automatically.

### 1.1 Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 1.2 Build and Deploy

#### Manual Deployment (Quick)

```bash
# Build the image
docker build -f Dockerfile.cloudrun -t gcr.io/PROJECT_ID/dsmi-api:latest .

# Push to Container Registry
docker push gcr.io/PROJECT_ID/dsmi-api:latest

# Deploy to Cloud Run
gcloud run deploy dsmi-api \
  --image gcr.io/PROJECT_ID/dsmi-api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 100 \
  --min-instances 1
```

#### Automated with Cloud Build (CI/CD)

```bash
# Create a trigger from your Git repository
gcloud builds submit --config cloudbuild.yaml

# Or set up automatic builds on push
gcloud builds connect --repo-name=dsmi --repo-owner=YOUR_GITHUB
```

### 1.3 Set Environment Variables

Store secrets in Secret Manager:

```bash
# Create secrets
echo "postgresql+asyncpg://user:pass@db:5432/dsmi" | \
  gcloud secrets create DATABASE_URL --data-file=-

echo "redis://cache:6379/0" | \
  gcloud secrets create REDIS_URL --data-file=-

echo "your-long-random-jwt-secret" | \
  gcloud secrets create JWT_SECRET_KEY --data-file=-

# Grant Cloud Run service account access
gcloud run services update dsmi-api \
  --set-env-vars="DATABASE_URL=projects/PROJECT_ID/secrets/DATABASE_URL/versions/latest"
```

Or set directly:

```bash
gcloud run deploy dsmi-api \
  --set-env-vars DATABASE_URL="..." \
  --set-env-vars REDIS_URL="..." \
  --set-env-vars JWT_SECRET_KEY="..."
```

### 1.4 Verify Deployment

```bash
# Get the service URL
gcloud run services describe dsmi-api --format='value(status.url)'

# Test the health endpoint
curl https://dsmi-api-xxx.run.app/api/v1/health
```

---

## Option 2: App Engine

**App Engine** provides automatic scaling and traffic splitting for gradual rollouts.

### 2.1 Enable Required APIs

```bash
gcloud services enable appengine.googleapis.com
```

### 2.2 Deploy

```bash
# Deploy using app.yaml
gcloud app deploy --version production

# Check status
gcloud app describe

# View logs
gcloud app logs read -n 50
```

### 2.3 Traffic Splitting (Canary Deployment)

```bash
# Deploy new version
gcloud app deploy --version v2

# Route 10% traffic to v2, 90% to v1
gcloud app services set-traffic default \
  --splits v1=0.9,v2=0.1 \
  --split-by random
```

---

## Option 3: Compute Engine (VM)

For more control over infrastructure and long-running processes.

### 3.1 Create an Instance

```bash
gcloud compute instances create dsmi-api-vm \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-standard-2 \
  --zone=us-central1-a \
  --scopes=cloud-platform
```

### 3.2 Connect and Deploy

```bash
# SSH into the instance
gcloud compute ssh dsmi-api-vm --zone=us-central1-a

# Inside the VM:
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv git

# Clone your repository
git clone YOUR_REPO
cd YOUR_REPO

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt gunicorn

# Create systemd service for auto-restart
sudo nano /etc/systemd/system/dsmi-api.service
```

### 3.3 Systemd Service File

```ini
[Unit]
Description=DSMI Agent API
After=network.target

[Service]
Type=notify
User=dsmi
WorkingDirectory=/home/dsmi/dsmi-agent
Environment="PATH=/home/dsmi/dsmi-agent/venv/bin"
ExecStart=/home/dsmi/dsmi-agent/venv/bin/gunicorn \
  --workers 4 \
  --bind 0.0.0.0:8080 \
  --timeout 300 \
  api.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3.4 Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable dsmi-api
sudo systemctl start dsmi-api
sudo journalctl -u dsmi-api -f
```

---

## Option 4: Kubernetes Engine (GKE)

For production-grade orchestration with auto-scaling and high availability.

### 4.1 Create a GKE Cluster

```bash
gcloud container clusters create dsmi-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 10 \
  --enable-stackdriver-kubernetes
```

### 4.2 Deploy Using Kubectl

```bash
# Get cluster credentials
gcloud container clusters get-credentials dsmi-cluster --zone us-central1-a

# Create namespace
kubectl create namespace dsmi

# Create secrets
kubectl create secret generic dsmi-secrets \
  --from-literal=database-url='...' \
  --from-literal=redis-url='...' \
  --from-literal=qdrant-url='...' \
  --from-literal=jwt-secret='...' \
  -n dsmi

# Deploy using the Kubernetes manifest
kubectl apply -f gcp-deploy.yaml -n dsmi

# Check deployment
kubectl get pods -n dsmi
kubectl logs -n dsmi POD_NAME
```

---

## Infrastructure Setup

### Database: Cloud SQL

```bash
# Create PostgreSQL instance
gcloud sql instances create dsmi-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create dsmi_agent --instance=dsmi-postgres

# Create user
gcloud sql users create dsmi_user \
  --instance=dsmi-postgres \
  --password=randompassword

# Get connection string
gcloud sql instances describe dsmi-postgres --format='value(connectionName)'
```

### Caching: Memorystore for Redis

```bash
gcloud services enable redis.googleapis.com

# Create Redis instance
gcloud redis instances create dsmi-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=7.0 \
  --tier=basic
```

### Vector DB: Qdrant on Compute Engine or GKE

```bash
# Option 1: Docker on Compute Engine
gcloud compute instances create-with-container qdrant-vm \
  --container-image=qdrant/qdrant:latest \
  --container-port=6333 \
  --machine-type=e2-standard-2 \
  --zone=us-central1-a

# Option 2: GKE deployment (add to gcp-deploy.yaml)
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qdrant
spec:
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        volumeMounts:
        - name: qdrant-data
          mountPath: /qdrant/storage
      volumes:
      - name: qdrant-data
        persistentVolumeClaim:
          claimName: qdrant-pvc
EOF
```

---

## Environment Variables

Use **Cloud Secret Manager** for sensitive data:

```bash
# Create secrets
gcloud secrets create PROD_DATABASE_URL --data-file=- << EOF
postgresql+asyncpg://user:pass@10.0.0.5:5432/dsmi
EOF

gcloud secrets create PROD_JWT_SECRET_KEY --data-file=- << EOF
your-super-secret-key-minimum-32-chars
EOF

# For Cloud Run
gcloud run deploy dsmi-api \
  --set-env-vars PROD_DATABASE_URL=projects/PROJECT_ID/secrets/PROD_DATABASE_URL/versions/latest
```

Or use a `.env.production` file for non-sensitive variables and load secrets at runtime.

---

## Monitoring & Logging

### Enable Cloud Logging

```bash
# View logs in real-time
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dsmi-api" \
  --limit 50 \
  --format json

# Create custom metrics
gcloud logging sinks create dsmi-metrics \
  logging.googleapis.com/projects/PROJECT_ID/logs/dsmi-api
```

### Setup Alerts

```bash
# Create an alert policy
gcloud alpha monitoring policies create \
  --notification-channels CHANNEL_ID \
  --display-name "DSMI API Error Rate" \
  --condition-display-name "Error rate > 5%" \
  --condition-threshold-value 0.05
```

### Application Performance Monitoring (APM)

Add to your FastAPI app:

```python
from google.cloud import trace_v2
from opencensus.trace import config_integration

config_integration.trace_integrations(['fastapi'])
tracer = trace_v2.TraceServiceClient()
```

---

## Troubleshooting

### Cloud Run Container Won't Start

```bash
# View detailed error logs
gcloud run services describe dsmi-api --format='value(status.conditions[0].message)'

# Test locally first
docker build -f Dockerfile.cloudrun -t dsmi-api:test .
docker run -p 8080:8080 \
  -e DATABASE_URL="..." \
  -e REDIS_URL="..." \
  dsmi-api:test
```

### Timeout Issues

Increase timeout in Cloud Run:

```bash
gcloud run deploy dsmi-api --timeout 300s
```

### Out of Memory

Increase memory allocation:

```bash
gcloud run deploy dsmi-api --memory 4Gi
```

### Database Connection Issues

```bash
# Test Cloud SQL connectivity
gcloud sql connect dsmi-postgres --user=dsmi_user

# For Compute Engine: Use Cloud SQL Auth proxy
cloud_sql_proxy -instances=PROJECT_ID:us-central1:dsmi-postgres &
```

---

## Deployment Checklist

- [ ] GCP project created and billing enabled
- [ ] APIs enabled (run, sql, redis, storage, logging)
- [ ] Database (Cloud SQL) created and initialized
- [ ] Redis instance (Memorystore) provisioned
- [ ] Secrets created in Secret Manager
- [ ] Docker image built and pushed to Container Registry
- [ ] Cloud Run service deployed
- [ ] Environment variables configured
- [ ] Health endpoints tested
- [ ] Monitoring and alerts configured
- [ ] Logging verified in Cloud Logging
- [ ] CORS origins configured for your domain
- [ ] SSL/TLS certificate configured (automatic with Cloud Run)

---

## Cost Optimization

- **Cloud Run**: Pay per request, auto-scales to zero (free tier: 2M requests/month)
- **Cloud SQL**: Use micro instances or serverless MySQL
- **Memorystore**: Start with 1GB, scale as needed
- **Compute Engine**: Auto-scaling groups for variable workloads
- **Set billing alerts** to prevent surprises

```bash
gcloud billing budgets create \
  --billing-account ACCOUNT_ID \
  --display-name "DSMI Agent Monthly Budget" \
  --budget-amount 100
```

---

## Next Steps

1. Choose your deployment option (Cloud Run recommended)
2. Set up infrastructure (Database + Cache + Vector DB)
3. Configure secrets in Secret Manager
4. Deploy and test endpoints
5. Set up monitoring and auto-scaling
6. Configure CI/CD pipeline for automatic deployments

For more help: https://cloud.google.com/docs
