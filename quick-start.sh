#!/bin/bash
# Quick start script for Docker development setup

set -e

echo "🚀 Myanmar Election Visualization - Quick Docker Setup"
echo "====================================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Quick validation
print_step "Validating configuration..."
python test-docker-basic.py
if [ $? -ne 0 ]; then
    echo "❌ Configuration validation failed"
    exit 1
fi

# Create minimal .env
print_step "Creating development environment..."
if [ ! -f .env ]; then
    echo "POSTGRES_PASSWORD=dev_password_2025" > .env
    echo "DATABASE_URL=postgresql://election_user:dev_password_2025@postgres:5432/myanmar_election" >> .env
    print_success "Created .env file"
fi

# Start development containers
print_step "Starting development containers (this may take a few minutes)..."
docker-compose -f docker-compose.dev.yml up -d --build

# Wait for postgres
print_step "Waiting for PostgreSQL to be ready..."
sleep 10

# Test postgres connection
for i in {1..30}; do
    if docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U election_user > /dev/null 2>&1; then
        print_success "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL failed to start"
        docker-compose -f docker-compose.dev.yml logs postgres
        exit 1
    fi
    sleep 2
done

# Check if app is running
print_step "Checking application startup..."
sleep 5

# Test app health
for i in {1..20}; do
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        print_success "Application is running"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Application failed to start"
        docker-compose -f docker-compose.dev.yml logs myanmar-election-viz
        exit 1
    fi
    sleep 3
done

# Initialize database with full dataset
print_step "Initializing database with 835 constituencies..."
print_info "This will take 2-3 minutes to complete all migrations..."

if docker-compose -f docker-compose.dev.yml exec -T myanmar-election-viz python database/init_complete.py; then
    print_success "Database initialized with complete dataset"
else
    print_info "Database initialization had issues, but basic schema exists"
    print_info "You can run manual initialization later if needed"
fi

print_success "🎉 Quick setup completed!"
echo ""
print_info "📊 Development Environment Ready:"
echo "  • Application: http://localhost:8501"
echo "  • Database: localhost:5432"
echo ""
print_info "🔧 Development Commands:"
echo "  • View logs: docker-compose -f docker-compose.dev.yml logs -f"
echo "  • Stop: docker-compose -f docker-compose.dev.yml down"
echo "  • Rebuild: docker-compose -f docker-compose.dev.yml up -d --build"
echo ""
print_info "📝 Initialize database with all 835 constituencies:"
echo "  docker-compose -f docker-compose.dev.yml exec myanmar-election-viz python database/init_complete.py"
echo ""
print_info "📝 Alternative: Run individual migration steps:"
echo "  • Base PTHT data: python database/migrate_csv_to_db.py"
echo "  • Expand assemblies: python database/expand_constituencies.py"
echo "  • Add AMTHT: python database/add_amyotha_hluttaw.py"
echo "  • Geocode all: python database/geocode_constituencies.py"