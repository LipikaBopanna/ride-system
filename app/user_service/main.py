import requests
from datetime import date, timedelta, time
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.common import models
from app.common.models import Ride


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 📍 LOCATION → LAT/LON MAP
# =========================
LOCATION_MAP = {
    "Koramangala": [77.6245, 12.9352],
    "Whitefield": [77.7499, 12.9698],
    "Indiranagar": [77.6408, 12.9784],
    "Marathahalli": [77.7010, 12.9591],
    "BTM": [77.6101, 12.9166],
    "Jayanagar": [77.5833, 12.9250],
    "MG Road": [77.6088, 12.9756],
    "Yelahanka": [77.5963, 13.1005],
    "Electronic City": [77.6730, 12.8456]
}

# =========================
# 🚀 DISTANCE API
# =========================
def get_distance_km(pickup_name, drop_name):
    API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImMyN2M1NGMyYjUyMjQwNmZiZDIyNzIwMjk4M2ExMjE1IiwiaCI6Im11cm11cjY0In0="

    pickup = LOCATION_MAP.get(pickup_name)
    drop = LOCATION_MAP.get(drop_name)

    if not pickup or not drop:
        return 10  # fallback

    url = "https://api.openrouteservice.org/v2/directions/driving-car"

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "coordinates": [
            pickup,
            drop
        ]
    }

    res = requests.post(url, json=body, headers=headers)

    if res.status_code != 200:
        return 10

    data = res.json()
    return data["routes"][0]["summary"]["distance"] / 1000


# =========================
# 👤 CREATE USER
# =========================
@app.post("/create-user")
def create_user(name: str, email: str, phone: str, db: Session = Depends(get_db)):
    user = models.User(
        name=name,
        email=email,
        phone=phone,
        otp=None,
        otp_expires_at=None,
        is_verified=True,
        is_subscriber=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# =========================
# 💰 CALCULATE PRICE
# =========================
@app.get("/calculate-price")
def calculate_price(pickup: str, drop: str, weekend: bool = False):

    distance = get_distance_km(pickup, drop)

    price = distance * 20 * 30

    if weekend:
        price += 500

    return {
        "distance_km": round(distance, 2),
        "monthly_price": round(price, 2)
    }


# =========================
# 📅 SCHEDULE COMMUTE
# =========================
@app.post("/schedule/monthly")
def schedule_monthly(
    user_id: int,
    pickup: str,
    drop: str,
    pickup_time: str,
    return_time: str,
    ride_mode: str = "two_way",
    weekend: bool = False,
    db: Session = Depends(get_db)
):

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    pt = time.fromisoformat(pickup_time)
    rt = time.fromisoformat(return_time)

    today = date.today()

    for i in range(30):
        d = today + timedelta(days=i)

        if not weekend and d.weekday() >= 5:
            continue

        db.add(Ride(
            user_id=user_id,
            pickup=pickup,
            drop=drop,
            date=d,
            time=pt,
            ride_type="COMMUTE",
            priority=1,
            status="PENDING"
        ))

        if ride_mode == "two_way":
            db.add(Ride(
                user_id=user_id,
                pickup=drop,
                drop=pickup,
                date=d,
                time=rt,
                ride_type="COMMUTE",
                priority=1,
                status="PENDING"
            ))

    db.commit()
    return {"message": "Commute scheduled"}


# =========================
# ⚡ INSTANT RIDE
# =========================
@app.post("/book/instant")
def book_instant(user_id: int, pickup: str, drop: str, db: Session = Depends(get_db)):

    ride = Ride(
        user_id=user_id,
        pickup=pickup,
        drop=drop,
        date=date.today(),
        time=time(9, 0),
        ride_type="INSTANT",
        priority=2,
        status="PENDING"
    )

    db.add(ride)
    db.commit()
    db.refresh(ride)

    return {"ride_id": ride.id}


# =========================
# 👀 RIDER VIEW
# =========================
@app.get("/user/rides")
def user_rides(user_id: int, db: Session = Depends(get_db)):

    rides = db.query(Ride).filter(Ride.user_id == user_id).all()

    return [
        {
            "ride_id": r.id,
            "name": r.user.name,
            "pickup": r.pickup,
            "drop": r.drop,
            "time": str(r.time),
            "date": str(r.date),
            "type": r.ride_type,
            "priority": r.priority,
            "status": r.status,
            "driver": r.driver_name,
            "vehicle": r.vehicle
        }
        for r in rides
    ]


# =========================
# 🚖 DRIVER VIEW
# =========================
@app.get("/match/rides")
def match_rides(db: Session = Depends(get_db)):

    rides = db.query(Ride).order_by(Ride.priority).all()

    return [
        {
            "ride_id": r.id,
            "name": r.user.name,
            "pickup": r.pickup,
            "drop": r.drop,
            "time": str(r.time),
            "type": r.ride_type,
            "priority": r.priority,
            "status": r.status
        }
        for r in rides
    ]


# =========================
# ✅ ACCEPT RIDE
# =========================
@app.post("/accept/{ride_id}")
def accept_ride(ride_id: int, driver_name: str, vehicle: str, db: Session = Depends(get_db)):

    ride = db.query(Ride).filter(Ride.id == ride_id).first()

    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    # ✅ Step 1: accept this ride
    ride.driver_name = driver_name
    ride.vehicle = vehicle
    ride.status = "ACCEPTED"

    # ✅ Step 2: cancel ALL other rides of SAME USER
    db.query(Ride).filter(
        Ride.user_id == ride.user_id,
        Ride.id != ride_id,
        Ride.status == "PENDING"
    ).update({"status": "CANCELLED"})

    db.commit()

    return {"message": "Ride accepted"}