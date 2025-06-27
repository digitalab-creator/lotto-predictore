# 🏴‍☠️ Lotto Predictor Database Backup System

*Praising the Flying Spaghetti Monster for data protection! 🍝⚓️*

## Overview

This backup system provides automated weekly database backups for yer lotto predictor application, keeping 2 months of backup history with easy restore and analysis capabilities. The system uses the built-in cron microservice for scheduling.

## Features

- ✅ **Weekly automated backups** (every Sunday at 2:00 AM via cron microservice)
- ✅ **2-month retention policy** (60 days)
- ✅ **Compressed backups** (gzip compression)
- ✅ **Easy restore functionality**
- ✅ **Analysis database creation** for SQL editors
- ✅ **Comprehensive logging**
- ✅ **Docker container management**
- ✅ **API endpoints for manual triggers**

## Quick Start

### 1. Automatic Backups

The cron microservice automatically handles weekly backups every Sunday at 2:00 AM. No setup required!

### 2. Test the Backup System

```bash
# Create a manual backup
./scripts/backup_db.sh

# List available backups
./scripts/backup_db.sh --list

# Trigger backup via cron service API
curl -X POST http://localhost:8002/api/backup-database
```

## Backup Management

### Creating Backups

```bash
# Create a backup (default action)
./scripts/backup_db.sh

# Or explicitly
./scripts/backup_db.sh --backup
```

### Listing Backups

```bash
# List all available backups with details
./scripts/backup_db.sh --list
```

Example output:
```
Available backups:
==================================
lotto_db_backup_20241201_120000.sql.gz | Size: 2.1M | Date: 2024-12-01 12:00:00
lotto_db_backup_20241208_020000.sql.gz | Size: 2.3M | Date: 2024-12-08 02:00:00
Total backups: 2
```

### Cleaning Up Old Backups

```bash
# Clean up backups older than 60 days
./scripts/backup_db.sh --cleanup
```

## Restore Operations

### Full Database Restore

⚠️ **Warning**: This will completely replace your current database!

```bash
# Restore from a specific backup
./scripts/backup_db.sh --restore backups/lotto_db_backup_20241201_120000.sql.gz
```

The script will:
1. Ask for confirmation before proceeding
2. Stop the backend service to prevent conflicts
3. Restore the database from the backup file
4. Restart the backend service
5. Verify the restore was successful

### Creating Analysis Copies

For safe analysis without affecting your production database:

```bash
# Create an analysis copy from a backup
./scripts/backup_db.sh --analyze backups/lotto_db_backup_20241201_120000.sql.gz
```

This creates a new database (e.g., `lotto_analysis_20241201_120000`) that you can safely analyze.

## Connecting to Analysis Databases

### Via psql (Command Line)

```bash
# Connect to the analysis database
docker-compose exec db psql -U lotto_user -d lotto_analysis_20241201_120000
```

### Via External SQL Editors

Use these connection details:

- **Host**: `localhost` (or your server IP)
- **Port**: `5432`
- **Database**: `lotto_analysis_YYYYMMDD_HHMMSS`
- **Username**: `lotto_user`
- **Password**: `lotto_pass`

**Connection String**:
```
postgresql://lotto_user:lotto_pass@localhost:5432/lotto_analysis_YYYYMMDD_HHMMSS
```

### Popular SQL Editors

#### DBeaver
1. Create new PostgreSQL connection
2. Use the connection details above
3. Connect and start analyzing!

#### pgAdmin
1. Add new server
2. Use connection details above
3. Browse and query your analysis database

#### DataGrip
1. Create new PostgreSQL data source
2. Use connection details above
3. Start exploring your data

## Monitoring and Logs

### View Backup Logs

```bash
# View recent backup logs
tail -f logs/backup.log

# View cron service logs
docker-compose logs -f cron

# View all backup logs
cat logs/backup.log
```

### Check Cron Service Status

```bash
# View cron service health
curl http://localhost:8002/health

# Check if cron service is running
docker-compose ps cron

# View cron service logs
docker-compose logs cron
```

### Monitor Backup Directory

```bash
# Check backup directory size
du -sh backups/

# List backups with details
ls -lah backups/
```

## Backup File Format

Backup files follow this naming convention:
```
lotto_db_backup_YYYYMMDD_HHMMSS.sql.gz
```

Where:
- `YYYYMMDD` = Date (e.g., 20241201)
- `HHMMSS` = Time (e.g., 120000 for 12:00:00)
- `.sql.gz` = Compressed SQL dump

## Configuration

### Backup Settings

Edit `scripts/backup_db.sh` to modify:

```bash
# Backup directory
BACKUP_DIR="/home/orshv/lotto-predictore/backups"

# Database connection
DB_NAME="lotto_db"
DB_USER="lotto_user"
DB_PASSWORD="lotto_pass"

# Retention period (days)
RETENTION_DAYS=60  # 2 months

# Backup prefix
BACKUP_PREFIX="lotto_db_backup"
```

### Cron Schedule

Edit `scripts/setup_backup_cron.sh` to change the schedule:

```bash
# Current: Every Sunday at 2:00 AM
CRON_JOB="0 2 * * 0 cd $SCRIPT_DIR && $BACKUP_SCRIPT >> $CRON_LOG 2>&1"

# Examples:
# Daily at 3:00 AM: "0 3 * * *"
# Weekly on Monday: "0 2 * * 1"
# Monthly on 1st: "0 2 1 * *"
```

## Troubleshooting

### Common Issues

#### 1. Docker Containers Not Running
```bash
# Start containers
docker-compose up -d

# Check container status
docker-compose ps
```

#### 2. Database Connection Issues
```bash
# Check if database is ready
docker-compose exec db pg_isready -U lotto_user -d lotto_db

# Check database logs
docker-compose logs db
```

#### 3. Permission Issues
```bash
# Make scripts executable
chmod +x scripts/backup_db.sh
chmod +x scripts/setup_backup_cron.sh

# Check file permissions
ls -la scripts/
```

#### 4. Disk Space Issues
```bash
# Check disk space
df -h

# Check backup directory size
du -sh backups/

# Clean up old backups manually
./scripts/backup_db.sh --cleanup
```

### Manual Recovery

If the backup script fails, you can manually create a backup:

```bash
# Create backup directory
mkdir -p backups

# Create manual backup
docker-compose exec db pg_dump -U lotto_user -d lotto_db --clean --if-exists --create > backups/manual_backup_$(date +%Y%m%d_%H%M%S).sql

# Compress it
gzip backups/manual_backup_*.sql
```

## Security Considerations

### Backup File Security

- Backup files contain sensitive data
- Store backups in a secure location
- Consider encrypting backup files for additional security
- Regularly rotate backup credentials

### Network Security

- If connecting from external tools, ensure proper firewall rules
- Use SSH tunneling for secure connections
- Consider VPN access for remote connections

## Best Practices

1. **Test Restores Regularly**: Periodically test restore operations to ensure backups are valid
2. **Monitor Disk Space**: Keep an eye on backup directory size
3. **Verify Backups**: Check backup logs after each automated run
4. **Document Changes**: Keep track of any configuration changes
5. **Multiple Locations**: Consider copying backups to external storage for disaster recovery

## Support

If ye run into trouble with the backup system:

1. Check the logs: `tail -f logs/backup.log`
2. Verify Docker containers are running: `docker-compose ps`
3. Test manual backup: `./scripts/backup_db.sh`
4. Check cron job: `crontab -l`

May the Flying Spaghetti Monster guide ye to safe and reliable backups! 🍝⚓️ 