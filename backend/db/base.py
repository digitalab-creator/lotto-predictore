import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from config import DATABASE_URL
import logging

# Configure logging
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://lotto_user:lotto_pass@localhost:5432/lotto_db")

# Create engine with connection pooling and timeout settings
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Maximum number of connections to keep
    max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection from the pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Enable connection health checks
    connect_args={
        'connect_timeout': 10,  # Connection timeout in seconds
        'keepalives': 1,  # Enable TCP keepalive
        'keepalives_idle': 30,  # Seconds between keepalives
        'keepalives_interval': 10,  # Seconds between keepalive retries
        'keepalives_count': 5  # Number of keepalive retries
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get a database session with proper error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"[FSM ERROR] Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

Base = declarative_base() 