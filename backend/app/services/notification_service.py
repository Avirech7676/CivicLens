import json
import logging
import datetime
import uuid
from typing import Optional, Union, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Notification, Incident, Report, WorkOrder

logger = logging.getLogger("civiclens.notifications")

class NotificationService:

    @staticmethod
    def _create_and_dispatch(
        db: Session,
        recipient_type: str,
        recipient_id: Optional[str],
        incident_id: Optional[str],
        work_order_id: Optional[str],
        channel: str,
        event_type: str,
        title: str,
        message: str,
        metadata: Optional[dict] = None
    ) -> Optional[Notification]:
        """
        Centralized internal dispatcher for CivicLens notifications.
        Prevents duplicate events, handles DEMO vs COURIER modes, and
        guarantees failures do not roll back civic transactions.
        """
        try:
            # 1. Idempotency & Duplicate Check
            idempotency_key = f"{event_type}:{incident_id or ''}:{work_order_id or ''}:{recipient_type}:{recipient_id or ''}"
            
            existing = db.query(Notification).filter(
                Notification.event_type == event_type,
                Notification.incident_id == incident_id,
                Notification.recipient_type == recipient_type,
                Notification.recipient_id == recipient_id
            ).first()

            if existing and event_type in ["REPORT_RECEIVED", "WORK_ORDER_ASSIGNED", "INCIDENT_PRIORITY_ALERT"]:
                logger.info(f"Notification {event_type} already exists for incident {incident_id}. Skipping duplicate.")
                return existing

            mode = (settings.NOTIFICATION_MODE or "demo").lower()
            provider = "DEMO"
            status = "DELIVERED"
            sent_at = datetime.datetime.utcnow()

            metadata_payload = metadata or {}
            metadata_payload["idempotency_key"] = idempotency_key

            # 2. Real Provider Mode (Courier Integration)
            if mode == "courier" and settings.COURIER_API_KEY:
                provider = "COURIER"
                try:
                    import courier
                    client = courier.Courier(authorization_token=settings.COURIER_API_KEY)
                    
                    template = settings.COURIER_NOTIFICATION_TEMPLATE_ID or "NT_CIVICLENS_DEFAULT"
                    recipient = recipient_id or "civiclens-user"

                    client.send.message(
                        message={
                            "to": {"user_id": recipient},
                            "template": template,
                            "data": {
                                "title": title,
                                "message": message,
                                "event_type": event_type,
                                "incident_id": incident_id,
                                "channel": channel
                            }
                        },
                        extra_headers={"Idempotency-Key": idempotency_key}
                    )
                    status = "DELIVERED"
                    logger.info(f"[COURIER] Successfully sent {event_type} notification to {recipient}")
                except Exception as courier_err:
                    status = "FAILED"
                    metadata_payload["courier_error"] = str(courier_err)
                    logger.error(f"[COURIER ERROR] Failed to send notification via Courier: {courier_err}")

            # 3. Persist Notification Entity to Database
            notification = Notification(
                id=str(uuid.uuid4()),
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                incident_id=incident_id,
                work_order_id=work_order_id,
                channel=channel,
                event_type=event_type,
                title=title,
                message=message,
                status=status,
                provider=provider,
                is_read=False,
                created_at=datetime.datetime.utcnow(),
                sent_at=sent_at,
                metadata_json=json.dumps(metadata_payload)
            )

            db.add(notification)
            db.commit()
            db.refresh(notification)
            return notification

        except Exception as err:
            logger.error(f"[NOTIFICATION SERVICE ERROR] Non-fatal notification error: {err}")
            try:
                db.rollback()
            except Exception:
                pass
            return None

    # --- HELPERS TO SAFELY EXTRACT FROM MODEL OR DICT ---

    @classmethod
    def _extract_inc_id(cls, incident) -> Optional[str]:
        if not incident:
            return None
        return incident.get("id") if isinstance(incident, dict) else getattr(incident, "id", None)

    @classmethod
    def _extract_inc_title(cls, incident) -> str:
        if not incident:
            return "Civic Incident"
        return incident.get("title") if isinstance(incident, dict) else getattr(incident, "title", "Civic Incident")

    @classmethod
    def _extract_inc_dept(cls, incident) -> str:
        if not incident:
            return "Municipal Department"
        return incident.get("assigned_department") if isinstance(incident, dict) else getattr(incident, "assigned_department", "Municipal Department")

    @classmethod
    def _extract_inc_score(cls, incident) -> int:
        if not incident:
            return 50
        return incident.get("priority_score") if isinstance(incident, dict) else getattr(incident, "priority_score", 50)

    @classmethod
    def _extract_inc_level(cls, incident) -> str:
        if not incident:
            return "P3_MEDIUM"
        val = incident.get("priority_level") if isinstance(incident, dict) else getattr(incident, "priority_level", "P3_MEDIUM")
        return val.value if hasattr(val, "value") else str(val)

    # --- SPECIFIC EVENT METHODS ---

    @classmethod
    def notify_report_received(cls, db: Session, report: Report) -> Optional[Notification]:
        return cls._create_and_dispatch(
            db=db,
            recipient_type="CITIZEN",
            recipient_id=report.citizen_id or "anonymous-citizen",
            incident_id=report.incident_id,
            work_order_id=None,
            channel="IN_APP",
            event_type="REPORT_RECEIVED",
            title="Report Received",
            message="Your civic report has been received and is being analyzed.",
            metadata={"report_id": report.id}
        )

    @classmethod
    def notify_report_consolidated(cls, db: Session, report: Report, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        title = cls._extract_inc_title(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="CITIZEN",
            recipient_id=report.citizen_id or "anonymous-citizen",
            incident_id=inc_id,
            work_order_id=None,
            channel="IN_APP",
            event_type="REPORT_CONSOLIDATED",
            title="Report Consolidated",
            message=f"Your report has been linked to an existing civic incident: '{title}'.",
            metadata={"report_id": report.id, "incident_title": title}
        )

    @classmethod
    def notify_incident_priority_alert(cls, db: Session, incident, report_count: int = 1) -> Optional[Notification]:
        p_level = cls._extract_inc_level(incident)
        p_score = cls._extract_inc_score(incident)
        title = cls._extract_inc_title(incident)
        inc_id = cls._extract_inc_id(incident)
        dept = cls._extract_inc_dept(incident)

        if p_level != "P1_CRITICAL" and p_score < settings.PRIORITY_P1_THRESHOLD:
            return None
            
        return cls._create_and_dispatch(
            db=db,
            recipient_type="DISPATCHER",
            recipient_id="admin-dispatcher",
            incident_id=inc_id,
            work_order_id=None,
            channel="IN_APP",
            event_type="INCIDENT_PRIORITY_ALERT",
            title=f"P1 ALERT: {title}",
            message=f"P1 Critical incident requires attention. Priority Score: {p_score}/100. Dept: {dept or 'Unassigned'}. Reports: {report_count}.",
            metadata={
                "priority_score": p_score,
                "assigned_department": dept,
                "report_count": report_count
            }
        )

    @classmethod
    def notify_department_assigned(cls, db: Session, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        dept = cls._extract_inc_dept(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="DISPATCHER",
            recipient_id="admin-dispatcher",
            incident_id=inc_id,
            work_order_id=None,
            channel="IN_APP",
            event_type="DEPARTMENT_ASSIGNED",
            title="Department Assigned",
            message=f"Incident #{inc_id[:8] if inc_id else ''} routed to {dept} department.",
            metadata={"assigned_department": dept}
        )

    @classmethod
    def notify_work_order_assigned(cls, db: Session, work_order: WorkOrder, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="FIELD_TEAM",
            recipient_id=work_order.assigned_department,
            incident_id=inc_id,
            work_order_id=work_order.id,
            channel="IN_APP",
            event_type="WORK_ORDER_ASSIGNED",
            title="New Work Order Assigned",
            message=f"New work order assigned to {work_order.assigned_department}. Action: {work_order.recommended_action}.",
            metadata={"recommended_action": work_order.recommended_action}
        )

    @classmethod
    def notify_work_started(cls, db: Session, work_order: WorkOrder, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        title = cls._extract_inc_title(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="CITIZEN",
            recipient_id="citizen-subscribers",
            incident_id=inc_id,
            work_order_id=work_order.id,
            channel="IN_APP",
            event_type="WORK_STARTED",
            title="Repair Work Started",
            message=f"Field crew has begun repair work on Incident '{title}'.",
            metadata={"department": work_order.assigned_department}
        )

    @classmethod
    def notify_incident_resolved(cls, db: Session, incident, work_order: Optional[WorkOrder] = None) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        title = cls._extract_inc_title(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="CITIZEN",
            recipient_id="citizen-subscribers",
            incident_id=inc_id,
            work_order_id=work_order.id if work_order else None,
            channel="IN_APP",
            event_type="VERIFICATION_REQUIRED",
            title="Repair Completed - Verification Requested",
            message=f"The reported civic issue '{title}' has been marked resolved. Please review the repair evidence and verify the result.",
            metadata={"notes": work_order.completion_notes if work_order else ""}
        )

    @classmethod
    def notify_incident_verified(cls, db: Session, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="CITIZEN",
            recipient_id="citizen-subscribers",
            incident_id=inc_id,
            work_order_id=None,
            channel="IN_APP",
            event_type="INCIDENT_VERIFIED",
            title="Resolution Verified",
            message=f"Thank you. Your verification has officially closed civic incident #{inc_id[:8] if inc_id else ''}."
        )

    @classmethod
    def notify_incident_reopened(cls, db: Session, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        title = cls._extract_inc_title(incident)
        dept = cls._extract_inc_dept(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="FIELD_TEAM",
            recipient_id=dept or "DISPATCH",
            incident_id=inc_id,
            work_order_id=None,
            channel="IN_APP",
            event_type="INCIDENT_REOPENED",
            title="Incident Reopened by Citizen",
            message=f"Citizen feedback indicates issue '{title}' persists. The incident has been reopened and returned to the operational queue.",
            metadata={"assigned_department": dept}
        )

    @classmethod
    def notify_sla_warning(cls, db: Session, work_order, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        title = cls._extract_inc_title(incident)
        dept = getattr(work_order, "assigned_department", None) or cls._extract_inc_dept(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="DISPATCHER",
            recipient_id="DISPATCH",
            incident_id=inc_id,
            work_order_id=getattr(work_order, "id", None),
            channel="IN_APP",
            event_type="SLA_WARNING",
            title="SLA Risk Warning",
            message=f"WorkOrder for '{title}' in {dept} has reached 75% of its SLA deadline duration.",
            metadata={"assigned_department": dept}
        )

    @classmethod
    def notify_sla_breached(cls, db: Session, work_order, incident) -> Optional[Notification]:
        inc_id = cls._extract_inc_id(incident)
        title = cls._extract_inc_title(incident)
        dept = getattr(work_order, "assigned_department", None) or cls._extract_inc_dept(incident)
        return cls._create_and_dispatch(
            db=db,
            recipient_type="DISPATCHER",
            recipient_id="DISPATCH",
            incident_id=inc_id,
            work_order_id=getattr(work_order, "id", None),
            channel="IN_APP",
            event_type="SLA_BREACHED",
            title="SLA Breach Alert",
            message=f"CRITICAL: WorkOrder for '{title}' in {dept} has breached its target SLA resolution deadline.",
            metadata={"assigned_department": dept}
        )
