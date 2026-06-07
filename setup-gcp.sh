#!/bin/bash
# GCP Deployment Setup Script
# Run this script to set up your Google Cloud infrastructure for DSMI Agent

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 DSMI Agent - Google Cloud Setup Script${NC}"
echo "============================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first:${NC}"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Variables
read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter deployment region (default: us-central1): " REGION
REGION=${REGION:-us-central1}

read -p "Select deployment option:
1) Cloud Run (recommended)
2) App Engine
3) Compute Engine
4) GKE
Enter choice (1-4): " DEPLOYMENT_OPTION

echo ""
echo -e "${YELLOW}Setting up GCP project...${NC}"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudresourcemanager.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com

# Create service account
echo -e "${YELLOW}Creating service account...${NC}"
gcloud iam service-accounts create dsmi-api \
    --display-name="DSMI API Service Account" || echo "Service account already exists"

# Grant necessary roles
SERVICE_ACCOUNT="dsmi-api@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/redis.editor"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/monitoring.metricWriter"

# Create Cloud SQL instance
echo -e "${YELLOW}Creating Cloud SQL instance...${NC}"
gcloud sql instances create dsmi-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --availability-type=zonal || echo "Cloud SQL instance already exists"

# Create database
echo -e "${YELLOW}Creating database...${NC}"
gcloud sql databases create dsmi_agent \
    --instance=dsmi-postgres || echo "Database already exists"

# Create database user
echo -e "${YELLOW}Creating database user...${NC}"
DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create dsmi_user \
    --instance=dsmi-postgres \
    --password=$DB_PASSWORD || echo "User already exists"

echo -e "${GREEN}Database user password: ${DB_PASSWORD}${NC}"
echo "Save this password securely!"

# Create Redis instance
echo -e "${YELLOW}Creating Memorystore for Redis...${NC}"
gcloud redis instances create dsmi-redis \
    --size=1 \
    --region=$REGION \
    --redis-version=7.0 \
    --tier=basic || echo "Redis instance already exists"

# Create secrets
echo -e "${YELLOW}Creating Cloud Secrets...${NC}"
echo $DB_PASSWORD | gcloud secrets create DATABASE_PASSWORD \
    --data-file=- || gcloud secrets versions add DATABASE_PASSWORD --data-file=-

# Deployment option specific setup
case $DEPLOYMENT_OPTION in
    1)
        echo -e "${YELLOW}Setting up Cloud Run...${NC}"
        echo -e "${GREEN}✅ To deploy to Cloud Run, run:${NC}"
        echo "   docker build -f Dockerfile.cloudrun -t gcr.io/$PROJECT_ID/dsmi-api:latest ."
        echo "   docker push gcr.io/$PROJECT_ID/dsmi-api:latest"
        echo "   gcloud run deploy dsmi-api --image gcr.io/$PROJECT_ID/dsmi-api:latest \\"
        echo "     --region=$REGION --memory=2Gi --cpu=2"
        ;;
    2)
        echo -e "${YELLOW}Setting up App Engine...${NC}"
        gcloud app create --region=$REGION || echo "App Engine already created"
        echo -e "${GREEN}✅ To deploy to App Engine, run:${NC}"
        echo "   gcloud app deploy"
        ;;
    3)
        echo -e "${YELLOW}Setting up Compute Engine...${NC}"
        echo -e "${GREEN}✅ Creating VM instance...${NC}"
        gcloud compute instances create dsmi-vm \
            --image-family=ubuntu-2204-lts \
            --image-project=ubuntu-os-cloud \
            --machine-type=e2-standard-2 \
            --zone=${REGION}-a \
            --service-account=$SERVICE_ACCOUNT
        ;;
    4)
        echo -e "${YELLOW}Setting up GKE...${NC}"
        gcloud container clusters create dsmi-cluster \
            --zone=${REGION}-a \
            --num-nodes=3 \
            --machine-type=n1-standard-2 \
            --enable-autoscaling \
            --min-nodes=1 \
            --max-nodes=10
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ GCP Setup Complete!${NC}"
echo "============================================="
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure your .env file with the secrets"
echo "2. Build and push the Docker image"
echo "3. Deploy using your chosen method"
echo "4. Test the API endpoints"
echo "5. Set up monitoring and logging"
echo ""
