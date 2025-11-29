# app/user_service/main.py
import os
import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.common.db import get_db, engine, Base
from app.common import models, schemas

# Create tables if needed
#Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

REQUEST_HANDLER_URL = os.getenv("REQUEST_HANDLER_URL", "http://request-handler:7001")

@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/request-ride", response_model=schemas.RideOut)
def request_ride(req: schemas.RideRequest):
    with httpx.Client(timeout=10.0) as client:
        response = client.post(f"{REQUEST_HANDLER_URL}/ride/request", json=req.dict())
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=str(response.text))
        return response.json()

@app.get("/ride-status/{ride_id}", response_model=schemas.RideOut)
def get_ride_status(ride_id: int, db: Session = Depends(get_db)):
    ride = db.query(models.Ride).filter(models.Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id:
        ride.driver = db.query(models.Driver).filter(models.Driver.id == ride.driver_id).first()
    return ride

@app.post("/users/{user_id}/subscribe", response_model=schemas.UserOut)
def subscribe_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.is_subscriber = True
    db.commit()
    db.refresh(db_user)
    return db_user
