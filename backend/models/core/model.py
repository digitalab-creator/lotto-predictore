import enum
from sqlalchemy import Column, Integer, String, Enum, JSON, DateTime, UniqueConstraint
import datetime
from db.base import Base

class ModelType(enum.Enum):
    main = "main"
    strong = "strong"

class Model(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    type = Column(Enum(ModelType), nullable=False)
    model_path = Column(String, nullable=True)
    params = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (UniqueConstraint('name', 'version', 'type', name='_model_version_uc'),) 