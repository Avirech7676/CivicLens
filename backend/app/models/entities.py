import datetime
import uuid
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel, PriorityLevel

def generate_uuid():
    return str(uuid.uuid4())

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    severity_level = Column(SQLEnum(SeverityLevel), default=SeverityLevel.MEDIUM)
    severity_reason = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    hazards = Column(Text, nullable=True) # JSON list string
    evidence_observations = Column(Text, nullable=True) # JSON list string
    recommended_action = Column(Text, nullable=True)
    priority_score = Column(Integer, default=50) # 1 - 100
    priority_level = Column(SQLEnum(PriorityLevel), default=PriorityLevel.P3_MEDIUM)
    priority_reason = Column(Text, nullable=True)
    priority_factors = Column(Text, nullable=True) # JSON array string
    assigned_department = Column(String, nullable=True)
    routing_reason = Column(Text, nullable=True)
    status = Column(SQLEnum(IncidentStatus), default=IncidentStatus.SUBMITTED, nullable=False)
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    reports = relationship("Report", back_populates="incident", cascade="all, delete-orphan")
    work_order = relationship("WorkOrder", back_populates="incident", uselist=False, cascade="all, delete-orphan")
    status_logs = relationship("StatusLog", back_populates="incident", cascade="all, delete-orphan", order_by="StatusLog.timestamp.desc()")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    citizen_id = Column(String, nullable=True) # Optional citizen tracking handle
    description = Column(Text, nullable=False)
    image_path = Column(String, nullable=True)
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    
    # Relationship
    incident = relationship("Incident", back_populates="reports")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False, unique=True)
    
    assigned_department = Column(String, nullable=False)
    recommended_action = Column(Text, nullable=False)
    required_materials = Column(Text, nullable=True) # JSON or newline string
    safety_precautions = Column(Text, nullable=True) # JSON or newline string
    
    status = Column(SQLEnum(WorkOrderStatus), default=WorkOrderStatus.PENDING, nullable=False)
    completion_notes = Column(Text, nullable=True)
    completion_image_path = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationship
    incident = relationship("Incident", back_populates="work_order")


class StatusLog(Base):
    __tablename__ = "status_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    
    old_status = Column(SQLEnum(IncidentStatus), nullable=True)
    new_status = Column(SQLEnum(IncidentStatus), nullable=False)
    changed_by = Column(String, default="SYSTEM") # CITIZEN, DISPATCHER, SYSTEM
    notes = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship
    incident = relationship("Incident", back_populates="status_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    recipient_type = Column(String, nullable=False, default="CITIZEN") # CITIZEN, DISPATCHER, FIELD_TEAM
    recipient_id = Column(String, nullable=True) # citizen_id, department name, etc.
    
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=True)
    
    channel = Column(String, nullable=False, default="IN_APP") # IN_APP, EMAIL, SMS, PUSH, WHATSAPP
    event_type = Column(String, nullable=False) # e.g. REPORT_RECEIVED, INCIDENT_PRIORITY_ALERT, etc.
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    status = Column(String, nullable=False, default="SENT") # PENDING, SENT, DELIVERED, FAILED
    provider = Column(String, nullable=False, default="DEMO") # DEMO, COURIER
    is_read = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

