#!/bin/bash

# GCP Deployment Script for Meeting Assistant
# Run this from the project root directory

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-your-project-id}"
REGION="${REGION:-us-central1}"
BUCKET="${PROJECT_ID}-meeting-assistant-frontend"
BACKEND_SERVICE_NAME="meeting-assistant-backend"
DB_INSTANCE_NAME="meeting-assistant-db"
REDIS_INSTANCE_NAME="meeting-assistant-redis"

# Functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed. Please install it first."
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        error "Not authenticated with gcloud. Run 'gcloud auth login' first."
    fi
    
    # Check if project is set
    if [ "$PROJECT_ID" = "your-project-id" ]; then
        error "Please set PROJECT_ID environment variable or edit this script"
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    log "Prerequisites check passed ✓"
}

enable_apis() {
    log "Enabling required GCP APIs..."
    
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        sql-component.googleapis.com \
        sqladmin.googleapis.com \
        redis.googleapis.com \
        secretmanager.googleapis.com \
        storage.googleapis.com
    
    log "APIs enabled ✓"
}

setup_secrets() {
    log "Setting up secrets..."
    
    # Check if secrets exist, create if they don't
    secrets=("google-client-id" "google-client-secret" "app-secret-key" "gemini-api-key")
    
    for secret in "${secrets[@]}"; do
        if ! gcloud secrets describe $secret &> /dev/null; then
            warn "Secret $secret does not exist. Please create it manually:"
            echo "  echo -n 'your-secret-value' | gcloud secrets create $secret --data-file=-"
        else
            log "Secret $secret exists ✓"
        fi
    done
}

setup_infrastructure() {
    log "Setting up infrastructure..."
    
    # Create Cloud SQL instance
    if ! gcloud sql instances describe $DB_INSTANCE_NAME &> /dev/null; then
        log "Creating Cloud SQL instance..."
        gcloud sql instances create $DB_INSTANCE_NAME \
            --database-version=POSTGRES_14 \
            --tier=db-f1-micro \
            --region=$REGION \
            --storage-type=SSD \
            --storage-size=10GB \
            --backup-start-time=03:00 \
            --enable-bin-log \
            --maintenance-window-day=SUN \
            --maintenance-window-hour=04 \
            --deletion-protection
        
        # Create database
        gcloud sql databases create meeting_assistant --instance=$DB_INSTANCE_NAME
        
        # Create user (you'll need to set the password)
        warn "Please set a secure password for the database user:"
        gcloud sql users create app_user --instance=$DB_INSTANCE_NAME --password
    else
        log "Cloud SQL instance already exists ✓"
    fi
    
    # Create Redis instance
    if ! gcloud redis instances describe $REDIS_INSTANCE_NAME --region=$REGION &> /dev/null; then
        log "Creating Redis instance..."
        gcloud redis instances create $REDIS_INSTANCE_NAME \
            --size=1 \
            --region=$REGION \
            --redis-version=redis_6_x
    else
        log "Redis instance already exists ✓"
    fi
    
    log "Infrastructure setup complete ✓"
}

deploy_backend() {
    log "Deploying backend..."
    
    cd backend
    
    # Build and push container
    log "Building container..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE_NAME
    
    # Get Cloud SQL connection name
    SQL_CONNECTION=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")
    
    # Get Redis IP
    REDIS_IP=$(gcloud redis instances describe $REDIS_INSTANCE_NAME --region=$REGION --format="value(host)")
    
    # Deploy to Cloud Run
    log "Deploying to Cloud Run..."
    gcloud run deploy $BACKEND_SERVICE_NAME \
        --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE_NAME \
        --platform=managed \
        --region=$REGION \
        --allow-unauthenticated \
        --port=8080 \
        --memory=1Gi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=10 \
        --add-cloudsql-instances=$SQL_CONNECTION \
        --set-env-vars="ENV=production" \
        --set-env-vars="CLOUD_SQL_CONNECTION_NAME=$SQL_CONNECTION" \
        --set-env-vars="REDIS_URL=redis://$REDIS_IP:6379/0" \
        --set-env-vars="API_BASE_URL=https://$BACKEND_SERVICE_NAME-$(gcloud run services describe $BACKEND_SERVICE_NAME --region=$REGION --format='value(status.url)' | cut -d'/' -f3)" \
        --set-env-vars="FRONTEND_URL=https://storage.googleapis.com/$BUCKET" \
        --set-secrets="GOOGLE_CLIENT_ID=google-client-id:latest" \
        --set-secrets="GOOGLE_CLIENT_SECRET=google-client-secret:latest" \
        --set-secrets="SECRET_KEY=app-secret-key:latest" \
        --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
        --timeout=300
    
    # Get the service URL
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE_NAME --region=$REGION --format='value(status.url)')
    
    cd ..
    
    log "Backend deployed ✓"
    log "Backend URL: $BACKEND_URL"
}

deploy_frontend() {
    log "Deploying frontend..."
    
    if [ ! -d "frontend" ]; then
        warn "Frontend directory not found. Skipping frontend deployment."
        return
    fi
    
    cd frontend
    
    # Build with production API URL
    if [ -n "$BACKEND_URL" ]; then
        log "Building frontend with API URL: $BACKEND_URL"
        REACT_APP_API_URL="$BACKEND_URL" npm run build
    else
        warn "Backend URL not found. Building with default configuration."
        npm run build
    fi
    
    # Create and configure bucket
    if ! gsutil ls -b gs://$BUCKET &> /dev/null; then
        log "Creating storage bucket..."
        gsutil mb -l $REGION gs://$BUCKET
        gsutil web set -m index.html -e 404.html gs://$BUCKET
        gsutil iam ch allUsers:objectViewer gs://$BUCKET
    fi
    
    # Upload build
    log "Uploading frontend files..."
    gsutil -m cp -r build/* gs://$BUCKET
    
    cd ..
    
    log "Frontend deployed ✓"
    log "Frontend URL: https://storage.googleapis.com/$BUCKET"
}

run_migrations() {
    log "Running database migrations..."
    
    # This would typically be done through a Cloud Build step or manually
    warn "Database migrations need to be run manually:"
    echo "  1. Connect to your Cloud SQL instance"
    echo "  2. Run: alembic upgrade head"
    echo "  Or use Cloud SQL Proxy for local migration"
}

main() {
    log "Starting deployment process..."
    
    check_prerequisites
    enable_apis
    setup_secrets
    setup_infrastructure
    deploy_backend
    deploy_frontend
    run_migrations
    
    log "Deployment complete! 🎉"
    log "Backend: $BACKEND_URL"
    log "Frontend: https://storage.googleapis.com/$BUCKET"
    
    warn "Don't forget to:"
    echo "  1. Set up your secrets in Secret Manager"
    echo "  2. Run database migrations"
    echo "  3. Configure your OAuth redirect URIs in Google Cloud Console"
    echo "  4. Set up monitoring and alerting"
}

# Run main function
main "$@" 