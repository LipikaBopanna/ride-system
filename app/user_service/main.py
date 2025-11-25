# app/user_service/main.py
import os
from datetime import datetime, date, time as dtime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.common import models
from app.common.db import get_db

app = FastAPI(title="Mini-Uber - User Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_HANDLER_URL = os.getenv("REQUEST_HANDLER_URL", "http://request-handler:7001")


# -------------------------
# Pydantic schemas (local)
# -------------------------
class UserCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    is_verified: bool
    is_subscriber: bool

    class Config:
        orm_mode = True


class CommuteSettingsCreate(BaseModel):
    home_lat: float
    home_lon: float
    work_lat: float
    work_lon: float
    morning_time: dtime
    evening_time: dtime
    fixed_price: float


class CommuteSettingsOut(CommuteSettingsCreate):
    id: int
    user_id: int

    class Config:
        orm_mode = True


class CommutePause(BaseModel):
    date: date
    ride_type: str = Field(..., description="one of 'morning','evening','all'")


class CommuteAdjust(BaseModel):
    date: date
    ride_type: str = Field(..., description="one of 'morning' or 'evening'")
    new_time: dtime


class RideCreate(BaseModel):
    user_id: int
    pickup_lat: float
    pickup_lon: float
    drop_lat: float
    drop_lon: float
    pickup_name: Optional[str] = None
    dropoff_name: Optional[str] = None
    fixed_price: Optional[float] = None


class RideOut(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int]
    status: str
    pickup_lat: float
    pickup_lon: float
    drop_lat: float
    drop_lon: float
    created_at: datetime

    class Config:
        orm_mode = True


# -------------------------
# User endpoints
# -------------------------
@app.post("/users", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # basic uniqueness checks
    if db.query(models.User).filter(models.User.phone == user.phone).first():
        raise HTTPException(status_code=400, detail="Phone already registered")

    db_user = models.User(
        name=user.name, phone=user.phone, email=user.email, is_verified=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/users/{user_id}/subscribe", response_model=UserOut)
def subscribe_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.is_subscriber = True
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/users/{user_id}/commute", response_model=CommuteSettingsOut)
def setup_commute(user_id: int, commute: CommuteSettingsCreate, db: Session = Depends(get_db)):
    # ensure user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_commute = db.query(models.CommuteSettings).filter(models.CommuteSettings.user_id == user_id).first()
    if db_commute:
        # update existing
        for k, v in commute.dict().items():
            setattr(db_commute, k, v)
    else:
        db_commute = models.CommuteSettings(**commute.dict(), user_id=user_id)
        db.add(db_commute)
    db.commit()
    db.refresh(db_commute)
    return db_commute


# -------------------------
# Commute pause & adjust
# -------------------------
@app.post("/commute/pause")
def pause_commute_ride(pause_req: CommutePause, db: Session = Depends(get_db)):
    # For demo: operate on user 1 commute settings (same convention as your demo)
    db_commute = db.query(models.CommuteSettings).filter(models.CommuteSettings.user_id == 1).first()
    if not db_commute:
        raise HTTPException(status_code=404, detail="Commute settings not found")

    # If pausing for today, enforce 1-hour cutoff
    today = datetime.utcnow().date()
    if pause_req.date == today:
        now_utc = datetime.utcnow()
        # determine relevant target time
        target_time = None
        if pause_req.ride_type == "morning":
            target_time = db_commute.morning_time
        elif pause_req.ride_type == "evening":
            target_time = db_commute.evening_time

        if target_time:
            ride_dt = datetime.combine(today, target_time)
            time_diff = (ride_dt - now_utc)
            # if difference in seconds is less than 3600 -> reject
            if time_diff.total_seconds() < 3600:
                raise HTTPException(status_code=400, detail="POLICY VIOLATION: Cannot cancel ride less than 1 hour before pickup.")

    # create or update override row
    override = db.query(models.CommuteScheduleOverride).filter(
        models.CommuteScheduleOverride.commute_id == db_commute.id,
        models.CommuteScheduleOverride.date == pause_req.date
    ).first()
    if not override:
        override = models.CommuteScheduleOverride(commute_id=db_commute.id, date=pause_req.date)
        db.add(override)

    if pause_req.ride_type == "all":
        override.morning_ride_status = "PAUSED"
        override.evening_ride_status = "PAUSED"
    elif pause_req.ride_type == "morning":
        override.morning_ride_status = "PAUSED"
    elif pause_req.ride_type == "evening":
        override.evening_ride_status = "PAUSED"

    db.commit()
    return {"status": "Ride(s) paused successfully", "date": pause_req.date}


@app.post("/commute/adjust")
def adjust_commute_ride(adjust_req: CommuteAdjust, db: Session = Depends(get_db)):
    db_commute = db.query(models.CommuteSettings).filter(models.CommuteSettings.user_id == 1).first()
    if not db_commute:
        raise HTTPException(status_code=404, detail="Commute settings not found")

    override = db.query(models.CommuteScheduleOverride).filter(
        models.CommuteScheduleOverride.commute_id == db_commute.id,
        models.CommuteScheduleOverride.date == adjust_req.date
    ).first()
    if not override:
        override = models.CommuteScheduleOverride(commute_id=db_commute.id, date=adjust_req.date)
        db.add(override)

    if adjust_req.ride_type == "morning":
        override.morning_ride_status = "ADJUSTED"
        override.morning_ride_time = adjust_req.new_time
    elif adjust_req.ride_type == "evening":
        override.evening_ride_status = "ADJUSTED"
        override.evening_ride_time = adjust_req.new_time

    db.commit()
    return {"status": "Ride time altered successfully"}


# -------------------------
# Ride endpoints (status + create helper)
# -------------------------
@app.get("/ride-status/{ride_id}", response_model=RideOut)
def get_ride_status(ride_id: int, db: Session = Depends(get_db)):
    """
    Returns ride status and key ride fields. Demo expects this endpoint.
    """
    ride = db.query(models.Ride).filter(models.Ride.id == ride_id).first()
    if not ride:
        # FastAPI by default returns {"detail": "Not Found"} when raising HTTPException(404)
        raise HTTPException(status_code=404, detail="Ride not found")

    # Ensure driver_id might be nullable; Pydantic will handle it
    return ride


@app.post("/rides", response_model=RideOut)
def create_ride(ride_in: RideCreate, db: Session = Depends(get_db)):
    """
    Convenience helper to create a ride quickly for testing/demo.
    In your real flow, rides may be created by the scheduler/request-handler.
    """
    # verify user exists
    user = db.query(models.User).filter(models.User.id == ride_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ride = models.Ride(
        user_id=ride_in.user_id,
        pickup_lat=ride_in.pickup_lat,
        pickup_lon=ride_in.pickup_lon,
        drop_lat=ride_in.drop_lat,
        drop_lon=ride_in.drop_lon,
        pickup_name=ride_in.pickup_name,
        dropoff_name=ride_in.dropoff_name,
        fixed_price=ride_in.fixed_price,
        status="PENDING",
        created_at=datetime.utcnow(),
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride


# -------------------------
# Root / health
# -------------------------
@app.get("/")
def root():
    return {"service": "user_service", "status": "ok"}
