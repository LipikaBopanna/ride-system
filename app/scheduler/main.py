# app/scheduler/main.py

import asyncio
from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.common.db import SessionLocal
from app.common import models
from datetime import datetime, timedelta, date, time as dt_time

app = FastAPI(title="Scheduler Service")

PRE_BOOK_MINUTES = 120


# =========================
# CREATE RIDE (NO DUPLICATES)
# =========================
def create_pre_booked_ride(
    db: Session,
    commute: models.CommuteSettings,
    ride_time: dt_time,
    ride_type: str,
    ride_date: date
):

    # ✅ STRICT duplicate check (FINAL FIX)
    existing = db.query(models.Ride).filter(
        models.Ride.user_id == commute.user_id,
        models.Ride.ride_date == ride_date,
        models.Ride.time == ride_time
    ).first()

    if existing:
        return

    # Decide route
    if ride_type == "morning":
        plat, plon = commute.home_lat, commute.home_lon
        dlat, dlon = commute.work_lat, commute.work_lon
        pname, dname = "Home", "Work"
    else:
        plat, plon = commute.work_lat, commute.work_lon
        dlat, dlon = commute.home_lat, commute.home_lon
        pname, dname = "Work", "Home"

    # ✅ create ride
    new_ride = models.Ride(
        user_id=commute.user_id,
        pickup_lat=plat,
        pickup_lon=plon,
        pickup_name=pname,
        drop_lat=dlat,
        drop_lon=dlon,
        dropoff_name=dname,
        status="PRE_BOOKED",
        price=commute.fixed_price,
        fixed_price=commute.fixed_price,
        ride_date=ride_date,      # ✅ important
        time=ride_time,           # ✅ important
        created_at=datetime.utcnow()
    )

    db.add(new_ride)
    db.commit()

    print(f"✔ Created {ride_type} ride for user {commute.user_id}")


# =========================
# MAIN SCHEDULER LOGIC
# =========================
def run_scheduler_cycle():
    db: Session = SessionLocal()

    try:
        now = datetime.utcnow()
        today = now.date()

        # skip weekends
        if today.weekday() >= 5:
            return

        window_end = (now + timedelta(minutes=PRE_BOOK_MINUTES)).time()

        commutes = db.query(models.CommuteSettings).all()

        for commute in commutes:

            override = db.query(models.CommuteScheduleOverride).filter(
                models.CommuteScheduleOverride.commute_id == commute.id,
                models.CommuteScheduleOverride.date == today
            ).first()

            # MORNING
            m_status = override.morning_ride_status if override else "SCHEDULED"
            m_time = override.morning_ride_time if override and override.morning_ride_time else commute.morning_time

            if m_status != "PAUSED" and (now.time() <= m_time <= window_end):
                create_pre_booked_ride(db, commute, m_time, "morning", today)

            # EVENING
            e_status = override.evening_ride_status if override else "SCHEDULED"
            e_time = override.evening_ride_time if override and override.evening_ride_time else commute.evening_time

            if e_status != "PAUSED" and (now.time() <= e_time <= window_end):
                create_pre_booked_ride(db, commute, e_time, "evening", today)

    except Exception as e:
        print("Scheduler error:", e)

    finally:
        db.close()


# =========================
# LOOP (DISABLED FOR NOW)
# =========================
async def scheduler_loop():
    while True:
        await asyncio.to_thread(run_scheduler_cycle)
        await asyncio.sleep(60)  # slower loop


# ❌ KEEP DISABLED (important for your demo)
# @app.on_event("startup")
# async def startup_event():
#     asyncio.create_task(scheduler_loop())