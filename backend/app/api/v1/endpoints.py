from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil

from app.db.session import get_db
from app.core.config import settings
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel
from app.models.entities import Report, Incident, Notification
from app.schemas.dto import (
    ReportResponse, IncidentResponse, IncidentStatusUpdate,
    WorkOrderResponse, WorkOrderUpdateStatus, DashboardStats,
    NotificationResponse, NotificationUnreadCount,
    HotspotResponse, HotspotsListResponse,
    AssistantQueryRequest, AssistantQueryResponse
)
from app.services.crud import IncidentService, WorkOrderService
from app.services.ai_service import AIService
from app.services.duplicate_service import DuplicateDetectionService
from app.services.priority_routing_service import PriorityEngine, DepartmentRoutingService
from app.services.work_order_service import WorkOrderGenerationService
from app.services.notification_service import NotificationService
from app.services.hotspot_service import HotspotService
from app.services.command_assistant_service import CommandAssistantService

router = APIRouter()

# --- HEALTH ---
@router.get("/health")

def health_check():
    return {
        "status": "ok", 
        "service": settings.PROJECT_NAME, 
        "version": settings.VERSION,
        "ai_demo_mode": settings.AI_DEMO_MODE or not bool(settings.OPENAI_API_KEY)
    }

MAX_UPLOAD_SIZE = 10 * 1024 * 1024 # 10 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/pjpeg", "image/x-png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

def validate_and_save_upload_file(file: UploadFile, prefix: str = "") -> str:
    """
    Strict file upload validation:
    - Checks file extension & MIME type
    - Inspects header magic byte signature (JPEG, PNG, WEBP, GIF)
    - Enforces 10MB max size limit
    - Sanitizes filename with UUID to prevent path traversal
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No valid file provided")

    # 1. Path Traversal & Extension Check
    clean_filename = os.path.basename(file.filename)
    file_ext = os.path.splitext(clean_filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file extension '{file_ext}'. Allowed formats: JPG, PNG, WEBP, GIF")

    # 2. Declared Content-Type Check
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid MIME type '{file.content_type}'. Uploaded file must be an image.")

    # 3. Read File Bytes & Check Size
    file_bytes = file.file.read()
    file.file.seek(0)

    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit of 10MB")

    if len(file_bytes) < 4:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or corrupted")

    # 4. Magic Byte Header Inspection
    is_valid_magic = False
    if file_bytes.startswith(b"\xFF\xD8\xFF"): # JPEG
        is_valid_magic = True
    elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"): # PNG
        is_valid_magic = True
    elif file_bytes.startswith(b"GIF87a") or file_bytes.startswith(b"GIF89a"): # GIF
        is_valid_magic = True
    elif file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP": # WEBP
        is_valid_magic = True

    if not is_valid_magic:
        raise HTTPException(status_code=400, detail="File signature validation failed. Uploaded file content is not a genuine image.")

    # 5. Save with Sanitized UUID Filename
    filename = f"{prefix}{uuid.uuid4()}{file_ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    with open(filepath, "wb") as buffer:
        buffer.write(file_bytes)

    return f"/uploads/{filename}"


# --- REPORTS ---
@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    description: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    address: Optional[str] = Form(None),
    citizen_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    image_path = None
    if file:
        image_path = validate_and_save_upload_file(file)

    report = Report(
        description=description,
        latitude=latitude,
        longitude=longitude,
        address=address,
        citizen_id=citizen_id,
        image_path=image_path
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Execute AI Incident Analysis Engine
    try:
        analysis = await AIService.analyze_incident(description, image_path)
    except Exception as e:
        db.delete(report)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Incident Analysis Engine Error: {str(e)}"
        )

    # Search existing active Incidents for potential duplicate match
    duplicate_match = DuplicateDetectionService.find_matching_incident(
        db=db,
        report_desc=description,
        report_lat=latitude,
        report_lon=longitude,
        analysis=analysis
    )

    if duplicate_match["is_duplicate"]:
        # Attach report to existing incident - DO NOT create a new Incident, DO NOT create a duplicate WorkOrder
        matched_id = duplicate_match["matched_incident_id"]
        canonical_inc = IncidentService.attach_report_to_existing_incident(
            db=db,
            report=report,
            incident_id=matched_id,
            duplicate_result=duplicate_match
        )
        target_incident_id = matched_id
        target_category = canonical_inc["category"]
        target_severity = canonical_inc["severity_level"]
        target_hazards = canonical_inc["hazards"]
        target_confidence = canonical_inc["confidence"]
        target_created_at = canonical_inc["created_at"]
        target_severity_reason = canonical_inc.get("severity_reason")
        report_count = len(canonical_inc.get("reports", [])) or 1
    else:
        # Create a new canonical Incident record from analysis
        raw_incident = IncidentService.create_incident_from_analysis(
            db=db,
            report=report,
            analysis=analysis
        )
        target_incident_id = raw_incident.id
        target_category = raw_incident.category
        target_severity = raw_incident.severity_level
        target_hazards = analysis.hazards
        target_confidence = raw_incident.confidence
        target_created_at = raw_incident.created_at
        target_severity_reason = raw_incident.severity_reason
        report_count = 1

    # --- Execute Priority Engine & Department Routing on canonical Incident ---
    priority_res = PriorityEngine.evaluate_priority(
        severity=target_severity,
        category=target_category,
        hazards=target_hazards,
        confidence=target_confidence,
        report_count=report_count,
        created_at=target_created_at,
        severity_reason=target_severity_reason
    )

    routing_res = DepartmentRoutingService.route_incident(target_category)

    # Persist priority & department routing updates on canonical Incident
    updated_inc = IncidentService.update_incident_priority_and_routing(
        db=db,
        incident_id=target_incident_id,
        priority_result=priority_res,
        routing_result=routing_res
    )

    # Ensure canonical WorkOrder exists or create/update assigned department
    existing_wo = WorkOrderService.get_by_incident(db, target_incident_id)
    if not existing_wo:
        wo_plan = WorkOrderGenerationService.generate_plan(
            category=target_category,
            title=updated_inc["title"],
            description=updated_inc["description"],
            ai_recommended_action=updated_inc.get("recommended_action"),
            hazards=updated_inc.get("hazards", []),
            severity=target_severity,
            department=routing_res["assigned_department"]
        )
        existing_wo = WorkOrderService.create_work_order(
            db=db,
            incident_id=target_incident_id,
            department=wo_plan["assigned_department"],
            action=wo_plan["recommended_action"],
            materials=wo_plan["required_materials"],
            safety=wo_plan["safety_precautions"]
        )
    elif existing_wo.assigned_department != routing_res["assigned_department"]:
        existing_wo.assigned_department = routing_res["assigned_department"]
        db.commit()

    # --- Dispatch Lifecycle Notifications ---
    inc_obj = db.query(Incident).filter(Incident.id == target_incident_id).first()
    if inc_obj:
        if duplicate_match["is_duplicate"]:
            NotificationService.notify_report_consolidated(db=db, report=report, incident=inc_obj)
        else:
            NotificationService.notify_report_received(db=db, report=report)
            NotificationService.notify_department_assigned(db=db, incident=inc_obj)
            NotificationService.notify_incident_priority_alert(db=db, incident=inc_obj, report_count=report_count)

        if existing_wo:
            NotificationService.notify_work_order_assigned(db=db, work_order=existing_wo, incident=inc_obj)

    # Attach duplicate intelligence metadata to report response object
    response_data = ReportResponse.model_validate(report)
    response_data.duplicate_info = {
        "is_duplicate": duplicate_match["is_duplicate"],
        "matched_incident_id": duplicate_match["matched_incident_id"],
        "semantic_similarity": duplicate_match["semantic_similarity"],
        "distance_meters": duplicate_match["distance_meters"],
        "category_match": duplicate_match["category_match"],
        "match_confidence": duplicate_match["match_confidence"],
        "reason": duplicate_match["reason"]
    }

    return response_data


@router.get("/reports/{id}", response_model=ReportResponse)
def get_report(id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

# --- INCIDENTS ---
@router.get("/incidents", response_model=List[IncidentResponse])
def list_incidents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return IncidentService.get_incidents(db, skip=skip, limit=limit)


@router.get("/incidents/{id}", response_model=IncidentResponse)
def get_incident(id: str, db: Session = Depends(get_db)):
    incident = IncidentService.get_incident(db, id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/incidents/{id}/status", response_model=IncidentResponse)
def update_incident_status(
    id: str,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db)
):
    try:
        incident = IncidentService.update_status(db, id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Synchronize Work Order status
    wo = WorkOrderService.get_by_incident(db, id)
    if wo:
        if payload.status == IncidentStatus.IN_PROGRESS and wo.status in [WorkOrderStatus.PENDING, WorkOrderStatus.ASSIGNED]:
            WorkOrderService.update_work_order_status(db, wo.id, WorkOrderUpdateStatus(status=WorkOrderStatus.IN_PROGRESS))
        elif payload.status == IncidentStatus.RESOLVED and wo.status != WorkOrderStatus.COMPLETED:
            WorkOrderService.update_work_order_status(db, wo.id, WorkOrderUpdateStatus(status=WorkOrderStatus.COMPLETED))

    # Dispatch Lifecycle Notifications
    if payload.status == IncidentStatus.IN_PROGRESS:
        NotificationService.notify_work_started(db, wo, incident) if wo else None
    elif payload.status == IncidentStatus.RESOLVED:
        NotificationService.notify_incident_resolved(db, incident, wo)
    elif payload.status == IncidentStatus.VERIFIED:
        NotificationService.notify_incident_verified(db, incident)

    return incident

# --- WORK ORDERS ---
@router.get("/work-orders", response_model=List[WorkOrderResponse])
def list_work_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return WorkOrderService.get_work_orders(db, skip=skip, limit=limit)


@router.get("/work-orders/{id}", response_model=WorkOrderResponse)
def get_work_order(id: str, db: Session = Depends(get_db)):
    wo = WorkOrderService.get_work_order(db, id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    return wo


@router.patch("/work-orders/{id}/status", response_model=WorkOrderResponse)
async def update_work_order_status(
    id: str,
    status: str = Form(...),
    completion_notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    image_path = None
    if file:
        image_path = validate_and_save_upload_file(file, prefix="resolved_")

    payload = WorkOrderUpdateStatus(status=status, completion_notes=completion_notes)
    wo = WorkOrderService.update_work_order_status(db, id, payload, image_path=image_path)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    # Keep incident status synced if work order completes or updates
    if status == "COMPLETED" or status == WorkOrderStatus.COMPLETED.value:
        try:
            inc_updated = IncidentService.update_status(
                db, wo.incident_id, 
                IncidentStatusUpdate(status=IncidentStatus.RESOLVED, changed_by="DISPATCHER", notes="Work order marked completed.")
            )
            NotificationService.notify_incident_resolved(db, inc_updated, wo)
        except ValueError:
            pass # Ignore if already resolved/verified
    elif status == "IN_PROGRESS" or status == WorkOrderStatus.IN_PROGRESS.value:
        try:
            inc_updated = IncidentService.update_status(
                db, wo.incident_id,
                IncidentStatusUpdate(status=IncidentStatus.IN_PROGRESS, changed_by="DISPATCHER", notes="Work started on work order.")
            )
            NotificationService.notify_work_started(db, wo, inc_updated)
        except ValueError:
            pass
        
    return wo

# --- CITIZEN VERIFICATION ---
@router.post("/incidents/{id}/verify", response_model=IncidentResponse)
def verify_incident_resolution(
    id: str,
    verified_fixed: bool = Form(...),
    citizen_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    incident_obj = db.query(Incident).filter(Incident.id == id).first()
    if not incident_obj:
        raise HTTPException(status_code=404, detail="Incident not found")

    if verified_fixed:
        # Mark Incident as VERIFIED
        try:
            updated = IncidentService.update_status(
                db, id,
                IncidentStatusUpdate(
                    status=IncidentStatus.VERIFIED,
                    changed_by="CITIZEN",
                    notes=f"Verified fixed by citizen. Notes: {citizen_notes or 'Resolution confirmed.'}"
                )
            )
            NotificationService.notify_incident_verified(db, updated)
            return updated
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Reopen Incident back to IN_PROGRESS
        try:
            updated = IncidentService.update_status(
                db, id,
                IncidentStatusUpdate(
                    status=IncidentStatus.IN_PROGRESS,
                    changed_by="CITIZEN",
                    notes=f"Reopened by citizen - Issue reported still NOT fixed. Notes: {citizen_notes or 'Citizen feedback indicates problem persists.'}"
                )
            )
            # Reopen associated Work Order back to IN_PROGRESS
            wo = WorkOrderService.get_by_incident(db, id)
            if wo:
                WorkOrderService.update_work_order_status(
                    db, wo.id,
                    WorkOrderUpdateStatus(status=WorkOrderStatus.IN_PROGRESS, completion_notes="Reopened by citizen feedback.")
                )
            NotificationService.notify_incident_reopened(db, updated)
            return updated
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_reports = db.query(Report).count()
    total_incidents = db.query(Incident).count()
    open_incidents = db.query(Incident).filter(Incident.status.in_([
        IncidentStatus.SUBMITTED, IncidentStatus.TRIAGED, IncidentStatus.ASSIGNED, IncidentStatus.IN_PROGRESS
    ])).count()
    resolved_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.RESOLVED).count()
    verified_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.VERIFIED).count()

    incidents = db.query(Incident).all()
    by_category = {}
    by_severity = {}

    for inc in incidents:
        cat = inc.category or "Uncategorized"
        by_category[cat] = by_category.get(cat, 0) + 1
        
        sev = inc.severity_level.value if hasattr(inc.severity_level, "value") else str(inc.severity_level)
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return DashboardStats(
        total_reports=total_reports,
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        resolved_incidents=resolved_incidents,
        verified_incidents=verified_incidents,
        by_category=by_category,
        by_severity=by_severity
    )


# --- NOTIFICATIONS ---
@router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    recipient_type: Optional[str] = None,
    recipient_id: Optional[str] = None,
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Notification)
    if recipient_type:
        query = query.filter(Notification.recipient_type == recipient_type)
    if recipient_id:
        query = query.filter(Notification.recipient_id == recipient_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
        
    return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/notifications/unread", response_model=NotificationUnreadCount)
def get_unread_count(
    recipient_type: Optional[str] = None,
    recipient_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.is_read == False)
    if recipient_type:
        query = query.filter(Notification.recipient_type == recipient_type)
    if recipient_id:
        query = query.filter(Notification.recipient_id == recipient_id)
        
    count = query.count()
    return NotificationUnreadCount(unread_count=count)


@router.patch("/notifications/{id}/read", response_model=NotificationResponse)
def mark_notification_read(id: str, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/notifications/read-all")
def mark_all_notifications_read(
    recipient_type: Optional[str] = None,
    recipient_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.is_read == False)
    if recipient_type:
        query = query.filter(Notification.recipient_type == recipient_type)
    if recipient_id:
        query = query.filter(Notification.recipient_id == recipient_id)
        
    updated_count = query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"message": f"Marked {updated_count} notifications as read", "count": updated_count}


# --- CIVIC HOTSPOT INTELLIGENCE ---
@router.get("/hotspots", response_model=HotspotsListResponse)
def get_hotspots(
    status: Optional[str] = None,
    min_score: int = 0,
    db: Session = Depends(get_db)
):
    """Dynamically calculates spatial hotspots from canonical Incident records."""
    return HotspotService.detect_hotspots(db, status_filter=status, min_score=min_score)


@router.get("/incidents/{id}/hotspot", response_model=HotspotResponse)
def get_incident_hotspot(id: str, db: Session = Depends(get_db)):
    """Finds if a specific incident belongs to an active civic hotspot."""
    hs = HotspotService.get_hotspot_for_incident(db, id)
    if not hs:
        raise HTTPException(status_code=404, detail="Incident is not part of any detected spatial hotspot")
    return hs


# --- CIVICLENS COMMAND ASSISTANT ---
@router.post("/assistant/query", response_model=AssistantQueryResponse)
def query_command_assistant(
    payload: AssistantQueryRequest,
    db: Session = Depends(get_db)
):
    """Processes operational questions for Dispatchers using grounded CivicLens data."""
    return CommandAssistantService.process_query(db, payload.question)

