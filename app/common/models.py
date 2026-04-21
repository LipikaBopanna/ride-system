# app/common/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Date, Time
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)

    otp = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)

    is_subscriber = Column(Boolean, default=False)
    commute = relationship("CommuteSettings", back_populates="user", uselist=False)

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)

    vehicle_type = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)
    license_plate = Column(String, unique=True, nullable=True)

    otp = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)

    lat = Column(Float, nullable=True, default=12.9716)
    lon = Column(Float, nullable=True, default=77.5946)
    available = Column(Boolean, default=True)
    current_ride_id = Column(Integer, nullable=True)

class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, nullable=True)
    driver_name = Column(String, nullable=True)
    vehicle = Column(String, nullable=True)

    pickup = Column(String)
    drop = Column(String)

    date = Column(Date)
    time = Column(Time)

    ride_type = Column(String)   # COMMUTE / INSTANT
    priority = Column(Integer)   # 1 = commute, 2 = instant

    status = Column(String, default="PENDING")

    # 🔥 NEW
    driver_name = Column(String, nullable=True)
    vehicle_number = Column(String, nullable=True)

    user = relationship("User")

class CommuteSettings(Base):
    __tablename__ = "commute_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    home_lat = Column(Float, nullable=False)
    home_lon = Column(Float, nullable=False)
    work_lat = Column(Float, nullable=False)
    work_lon = Column(Float, nullable=False)
    morning_time = Column(Time, nullable=False)
    evening_time = Column(Time, nullable=False)
    fixed_price = Column(Float, nullable=False)
    user = relationship("User", back_populates="commute")
    overrides = relationship("CommuteScheduleOverride", back_populates="commute")

class CommuteScheduleOverride(Base):
    __tablename__ = "commute_overrides"
    id = Column(Integer, primary_key=True, index=True)
    commute_id = Column(Integer, ForeignKey("commute_settings.id"), nullable=True)
    date = Column(Date, nullable=False)
    morning_ride_status = Column(String, default="SCHEDULED")
    morning_ride_time = Column(Time, nullable=True)
    evening_ride_status = Column(String, default="SCHEDULED")
    evening_ride_time = Column(Time, nullable=True)
    commute = relationship("CommuteSettings", back_populates="overrides")
