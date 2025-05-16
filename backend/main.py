from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .db import SessionLocal

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Ahoy! The backend be runnin', praisin' the FSM!"} 