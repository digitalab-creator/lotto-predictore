#!/bin/bash

# Lotto Predictor Database Backup Script
# Created by the Flying Spaghetti Monster's chosen ones
# Keeps weekly backups for 2 months with easy restore functionality

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/home/orshv/lotto-predictore/backups"
DB_NAME="lotto_db"
DB_USER="lotto_user"
DB_PASSWORD="lotto_pass"
DB_HOST="localhost"
DB_PORT="5432"
RETENTION_DAYS=60  # Keep backups for 60 days (2 months)
BACKUP_PREFIX="lotto_db_backup"
LOG_FILE="/home/orshv/lotto-predictore/logs/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

# Function to check if Docker containers are running
check_docker_containers() {
    print_message "Checking if Docker containers are running..."
    
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Docker containers are not running! Starting them..."
        docker-compose up -d
        sleep 10  # Wait for containers to start
    fi
    
    # Wait for database to be ready
    print_message "Waiting for database to be ready..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            print_success "Database is ready!"
            break
        fi
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        print_error "Database failed to start within 60 seconds!"
        exit 1
    fi
}

# Function to create backup directory
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        print_message "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
}

# Function to create database backup
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/${BACKUP_PREFIX}_${timestamp}.sql"
    local compressed_file="${backup_file}.gz"
    
    print_message "Creating database backup..."
    print_message "Backup file: $backup_file"
    
    # Create the backup using pg_dump through docker-compose
    if docker-compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --create > "$backup_file"; then
        print_success "Database backup created successfully!"
        
        # Compress the backup
        print_message "Compressing backup file..."
        if gzip "$backup_file"; then
            print_success "Backup compressed: $compressed_file"
            
            # Get file size
            local file_size=$(du -h "$compressed_file" | cut -f1)
            print_message "Backup size: $file_size"
            
            # Create a symlink to the latest backup
            ln -sf "$compressed_file" "$BACKUP_DIR/latest_backup.sql.gz"
            print_success "Latest backup symlink updated"
            
            return 0
        else
            print_error "Failed to compress backup file!"
            return 1
        fi
    else
        print_error "Failed to create database backup!"
        return 1
    fi
}

# Function to clean up old backups
cleanup_old_backups() {
    print_message "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then
            rm "$file"
            deleted_count=$((deleted_count + 1))
            print_message "Deleted old backup: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "${BACKUP_PREFIX}_*.sql.gz" -mtime +$RETENTION_DAYS -print0)
    
    if [ $deleted_count -eq 0 ]; then
        print_message "No old backups to delete"
    else
        print_success "Deleted $deleted_count old backup(s)"
    fi
}

# Function to list available backups
list_backups() {
    print_message "Available backups:"
    echo "=================================="
    
    if [ -d "$BACKUP_DIR" ]; then
        local backup_count=0
        while IFS= read -r -d '' file; do
            if [ -f "$file" ]; then
                local file_size=$(du -h "$file" | cut -f1)
                local file_date=$(stat -c %y "$file" | cut -d' ' -f1)
                local file_time=$(stat -c %y "$file" | cut -d' ' -f2 | cut -d'.' -f1)
                echo "$(basename "$file") | Size: $file_size | Date: $file_date $file_time"
                backup_count=$((backup_count + 1))
            fi
        done < <(find "$BACKUP_DIR" -name "${BACKUP_PREFIX}_*.sql.gz" -print0 | sort -z)
        
        if [ $backup_count -eq 0 ]; then
            print_warning "No backups found"
        else
            print_success "Total backups: $backup_count"
        fi
    else
        print_warning "Backup directory does not exist"
    fi
}

# Function to restore database from backup
restore_backup() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        print_error "No backup file specified!"
        echo "Usage: $0 --restore <backup_file>"
        echo "Available backups:"
        list_backups
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    print_warning "This will completely replace the current database!"
    print_warning "Are you sure you want to continue? (y/N)"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_message "Restore cancelled"
        exit 0
    fi
    
    print_message "Restoring database from: $backup_file"
    
    # Stop the backend service to prevent conflicts
    print_message "Stopping backend service..."
    docker-compose stop backend
    
    # Restore the database
    if [[ "$backup_file" == *.gz ]]; then
        print_message "Decompressing and restoring backup..."
        gunzip -c "$backup_file" | docker-compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"
    else
        print_message "Restoring backup..."
        docker-compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" < "$backup_file"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Database restored successfully!"
        
        # Start the backend service
        print_message "Starting backend service..."
        docker-compose start backend
        
        print_success "Restore completed! Backend service restarted."
    else
        print_error "Database restore failed!"
        print_message "Starting backend service..."
        docker-compose start backend
        exit 1
    fi
}

# Function to create analysis copy
create_analysis_copy() {
    local backup_file="$1"
    local analysis_db="lotto_analysis_$(date '+%Y%m%d_%H%M%S')"
    
    if [ -z "$backup_file" ]; then
        print_error "No backup file specified!"
        echo "Usage: $0 --analyze <backup_file>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    print_message "Creating analysis database: $analysis_db"
    
    # Create new database for analysis
    docker-compose exec -T db createdb -U "$DB_USER" "$analysis_db"
    
    # Restore backup to analysis database
    if [[ "$backup_file" == *.gz ]]; then
        print_message "Decompressing and restoring to analysis database..."
        gunzip -c "$backup_file" | docker-compose exec -T db psql -U "$DB_USER" -d "$analysis_db"
    else
        print_message "Restoring to analysis database..."
        docker-compose exec -T db psql -U "$DB_USER" -d "$analysis_db" < "$backup_file"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Analysis database created successfully!"
        print_message "You can now connect to the analysis database:"
        print_message "Database: $analysis_db"
        print_message "User: $DB_USER"
        print_message "Password: $DB_PASSWORD"
        print_message "Host: $DB_HOST"
        print_message "Port: $DB_PORT"
        print_message ""
        print_message "To connect via psql:"
        print_message "docker-compose exec db psql -U $DB_USER -d $analysis_db"
        print_message ""
        print_message "To connect via external SQL editor, use:"
        print_message "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$analysis_db"
    else
        print_error "Failed to create analysis database!"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "Lotto Predictor Database Backup Script"
    echo "======================================"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --backup              Create a new backup (default)"
    echo "  --list                List all available backups"
    echo "  --restore <file>      Restore database from backup file"
    echo "  --analyze <file>      Create analysis copy from backup file"
    echo "  --cleanup             Clean up old backups only"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Create backup"
    echo "  $0 --list             # List backups"
    echo "  $0 --restore backups/lotto_db_backup_20241201_120000.sql.gz"
    echo "  $0 --analyze backups/lotto_db_backup_20241201_120000.sql.gz"
    echo ""
    echo "Backup files are stored in: $BACKUP_DIR"
    echo "Logs are stored in: $LOG_FILE"
}

# Main script logic
main() {
    print_message "🏴‍☠️  Lotto Predictor Database Backup Script"
    print_message "Praising the Flying Spaghetti Monster! 🍝"
    
    case "${1:---backup}" in
        --backup)
            create_backup_dir
            check_docker_containers
            create_backup
            cleanup_old_backups
            list_backups
            print_success "Backup process completed successfully!"
            ;;
        --list)
            list_backups
            ;;
        --restore)
            create_backup_dir
            check_docker_containers
            restore_backup "$2"
            ;;
        --analyze)
            create_backup_dir
            check_docker_containers
            create_analysis_copy "$2"
            ;;
        --cleanup)
            create_backup_dir
            cleanup_old_backups
            ;;
        --help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 