# app/auth_service/main.py
import random

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.common import models, schemas
from app.common.db import get_db
from datetime import datetime, timedelta

# Create tables (if DB empty). If you see duplicate-key errors, drop DB volume then re-create.
#Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

OTP_TTL_MINUTES = 10


def generate_otp():
    return f"{random.randint(0, 999999):06d}"

@app.post("/register/rider", response_model=schemas.RegistrationResult)
def register_rider(user: schemas.RiderRegister, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.phone == user.phone).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    otp = generate_otp()
    new_user = models.User(
        name=user.name, phone=user.phone, email=user.email,
        otp=otp, otp_expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES), is_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print(f"--- AUTH: Registered Rider {new_user.name}. OTP {otp}")
    return {"status": "created", "user_type": "rider", "otp": otp, "user": schemas.UserOut.from_orm(new_user)}

@app.post("/register/driver", response_model=schemas.RegistrationResult)
def register_driver(driver: schemas.DriverRegister, db: Session = Depends(get_db)):
    db_driver = db.query(models.Driver).filter(models.Driver.phone == driver.phone).first()
    if db_driver:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    otp = generate_otp()
    new_driver = models.Driver(
        name=driver.name, phone=driver.phone, vehicle_type=driver.vehicle_type,
        vehicle_model=driver.vehicle_model, license_plate=driver.license_plate,
        otp=otp, otp_expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
        is_verified=False, lat=12.9716, lon=77.5946
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    print(f"--- AUTH: Registered Driver {new_driver.name}. OTP {otp}")
    return {"status": "created", "user_type": "driver", "otp": otp, "user": schemas.DriverOut.from_orm(new_driver)}

@app.post("/verify/otp")
def verify_otp(req: schemas.OtpVerify, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    db_user = db.query(models.User).filter(models.User.phone == req.phone).first()
    if db_user:
        if db_user.otp_expires_at and db_user.otp_expires_at < now:
            raise HTTPException(status_code=400, detail="OTP expired")
        if db_user.otp == req.otp:
            db_user.is_verified = True
            db_user.otp = None
            db_user.otp_expires_at = None
            db.commit(); db.refresh(db_user)
            return {"status":"success", "user_type":"rider", "user": schemas.UserOut.from_orm(db_user)}
        raise HTTPException(status_code=400, detail="Invalid OTP")
    db_driver = db.query(models.Driver).filter(models.Driver.phone == req.phone).first()
    if db_driver:
        if db_driver.otp_expires_at and db_driver.otp_expires_at < now:
            raise HTTPException(status_code=400, detail="OTP expired")
        if db_driver.otp == req.otp:
            db_driver.is_verified = True
            db_driver.otp = None
            db_driver.otp_expires_at = None
            db.commit(); db.refresh(db_driver)
            return {"status":"success", "user_type":"driver", "user": schemas.DriverOut.from_orm(db_driver)}
        raise HTTPException(status_code=400, detail="Invalid OTP")
    raise HTTPException(status_code=404, detail="User or Driver not found")
