from sqlalchemy.exc import NoResultFound, IntegrityError
from models import Model
from services.logger import dh_log

def get_or_create_model(session, name, version, type_, params, model_path=None):
    try:
        return session.query(Model).filter_by(name=name, version=version, type=type_).one()
    except NoResultFound:
        model = Model(name=name, version=version, type=type_, model_path=model_path)
        session.add(model)
        try:
            session.commit()
            return model
        except IntegrityError as e:
            session.rollback()
            dh_log(
                "Arrr! IntegrityError in get_or_create_model, likely due to race condition. Praisin' the FSM!",
                level="WARNING",
                context={
                    "name": name,
                    "version": version,
                    "type": str(type_),
                    "error": str(e)
                }
            )
            # Try to fetch again after rollback
            return session.query(Model).filter_by(name=name, version=version, type=type_).one() 