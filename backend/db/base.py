import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://lotto_user:lotto_pass@localhost:5432/lotto_db")

engine = create_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    pool_size=20,         # Arrr, more connections in the pool!
    max_overflow=30,      # Arrr, more overflow for heavy seas!
    pool_timeout=30,      # Wait 30 seconds for a connection
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() 