@echo off
REM GCP Deployment Setup Script for Windows
REM Run this script to set up your Google Cloud infrastructure for DSMI Agent

setlocal enabledelayedexpansion

echo.
echo ============================================
echo   DSMI Agent - Google Cloud Setup Script
echo ============================================
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] gcloud CLI not found. Please install it first:
    echo   https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Variables
set /p PROJECT_ID="Enter your GCP Project ID: "
set /p REGION="Enter deployment region (default: us-central1): "
if "%REGION%"=="" set REGION=us-central1

echo.
echo Select deployment option:
echo 1) Cloud Run (recommended)
echo 2) App Engine
echo 3) Compute Engine
echo 4) GKE
set /p DEPLOYMENT_OPTION="Enter choice (1-4): "

echo.
echo [INFO] Setting up GCP project...

REM Set project
gcloud config set project %PROJECT_ID%

REM Enable required APIs
echo [INFO] Enabling required APIs...
gcloud services enable ^
    run.googleapis.com ^
    cloudresourcemanager.googleapis.com ^
    containerregistry.googleapis.com ^
    cloudbuild.googleapis.com ^
    sqladmin.googleapis.com ^
    redis.googleapis.com ^
    logging.googleapis.com ^
    monitoring.googleapis.com

REM Create service account
echo [INFO] Creating service account...
gcloud iam service-accounts create dsmi-api ^
    --display-name="DSMI API Service Account" 2>nul || echo [INFO] Service account already exists

set SERVICE_ACCOUNT=dsmi-api@%PROJECT_ID%.iam.gserviceaccount.com

REM Grant necessary roles
gcloud projects add-iam-policy-binding %PROJECT_ID% ^
    --member="serviceAccount:%SERVICE_ACCOUNT%" ^
    --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding %PROJECT_ID% ^
    --member="serviceAccount:%SERVICE_ACCOUNT%" ^
    --role="roles/redis.editor"
gcloud projects add-iam-policy-binding %PROJECT_ID% ^
    --member="serviceAccount:%SERVICE_ACCOUNT%" ^
    --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding %PROJECT_ID% ^
    --member="serviceAccount:%SERVICE_ACCOUNT%" ^
    --role="roles/monitoring.metricWriter"

REM Create Cloud SQL instance
echo [INFO] Creating Cloud SQL instance...
gcloud sql instances create dsmi-postgres ^
    --database-version=POSTGRES_15 ^
    --tier=db-f1-micro ^
    --region=%REGION% ^
    --availability-type=zonal 2>nul || echo [INFO] Cloud SQL instance already exists

REM Create database
echo [INFO] Creating database...
gcloud sql databases create dsmi_agent ^
    --instance=dsmi-postgres 2>nul || echo [INFO] Database already exists

REM Create database user with random password
echo [INFO] Creating database user...
for /f "delims=" %%A in ('powershell -Command "Add-Type 'System.Web'; Write-Host ([System.Web.Security.Membership]::GeneratePassword(32,0))"') do set DB_PASSWORD=%%A

gcloud sql users create dsmi_user ^
    --instance=dsmi-postgres ^
    --password=%DB_PASSWORD% 2>nul || echo [INFO] User already exists

echo.
echo [SUCCESS] Database user password: %DB_PASSWORD%
echo Save this password securely!

REM Create Redis instance
echo [INFO] Creating Memorystore for Redis...
gcloud redis instances create dsmi-redis ^
    --size=1 ^
    --region=%REGION% ^
    --redis-version=7.0 ^
    --tier=basic 2>nul || echo [INFO] Redis instance already exists

REM Create secrets
echo [INFO] Creating Cloud Secrets...
echo %DB_PASSWORD% | gcloud secrets create DATABASE_PASSWORD ^
    --data-file=- 2>nul || gcloud secrets versions add DATABASE_PASSWORD --data-file=-

REM Deployment option specific setup
if "%DEPLOYMENT_OPTION%"=="1" (
    echo [INFO] Setting up Cloud Run...
    echo.
    echo [SUCCESS] To deploy to Cloud Run, run:
    echo   docker build -f Dockerfile.cloudrun -t gcr.io/%PROJECT_ID%/dsmi-api:latest .
    echo   docker push gcr.io/%PROJECT_ID%/dsmi-api:latest
    echo   gcloud run deploy dsmi-api --image gcr.io/%PROJECT_ID%/dsmi-api:latest ^
    echo     --region=%REGION% --memory=2Gi --cpu=2
) else if "%DEPLOYMENT_OPTION%"=="2" (
    echo [INFO] Setting up App Engine...
    gcloud app create --region=%REGION% 2>nul || echo [INFO] App Engine already created
    echo.
    echo [SUCCESS] To deploy to App Engine, run: gcloud app deploy
) else if "%DEPLOYMENT_OPTION%"=="3" (
    echo [INFO] Setting up Compute Engine...
    echo [SUCCESS] Creating VM instance...
    gcloud compute instances create dsmi-vm ^
        --image-family=ubuntu-2204-lts ^
        --image-project=ubuntu-os-cloud ^
        --machine-type=e2-standard-2 ^
        --zone=%REGION%-a ^
        --service-account=%SERVICE_ACCOUNT%
) else if "%DEPLOYMENT_OPTION%"=="4" (
    echo [INFO] Setting up GKE...
    gcloud container clusters create dsmi-cluster ^
        --zone=%REGION%-a ^
        --num-nodes=3 ^
        --machine-type=n1-standard-2 ^
        --enable-autoscaling ^
        --min-nodes=1 ^
        --max-nodes=10
) else (
    echo [ERROR] Invalid option
    pause
    exit /b 1
)

echo.
echo ============================================
echo   GCP Setup Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Configure your .env file with the secrets
echo 2. Build and push the Docker image
echo 3. Deploy using your chosen method
echo 4. Test the API endpoints
echo 5. Set up monitoring and logging
echo.
pause
