# backend/models_db.py
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Fleet(Base):
    __tablename__ = "fleet"

    tail_number = Column(String, primary_key=True, index=True) # e.g., "AP-BLC"
    aircraft_type = Column(String)                             # e.g., "Boeing 737-800"
    engine_type = Column(String)                               # e.g., "CFM56-7B"
    age_years = Column(Float)
    total_flight_hours = Column(Float)
    total_cycles = Column(Integer)

    # Relationships (Allows us to fetch connected data easily)
    maintenance_logs = relationship("MaintenanceRecord", back_populates="aircraft")
    telemetry_logs = relationship("FlightTelemetry", back_populates="aircraft")
    health_logs = relationship("HealthPrediction", back_populates="aircraft")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    record_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tail_number = Column(String, ForeignKey("fleet.tail_number"))
    maintenance_date = Column(DateTime, default=func.now())
    maintenance_type = Column(String)
    days_since_last_check = Column(Integer)

    # Relationship back to Fleet
    aircraft = relationship("Fleet", back_populates="maintenance_logs")


class FlightTelemetry(Base):
    __tablename__ = "flight_telemetry"

    # Note: We mapped 'callsign' to 'tail_number' for the live API context
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tail_number = Column(String, index=True)
    callsign = Column(String, ForeignKey("fleet.tail_number"), index=True) 
    altitude = Column(Float)
    velocity = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    timestamp = Column(DateTime, default=func.now())
    anomaly_flag = Column(Boolean, default=False) # For Kamal's Isolation Forest

    # Relationship back to Fleet
    aircraft = relationship("Fleet", back_populates="telemetry_logs")


class HealthPrediction(Base):
    __tablename__ = "health_predictions"

    prediction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tail_number = Column(String, ForeignKey("fleet.tail_number"))
    timestamp = Column(DateTime, default=func.now())
    health_score = Column(Float)          # 0-100 score from Random Forest
    predicted_rul_cycles = Column(Integer) # From Kamal's upcoming LSTM
    shap_top_feature = Column(String)      # For Areeba's Waterfall Chart

    # Relationship back to Fleet
    aircraft = relationship("Fleet", back_populates="health_logs")
    # ==========================================
# FYP-2: FLIGHT HISTORY TABLE
# ==========================================
class FlightHistory(Base):
    __tablename__ = "flight_history"

    flight_id = Column(Integer, primary_key=True, index=True)
    tail_number = Column(String, index=True) 
    origin = Column(String)
    destination = Column(String)
    total_fuel_liters = Column(Float)
    co2_kg = Column(Float)
    final_health_score = Column(Float)
    
    # Automatically logs the exact time the flight was completed
    timestamp = Column(DateTime(timezone=True), server_default=func.now())