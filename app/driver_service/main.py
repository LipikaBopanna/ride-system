from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.common.db import get_db
from app.common import models, schemas
from sqlalchemy.orm import Session
from datetime import datetime

app = FastAPI(title="Mini-Uber Driver Service")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.get("/drivers/{driver_id}", response_model=schemas.DriverOut)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    drv = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not drv: raise HTTPException(status_code=404, detail="Driver not found")
    return drv

@app.get("/drivers/{driver_id}/assigned")
def get_assigned(driver_id: int, db: Session = Depends(get_db)):
    drv = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not drv or not drv.current_ride_id: return {"assigned": False}
    
    ride = db.query(models.Ride).filter(models.Ride.id == drv.current_ride_id).first()
    if not ride or ride.status in ["COMPLETED", "CANCELLED"]:
        drv.current_ride_id = None
        drv.available = True
        db.commit()
        return {"assigned": False}
        
    return {
        "assigned": True,
        "ride": {
            "id": ride.id, "user_id": ride.user_id, "pickup_name": ride.pickup_name,
            "pickup_lat": ride.pickup_lat, "pickup_lon": ride.pickup_lon,
            "dropoff_name": ride.dropoff_name, "drop_lat": ride.drop_lat, "drop_lon": ride.drop_lon,
            "status": ride.status, "price": ride.price, "fixed_price": ride.fixed_price
        }
    }

@app.post("/drivers/{driver_id}/accept", response_model=schemas.RideOut)
def accept_ride(driver_id: int, db: Session = Depends(get_db)):
    drv = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    ride = db.query(models.Ride).filter(models.Ride.id == drv.current_ride_id).first()
    ride.status = "ONGOING"
    ride.started_at = datetime.utcnow()
    db.commit()
    db.refresh(ride)
    return ride

@app.post("/drivers/{driver_id}/complete", response_model=schemas.RideOut)
def complete_ride(driver_id: int, db: Session = Depends(get_db)):
    drv = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    ride = db.query(models.Ride).filter(models.Ride.id == drv.current_ride_id).first()
    ride.status = "COMPLETED"
    ride.ended_at = datetime.utcnow()
    drv.available = True
    drv.current_ride_id = None
    db.add(drv)
    db.commit()
    db.refresh(ride)
    return ride