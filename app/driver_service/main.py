# app/driver_service/main.py
import os
import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.common.db import get_db, engine, SessionLocal
from app.common import models, schemas
from datetime import datetime

app = FastAPI(title="Driver Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

NOTIFIER_URL = os.getenv("NOTIFIER_URL", "http://notifier:7003")

@app.get("/drivers/{driver_id}", response_model=schemas.DriverOut)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    drv = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not drv:
        raise HTTPException(status_code=404, detail="Driver not found")
    return drv

@app.get("/drivers/{driver_id}/assigned")
def get_assigned(driver_id: int, db: Session = Depends(get_db)):
    drv = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not drv or not drv.current_ride_id:
        return {"assigned": False}
    ride = db.query(models.Ride).filter(models.Ride.id == drv.current_ride_id).first()
    if not ride or ride.status in ["COMPLETED", "CANCELLED"]:
        drv.current_ride_id = None
        drv.available = True
        db.commit()
        return {"assigned": False}
    return {"assigned": True, "ride": {
        "id": ride.id, "user_id": ride.user_id, "pickup_name": ride.pickup_name,
        "pickup_lat": ride.pickup_lat, "pickup_lon": ride.pickup_lon,
        "dropoff_name": ride.dropoff_name, "drop_lat": ride.drop_lat, "drop_lon": ride.drop_lon,
        "status": ride.status, "price": ride.price
    }}

@app.post("/drivers/{driver_id}/accept")
def driver_accept(driver_id: int, db: Session = Depends(get_db)):
    # Accept only rides in REQUESTED status directed to this driver (matcher set driver.current_ride_id OR matcher left as available driver)
    # Simpler: find a ride with driver_id == NULL but status REQUESTED and pick the one that matches driver's current_ride_id if set.
    ride = db.query(models.Ride).filter(
        models.Ride.status == "REQUESTED"
    ).order_by(models.Ride.assigned_at).first()

    if not ride:
        raise HTTPException(status_code=404, detail="No REQUESTED ride available to accept")

    # assign this driver
    ride.driver_id = driver_id
    ride.status = "ACCEPTED"
    ride.assigned_at = datetime.utcnow()

    driver = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if driver:
        driver.available = False
        driver.current_ride_id = ride.id

    db.add(ride)
    db.add(driver)
    db.commit()
    db.refresh(ride)
    db.refresh(driver)

    # notify rider via notifier service
    payload = {
        "user_id": ride.user_id,
        "ride_id": ride.id,
        "driver": {
            "id": driver.id,
            "name": driver.name,
            "vehicle_model": driver.vehicle_model,
            "license_plate": driver.license_plate
        }
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(f"{NOTIFIER_URL}/ride/accepted", json=payload)
    except Exception as e:
        print("Driver Service: notifier call error", e)

    return {"success": True, "ride": {
        "id": ride.id, "status": ride.status, "driver_id": ride.driver_id
    }}
