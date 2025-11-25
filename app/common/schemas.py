from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, time

# --- REGISTRATION SCHEMAS ---
class RiderRegister(BaseModel):
    name: str
    phone: str
    email: str

class DriverRegister(BaseModel):
    name: str
    phone: str
    vehicle_type: str
    vehicle_model: str
    license_plate: str

class OtpVerify(BaseModel):
    phone: str
    otp: str

# --- MISSING SCHEMAS (ADDED) ---
class UserCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class DriverCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    vehicle_model: Optional[str] = None
    license_plate: Optional[str] = None
    license_proof_url: Optional[str] = None

# --- OUTPUT SCHEMAS ---
class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    is_verified: bool
    is_subscriber: bool
    class Config:
        from_attributes = True

class DriverOut(BaseModel):
    id: int
    name: str
    phone: str
    is_verified: bool
    vehicle_type: str
    vehicle_model: str
    license_plate: str
    available: bool
    class Config:
        from_attributes = True

class GeoCodeResult(BaseModel):
    name: str
    lat: float
    lon: float

class PriceEstimateRequest(BaseModel):
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float

class PriceEstimateResponse(BaseModel):
    distance_km: float
    price: float

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
    status: str
    pickup_name: str
    dropoff_name: str
    price: float
    driver: Optional[DriverOut] = None
    class Config:
        from_attributes = True

class CommuteSettingsBase(BaseModel):
    home_lat: float
    home_lon: float
    work_lat: float
    work_lon: float
    morning_time: time
    evening_time: time
    fixed_price: float

class CommuteSettingsCreate(CommuteSettingsBase):
    pass

class CommuteSettingsOut(CommuteSettingsBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

class CommuteAdjust(BaseModel):
    date: date
    ride_type: str
    new_time: time

class CommutePause(BaseModel):
    date: date
    ride_type: str