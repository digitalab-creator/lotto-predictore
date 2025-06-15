from sqlalchemy.exc import NoResultFound, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from models import Model, ModelType, Draw, Prediction
from typing import Dict, Any, Optional, List
from logger import logger
import traceback

def get_or_create_model(session: Session, version: str, algo_version: str, model_type: ModelType, params: Dict[str, Any]) -> Optional[Model]:
    """
    Get or create a model in the database.
    
    Args:
        session (Session): Database session
        version (str): Model version
        algo_version (str): Algorithm version (used for logging only)
        model_type (ModelType): Type of model
        params (Dict[str, Any]): Model parameters
        
    Returns:
        Optional[Model]: Database model instance or None if an error occurs
        
    Raises:
        ValueError: If required parameters are missing or invalid
        SQLAlchemyError: If database operations fail
    """
    try:
        # Input validation
        if not version or not model_type:
            raise ValueError("Missing required parameters: version and model_type are required")
        
        logger.debug(
            "Arrr! Attempting to get or create model",
            context={
                "version": version,
                "algo_version": algo_version,  # Keep for logging
                "model_type": model_type.value,
                "params_keys": list(params.keys()) if params else []
            }
        )
        
        # Try to find existing model
        try:
            model = session.query(Model).filter(
                Model.version == version,
                Model.type == model_type
            ).first()
            
            if model:
                logger.debug(
                    "Arrr! Found existing model",
                    context={
                        "model_id": model.id,
                        "version": model.version,
                        "model_type": model.type.value,
                        "algo_version": algo_version  # Keep for logging
                    }
                )
                return model
                
        except SQLAlchemyError as e:
            logger.error(
                "Arrr! Database error while querying model",
                context={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "version": version,
                    "algo_version": algo_version,  # Keep for logging
                    "model_type": model_type.value
                }
            )
            raise
        
        # Create new model if not found
        try:
            logger.info(
                "Arrr! Creating new model",
                context={
                    "version": version,
                    "algo_version": algo_version,  # Keep for logging
                    "model_type": model_type.value
                }
            )
            
            model = Model(
                name=f"{model_type.value}_{version}",  # Create a name from type and version
                version=version,
                type=model_type,
                params=params
            )
            session.add(model)
            session.flush()
            
            logger.info(
                "Arrr! Successfully created new model",
                context={
                    "model_id": model.id,
                    "version": model.version,
                    "model_type": model.type.value,
                    "algo_version": algo_version  # Keep for logging
                }
            )
            
            return model
            
        except IntegrityError as e:
            logger.warning(
                "Arrr! Integrity error while creating model - likely a race condition",
                context={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "version": version,
                    "algo_version": algo_version,
                    "model_type": model_type.value
                }
            )
            # Try to get the model again in case it was created by another process
            try:
                model = session.query(Model).filter(
                    Model.version == version,
                    Model.type == model_type
                ).first()
                if model:
                    logger.info(
                        "Arrr! Found model after integrity error (race condition)",
                        context={
                            "model_id": model.id,
                            "version": model.version,
                            "model_type": model.type.value
                        }
                    )
                    return model
            except SQLAlchemyError as e2:
                logger.error(
                    "Arrr! Failed to recover from integrity error",
                    context={
                        "original_error": str(e),
                        "recovery_error": str(e2),
                        "traceback": traceback.format_exc()
                    }
                )
                raise
                
        except SQLAlchemyError as e:
            logger.error(
                "Arrr! Database error while creating model",
                context={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "version": version,
                    "algo_version": algo_version,
                    "model_type": model_type.value
                }
            )
            raise
            
    except Exception as e:
        logger.error(
            "Arrr! Unexpected error in get_or_create_model",
            context={
                "error": str(e),
                "traceback": traceback.format_exc(),
                "version": version,
                "algo_version": algo_version,
                "model_type": model_type.value if model_type else None
            }
        )
        raise 