# app/common/schemas.py
from pydantic import BaseModel
from typing import Optional

class RiderRegister(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None

class DriverRegister(BaseModel):
    name: str
    phone: str
    vehicle_type: str
    vehicle_model: str
    license_plate: str

class OtpVerify(BaseModel):
    phone: str
    otp: str

class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]
    is_verified: bool
    is_subscriber: Optional[bool] = False

    class Config:
        from_attributes = True

class DriverOut(BaseModel):
    id: int
    name: str
    phone: str
    vehicle_type: Optional[str] = None
    vehicle_model: Optional[str] = None
    license_plate: Optional[str] = None
    is_verified: bool
    available: bool
    lat: float
    lon: float

    class Config:
        from_attributes = True

# Ride related
class RideRequest(BaseModel):
    user_id: int
    pickup_lat: float
    pickup_lon: float
    pickup_name: str
    drop_lat: float
    drop_lon: float
    dropoff_name: str
    price: float

class RideOut(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int]
    pickup_name: str
    pickup_lat: float
    pickup_lon: float
    dropoff_name: str
    drop_lat: float
    drop_lon: float
    status: str
    price: Optional[float]

    class Config:
        from_attributes = True

class PriceEstimateRequest(BaseModel):
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float

class PriceEstimateResponse(BaseModel):
    distance_km: float
    price: float
