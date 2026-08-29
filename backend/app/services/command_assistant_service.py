import json
import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.core.enums import IncidentStatus, PriorityLevel
from app.models.entities import Incident, Report, WorkOrder
from app.services.hotspot_service import HotspotService

logger = logging.getLogger("civiclens.assistant")

class CommandAssistantService:

    @classmethod
    def detect_intent(cls, question: str) -> str:
        q = question.lower().strip()

        if not q:
            return "EMPTY_QUESTION"

        # Check unsupported topics
        unsupported_keywords = ["budget", "taxes", "salary", "election", "weather", "sports", "mayor", "president", "policy"]
        if any(kw in q for kw in unsupported_keywords):
            return "UNSUPPORTED_QUESTION"

        # 1. TOP_PRIORITY_INCIDENTS
        if any(kw in q for kw in ["fix first", "attention first", "urgent", "most critical", "top priority", "highest priority", "what to fix"]):
            return "TOP_PRIORITY_INCIDENTS"

        # 2. HOTSPOT_SUMMARY
        if any(kw in q for kw in ["hotspots", "hot spot", "concentrated", "concentrations", "problem areas", "high density"]):
            return "HOTSPOT_SUMMARY"

        # 3. INCIDENT_EXPLANATION
        if any(kw in q for kw in ["why is", "why p1", "why critical", "why priority", "explain p1", "explain priority", "driver"]):
            return "INCIDENT_EXPLANATION"

        # 4. INCIDENT_REPORT_COUNT
        if any(kw in q for kw in ["how many reports", "report count", "linked reports", "reports linked"]):
            return "INCIDENT_REPORT_COUNT"

        # 5. DEPARTMENT_WORKLOAD
        if any(kw in q for kw in ["department", "dept", "most active work", "workload", "assigned department"]):
            return "DEPARTMENT_WORKLOAD"

        # 6. STATUS_SUMMARY
        if any(kw in q for kw in ["awaiting verification", "verification", "status summary", "active incidents", "how many incidents"]):
            return "STATUS_SUMMARY"

        # 7. CATEGORY_SUMMARY
        if any(kw in q for kw in ["common civic problems", "common problems", "categories", "most common"]):
            return "CATEGORY_SUMMARY"

        # 8. HOTSPOT_INCIDENTS
        if any(kw in q for kw in ["inside hotspot", "inside the hotspot", "in hotspot", "hotspot incidents"]):
            return "HOTSPOT_INCIDENTS"

        # 9. INCIDENT_STATUS
        if any(kw in q for kw in ["status of", "incident status", "what is the status"]):
            return "INCIDENT_STATUS"

        # Default fallback to TOP_PRIORITY_INCIDENTS if question asks about priority/action
        if "priority" in q or "fix" in q or "pothole" in q or "issue" in q:
            return "TOP_PRIORITY_INCIDENTS"

        return "UNSUPPORTED_QUESTION"

    @classmethod
    def process_query(cls, db: Session, question: str) -> Dict[str, Any]:
        """
        Executes grounded, deterministic query processing for Command Assistant.
        Never generates raw SQL. Never fabricates values.
        """
        q = question.strip()
        if not q:
            return {
                "question": question,
                "intent": "EMPTY_QUESTION",
                "answer": "Please provide a valid question about CivicLens operations.",
                "sources": []
            }

        if len(q) > 500:
            return {
                "question": question,
                "intent": "INVALID_QUESTION",
                "answer": "Question is too long. Please shorten your query to under 500 characters.",
                "sources": []
            }

        intent = cls.detect_intent(q)

        if intent == "UNSUPPORTED_QUESTION":
            return {
                "question": question,
                "intent": intent,
                "answer": "I don't have enough information in CivicLens data to answer that. CivicLens focuses on real-time civic incident triage, spatial hotspots, priority routing, and work order dispatch.",
                "sources": []
            }

        if intent == "TOP_PRIORITY_INCIDENTS":
            return cls._handle_top_priority(db, question)
        elif intent == "HOTSPOT_SUMMARY":
            return cls._handle_hotspot_summary(db, question)
        elif intent == "INCIDENT_EXPLANATION":
            return cls._handle_incident_explanation(db, question)
        elif intent == "INCIDENT_REPORT_COUNT":
            return cls._handle_report_count(db, question)
        elif intent == "DEPARTMENT_WORKLOAD":
            return cls._handle_department_workload(db, question)
        elif intent == "STATUS_SUMMARY":
            return cls._handle_status_summary(db, question)
        elif intent == "CATEGORY_SUMMARY":
            return cls._handle_category_summary(db, question)
        elif intent == "HOTSPOT_INCIDENTS":
            return cls._handle_hotspot_incidents(db, question)
        elif intent == "INCIDENT_STATUS":
            return cls._handle_incident_status(db, question)

        return {
            "question": question,
            "intent": "UNSUPPORTED_QUESTION",
            "answer": "I don't have enough information in CivicLens data to answer that.",
            "sources": []
        }

    # --- HANDLER IMPLEMENTATIONS ---

    @classmethod
    def _handle_top_priority(cls, db: Session, question: str) -> Dict[str, Any]:
        incidents = db.query(Incident).filter(
            Incident.status != IncidentStatus.VERIFIED
        ).order_by(Incident.priority_score.desc()).limit(3).all()

        if not incidents:
            return {
                "question": question,
                "intent": "TOP_PRIORITY_INCIDENTS",
                "answer": "CivicLens currently records no active unresolved incidents.",
                "sources": []
            }

        lines = ["CivicLens currently identifies the highest-priority active incidents:"]
        sources = []

        for idx, inc in enumerate(incidents, start=1):
            p_level = inc.priority_level.value if hasattr(inc.priority_level, 'value') else str(inc.priority_level)
            rep_count = len(inc.reports) if inc.reports else 1
            dept = inc.assigned_department or "Unassigned"
            lines.append(
                f"\n{idx}. {inc.title} — {p_level.replace('_', ' ')} — {inc.priority_score}/100"
                f"\n   {rep_count} citizen reports | {dept}"
            )
            sources.append({
                "type": "incident",
                "id": inc.id,
                "label": f"{inc.title} ({inc.priority_score}/100)"
            })

        lines.append("\nThese rankings are based on CivicLens's deterministic priority engine.")

        return {
            "question": question,
            "intent": "TOP_PRIORITY_INCIDENTS",
            "answer": "\n".join(lines),
            "sources": sources
        }

    @classmethod
    def _handle_hotspot_summary(cls, db: Session, question: str) -> Dict[str, Any]:
        hs_res = HotspotService.detect_hotspots(db)
        hotspots = hs_res.get("hotspots", [])

        if not hotspots:
            return {
                "question": question,
                "intent": "HOTSPOT_SUMMARY",
                "answer": "CivicLens currently detects no active spatial hotspots across active incidents.",
                "sources": []
            }

        lines = [f"CivicLens currently detects {len(hotspots)} active spatial hotspots:"]
        sources = []

        for idx, hs in enumerate(hotspots, start=1):
            lines.append(
                f"\n{idx}. {hs['name']}"
                f"\n   Score: {hs['hotspot_score']}/100 ({hs['hotspot_level']})"
                f"\n   {hs['incident_count']} incidents | {hs['report_count']} reports"
                f"\n   Pattern: {hs['pattern']}"
            )
            sources.append({
                "type": "hotspot",
                "id": hs["hotspot_id"],
                "label": f"Hotspot: {hs['name']} ({hs['hotspot_score']}/100)"
            })

        return {
            "question": question,
            "intent": "HOTSPOT_SUMMARY",
            "answer": "\n".join(lines),
            "sources": sources
        }

    @classmethod
    def _handle_incident_explanation(cls, db: Session, question: str) -> Dict[str, Any]:
        # Try finding incident by ID or keyword match
        inc = cls._find_target_incident(db, question)

        if not inc:
            # Fallback to top incident
            inc = db.query(Incident).order_by(Incident.priority_score.desc()).first()

        if not inc:
            return {
                "question": question,
                "intent": "INCIDENT_EXPLANATION",
                "answer": "I couldn't find that incident in CivicLens data.",
                "sources": []
            }

        p_level = inc.priority_level.value if hasattr(inc.priority_level, 'value') else str(inc.priority_level)
        rep_count = len(inc.reports) if inc.reports else 1
        dept = inc.assigned_department or "Unassigned"

        factors_text = ""
        if inc.priority_factors:
            try:
                factors_list = json.loads(inc.priority_factors) if isinstance(inc.priority_factors, str) else inc.priority_factors
                if isinstance(factors_list, list):
                    top_contribs = []
                    for f in factors_list:
                        f_name = f.get("factor", "").replace("_", " ").title()
                        f_contrib = f.get("contribution", 0.0)
                        if f_contrib > 0:
                            top_contribs.append(f"{f_name}: {f_contrib}pts")
                    if top_contribs:
                        factors_text = " Score breakdown: " + ", ".join(top_contribs) + "."
            except Exception:
                pass

        reason = inc.priority_reason or "Calculated by CivicLens priority engine."

        answer = (
            f"Incident '{inc.title}' is classified as {p_level.replace('_', ' ')} with a priority score of {inc.priority_score}/100.{factors_text} "
            f"It aggregates {rep_count} citizen reports and is routed to {dept}. "
            f"Reasoning: {reason}"
        )

        return {
            "question": question,
            "intent": "INCIDENT_EXPLANATION",
            "answer": answer,
            "sources": [{
                "type": "incident",
                "id": inc.id,
                "label": f"{inc.title} ({inc.priority_score}/100)"
            }]
        }

    @classmethod
    def _handle_report_count(cls, db: Session, question: str) -> Dict[str, Any]:
        inc = cls._find_target_incident(db, question)
        if not inc:
            inc = db.query(Incident).order_by(Incident.priority_score.desc()).first()

        if not inc:
            return {
                "question": question,
                "intent": "INCIDENT_REPORT_COUNT",
                "answer": "I couldn't find a matching incident in CivicLens data.",
                "sources": []
            }

        rep_count = len(inc.reports) if inc.reports else 1
        answer = f"Canonical incident '{inc.title}' (INC-{inc.id[:6].upper()}) aggregates {rep_count} citizen reports."

        return {
            "question": question,
            "intent": "INCIDENT_REPORT_COUNT",
            "answer": answer,
            "sources": [{
                "type": "incident",
                "id": inc.id,
                "label": f"{inc.title} ({rep_count} Reports)"
            }]
        }

    @classmethod
    def _handle_department_workload(cls, db: Session, question: str) -> Dict[str, Any]:
        incidents = db.query(Incident).filter(Incident.status != IncidentStatus.VERIFIED).all()

        if not incidents:
            return {
                "question": question,
                "intent": "DEPARTMENT_WORKLOAD",
                "answer": "There are currently no active workloads assigned to departments.",
                "sources": []
            }

        workloads: Dict[str, Dict[str, int]] = {}
        for inc in incidents:
            dept = inc.assigned_department or "Unassigned"
            if dept not in workloads:
                workloads[dept] = {"active": 0, "p1": 0, "p2": 0, "in_progress": 0}
            workloads[dept]["active"] += 1
            p_level = inc.priority_level.value if hasattr(inc.priority_level, 'value') else str(inc.priority_level)
            if p_level == "P1_CRITICAL" or (inc.priority_score or 0) >= 80:
                workloads[dept]["p1"] += 1
            elif p_level == "P2_HIGH" or (65 <= (inc.priority_score or 0) < 80):
                workloads[dept]["p2"] += 1
            st = inc.status.value if hasattr(inc.status, 'value') else str(inc.status)
            if st == "IN_PROGRESS":
                workloads[dept]["in_progress"] += 1

        sorted_workloads = sorted(workloads.items(), key=lambda x: x[1]["active"], reverse=True)

        lines = ["Department Active Workload Summary:"]
        sources = []

        for dept, stats in sorted_workloads:
            lines.append(
                f"\n• {dept}: {stats['active']} Active Incidents "
                f"(P1: {stats['p1']}, P2: {stats['p2']}, In-Progress: {stats['in_progress']})"
            )
            sources.append({
                "type": "department",
                "id": dept,
                "label": f"Dept: {dept} ({stats['active']} Active)"
            })

        return {
            "question": question,
            "intent": "DEPARTMENT_WORKLOAD",
            "answer": "\n".join(lines),
            "sources": sources
        }

    @classmethod
    def _handle_status_summary(cls, db: Session, question: str) -> Dict[str, Any]:
        resolved_count = db.query(Incident).filter(Incident.status == IncidentStatus.RESOLVED).count()
        in_progress_count = db.query(Incident).filter(Incident.status == IncidentStatus.IN_PROGRESS).count()
        submitted_count = db.query(Incident).filter(Incident.status == IncidentStatus.SUBMITTED).count()
        verified_count = db.query(Incident).filter(Incident.status == IncidentStatus.VERIFIED).count()

        answer = (
            f"CivicLens Operational Status Breakdown:\n"
            f"• Awaiting Citizen Verification: {resolved_count}\n"
            f"• Active In-Progress Repairs: {in_progress_count}\n"
            f"• Submitted / Under Triage: {submitted_count}\n"
            f"• Closed & Citizen Verified: {verified_count}"
        )

        return {
            "question": question,
            "intent": "STATUS_SUMMARY",
            "answer": answer,
            "sources": []
        }

    @classmethod
    def _handle_category_summary(cls, db: Session, question: str) -> Dict[str, Any]:
        results = db.query(
            Incident.category, func.count(Incident.id)
        ).group_by(Incident.category).all()

        if not results:
            return {
                "question": question,
                "intent": "CATEGORY_SUMMARY",
                "answer": "No incidents found by category.",
                "sources": []
            }

        lines = ["Civic Incident Distribution by Category:"]
        for cat, cnt in sorted(results, key=lambda x: x[1], reverse=True):
            cat_name = cat.value if hasattr(cat, 'value') else str(cat)
            lines.append(f"• {cat_name.replace('_', ' ').title()}: {cnt} Incidents")

        return {
            "question": question,
            "intent": "CATEGORY_SUMMARY",
            "answer": "\n".join(lines),
            "sources": []
        }

    @classmethod
    def _handle_hotspot_incidents(cls, db: Session, question: str) -> Dict[str, Any]:
        hs_res = HotspotService.detect_hotspots(db)
        hotspots = hs_res.get("hotspots", [])

        if not hotspots:
            return {
                "question": question,
                "intent": "HOTSPOT_INCIDENTS",
                "answer": "No active spatial hotspots found.",
                "sources": []
            }

        target_hs = hotspots[0]
        inc_ids = target_hs.get("incident_ids", [])
        incidents = db.query(Incident).filter(Incident.id.in_(inc_ids)).all()

        lines = [f"Incidents inside Hotspot '{target_hs['name']}' ({target_hs['hotspot_id'].upper()}):"]
        sources = [{
            "type": "hotspot",
            "id": target_hs["hotspot_id"],
            "label": f"Hotspot: {target_hs['name']}"
        }]

        for inc in incidents:
            lines.append(f"• INC-{inc.id[:6].upper()}: {inc.title} ({inc.priority_level} - {inc.priority_score}/100)")
            sources.append({
                "type": "incident",
                "id": inc.id,
                "label": inc.title
            })

        return {
            "question": question,
            "intent": "HOTSPOT_INCIDENTS",
            "answer": "\n".join(lines),
            "sources": sources
        }

    @classmethod
    def _handle_incident_status(cls, db: Session, question: str) -> Dict[str, Any]:
        inc = cls._find_target_incident(db, question)
        if not inc:
            inc = db.query(Incident).order_by(Incident.priority_score.desc()).first()

        if not inc:
            return {
                "question": question,
                "intent": "INCIDENT_STATUS",
                "answer": "I couldn't find that incident in CivicLens.",
                "sources": []
            }

        st = inc.status.value if hasattr(inc.status, 'value') else str(inc.status)
        wo = db.query(WorkOrder).filter(WorkOrder.incident_id == inc.id).first()
        wo_status = wo.status.value if (wo and hasattr(wo.status, 'value')) else (str(wo.status) if wo else "None")

        answer = (
            f"Status for Incident '{inc.title}' (INC-{inc.id[:6].upper()}):\n"
            f"• Incident Status: {st}\n"
            f"• Priority Level: {inc.priority_level} ({inc.priority_score}/100)\n"
            f"• Assigned Department: {inc.assigned_department or 'Unassigned'}\n"
            f"• Work Order Status: {wo_status}"
        )

        return {
            "question": question,
            "intent": "INCIDENT_STATUS",
            "answer": answer,
            "sources": [{
                "type": "incident",
                "id": inc.id,
                "label": f"{inc.title} ({st})"
            }]
        }

    @classmethod
    def _find_target_incident(cls, db: Session, question: str) -> Optional[Incident]:
        q_lower = question.lower()
        # Search by UUID prefix or title keyword match
        all_incidents = db.query(Incident).all()
        for inc in all_incidents:
            if inc.id.lower() in q_lower or inc.id[:8].lower() in q_lower:
                return inc
            if "pothole" in q_lower and "pothole" in inc.title.lower():
                return inc
            if "storm drain" in q_lower and ("storm drain" in inc.title.lower() or "drain" in inc.title.lower()):
                return inc
            if "electrical" in q_lower and ("electrical" in inc.title.lower() or "power" in inc.title.lower() or "lamp" in inc.title.lower()):
                return inc
        return None
