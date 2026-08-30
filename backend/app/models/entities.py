import datetime
import uuid
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel, PriorityLevel, UserRole, SLAStatus

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.CITIZEN, nullable=False)
    department = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    
    # Original Immutable AI Predictions
    ai_category = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_department = Column(String, nullable=True)
    confidence_tier = Column(String, default="HIGH") # HIGH (>=0.80), MEDIUM (0.60-0.79), LOW (<0.60)
    requires_human_review = Column(Boolean, default=False)
    
    # Human Review & Governance
    review_status = Column(String, default="ACCEPTED") # PENDING, ACCEPTED, CORRECTED
    review_reason = Column(Text, nullable=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

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
    verification_notes = Column(Text, nullable=True)
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
    assigned_team = Column(String, nullable=True)
    assigned_worker = Column(String, nullable=True)
    assigned_worker_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    recommended_action = Column(Text, nullable=False)
    required_materials = Column(Text, nullable=True) # JSON or newline string
    safety_precautions = Column(Text, nullable=True) # JSON or newline string
    
    status = Column(SQLEnum(WorkOrderStatus), default=WorkOrderStatus.PENDING, nullable=False)
    sla_deadline = Column(DateTime, nullable=True)
    sla_status = Column(SQLEnum(SLAStatus), default=SLAStatus.ON_TRACK, nullable=False)
    
    completion_notes = Column(Text, nullable=True)
    completion_image_path = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
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


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(String, primary_key=True, default=generate_uuid)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    
    ai_category = Column(String, nullable=False)
    ai_department = Column(String, nullable=True)
    ai_confidence = Column(Float, default=1.0, nullable=False)
    confidence_tier = Column(String, default="HIGH")
    
    final_category = Column(String, nullable=False)
    final_department = Column(String, nullable=True)
    final_priority = Column(String, nullable=True)
    
    review_status = Column(String, default="CORRECTED") # ACCEPTED or CORRECTED
    reason = Column(Text, nullable=True)
    
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewer_email = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship
    incident = relationship("Incident")


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

