#!/bin/bash
# Docker helper script for Claude Chat Interface

set -e

DOCKER_COMPOSE_FILE="docker-compose.yml"
SERVICE_NAME="claude-chat"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Commands
case "$1" in
    up|start)
        print_info "Starting Claude Chat application..."
        docker compose up -d
        print_success "Application started!"
        print_info "Access at: http://localhost:8501"
        ;;
    
    down|stop)
        print_info "Stopping Claude Chat application..."
        docker compose down
        print_success "Application stopped!"
        ;;
    
    restart)
        print_info "Restarting Claude Chat application..."
        docker compose restart
        print_success "Application restarted!"
        ;;
    
    build)
        print_info "Building Docker image..."
        docker compose build
        print_success "Build complete!"
        ;;
    
    rebuild)
        print_info "Rebuilding Docker image (no cache)..."
        docker compose build --no-cache
        print_success "Rebuild complete!"
        ;;
    
    logs)
        print_info "Showing application logs..."
        docker compose logs -f
        ;;
    
    status)
        print_info "Checking application status..."
        docker compose ps
        ;;
    
    shell)
        print_info "Opening shell in running container..."
        docker compose exec ${SERVICE_NAME}-app /bin/bash
        ;;
    
    test)
        print_info "Running test command..."
        docker compose exec ${SERVICE_NAME}-app curl http://localhost:8501/_stcore/health
        print_success "Health check passed!"
        ;;
    
    clean)
        print_info "Cleaning up containers and volumes..."
        docker compose down -v
        print_success "Cleanup complete! Data has been deleted."
        ;;
    
    backup)
        print_info "Backing up chat history..."
        BACKUP_DIR="./backups"
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="$BACKUP_DIR/claude_data_$(date +%Y%m%d_%H%M%S).tar.gz"
        docker run --rm -v claude_claude_data:/data -v "$(pwd)":/backup \
            alpine tar czf "/backup/$BACKUP_FILE" -C /data .
        print_success "Backup created: $BACKUP_FILE"
        ;;
    
    restore)
        if [ -z "$2" ]; then
            print_error "Please provide backup file path: ./docker_helper.sh restore <backup_file>"
            exit 1
        fi
        print_info "Restoring from backup: $2"
        docker run --rm -v claude_claude_data:/data -v "$(pwd)":/backup \
            alpine tar xzf "/backup/$2" -C /data
        print_success "Restore complete!"
        ;;
    
    stats)
        print_info "Showing resource usage..."
        docker stats ${SERVICE_NAME}-app
        ;;
    
    clean-logs)
        print_info "Clearing application logs..."
        docker compose exec ${SERVICE_NAME}-app truncate -s 0 /app/logs/*.log 2>/dev/null || true
        print_success "Logs cleared!"
        ;;
    
    *)
        echo "Claude Chat Docker Helper"
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  up                Build and start the application"
        echo "  down              Stop the application"
        echo "  restart           Restart the application"
        echo "  build             Build Docker image"
        echo "  rebuild           Rebuild Docker image (no cache)"
        echo "  logs              Show application logs (follow mode)"
        echo "  status            Check application status"
        echo "  shell             Open bash shell in container"
        echo "  test              Run health check"
        echo "  stats             Show resource usage"
        echo "  clean             Remove containers and volumes (DELETE DATA)"
        echo "  backup            Backup chat history"
        echo "  restore <file>    Restore from backup"
        echo "  clean-logs        Clear application logs"
        echo ""
        echo "Examples:"
        echo "  $0 up                              # Start the app"
        echo "  $0 logs                            # View logs"
        echo "  $0 backup                          # Backup data"
        echo "  $0 restore ./backups/backup.tar.gz # Restore data"
        exit 1
        ;;
esac
