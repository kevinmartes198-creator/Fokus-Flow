#!/bin/bash
# FocusFlow Production Deployment Script

set -e  # Exit on any error

echo "🚀 Starting FocusFlow Production Deployment"

# Configuration
ENVIRONMENT="production"
APP_NAME="focusflow"
COMPOSE_FILE="docker-compose.production.yml"
BACKUP_DIR="/backups/focusflow"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check if required files exist
    if [ ! -f ".env.production" ]; then
        error ".env.production file not found!"
        exit 1
    fi
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "$COMPOSE_FILE file not found!"
        exit 1
    fi
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed!"
        exit 1
    fi
    
    # Check disk space (at least 5GB free)
    FREE_SPACE=$(df / | tail -1 | awk '{print $4}')
    if [ "$FREE_SPACE" -lt 5242880 ]; then  # 5GB in KB
        warning "Low disk space detected. Consider freeing up space."
    fi
    
    success "Pre-deployment checks completed"
}

# Backup current deployment
backup_current_deployment() {
    log "Creating backup of current deployment..."
    
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_TIMESTAMP"
    
    mkdir -p "$BACKUP_PATH"
    
    # Backup database
    if docker-compose -f "$COMPOSE_FILE" ps mongodb | grep -q "Up"; then
        log "Backing up MongoDB database..."
        docker-compose -f "$COMPOSE_FILE" exec -T mongodb mongodump --out /tmp/backup
        docker-compose -f "$COMPOSE_FILE" exec -T mongodb tar czf /tmp/mongodb_backup_$BACKUP_TIMESTAMP.tar.gz -C /tmp/backup .
        docker cp $(docker-compose -f "$COMPOSE_FILE" ps -q mongodb):/tmp/mongodb_backup_$BACKUP_TIMESTAMP.tar.gz "$BACKUP_PATH/"
    fi
    
    # Backup configuration files
    cp .env.production "$BACKUP_PATH/"
    cp "$COMPOSE_FILE" "$BACKUP_PATH/"
    
    success "Backup created at $BACKUP_PATH"
}

# Build and deploy application
deploy_application() {
    log "Building and deploying FocusFlow..."
    
    # Pull latest images
    log "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build custom images
    log "Building application images..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # Stop current services
    log "Stopping current services..."
    docker-compose -f "$COMPOSE_FILE" down
    
    # Start new deployment
    log "Starting new deployment..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    success "Application deployed successfully"
}

# Health check
health_check() {
    log "Running health checks..."
    
    # Wait for services to start
    sleep 30
    
    # Check API health
    MAX_ATTEMPTS=10
    ATTEMPT=1
    
    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        log "Health check attempt $ATTEMPT/$MAX_ATTEMPTS..."
        
        if curl -f -s http://localhost/api/health > /dev/null; then
            success "API health check passed"
            break
        fi
        
        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            error "Health check failed after $MAX_ATTEMPTS attempts"
            exit 1
        fi
        
        sleep 10
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    # Check database connectivity
    if docker-compose -f "$COMPOSE_FILE" exec -T api python -c "
import asyncio
from backend.server import client
async def test_db():
    try:
        await client.server_info()
        print('Database connection successful')
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False
asyncio.run(test_db())
" | grep -q "successful"; then
        success "Database connectivity check passed"
    else
        error "Database connectivity check failed"
        exit 1
    fi
}

# Clean up old images and containers
cleanup() {
    log "Cleaning up old Docker resources..."
    
    # Remove old images
    docker image prune -f
    
    # Remove old containers
    docker container prune -f
    
    # Remove old volumes (be careful with this in production)
    # docker volume prune -f
    
    success "Cleanup completed"
}

# Main deployment process
main() {
    log "🎯 FocusFlow Production Deployment v1.0"
    log "Environment: $ENVIRONMENT"
    log "Timestamp: $(date)"
    
    pre_deployment_checks
    backup_current_deployment
    deploy_application
    health_check
    cleanup
    
    success "🎉 FocusFlow deployment completed successfully!"
    log "🌐 Application should be available at: https://focusflow.app"
    log "📊 API documentation (if enabled): https://focusflow.app/docs"
    log "💚 Health check: https://focusflow.app/api/health"
}

# Handle script arguments
case "${1}" in
    "backup-only")
        backup_current_deployment
        ;;
    "health-check")
        health_check
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        main
        ;;
esac