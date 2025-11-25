from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.common import models, schemas
from app.common.db import get_db, Base, engine
from datetime import datetime, timedelta

app = FastAPI(title="Auth Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/register/rider", response_model=schemas.UserOut)
def register_rider(user: schemas.RiderRegister, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.phone == user.phone).first()
    if db_user: return db_user 
    new_user = models.User(name=user.name, phone=user.phone, email=user.email, otp="123456", is_verified=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/register/driver", response_model=schemas.DriverOut)
def register_driver(driver: schemas.DriverRegister, db: Session = Depends(get_db)):
    db_driver = db.query(models.Driver).filter(models.Driver.phone == driver.phone).first()
    if db_driver: return db_driver
    new_driver = models.Driver(name=driver.name, phone=driver.phone, vehicle_type=driver.vehicle_type, vehicle_model=driver.vehicle_model, license_plate=driver.license_plate, otp="123456", is_verified=False)
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    return new_driver

@app.post("/verify/otp", response_model=dict)
def verify_otp(req: schemas.OtpVerify, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.phone == req.phone).first()
    if db_user:
        if req.otp == "123456":
            db_user.is_verified = True
            db.commit()
            return {"status": "success", "user_type": "rider", "user": schemas.UserOut.from_orm(db_user)}
    db_driver = db.query(models.Driver).filter(models.Driver.phone == req.phone).first()
    if db_driver:
        if req.otp == "123456":
            db_driver.is_verified = True
            db.commit()
            return {"status": "success", "user_type": "driver", "user": schemas.DriverOut.from_orm(db_driver)}
    raise HTTPException(status_code=400, detail="Invalid OTP")