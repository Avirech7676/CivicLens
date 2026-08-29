from sqlalchemy.orm import Session
from app.models.entities import Incident, Report, WorkOrder, StatusLog
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel
from app.schemas.dto import IncidentStatusUpdate, WorkOrderUpdateStatus
import datetime

import json
from sqlalchemy.orm import Session
from app.models.entities import Incident, Report, WorkOrder, StatusLog
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel
from app.schemas.dto import IncidentStatusUpdate, WorkOrderUpdateStatus, IncidentAnalysisResult
import datetime

VALID_INCIDENT_TRANSITIONS = {
    IncidentStatus.SUBMITTED: [IncidentStatus.TRIAGED, IncidentStatus.ASSIGNED, IncidentStatus.IN_PROGRESS],
    IncidentStatus.TRIAGED: [IncidentStatus.ASSIGNED, IncidentStatus.IN_PROGRESS],
    IncidentStatus.ASSIGNED: [IncidentStatus.IN_PROGRESS],
    IncidentStatus.IN_PROGRESS: [IncidentStatus.RESOLVED],
    IncidentStatus.RESOLVED: [IncidentStatus.VERIFIED, IncidentStatus.IN_PROGRESS],
    IncidentStatus.VERIFIED: [] # Terminal state
}

class IncidentService:
    @staticmethod
    def _parse_json_list(val) -> list:
        if isinstance(val, str) and val:
            try:
                parsed = json.loads(val)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        elif isinstance(val, list):
            return val
        return []

    @staticmethod
    def _format_incident_data(incident: Incident) -> dict:
        """Converts SQLAlchemy Incident model to a dict with deserialized JSON list fields for schemas."""
        if not incident:
            return None
        data = {c.name: getattr(incident, c.name) for c in incident.__table__.columns}
        data["hazards"] = IncidentService._parse_json_list(data.get("hazards"))
        data["evidence_observations"] = IncidentService._parse_json_list(data.get("evidence_observations"))
        data["priority_factors"] = IncidentService._parse_json_list(data.get("priority_factors"))
        data["reports"] = incident.reports
        data["work_order"] = incident.work_order
        data["status_logs"] = incident.status_logs
        return data

    @staticmethod
    def get_incidents(db: Session, skip: int = 0, limit: int = 100):
        incidents = db.query(Incident).order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()
        return [IncidentService._format_incident_data(inc) for inc in incidents]

    @staticmethod
    def get_incident(db: Session, incident_id: str):
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        return IncidentService._format_incident_data(incident)

    @staticmethod
    def create_incident_from_analysis(
        db: Session, 
        report: Report, 
        analysis: IncidentAnalysisResult
    ) -> Incident:
        cat_val = analysis.category.value if hasattr(analysis.category, "value") else str(analysis.category)
        sev_val = analysis.severity_level.value if hasattr(analysis.severity_level, "value") else str(analysis.severity_level)

        incident = Incident(
            title=analysis.title,
            description=analysis.normalized_description,
            category=cat_val,
            severity_level=sev_val,
            severity_reason=analysis.severity_reason,
            confidence=analysis.confidence,
            hazards=json.dumps(analysis.hazards),
            evidence_observations=json.dumps(analysis.evidence_observations),
            recommended_action=analysis.recommended_action,
            status=IncidentStatus.SUBMITTED,
            latitude=report.latitude,
            longitude=report.longitude,
            address=report.address
        )
        db.add(incident)
        db.flush()

        # Associate report with incident
        report.incident_id = incident.id
        
        # Log initial status
        log = StatusLog(
            incident_id=incident.id,
            old_status=None,
            new_status=IncidentStatus.SUBMITTED,
            changed_by="AI_ENGINE",
            notes=f"Analyzed by AI Engine. Category: {cat_val}, Severity: {sev_val}, Confidence: {analysis.confidence:.2f}"
        )
        db.add(log)
        db.commit()
        db.refresh(incident)
        return incident

    @staticmethod
    def attach_report_to_existing_incident(
        db: Session,
        report: Report,
        incident_id: str,
        duplicate_result: dict
    ) -> Incident:
        """Attaches a report to an existing canonical incident, logging status & metadata updates."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        report.incident_id = incident.id
        incident.updated_at = datetime.datetime.utcnow()

        # Log status log entry noting duplicate report attachment
        log = StatusLog(
            incident_id=incident.id,
            old_status=incident.status,
            new_status=incident.status,
            changed_by="DUPLICATE_ENGINE",
            notes=f"Linked additional report {report.id[:8]} (Confidence: {duplicate_result.get('match_confidence', 0):.2f}). Reason: {duplicate_result.get('reason', '')}"
        )
        db.add(log)
        db.commit()
        db.refresh(incident)
        return IncidentService._format_incident_data(incident)

    @staticmethod
    def update_incident_priority_and_routing(
        db: Session,
        incident_id: str,
        priority_result: dict,
        routing_result: dict
    ) -> dict:
        """Updates canonical Incident record with priority evaluation & routing decisions."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        incident.priority_score = priority_result["priority_score"]
        incident.priority_level = priority_result["priority_level"]
        incident.priority_reason = priority_result["priority_reason"]
        incident.priority_factors = json.dumps(priority_result["priority_factors"])
        
        incident.assigned_department = routing_result["assigned_department"]
        incident.routing_reason = routing_result["routing_reason"]
        incident.updated_at = datetime.datetime.utcnow()

        db.commit()
        db.refresh(incident)
        return IncidentService._format_incident_data(incident)

    @staticmethod
    def update_status(db: Session, incident_id: str, payload: IncidentStatusUpdate) -> Incident:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        old_status = incident.status
        new_status = payload.status

        # Validate status lifecycle transition
        if old_status != new_status:
            allowed = VALID_INCIDENT_TRANSITIONS.get(old_status, [])
            if new_status not in allowed:
                raise ValueError(f"Invalid status transition from '{old_status.value}' to '{new_status.value}'. Allowed transitions: {[s.value for s in allowed]}")

            incident.status = new_status
            incident.updated_at = datetime.datetime.utcnow()

            # Record status change log
            log = StatusLog(
                incident_id=incident.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=payload.changed_by or "SYSTEM",
                notes=payload.notes
            )
            db.add(log)
            db.commit()
            db.refresh(incident)
        return IncidentService._format_incident_data(incident)


class WorkOrderService:
    @staticmethod
    def get_work_orders(db: Session, skip: int = 0, limit: int = 100):
        return db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_work_order(db: Session, work_order_id: str):
        return db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()

    @staticmethod
    def get_by_incident(db: Session, incident_id: str):
        return db.query(WorkOrder).filter(WorkOrder.incident_id == incident_id).first()

    @staticmethod
    def create_work_order(db: Session, incident_id: str, department: str, action: str, materials: str, safety: str) -> WorkOrder:
        work_order = WorkOrder(
            incident_id=incident_id,
            assigned_department=department,
            recommended_action=action,
            required_materials=materials,
            safety_precautions=safety,
            status=WorkOrderStatus.PENDING
        )
        db.add(work_order)
        db.commit()
        db.refresh(work_order)
        return work_order

    @staticmethod
    def update_work_order_status(db: Session, work_order_id: str, payload: WorkOrderUpdateStatus, image_path: str = None) -> WorkOrder:
        wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
        if not wo:
            return None
        
        wo.status = payload.status
        if payload.completion_notes:
            wo.completion_notes = payload.completion_notes
        if image_path:
            wo.completion_image_path = image_path
        if payload.status == WorkOrderStatus.COMPLETED:
            wo.completed_at = datetime.datetime.utcnow()
        
        db.commit()
        db.refresh(wo)
        return wo
