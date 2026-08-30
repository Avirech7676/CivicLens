from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel, PriorityLevel, UserRole, SLAStatus, IncidentCategory

# --- Auth & User Schemas ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user_id: str
    email: str
    role: UserRole
    full_name: str
    department: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    department: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Priority Engine Schemas ---
class PriorityFactor(BaseModel):
    factor: str
    score: float
    contribution: float
    reason: str

class PriorityEvaluationResult(BaseModel):
    priority_score: int
    priority_level: PriorityLevel
    priority_reason: str
    priority_factors: List[PriorityFactor]

# --- Department Routing Schemas ---
class RoutingResult(BaseModel):
    assigned_department: str
    routing_reason: str
    category: str
    confidence: float = 1.0

# --- AI Incident Analysis Output Model ---
class IncidentAnalysisResult(BaseModel):
    category: IncidentCategory
    primary_asset: str = Field(default="Road / Pavement", description="Primary physical infrastructure asset damaged (e.g., Road/Pavement, Water Pipe, Catch Basin, Light Pole)")
    secondary_conditions: List[str] = Field(default_factory=list, description="Secondary environmental conditions observed (e.g., standing rainwater, mud, traffic congestion)")
    title: str = Field(description="Concise 4-8 word descriptive title for the incident")
    normalized_description: str = Field(description="Normalized summary of the reported complaint and evidence")
    severity_level: SeverityLevel
    severity_reason: str = Field(description="Detailed justification for the assigned severity level based on risks/evidence")
    hazards: List[str] = Field(default_factory=list, description="List of detected immediate or potential safety hazards")
    evidence_observations: List[str] = Field(default_factory=list, description="List of physical observations supported by the text and image")
    confidence: float = Field(ge=0.0, le=1.0, description="Normalized classification confidence score between 0 and 1")
    confidence_tier: str = Field(default="HIGH", description="Confidence policy tier: HIGH (>=0.85), MEDIUM (0.60-0.849), or LOW (<0.60)")
    recommended_action: str = Field(description="Recommended immediate municipal action")

# --- Duplicate Intelligence Schemas ---
class DuplicateMatchResult(BaseModel):
    is_duplicate: bool
    matched_incident_id: Optional[str] = None
    semantic_similarity: float = 0.0
    distance_meters: Optional[float] = None
    category_match: bool = False
    match_confidence: float = 0.0
    reason: str

# --- Report Schemas ---
class ReportBase(BaseModel):
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    citizen_id: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: str
    image_path: Optional[str] = None
    incident_id: Optional[str] = None
    created_at: datetime
    duplicate_info: Optional[DuplicateMatchResult] = None

    model_config = ConfigDict(from_attributes=True)


# --- WorkOrder Schemas ---
class WorkOrderBase(BaseModel):
    assigned_department: str
    recommended_action: str
    required_materials: Optional[str] = None
    safety_precautions: Optional[str] = None

class WorkOrderCreate(WorkOrderBase):
    incident_id: str

class WorkOrderUpdateStatus(BaseModel):
    status: WorkOrderStatus
    completion_notes: Optional[str] = None

class WorkOrderAssignRequest(BaseModel):
    assigned_team: Optional[str] = None
    assigned_worker: Optional[str] = None
    assigned_worker_id: Optional[str] = None

class WorkOrderResponse(WorkOrderBase):
    id: str
    incident_id: str
    status: WorkOrderStatus
    assigned_team: Optional[str] = None
    assigned_worker: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    sla_deadline: Optional[datetime] = None
    sla_status: SLAStatus = SLAStatus.ON_TRACK
    completion_notes: Optional[str] = None
    completion_image_path: Optional[str] = None
    created_at: datetime
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- StatusLog Schemas ---
class StatusLogResponse(BaseModel):
    id: str
    incident_id: str
    old_status: Optional[IncidentStatus] = None
    new_status: IncidentStatus
    changed_by: str
    notes: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Incident Schemas ---
class IncidentBase(BaseModel):
    title: str
    description: str
    category: Optional[str] = "ROAD_HAZARD"
    
    # Original AI & Governance fields
    ai_category: Optional[str] = None
    ai_confidence: Optional[float] = 1.0
    ai_department: Optional[str] = None
    confidence_tier: Optional[str] = "HIGH"
    requires_human_review: Optional[bool] = False
    review_status: Optional[str] = "ACCEPTED" # PENDING, ACCEPTED, CORRECTED
    review_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    severity_level: SeverityLevel = SeverityLevel.MEDIUM
    severity_reason: Optional[str] = None
    confidence: float = 1.0
    hazards: Optional[List[str]] = []
    evidence_observations: Optional[List[str]] = []
    recommended_action: Optional[str] = None
    priority_score: int = 50
    priority_level: PriorityLevel = PriorityLevel.P3_MEDIUM
    priority_reason: Optional[str] = None
    priority_factors: Optional[List[PriorityFactor]] = []
    assigned_department: Optional[str] = None
    routing_reason: Optional[str] = None
    verification_notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None

class IncidentCreate(IncidentBase):
    pass

class IncidentHumanOverride(BaseModel):
    category: Optional[IncidentCategory] = None
    assigned_department: Optional[str] = None
    priority_level: Optional[PriorityLevel] = None
    reason: str = Field(description="Dispatcher justification for human override")

class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    changed_by: Optional[str] = "DISPATCHER"
    notes: Optional[str] = None

class IncidentResponse(IncidentBase):
    id: str
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    reports: List[ReportResponse] = []
    work_order: Optional[WorkOrderResponse] = None
    status_logs: List[StatusLogResponse] = []

    model_config = ConfigDict(from_attributes=True)



# --- Dashboard Stats Schema ---
class DashboardStats(BaseModel):
    total_reports: int
    total_incidents: int
    open_incidents: int
    resolved_incidents: int
    verified_incidents: int
    by_category: dict[str, int]
    by_severity: dict[str, int]


# --- Notification Schemas ---
class NotificationResponse(BaseModel):
    id: str
    recipient_type: str
    recipient_id: Optional[str] = None
    incident_id: Optional[str] = None
    work_order_id: Optional[str] = None
    channel: str
    event_type: str
    title: str
    message: str
    status: str
    provider: str
    is_read: bool
    created_at: datetime
    sent_at: Optional[datetime] = None
    metadata_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCount(BaseModel):
    unread_count: int


# --- Hotspot Intelligence Schemas ---
class HotspotResponse(BaseModel):
    hotspot_id: str
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    incident_count: int
    report_count: int
    average_priority_score: int
    highest_priority_score: int
    p1_count: int
    p2_count: int
    dominant_category: str
    pattern: str
    category_distribution: dict[str, int]
    status_distribution: dict[str, int]
    hotspot_score: int
    hotspot_level: str
    explanation: str
    incident_ids: list[str]


class HotspotsListResponse(BaseModel):
    total_hotspots: int
    hotspots: list[HotspotResponse]
    recommendations: list[dict]


# --- Command Assistant Schemas ---
class AssistantQueryRequest(BaseModel):
    question: str


class AssistantSource(BaseModel):
    type: str # "incident", "hotspot", "department"
    id: str
    label: str


class AssistantQueryResponse(BaseModel):
    question: str
    intent: str
    answer: str
    sources: list[AssistantSource] = []

IncidentAnalysisResult.model_rebuild()



