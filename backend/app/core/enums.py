import enum

class IncidentStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"

class WorkOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class SeverityLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PriorityLevel(str, enum.Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"

class IncidentCategory(str, enum.Enum):
    ROAD_HAZARD = "ROAD_HAZARD"
    STREETLIGHT = "STREETLIGHT"
    SANITATION = "SANITATION"
    WATER_LEAK = "WATER_LEAK"
    DRAINAGE = "DRAINAGE"
    ELECTRICAL = "ELECTRICAL"
    PUBLIC_PROPERTY = "PUBLIC_PROPERTY"
    TRAFFIC_SIGNAL = "TRAFFIC_SIGNAL"
    OTHER = "OTHER"

