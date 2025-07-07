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
PROJECT_ID="${PROJECT_ID:-ps-apprentice}"
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
        storage.googleapis.com \
        servicenetworking.googleapis.com
    
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

grant_permissions() {
    log "Granting required IAM permissions..."
    
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    SERVICE_ACCOUNT_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    
    # Grant Secret Manager access to the default Compute service account (used by Cloud Run)
    if ! gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:$SERVICE_ACCOUNT_EMAIL" | grep -q "roles/secretmanager.secretAccessor"; then
        log "Granting Secret Manager access to Cloud Run service account..."
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --role="roles/secretmanager.secretAccessor" \
            --condition=None # Explicitly set no condition
    else
        log "Secret Manager access already granted to Cloud Run service account ✓"
    fi
    
    log "IAM permissions setup complete ✓"
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
            --maintenance-window-day=SUN \
            --maintenance-window-hour=04 \
            --deletion-protection
    else
        log "Cloud SQL instance already exists ✓"
    fi

    # Create database if it doesn't exist
    if ! gcloud sql databases describe meeting_assistant --instance=$DB_INSTANCE_NAME &> /dev/null; then
        log "Creating 'meeting_assistant' database..."
        gcloud sql databases create meeting_assistant --instance=$DB_INSTANCE_NAME
    else
        log "Database 'meeting_assistant' already exists ✓"
    fi

    # Create database user and password secret if the user doesn't exist
    if ! gcloud sql users list --instance=$DB_INSTANCE_NAME | grep -q "app_user"; then
        log "Creating database user 'app_user' and password secret..."
        DB_PASSWORD=$(openssl rand -base64 32)
        echo -n "$DB_PASSWORD" | gcloud secrets create db-password --data-file=- --quiet || \
        echo -n "$DB_PASSWORD" | gcloud secrets versions add db-password --data-file=- --quiet
        
        gcloud sql users create app_user --instance=$DB_INSTANCE_NAME --password="$DB_PASSWORD"
        log "Database user 'app_user' created and password stored in Secret Manager."
    else
        log "Database user 'app_user' already exists ✓"
    fi
    
    # Check for default network and create if it doesn't exist
    log "Checking for default VPC network..."
    if ! gcloud compute networks describe default &> /dev/null; then
        log "Default network not found. Creating it now with auto-subnets..."
        gcloud compute networks create default --subnet-mode=auto
        log "Default network created ✓"
    else
        log "Default network already exists ✓"
    fi
    
    # Set up VPC Peering for Redis, which is required for PRIVATE_SERVICE_ACCESS
    log "Setting up VPC Peering for Redis..."
    if ! gcloud compute addresses describe google-managed-services-default --global &> /dev/null; then
        log "Allocating IP range for service networking..."
        gcloud compute addresses create google-managed-services-default \
            --global \
            --purpose=VPC_PEERING \
            --prefix-length=16 \
            --network=default
    else
        log "IP range 'google-managed-services-default' already allocated ✓"
    fi

    if ! gcloud services vpc-peerings list --network=default | grep -q "servicenetworking-googleapis-com"; then
        log "Creating VPC peering connection..."
        gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com --ranges=google-managed-services-default --network=default
    else
        log "VPC peering connection already exists ✓"
    fi

    # Create Redis instance
    if ! gcloud redis instances describe $REDIS_INSTANCE_NAME --region=$REGION &> /dev/null; then
        log "Creating Redis instance..."
        gcloud redis instances create $REDIS_INSTANCE_NAME \
            --size=1 \
            --region=$REGION \
            --redis-version=redis_6_x \
            --connect-mode=PRIVATE_SERVICE_ACCESS
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
    
    # Deploy to Cloud Run (pass 1/2, without API_BASE_URL)
    log "Deploying to Cloud Run (pass 1/2)..."
    gcloud run deploy $BACKEND_SERVICE_NAME \
        --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE_NAME \
        --platform=managed \
        --region=$REGION \
        --allow-unauthenticated \
        --port=8000 \
        --memory=1Gi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=10 \
        --add-cloudsql-instances=$SQL_CONNECTION \
        --set-env-vars="ENV=production" \
        --set-env-vars="CLOUD_SQL_CONNECTION_NAME=$SQL_CONNECTION" \
        --set-env-vars="REDIS_URL=redis://$REDIS_IP:6379/0" \
        --set-env-vars="FRONTEND_URL=https://storage.googleapis.com/$BUCKET" \
        --set-secrets="GOOGLE_CLIENT_ID=google-client-id:latest" \
        --set-secrets="GOOGLE_CLIENT_SECRET=google-client-secret:latest" \
        --set-secrets="SECRET_KEY=app-secret-key:latest" \
        --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
        --set-secrets="DB_PASSWORD=db-password:latest" \
        --timeout=300
    
    # Get the service URL
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE_NAME --region=$REGION --format='value(status.url)')
    
    # Update service with its own URL (pass 2/2)
    log "Updating Cloud Run service with API_BASE_URL (pass 2/2)..."
    gcloud run services update $BACKEND_SERVICE_NAME \
        --region=$REGION \
        --update-env-vars="API_BASE_URL=$BACKEND_URL"

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
        NEXT_PUBLIC_API_URL="$BACKEND_URL" npm run build
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
    grant_permissions
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