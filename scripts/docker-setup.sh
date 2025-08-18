#!/bin/bash
# Myanmar Election Visualization - Docker Setup Script

set -e  # Exit on any error

echo "🐳 Myanmar Election Visualization - Docker Migration Setup"
echo "=========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
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

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Create environment file
create_env_file() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        print_success "Created .env file from template"
        print_warning "Please edit .env file with your specific configuration"
        
        # Generate a random password if not set
        if ! grep -q "POSTGRES_PASSWORD=" .env || grep -q "your_secure_password_here" .env; then
            RANDOM_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
            sed -i "s/your_secure_password_here/${RANDOM_PASSWORD}/g" .env
            print_success "Generated random PostgreSQL password"
        fi
    else
        print_success ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p data/backup
    mkdir -p nginx
    
    print_success "Directories created"
}

# Create nginx configuration
create_nginx_config() {
    print_status "Creating nginx configuration..."
    
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream streamlit_app {
        server myanmar-election-app:8501;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        
        # Gzip compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
        
        location / {
            proxy_pass http://streamlit_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support for Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Increase timeout for large data operations
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
        
        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF
    
    print_success "Nginx configuration created"
}

# Build and start containers
start_containers() {
    print_status "Building and starting Docker containers..."
    
    # Build the application
    docker-compose build
    
    # Start PostgreSQL first
    print_status "Starting PostgreSQL container..."
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Check if PostgreSQL is ready
    POSTGRES_READY=0
    for i in {1..30}; do
        if docker-compose exec postgres pg_isready -U election_user > /dev/null 2>&1; then
            POSTGRES_READY=1
            break
        fi
        print_status "Waiting for PostgreSQL... ($i/30)"
        sleep 2
    done
    
    if [ $POSTGRES_READY -eq 0 ]; then
        print_error "PostgreSQL failed to start within 60 seconds"
        exit 1
    fi
    
    print_success "PostgreSQL is ready"
    
    # Start other services
    print_status "Starting remaining services..."
    docker-compose up -d
    
    print_success "All containers started"
}

# Run migration
run_migration() {
    print_status "Running data migration from CSV to PostgreSQL..."
    
    # Check if CSV data exists
    if [ ! -f "data/processed/myanmar_constituencies.json" ] && [ ! -f "data/processed/myanmar_constituencies.csv" ]; then
        print_warning "No CSV data found. Skipping migration."
        return
    fi
    
    # Run migration script inside container
    docker-compose exec myanmar-election-app python database/migrate_csv_to_db.py
    
    if [ $? -eq 0 ]; then
        print_success "Data migration completed successfully"
    else
        print_error "Data migration failed"
        exit 1
    fi
}

# Check container health
check_health() {
    print_status "Checking container health..."
    
    # Wait a bit for containers to fully start
    sleep 5
    
    # Check if Streamlit app is responding
    for i in {1..10}; do
        if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            print_success "Streamlit app is healthy"
            break
        fi
        if [ $i -eq 10 ]; then
            print_error "Streamlit app health check failed"
            docker-compose logs myanmar-election-app
            exit 1
        fi
        print_status "Waiting for app to be ready... ($i/10)"
        sleep 3
    done
}

# Show final status
show_status() {
    echo ""
    echo "🎉 Docker setup completed successfully!"
    echo "========================================="
    echo ""
    echo "📊 Services running:"
    echo "  • Myanmar Election App: http://localhost:8501"
    echo "  • PostgreSQL Database: localhost:5432"
    echo "  • Redis Cache: localhost:6379"
    echo "  • Nginx Proxy: http://localhost:80"
    echo ""
    echo "🔧 Useful commands:"
    echo "  • View logs: docker-compose logs -f"
    echo "  • Stop services: docker-compose down"
    echo "  • Restart services: docker-compose restart"
    echo "  • Access database: docker-compose exec postgres psql -U election_user myanmar_election"
    echo ""
    echo "📁 Data locations:"
    echo "  • Database data: docker volume 'postgres_data'"
    echo "  • Cache data: docker volume 'redis_data'"
    echo "  • Application logs: ./logs/"
    echo ""
    print_success "Your Myanmar Election Visualization is now running in Docker!"
}

# Main execution
main() {
    check_docker
    create_env_file
    create_directories
    create_nginx_config
    start_containers
    run_migration
    check_health
    show_status
}

# Run main function
main