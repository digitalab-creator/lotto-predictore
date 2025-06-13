from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.orm import Session
from models import Model, ModelType
from typing import Dict, Any
from services.logger import dh_log

def get_or_create_model(session: Session, version: str, algo_version: str, model_type: ModelType, params: Dict[str, Any]) -> Model:
    """
    Get or create a model in the database.
    
    Args:
        session (Session): Database session
        version (str): Model version
        algo_version (str): Algorithm version
        model_type (ModelType): Type of model
        params (Dict[str, Any]): Model parameters
        
    Returns:
        Model: Database model instance
    """
    model = session.query(Model).filter(
        Model.version == version,
        Model.algo_version == algo_version,
        Model.model_type == model_type
    ).first()
    
    if not model:
        model = Model(
            version=version,
            algo_version=algo_version,
            model_type=model_type,
            params=params
        )
        session.add(model)
        session.flush()
        
    return model 