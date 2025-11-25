# app/request_handler/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from app.common.db import get_db, engine, Base
from app.common import models, schemas, utils

# This service is responsible for creating the tables
try:
    Base.metadata.create_all(bind=engine)
    print("--- Request Handler: Tables created/checked. ---")
except Exception as e:
    print(f"--- Request Handler: Error creating tables: {e} ---")

app = FastAPI(title="Request Handler Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

PRICE_PER_KM = 18.5 # 37 / 2km
BASE_FARE = 20.0

@app.post("/ride/calculate-price", response_model=schemas.PriceEstimateResponse)
def calculate_price(req: schemas.PriceEstimateRequest):
    distance_km = utils.haversine_distance(
        req.pickup_lat, req.pickup_lon, 
        req.dropoff_lat, req.dropoff_lon
    )
    price = (distance_km * PRICE_PER_KM) + BASE_FARE
    return schemas.PriceEstimateResponse(
        distance_km=round(distance_km, 2),
        price=round(price, 2)
    )

@app.post("/ride/request", response_model=schemas.RideOut)
def create_ride(req: schemas.RideRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    # Allow unverified users for demo ease if needed, but keeping it strict is better
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create the ride
    ride = models.Ride(
        user_id=req.user_id,
        pickup_lat=req.pickup_lat,
        pickup_lon=req.pickup_lon,
        pickup_name=req.pickup_name,
        drop_lat=req.drop_lat,
        drop_lon=req.drop_lon,
        dropoff_name=req.dropoff_name,
        status="PENDING",
        price=req.price,
        created_at=datetime.utcnow()
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    print(f"--- REQUEST: Ride {ride.id} created for user {ride.user_id}. Status: PENDING.")
    
    # Return the ride object so the frontend gets the ID
    return ride