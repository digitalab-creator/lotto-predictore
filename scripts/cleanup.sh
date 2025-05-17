#!/bin/bash

# Function to print colored output and log to Google Cloud
print_message() {
    echo -e "\033[1;34m$1\033[0m"
    logger -t docker-cleanup "$1"
}

print_error() {
    echo -e "\033[1;31m$1\033[0m"
    logger -t docker-cleanup -p err "$1"
}

print_success() {
    echo -e "\033[1;32m$1\033[0m"
    logger -t docker-cleanup -p info "$1"
}

# Function to check if a container is running
is_container_running() {
    docker ps -q --filter "name=$1" | grep -q .
}

# Function to check if a container exists
container_exists() {
    docker ps -a -q --filter "name=$1" | grep -q .
}

# Function to get disk usage percentage
get_disk_usage() {
    df -h / | awk 'NR==2 {print $5}' | sed 's/%//'
}

# Function to check if disk usage is above threshold
check_disk_usage() {
    local threshold=${1:-85}  # Default threshold is 85%
    local usage=$(get_disk_usage)
    if [ "$usage" -gt "$threshold" ]; then
        return 0  # True - disk usage is high
    else
        return 1  # False - disk usage is normal
    fi
}

# Function to clean up old containers
cleanup_old_containers() {
    local days=${1:-7}  # Default to 7 days
    print_message "Cleaning up containers older than $days days..."
    docker container prune -f
}

# Function to clean up old images
cleanup_old_images() {
    local days=${1:-7}  # Default to 7 days
    print_message "Cleaning up images older than $days days..."
    docker image prune -f
}

# Function to clean up unused volumes
cleanup_unused_volumes() {
    print_message "Cleaning up unused volumes..."
    # List volumes before cleanup
    print_message "Current volumes before cleanup:"
    docker volume ls --format "table {{.Name}}\t{{.Size}}\t{{.Driver}}"
    
    # Only remove volumes that are not in use
    docker volume prune -f
    
    # List remaining volumes
    print_message "Remaining volumes after cleanup:"
    docker volume ls --format "table {{.Name}}\t{{.Size}}\t{{.Driver}}"
}

# Function to perform automatic cleanup
auto_cleanup() {
    local disk_threshold=${1:-85}  # Default threshold is 85%
    local container_age=${2:-7}    # Default age is 7 days
    local image_age=${3:-7}        # Default age is 7 days

    print_message "Starting automatic cleanup..."
    print_message "Disk threshold: ${disk_threshold}%, Container age: ${container_age}d, Image age: ${image_age}d"
    
    # Check disk usage
    if check_disk_usage "$disk_threshold"; then
        print_message "Disk usage is high, performing full cleanup..."
        # Before full cleanup, backup important volumes if needed
        docker system prune -af --volumes
    else
        # Regular cleanup based on age
        cleanup_old_containers "$container_age"
        cleanup_old_images "$image_age"
        cleanup_unused_volumes
    fi
}

# Parse command line arguments
case "$1" in
    "--auto")
        auto_cleanup "${2:-85}" "${3:-7}" "${4:-7}"
        ;;
    "--volumes")
        print_message "Stopping all running containers..."
        docker-compose down
        print_message "Removing stopped containers..."
        docker container prune -f
        print_message "Removing unused networks..."
        docker network prune -f
        print_message "Removing unused volumes..."
        docker volume prune -f
        print_message "Removing dangling images..."
        docker image prune -f
        ;;
    "--optimize-frontend")
        print_message "Arrr! Optimizing frontend performance for the glory of the FSM!"
        print_message "1. Clearing Next.js build cache in backend container..."
        docker-compose exec backend rm -rf /app/frontend/.next/cache
        print_message "2. Restarting the backend service (frontend/backend)..."
        docker-compose restart backend
        print_message "3. Waiting for frontend to initialize (30 seconds)..."
        sleep 30
        print_success "Frontend should now be optimized and runnin', matey!"
        print_message "If still slow, try:"
        print_message "- Run this script with --auto for a full cleanup."
        print_message "- Check Docker resources (increase CPU/memory)."
        print_message "- Disable any virus scanning on the frontend directory."
        print_message "- Rejoice in the noodly embrace of the FSM!"
        print_message "You can now access the frontend at http://localhost:3000"
        ;;
    *)
        print_message "Stopping all running containers..."
        docker-compose down
        print_message "Removing stopped containers..."
        docker container prune -f
        print_message "Removing unused networks..."
        docker network prune -f
        print_message "Removing dangling images..."
        docker image prune -f
        ;;
esac

print_success "Cleanup completed successfully!" 