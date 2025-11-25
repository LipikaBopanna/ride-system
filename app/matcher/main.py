import asyncio
from fastapi import FastAPI
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.common.db import SessionLocal
from app.common import models, utils
from datetime import datetime

app = FastAPI(title="Mini-Uber Matcher Service")  # <-- ADDED THIS

def run_matching_cycle():
    db: Session = SessionLocal()
    try:
        pending_rides = db.query(models.Ride).filter(or_(models.Ride.status == "PENDING", models.Ride.status == "PRE_BOOKED")).all()
        available_drivers = db.query(models.Driver).filter(models.Driver.available == True).all()
        if not pending_rides or not available_drivers: return
        
        drivers_pool = available_drivers[:]
        for ride in pending_rides:
            if not drivers_pool: break
            best_driver = None
            best_dist = 10.0
            for driver in drivers_pool:
                dist = utils.haversine_distance(ride.pickup_lat, ride.pickup_lon, driver.lat, driver.lon)
                if dist < best_dist:
                    best_dist = dist
                    best_driver = driver
            if best_driver:
                ride.driver_id = best_driver.id
                ride.status = "ASSIGNED"
                ride.assigned_at = datetime.utcnow()
                best_driver.available = False
                best_driver.current_ride_id = ride.id
                db.add(best_driver)
                db.add(ride)
                drivers_pool.remove(best_driver)
                print(f"--- Matcher: Matched Ride {ride.id} to Driver {best_driver.id}")
        db.commit()
    except Exception as e:
        print(f"Matcher Error: {e}")
        db.rollback()
    finally: db.close()

async def run_loop():
    while True:
        await asyncio.to_thread(run_matching_cycle)
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event(): asyncio.create_task(run_loop())
