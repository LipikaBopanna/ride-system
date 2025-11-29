# app/scheduler/main.py
import asyncio
from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.common.db import SessionLocal, Base, engine
from app.common import models
from datetime import datetime, timedelta, date, time as dt_time

#Base.metadata.create_all(bind=engine)

app = FastAPI(title="Scheduler Service")

PRE_BOOK_MINUTES = 120

def create_pre_booked_ride(db: Session, commute: models.CommuteSettings, ride_time: dt_time, ride_type: str, ride_date: date):
    existing = db.query(models.Ride).filter(
        models.Ride.user_id == commute.user_id,
        models.Ride.status.in_(["PRE_BOOKED", "ASSIGNED", "ONGOING", "COMPLETED"]),
        models.Ride.created_at >= datetime.combine(ride_date, dt_time(0,0)),
        models.Ride.created_at <= datetime.combine(ride_date, dt_time(23,59))
    ).first()
    if existing:
        return

    if ride_type == "morning":
        plat, plon, dlat, dlon = commute.home_lat, commute.home_lon, commute.work_lat, commute.work_lon
        pname, dname = "Home", "Work"
    else:
        plat, plon, dlat, dlon = commute.work_lat, commute.work_lon, commute.home_lat, commute.home_lon
        pname, dname = "Work", "Home"

    new_ride = models.Ride(
        user_id=commute.user_id,
        pickup_lat=plat, pickup_lon=plon, pickup_name=pname,
        drop_lat=dlat, drop_lon=dlon, dropoff_name=dname,
        status="PRE_BOOKED",
        price=commute.fixed_price,
        fixed_price=commute.fixed_price,
        created_at=datetime.utcnow()
    )
    db.add(new_ride)
    db.commit()
    print(f"--- Scheduler: Created {ride_type} PRE_BOOKED ride for user {commute.user_id} at {ride_time}")

def run_scheduler_cycle():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        today = now.date()
        if today.weekday() >= 5:
            return
        window_end = (now + timedelta(minutes=PRE_BOOK_MINUTES)).time()

        commutes = db.query(models.CommuteSettings).all()
        for commute in commutes:
            override = db.query(models.CommuteScheduleOverride).filter(
                models.CommuteScheduleOverride.commute_id == commute.id,
                models.CommuteScheduleOverride.date == today
            ).first()

            m_status = override.morning_ride_status if override else "SCHEDULED"
            m_time = override.morning_ride_time if override and override.morning_ride_time else commute.morning_time
            if m_status != "PAUSED" and (now.time() <= m_time <= window_end):
                create_pre_booked_ride(db, commute, m_time, "morning", today)

            e_status = override.evening_ride_status if override else "SCHEDULED"
            e_time = override.evening_ride_time if override and override.evening_ride_time else commute.evening_time
            if e_status != "PAUSED" and (now.time() <= e_time <= window_end):
                create_pre_booked_ride(db, commute, e_time, "evening", today)
    except Exception as e:
        print("Scheduler error", e)
    finally:
        db.close()

async def scheduler_loop():
    while True:
        await asyncio.to_thread(run_scheduler_cycle)
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduler_loop())
