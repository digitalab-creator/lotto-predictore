"""Public go/no-go report. The table is the sealed holdout, or a clear not-yet."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.base import get_db
from services.validation_engine_v2 import load_public_report

router = APIRouter(tags=["validation"])


@router.get("/validation/report")
def validation_report(db: Session = Depends(get_db)):
    return load_public_report(db)
