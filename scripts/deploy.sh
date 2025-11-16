#!/bin/bash

# NexusAIPlatform - Deployment Script for Linux/macOS
# This script handles the complete deployment of NexusAIPlatform

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose found"
    
    # Check NVIDIA GPU (optional)
    if command -v nvidia-smi &> /dev/null; then
        print_success "NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)"
    else
        print_warning "NVIDIA GPU not detected. Will use CPU for inference."
    fi
}

setup_environment() {
    print_info "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f config/.env ]; then
        if [ -f config/.env.example ]; then
            cp config/.env.example config/.env
            print_success "Created config/.env from example"
            print_warning "Please edit config/.env with your settings before continuing"
            read -p "Press Enter to continue after editing .env, or Ctrl+C to exit..."
        else
            print_error "config/.env.example not found"
            exit 1
        fi
    else
        print_success "Environment file already exists"
    fi
    
    # Create necessary directories
    mkdir -p data logs models/checkpoints models/onnx models/tensorrt
    print_success "Created data directories"
}

pull_images() {
    print_info "Pulling Docker images..."
    docker-compose pull
    print_success "Docker images pulled successfully"
}

build_services() {
    print_info "Building services..."
    docker-compose build --parallel
    print_success "Services built successfully"
}

start_services() {
    print_info "Starting NexusAIPlatform services..."
    
    # Start infrastructure services first
    print_info "Starting database and storage services..."
    docker-compose up -d postgres redis minio
    
    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 10
    
    # Start MLflow
    print_info "Starting MLflow..."
    docker-compose up -d mlflow
    sleep 5
    
    # Start application services
    print_info "Starting application services..."
    docker-compose up -d backend celery-worker frontend
    
    # Start monitoring services
    print_info "Starting monitoring services..."
    docker-compose up -d prometheus grafana
    
    print_success "All services started successfully"
}

show_status() {
    print_info "Service status:"
    docker-compose ps
}

show_logs() {
    print_info "Showing logs (Ctrl+C to exit)..."
    docker-compose logs -f --tail=50
}

run_migrations() {
    print_info "Running database migrations..."
    docker-compose exec backend alembic upgrade head
    print_success "Database migrations completed"
}

initialize_storage() {
    print_info "Initializing object storage buckets..."
    docker-compose exec backend python -m scripts.init_storage
    print_success "Storage initialized"
}

show_access_urls() {
    echo ""
    print_success "=== NexusAIPlatform is now running ==="
    echo ""
    echo "Access the platform at:"
    echo "  Frontend Dashboard:  http://localhost:3000"
    echo "  Backend API:         http://localhost:8000"
    echo "  API Documentation:   http://localhost:8000/docs"
    echo "  MLflow UI:           http://localhost:5000"
    echo "  MinIO Console:       http://localhost:9001"
    echo "  Grafana Dashboard:   http://localhost:3001 (admin/admin)"
    echo "  Prometheus:          http://localhost:9090"
    echo ""
    print_info "Default credentials:"
    echo "  Admin user: admin@NexusAIPlatform.io"
    echo "  Password: changeme (please change on first login)"
    echo ""
}

# Main deployment flow
main() {
    echo ""
    echo "========================================="
    echo "  NexusAIPlatform Deployment Script"
    echo "========================================="
    echo ""
    
    # Parse arguments
    SKIP_BUILD=false
    SKIP_PULL=false
    NO_LOGS=false
    
    for arg in "$@"; do
        case $arg in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-pull)
                SKIP_PULL=true
                shift
                ;;
            --no-logs)
                NO_LOGS=true
                shift
                ;;
            --help)
                echo "Usage: ./deploy.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-build    Skip building Docker images"
                echo "  --skip-pull     Skip pulling Docker images"
                echo "  --no-logs       Don't show logs after deployment"
                echo "  --help          Show this help message"
                exit 0
                ;;
        esac
    done
    
    # Execute deployment steps
    check_dependencies
    setup_environment
    
    if [ "$SKIP_PULL" = false ]; then
        pull_images
    fi
    
    if [ "$SKIP_BUILD" = false ]; then
        build_services
    fi
    
    start_services
    sleep 5
    
    run_migrations
    initialize_storage
    
    show_status
    show_access_urls
    
    if [ "$NO_LOGS" = false ]; then
        show_logs
    fi
}

# Run main function
main "$@"
