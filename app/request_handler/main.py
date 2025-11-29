# app/request_handler/main.py
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from app.common.db import get_db, engine, SessionLocal, Base
from app.common import models, schemas, utils
from typing import Dict

# Create tables if DB empty (safe to call)
#Base.metadata.create_all(bind=engine)

app = FastAPI(title="Request Handler Service (WS matcher)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

PRICE_PER_KM = 18.0
BASE_FARE = 20.0

# WebSocket management for rider connections
ACTIVE_RIDE_WS: Dict[str, WebSocket] = {}

@app.post("/ride/calculate-price", response_model=schemas.PriceEstimateResponse)
def calculate_price(req: schemas.PriceEstimateRequest):
    distance_km = utils.haversine_distance(req.pickup_lat, req.pickup_lon, req.dropoff_lat, req.dropoff_lon)
    price = (distance_km * PRICE_PER_KM) + BASE_FARE
    return schemas.PriceEstimateResponse(distance_km=round(distance_km,2), price=round(price,2))

@app.post("/ride/request", response_model=schemas.RideOut)
def create_ride(req: schemas.RideRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="User is not verified")

    ride = models.Ride(
        user_id=req.user_id,
        pickup_lat=req.pickup_lat, pickup_lon=req.pickup_lon, pickup_name=req.pickup_name,
        drop_lat=req.drop_lat, drop_lon=req.drop_lon, dropoff_name=req.dropoff_name,
        status="PENDING", price=req.price, created_at=datetime.utcnow()
    )
    db.add(ride); db.commit(); db.refresh(ride)
    print(f"--- REQUEST: Ride {ride.id} created for user {ride.user_id}. Status: PENDING.")
    return ride

# WebSocket endpoint for rider to receive assignment and updates
@app.websocket("/ws/rides/{ride_id}")
async def ride_ws(websocket: WebSocket, ride_id: int):
    await websocket.accept()
    key = str(ride_id)
    ACTIVE_RIDE_WS[key] = websocket
    print(f"WS: Rider connected for ride {ride_id}")
    try:
        while True:
            try:
                await websocket.receive_text()
            except Exception:
                # keep alive
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print(f"WS: Rider disconnected for ride {ride_id}")
    finally:
        ACTIVE_RIDE_WS.pop(key, None)
        try: await websocket.close()
        except: pass

# Endpoint used by matcher/requester to push an immediate ASSIGNED payload to the rider WS
@app.post("/push/assign")
def push_assign(payload: dict):
    ride_id = payload.get("ride_id")
    if not ride_id:
        raise HTTPException(status_code=400, detail="ride_id required")
    key = str(ride_id)
    ws = ACTIVE_RIDE_WS.get(key)
    if not ws:
        return {"status":"no_ws"}
    try:
        ws.send_json(payload)
        return {"status":"sent"}
    except Exception as e:
        return {"status":"error", "detail":str(e)}
