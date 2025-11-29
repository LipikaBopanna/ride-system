# app/auth_service/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.common import models, schemas
from app.common.db import get_db, engine, Base
from datetime import datetime, timedelta

# Create tables (if DB empty). If you see duplicate-key errors, drop DB volume then re-create.
#Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

MOCK_OTP = "123456"

@app.post("/register/rider", response_model=schemas.UserOut)
def register_rider(user: schemas.RiderRegister, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.phone == user.phone).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    new_user = models.User(
        name=user.name, phone=user.phone, email=user.email,
        otp=MOCK_OTP, otp_expires_at=datetime.utcnow() + timedelta(minutes=10), is_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print(f"--- AUTH: Registered Rider {new_user.name}. OTP {MOCK_OTP}")
    return new_user

@app.post("/register/driver", response_model=schemas.DriverOut)
def register_driver(driver: schemas.DriverRegister, db: Session = Depends(get_db)):
    db_driver = db.query(models.Driver).filter(models.Driver.phone == driver.phone).first()
    if db_driver:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    new_driver = models.Driver(
        name=driver.name, phone=driver.phone, vehicle_type=driver.vehicle_type,
        vehicle_model=driver.vehicle_model, license_plate=driver.license_plate,
        otp=MOCK_OTP, otp_expires_at=datetime.utcnow() + timedelta(minutes=10),
        is_verified=False, lat=12.9716, lon=77.5946
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    print(f"--- AUTH: Registered Driver {new_driver.name}. OTP {MOCK_OTP}")
    return new_driver

@app.post("/verify/otp")
def verify_otp(req: schemas.OtpVerify, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.phone == req.phone).first()
    if db_user:
        if db_user.otp == req.otp or req.otp == MOCK_OTP:
            db_user.is_verified = True
            db_user.otp = None
            db.commit(); db.refresh(db_user)
            return {"status":"success", "user_type":"rider", "user": schemas.UserOut.from_orm(db_user)}
        raise HTTPException(status_code=400, detail="Invalid OTP")
    db_driver = db.query(models.Driver).filter(models.Driver.phone == req.phone).first()
    if db_driver:
        if db_driver.otp == req.otp or req.otp == MOCK_OTP:
            db_driver.is_verified = True
            db_driver.otp = None
            db.commit(); db.refresh(db_driver)
            return {"status":"success", "user_type":"driver", "user": schemas.DriverOut.from_orm(db_driver)}
        raise HTTPException(status_code=400, detail="Invalid OTP")
    raise HTTPException(status_code=404, detail="User or Driver not found")
