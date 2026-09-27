import os
import json
import gzip
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from google.cloud import storage
from google.auth import default
from shared.logging_service import get_cron_logger, LoggingService

logger = get_cron_logger()

def cleanup_system() -> None:
    """Remove old log files via the shared LoggingService (no Docker host operations)."""
    try:
        logger.info("Arrr! Starting log cleanup!")
        removed_files = LoggingService.cleanup_old_logs()
        if removed_files:
            logger.info(
                "Arrr! Successfully cleaned up old logs!",
                context={"removed_files": removed_files},
            )
        else:
            logger.info("Arrr! No old logs to clean up!")
        logger.info("Arrr! Log cleanup completed successfully!")
    except Exception as e:
        logger.error(
            "Arrr! Error during log cleanup!",
            context={"error": str(e)},
        )
        raise

def backup_database() -> None:
    """
    Create a database backup using SQLAlchemy and upload to Google Cloud Storage.
    This function creates a compressed database dump and uploads it to cloud storage.
    """
    try:
        logger.info("Arrr! Starting database backup!")
        
        # Use the same database connection as backend
        DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://lotto_user:lotto_pass@db:5432/lotto_db')
        
        # Create backup directory
        backup_dir = "/app/logs/backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{backup_dir}/lotto_db_backup_{timestamp}.json.gz"
        
        logger.info(f"Arrr! Creating backup: {backup_file}")
        
        # Create SQLAlchemy engine
        engine = create_engine(DATABASE_URL)
        
        # Get database inspector
        inspector = inspect(engine)
        
        # Get all table names
        table_names = inspector.get_table_names()
        
        backup_data = {
            "metadata": {
                "timestamp": timestamp,
                "database": "lotto_db",
                "tables": table_names,
                "backup_type": "sqlalchemy_json"
            },
            "tables": {}
        }
        
        # Backup each table
        for table_name in table_names:
            logger.info(f"Arrr! Backing up table: {table_name}")
            
            # Get table structure
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            
            # Get table data
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name}"))
                rows = [dict(row._mapping) for row in result]
            
            backup_data["tables"][table_name] = {
                "columns": columns,
                "primary_keys": primary_keys,
                "data": rows
            }
        
        # Compress and save backup
        with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        # Get file size
        file_size = os.path.getsize(backup_file)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(
            "Arrr! Local database backup completed successfully!",
            context={
                "backup_file": backup_file,
                "file_size_mb": round(file_size_mb, 2),
                "tables_backed_up": len(table_names),
                "total_rows": sum(len(table_data["data"]) for table_data in backup_data["tables"].values())
            }
        )
        
        # Upload to Google Cloud Storage
        try:
            upload_to_cloud_storage(backup_file, timestamp)
        except Exception as cloud_error:
            logger.error(
                "Arrr! Failed to upload to cloud storage, but local backup succeeded!",
                context={"error": str(cloud_error)}
            )
        
        logger.info("Arrr! Database backup completed successfully!")
            
    except Exception as e:
        logger.error(
            "Arrr! Error during database backup!",
            context={"error": str(e)}
        )
        raise

def upload_to_cloud_storage(backup_file: str, timestamp: str) -> None:
    """
    Upload backup file to Google Cloud Storage.
    
    Args:
        backup_file: Path to the backup file
        timestamp: Timestamp string for the backup
    """
    try:
        # Get bucket name from environment variable
        bucket_name = os.getenv('GCS_BUCKET_NAME')
        if not bucket_name:
            logger.warning("Arrr! GCS_BUCKET_NAME not set, skipping cloud upload!")
            return
        
        logger.info(f"Arrr! Attempting to upload to bucket: {bucket_name}")
        
        # Try to get application default credentials
        try:
            credentials, project = default()
            logger.info(f"Arrr! Using application default credentials for project: {project}")
        except Exception as cred_error:
            logger.error(
                "Arrr! Failed to get application default credentials!",
                context={"error": str(cred_error)}
            )
            raise
        
        # Initialize Google Cloud Storage client with credentials
        storage_client = storage.Client(credentials=credentials, project=project)
        
        # Get bucket
        bucket = storage_client.bucket(bucket_name)
        
        # Create blob name with timestamp
        blob_name = f"backups/lotto_db_backup_{timestamp}.json.gz"
        blob = bucket.blob(blob_name)
        
        # Upload file
        logger.info(f"Arrr! Uploading to cloud storage: gs://{bucket_name}/{blob_name}")
        blob.upload_from_filename(backup_file)
        
        # Set metadata
        blob.metadata = {
            'backup_type': 'lotto_predictor_database',
            'timestamp': timestamp,
            'database': 'lotto_db'
        }
        blob.patch()
        
        # Get file size
        file_size = os.path.getsize(backup_file)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(
            "Arrr! Cloud storage upload completed successfully!",
            context={
                "bucket": bucket_name,
                "blob": blob_name,
                "file_size_mb": round(file_size_mb, 2),
                "url": f"gs://{bucket_name}/{blob_name}"
            }
        )
        
    except Exception as e:
        logger.error(
            "Arrr! Error uploading to cloud storage!",
            context={"error": str(e)}
        )
        raise 