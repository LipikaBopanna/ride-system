import time
import asyncio
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.common.db import SessionLocal, get_db
from app.common import models
from typing import List

app = FastAPI(title="Mini-Uber Notifier Service")

# A simple in-memory log to show the last few notifications sent
notification_log = []

def run_notification_cycle(db: Session):
    print("--- Notifier: Checking for assigned rides to notify...")
    assigned_rides = db.query(models.Ride).filter(
        models.Ride.status == "ASSIGNED",
        models.Ride.notified == False
    ).all()

    for ride in assigned_rides:
        message = f"[!] DRIVER ASSIGNED [!] Ride ID: {ride.id}, User ID: {ride.user_id}, Driver ID: {ride.driver_id}"
        print(f"--- Notifier: {message}")
        notification_log.insert(0, message) # Add to the top of our log
        
        ride.notified = True
        db.add(ride)
        db.commit()

async def notification_loop():
    # Give other services a moment to start
    await asyncio.sleep(5)
    db = SessionLocal()
    while True:
        try:
            run_notification_cycle(db)
        except Exception as e:
            print(f"Notifier error: {e}")
            db.rollback()
        await asyncio.sleep(5) # The polling interval
    db.close()

@app.on_event("startup")
async def startup_event():
    print("Notifier service started. Launching background task...")
    asyncio.create_task(notification_loop())

@app.get("/notification-log")
def get_notification_log():
    """See a list of the most recent notifications sent by this service."""
    return {"log": notification_log[:20]} # Show the last 20 notifications

