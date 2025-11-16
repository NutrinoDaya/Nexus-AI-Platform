#!/bin/bash
# NexusAIPlatform Monitoring Script
# Monitors system health, logs, and resource usage

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "NexusAIPlatform System Monitor"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}[ERROR]${NC} Services are not running. Start with: docker-compose up -d"
    exit 1
fi

# Function to check service health
check_service_health() {
    local service=$1
    local status=$(docker-compose ps -q $service 2>/dev/null)
    
    if [ -z "$status" ]; then
        echo -e "${RED}[DOWN]${NC} $service"
        return 1
    fi
    
    local health=$(docker inspect --format='{{.State.Health.Status}}' $(docker-compose ps -q $service) 2>/dev/null || echo "unknown")
    
    if [ "$health" == "healthy" ]; then
        echo -e "${GREEN}[HEALTHY]${NC} $service"
        return 0
    elif [ "$health" == "starting" ]; then
        echo -e "${YELLOW}[STARTING]${NC} $service"
        return 0
    elif [ "$health" == "unknown" ]; then
        # Service doesn't have health check
        local running=$(docker inspect --format='{{.State.Running}}' $(docker-compose ps -q $service) 2>/dev/null || echo "false")
        if [ "$running" == "true" ]; then
            echo -e "${GREEN}[RUNNING]${NC} $service"
            return 0
        else
            echo -e "${RED}[STOPPED]${NC} $service"
            return 1
        fi
    else
        echo -e "${RED}[UNHEALTHY]${NC} $service"
        return 1
    fi
}

# Check all services
echo "Service Status:"
echo "----------------------------------------"
check_service_health "postgres"
check_service_health "redis"
check_service_health "minio"
check_service_health "mlflow"
check_service_health "backend"
check_service_health "celery-worker"
check_service_health "frontend"
check_service_health "prometheus"
check_service_health "grafana"
echo ""

# Resource usage
echo "Resource Usage:"
echo "----------------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | grep NexusAIPlatform
echo ""

# Recent errors
echo "Recent Errors (last 10 minutes):"
echo "----------------------------------------"
SINCE=$(date -u -d '10 minutes ago' '+%Y-%m-%dT%H:%M:%S')
ERROR_COUNT=$(docker-compose logs --since $SINCE 2>&1 | grep -i error | wc -l)

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${RED}Found $ERROR_COUNT errors${NC}"
    docker-compose logs --since $SINCE 2>&1 | grep -i error | tail -20
else
    echo -e "${GREEN}No errors found${NC}"
fi
echo ""

# API Health Check
echo "API Health Check:"
echo "----------------------------------------"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")

if [ "$HEALTH_RESPONSE" == "200" ]; then
    echo -e "${GREEN}[OK]${NC} API is responding (HTTP $HEALTH_RESPONSE)"
    
    # Get detailed metrics
    echo ""
    echo "API Metrics:"
    curl -s http://localhost:8000/metrics 2>/dev/null | grep -E "(http_requests_total|http_request_duration)" | head -10
else
    echo -e "${RED}[FAIL]${NC} API is not responding (HTTP $HEALTH_RESPONSE)"
fi
echo ""

# Database connections
echo "Database Status:"
echo "----------------------------------------"
DB_CONN=$(docker exec NexusAIPlatform-postgres psql -U NexusAIPlatform -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
if [ ! -z "$DB_CONN" ]; then
    echo "Active connections: $DB_CONN"
    
    # Slow queries
    echo "Slow queries (>1s):"
    docker exec NexusAIPlatform-postgres psql -U NexusAIPlatform -c "
        SELECT pid, usename, application_name, state, 
               round(extract(epoch from (now() - query_start))) as duration_seconds
        FROM pg_stat_activity 
        WHERE state != 'idle' AND query_start < now() - interval '1 second'
        ORDER BY duration_seconds DESC LIMIT 5;" 2>/dev/null || echo "None"
else
    echo -e "${RED}[ERROR]${NC} Cannot connect to database"
fi
echo ""

# Redis status
echo "Redis Status:"
echo "----------------------------------------"
REDIS_INFO=$(docker exec NexusAIPlatform-redis redis-cli -a redis_secret INFO stats 2>/dev/null | grep -E "(total_commands_processed|keyspace)" || echo "error")
if [ "$REDIS_INFO" != "error" ]; then
    echo "$REDIS_INFO"
else
    echo -e "${RED}[ERROR]${NC} Cannot connect to Redis"
fi
echo ""

# Disk usage
echo "Disk Usage:"
echo "----------------------------------------"
df -h | grep -E "(Filesystem|/var/lib/docker|/$)"
echo ""

echo "======================================"
echo "Monitor Options:"
echo "======================================"
echo "1. Watch logs:       docker-compose logs -f"
echo "2. Specific service: docker-compose logs -f <service>"
echo "3. Restart service:  docker-compose restart <service>"
echo "4. View Grafana:     http://localhost:3001"
echo "5. View Prometheus:  http://localhost:9090"
echo ""
