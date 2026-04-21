# app/matcher/main.py
import asyncio
import httpx
from fastapi import FastAPI
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.common.db import SessionLocal
from app.common import models, utils
from datetime import datetime

app = FastAPI(title="Matcher Service")

NOTIFIER_URL = "http://notifier:7003"
MATCH_RADIUS_KM = 5.0

def run_matching_cycle():
    db: Session = SessionLocal()
    try:
        pending_rides = db.query(models.Ride).filter(
            or_(models.Ride.status == "PENDING", models.Ride.status == "PRE_BOOKED")
        ).order_by(models.Ride.created_at).all()
        if not pending_rides:
            return

        available_drivers = db.query(models.Driver).filter(models.Driver.available == True, models.Driver.is_verified == True).all()
        if not available_drivers:
            print("--- Matcher: No available drivers.")
            return

        for ride in pending_rides:
            best_driver = None
            best_dist = MATCH_RADIUS_KM
            for driver in available_drivers:
                dist = utils.haversine_distance(ride.pickup_lat, ride.pickup_lon, driver.lat, driver.lon)
                if dist < best_dist:
                    best_dist = dist
                    best_driver = driver
            if not best_driver:
                print(f"--- Matcher: No driver within {MATCH_RADIUS_KM} km for ride {ride.id}")
                continue

            # Mark ride as REQUESTED (driver has been asked but not assigned)
            ride.status = "REQUESTED"
            ride.assigned_at = datetime.utcnow()
            best_driver.current_ride_id = ride.id
            best_driver.available = False
            db.add(ride)
            db.add(best_driver)
            db.commit()
            print(f"Matcher: Requesting Driver {best_driver.id} for Ride {ride.id} (dist {best_dist:.2f} km)")

            available_drivers = [driver for driver in available_drivers if driver.id != best_driver.id]

            payload = {
                "driver_id": best_driver.id,
                "ride": {
                    "id": ride.id,
                    "user_id": ride.user_id,
                    "pickup_name": ride.pickup_name,
                    "pickup_lat": ride.pickup_lat,
                    "pickup_lon": ride.pickup_lon,
                    "dropoff_name": ride.dropoff_name,
                    "drop_lat": ride.drop_lat,
                    "drop_lon": ride.drop_lon,
                    "price": ride.price,
                }
            }
            try:
                with httpx.Client(timeout=5.0) as client:
                    client.post(f"{NOTIFIER_URL}/driver/request", json=payload)
            except Exception as e:
                print("Matcher: notify driver error", e)
    except Exception as e:
        print("Matcher error:", e)
    finally:
        db.close()

async def run_matching_cycle_async():
    print("--- Matcher: background started")
    while True:
        await asyncio.to_thread(run_matching_cycle)
        await asyncio.sleep(4)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_matching_cycle_async())

@app.get("/pending-rides")
def pending():
    return {"status": "ok"}
