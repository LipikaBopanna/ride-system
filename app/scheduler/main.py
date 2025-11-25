import time
import asyncio
from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.common.db import get_db, SessionLocal
from app.common import models
from datetime import datetime, timedelta, date, time as dt_time

app = FastAPI(title="Mini-Uber Scheduler Service")

# We look 2 hours ahead so rides are booked well in advance
PRE_BOOK_MINUTES = 120 

def run_scheduler_cycle():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        # (Optional: Adjust for timezone if needed, keeping UTC for Docker simplicity)
        current_time = now.time()
        today = now.date()
        
        # --- RULE: EXCLUDE WEEKENDS ---
        # weekday(): 0=Mon, 1=Tue, ... 5=Sat, 6=Sun
        if today.weekday() >= 5:
            # print("--- Scheduler: Weekend detected. No commute rides today. ---")
            return

        # Look-ahead window
        window_end = (now + timedelta(minutes=PRE_BOOK_MINUTES)).time()
        
        commutes = db.query(models.CommuteSettings).all()
        
        for commute in commutes:
            # Check overrides (Paused/Adjusted)
            override = db.query(models.CommuteScheduleOverride).filter(
                models.CommuteScheduleOverride.commute_id == commute.id,
                models.CommuteScheduleOverride.date == today
            ).first()

            # Check Morning
            m_status = override.morning_ride_status if override else "SCHEDULED"
            m_time = override.morning_ride_time if override and override.morning_ride_time else commute.morning_time
            
            if m_status != "PAUSED" and (current_time <= m_time <= window_end):
                create_pre_booked_ride(db, commute, m_time, "morning", today)

            # Check Evening
            e_status = override.evening_ride_status if override else "SCHEDULED"
            e_time = override.evening_ride_time if override and override.evening_ride_time else commute.evening_time
            
            if e_status != "PAUSED" and (current_time <= e_time <= window_end):
                create_pre_booked_ride(db, commute, e_time, "evening", today)

        db.commit()
    except Exception as e:
        print(f"Scheduler error: {e}")
    finally:
        db.close()

def create_pre_booked_ride(db: Session, commute: models.CommuteSettings, ride_time: dt_time, ride_type: str, ride_date: date):
    # Check if already booked for this day
    existing = db.query(models.Ride).filter(
        models.Ride.user_id == commute.user_id,
        models.Ride.status.in_(["PRE_BOOKED", "ASSIGNED", "ONGOING", "COMPLETED"]),
        models.Ride.created_at >= datetime.combine(ride_date, dt_time(0,0)),
        models.Ride.created_at <= datetime.combine(ride_date, dt_time(23,59))
    ).first()
    
    if existing: return

    # Swap coordinates based on morning/evening
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
        price=commute.fixed_price, # Use Subscription Price
        fixed_price=commute.fixed_price,
        created_at=datetime.now() 
    )
    db.add(new_ride)
    print(f"--- Scheduler: AUTOMATION SUCCESS! Created {ride_type} ride for User {commute.user_id} at {ride_time} ---")

async def scheduler_loop():
    while True:
        await asyncio.to_thread(run_scheduler_cycle)
        await asyncio.sleep(10) # Check every 10 seconds

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduler_loop())