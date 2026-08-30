import os
import sys
import json
import datetime
from sqlalchemy.orm import Session

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal, engine, Base
from app.models.entities import Incident, Report, WorkOrder, StatusLog, Notification, User, AIFeedback
from app.core.enums import IncidentStatus, WorkOrderStatus, SeverityLevel, PriorityLevel, IncidentCategory, UserRole, SLAStatus
from app.core.security import hash_password
from app.services.priority_routing_service import PriorityEngine, DepartmentRoutingService
from app.services.work_order_service import WorkOrderGenerationService

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_demo_data():
    print("Initializing database and seeding Phase 7 Competition-Hardened demo data...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        db.query(AIFeedback).delete()
        db.query(StatusLog).delete()
        db.query(Notification).delete()
        db.query(WorkOrder).delete()
        db.query(Report).delete()
        db.query(Incident).delete()
        db.query(User).delete()
        db.commit()

        # Seed authenticated demo users
        u1 = User(id="usr-citizen-1", email="citizen@civiclens.local", hashed_password=hash_password("Citizen123!"), full_name="Citizen User", role=UserRole.CITIZEN)
        u2 = User(id="usr-dispatcher-1", email="dispatcher@civiclens.local", hashed_password=hash_password("Dispatcher123!"), full_name="Dispatcher Operator", role=UserRole.DISPATCHER)
        u3 = User(id="usr-crew-1", email="crew@civiclens.local", hashed_password=hash_password("Crew123!"), full_name="Road Worker Alpha", role=UserRole.FIELD_CREW, department="Public Works - Roads")
        u3_beta = User(id="usr-crew-2", email="crew_beta@civiclens.local", hashed_password=hash_password("Crew123!"), full_name="Road Worker Beta", role=UserRole.FIELD_CREW, department="Public Works - Roads")
        u4 = User(id="usr-crew-water", email="crew_water@civiclens.local", hashed_password=hash_password("Crew123!"), full_name="Water Department Crew Worker", role=UserRole.FIELD_CREW, department="Water Department")
        u5 = User(id="usr-crew-traffic", email="crew_traffic@civiclens.local", hashed_password=hash_password("Crew123!"), full_name="Traffic Management Crew Worker", role=UserRole.FIELD_CREW, department="Traffic Management")
        u6 = User(id="usr-crew-electrical", email="crew_electrical@civiclens.local", hashed_password=hash_password("Crew123!"), full_name="Electrical Maintenance Crew Worker", role=UserRole.FIELD_CREW, department="Electrical Maintenance")
        u7 = User(id="usr-crew-drainage", email="crew_drainage@civiclens.local", hashed_password=hash_password("Crew123!"), full_name="Drainage & Sewer Crew Worker", role=UserRole.FIELD_CREW, department="Drainage & Sewer")
        u8 = User(id="usr-crew-sanitation", email="crew_sanitation@civiclens.local", hashed_password=hash_password("Crew123!"), full_name="Waste Management Crew Worker", role=UserRole.FIELD_CREW, department="Waste Management")
        db.add_all([u1, u2, u3, u3_beta, u4, u5, u6, u7, u8])
        db.commit()

        # =========================================================================
        # HOTSPOT A: MAIN GATE ROAD CONDITION CLUSTER (6 Incidents, 23 Reports)
        # Lat: 28.5450, Lon: 77.1926 (Indian Campus Demo Context - Concentrated within 150m)
        # =========================================================================
        lat_a, lon_a = 28.5450, 77.1926

        p1_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.CRITICAL,
            category=IncidentCategory.ROAD_HAZARD.value,
            hazards=["Vehicle rim damage", "Traffic swerving"],
            confidence=0.95,
            report_count=5,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)
        )
        r1_res = DepartmentRoutingService.route_incident(IncidentCategory.ROAD_HAZARD.value)

        inc1 = Incident(
            id="inc-demo-001-pothole",
            title="Large Hazardous Pothole near Gate 1",
            description="Deep 2-foot pothole in active driving lane near Gate 1 causing rim damage and traffic swerving.",
            category=IncidentCategory.ROAD_HAZARD.value,
            severity_level=SeverityLevel.CRITICAL,
            severity_reason="Immediate traffic collision hazard.",
            confidence=0.95,
            hazards=json.dumps(["Vehicle rim damage", "Traffic swerving"]),
            evidence_observations=json.dumps(["Asphalt cavity 60cm wide"]),
            recommended_action="Dispatch road crew for asphalt cold patching.",
            priority_score=p1_res["priority_score"],
            priority_level=p1_res["priority_level"].value,
            priority_reason=p1_res["priority_reason"],
            priority_factors=json.dumps(p1_res["priority_factors"]),
            assigned_department=r1_res["assigned_department"],
            routing_reason=r1_res["routing_reason"],
            status=IncidentStatus.IN_PROGRESS,
            latitude=lat_a,
            longitude=lon_a,
            address="100 Gate 1 Way, Main Entrance",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)
        )

        p2_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.HIGH,
            category=IncidentCategory.ROAD_HAZARD.value,
            hazards=["Cyclist hazard", "Loose concrete"],
            confidence=0.88,
            report_count=4,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=18)
        )
        r2_res = DepartmentRoutingService.route_incident(IncidentCategory.ROAD_HAZARD.value)

        inc2 = Incident(
            id="inc-demo-002-curb",
            title="Broken Curb & Asphalt Cracking",
            description="Curbed pavement crumbling into bike lane 80 meters from Gate 1.",
            category=IncidentCategory.ROAD_HAZARD.value,
            severity_level=SeverityLevel.HIGH,
            severity_reason="Cyclist tripping hazard.",
            confidence=0.88,
            hazards=json.dumps(["Cyclist hazard", "Loose concrete"]),
            evidence_observations=json.dumps(["Curb displacement 15cm"]),
            recommended_action="Repair concrete curb line.",
            priority_score=p2_res["priority_score"],
            priority_level=p2_res["priority_level"].value,
            priority_reason=p2_res["priority_reason"],
            priority_factors=json.dumps(p2_res["priority_factors"]),
            assigned_department=r2_res["assigned_department"],
            routing_reason=r2_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_a + 0.0006,
            longitude=lon_a + 0.0005,
            address="120 Gate 1 Way",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=18)
        )

        p3_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.HIGH,
            category=IncidentCategory.TRAFFIC_SIGNAL.value,
            hazards=["Intersection gridlock"],
            confidence=0.91,
            report_count=4,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=12)
        )
        r3_res = DepartmentRoutingService.route_incident(IncidentCategory.TRAFFIC_SIGNAL.value)

        inc3 = Incident(
            id="inc-demo-003-signal",
            title="Traffic Signal Controller Glitch",
            description="Gate 1 intersection traffic light stuck on flashing red.",
            category=IncidentCategory.TRAFFIC_SIGNAL.value,
            severity_level=SeverityLevel.HIGH,
            severity_reason="Intersection bottleneck.",
            confidence=0.91,
            hazards=json.dumps(["Intersection gridlock"]),
            evidence_observations=json.dumps(["Signal controller fault code 42"]),
            recommended_action="Reset controller box.",
            priority_score=p3_res["priority_score"],
            priority_level=p3_res["priority_level"].value,
            priority_reason=p3_res["priority_reason"],
            priority_factors=json.dumps(p3_res["priority_factors"]),
            assigned_department=r3_res["assigned_department"],
            routing_reason=r3_res["routing_reason"],
            status=IncidentStatus.IN_PROGRESS,
            latitude=lat_a - 0.0005,
            longitude=lon_a - 0.0004,
            address="Gate 1 & Main St Junction",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=12)
        )

        p4_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.MEDIUM,
            category=IncidentCategory.ROAD_HAZARD.value,
            hazards=["Pavement depression"],
            confidence=0.85,
            report_count=3,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=8)
        )
        r4_res = DepartmentRoutingService.route_incident(IncidentCategory.ROAD_HAZARD.value)

        inc4 = Incident(
            id="inc-demo-004-trench",
            title="Sunken Utility Trench Cut",
            description="Unfilled utility trench across driving lane near Gate 1 parking lot.",
            category=IncidentCategory.ROAD_HAZARD.value,
            severity_level=SeverityLevel.MEDIUM,
            severity_reason="Vehicle suspension impact.",
            confidence=0.85,
            hazards=json.dumps(["Pavement depression"]),
            evidence_observations=json.dumps(["3-inch trench depression"]),
            recommended_action="Backfill and level trench asphalt.",
            priority_score=p4_res["priority_score"],
            priority_level=p4_res["priority_level"].value,
            priority_reason=p4_res["priority_reason"],
            priority_factors=json.dumps(p4_res["priority_factors"]),
            assigned_department=r4_res["assigned_department"],
            routing_reason=r4_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_a + 0.0003,
            longitude=lon_a - 0.0006,
            address="Gate 1 Parking Entrance",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=8)
        )

        p5_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.MEDIUM,
            category=IncidentCategory.ROAD_HAZARD.value,
            hazards=["Skid risk"],
            confidence=0.82,
            report_count=2,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=5)
        )
        r5_res = DepartmentRoutingService.route_incident(IncidentCategory.ROAD_HAZARD.value)

        inc5 = Incident(
            id="inc-demo-005-gravel",
            title="Loose Gravel & Surface Oil Spill",
            description="Slippery gravel spill on Gate 1 exit ramp.",
            category=IncidentCategory.ROAD_HAZARD.value,
            severity_level=SeverityLevel.MEDIUM,
            severity_reason="Skid risk for motorcycles.",
            confidence=0.82,
            hazards=json.dumps(["Skid risk"]),
            evidence_observations=json.dumps(["Gravel patch on asphalt"]),
            recommended_action="Street sweeper cleanup.",
            priority_score=p5_res["priority_score"],
            priority_level=p5_res["priority_level"].value,
            priority_reason=p5_res["priority_reason"],
            priority_factors=json.dumps(p5_res["priority_factors"]),
            assigned_department=r5_res["assigned_department"],
            routing_reason=r5_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_a - 0.0004,
            longitude=lon_a + 0.0007,
            address="Gate 1 Exit Ramp",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=5)
        )

        p6_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.CRITICAL,
            category=IncidentCategory.ROAD_HAZARD.value,
            hazards=["Missing regulatory sign"],
            confidence=0.94,
            report_count=3,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=3)
        )
        r6_res = DepartmentRoutingService.route_incident(IncidentCategory.ROAD_HAZARD.value)

        inc6 = Incident(
            id="inc-demo-006-stopsign",
            title="Damaged Stop Sign at Gate 1 Access Road",
            description="Stop sign knocked over by delivery truck near Gate 1.",
            category=IncidentCategory.ROAD_HAZARD.value,
            severity_level=SeverityLevel.CRITICAL,
            severity_reason="Missing regulatory traffic control sign.",
            confidence=0.94,
            hazards=json.dumps(["Missing regulatory sign"]),
            evidence_observations=json.dumps(["Sign post bent 90 degrees"]),
            recommended_action="Re-erect stop sign post.",
            priority_score=p6_res["priority_score"],
            priority_level=p6_res["priority_level"].value,
            priority_reason=p6_res["priority_reason"],
            priority_factors=json.dumps(p6_res["priority_factors"]),
            assigned_department=r6_res["assigned_department"],
            routing_reason=r6_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_a + 0.0002,
            longitude=lon_a + 0.0002,
            address="Gate 1 Access Loop",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=3)
        )

        db.add_all([inc1, inc2, inc3, inc4, inc5, inc6])
        db.flush()

        # Seed 23 total reports for Hotspot A
        reps_a = [
            Report(id=f"rep-a-{i}", citizen_id=f"citizen-{i}", description=f"Gate 1 Road report #{i}", latitude=lat_a, longitude=lon_a, incident_id=inc1.id)
            for i in range(1, 6)
        ] + [
            Report(id=f"rep-b-{i}", citizen_id=f"citizen-{i+5}", description=f"Curb report #{i}", latitude=lat_a + 0.0006, longitude=lon_a + 0.0005, incident_id=inc2.id)
            for i in range(1, 5)
        ] + [
            Report(id=f"rep-c-{i}", citizen_id=f"citizen-{i+9}", description=f"Traffic light glitch #{i}", latitude=lat_a - 0.0005, longitude=lon_a - 0.0004, incident_id=inc3.id)
            for i in range(1, 5)
        ] + [
            Report(id=f"rep-d-{i}", citizen_id=f"citizen-{i+13}", description=f"Trench report #{i}", latitude=lat_a + 0.0003, longitude=lon_a - 0.0006, incident_id=inc4.id)
            for i in range(1, 4)
        ] + [
            Report(id=f"rep-e-{i}", citizen_id=f"citizen-{i+16}", description=f"Gravel spill #{i}", latitude=lat_a - 0.0004, longitude=lon_a + 0.0007, incident_id=inc5.id)
            for i in range(1, 3)
        ] + [
            Report(id=f"rep-f-{i}", citizen_id=f"citizen-{i+18}", description=f"Stop sign report #{i}", latitude=lat_a + 0.0002, longitude=lon_a + 0.0002, incident_id=inc6.id)
            for i in range(1, 4)
        ]
        db.add_all(reps_a)

        # Work Orders for Hotspot A using canonical departments
        wo1 = WorkOrder(
            id="wo-demo-001",
            incident_id=inc1.id,
            assigned_department="Public Works - Roads",
            assigned_team="Road Maintenance Crew Alpha",
            assigned_worker="crew@civiclens.local",
            assigned_worker_id="usr-crew-1",
            recommended_action="Dispatch road crew for asphalt cold patching.",
            required_materials="Cold-mix asphalt, compaction roller",
            safety_precautions="Traffic cones, high-vis vests",
            status=WorkOrderStatus.ASSIGNED,
            sla_deadline=datetime.datetime.utcnow() + datetime.timedelta(hours=2),
            sla_status=SLAStatus.ON_TRACK,
            assigned_at=datetime.datetime.utcnow()
        )
        wo3 = WorkOrder(
            id="wo-demo-003",
            incident_id=inc3.id,
            assigned_department="Traffic Management",
            assigned_team="Traffic Signal Team 1",
            assigned_worker="crew_traffic@civiclens.local",
            assigned_worker_id="usr-crew-traffic",
            recommended_action="Reset controller box unit.",
            required_materials="Multimeter, signal firmware patch module",
            safety_precautions="Traffic control flagger",
            status=WorkOrderStatus.ASSIGNED,
            sla_deadline=datetime.datetime.utcnow() + datetime.timedelta(hours=8),
            sla_status=SLAStatus.ON_TRACK,
            assigned_at=datetime.datetime.utcnow()
        )
        db.add_all([wo1, wo3])


        # =========================================================================
        # HOTSPOT B: NORTH RESIDENTIAL DRAINAGE CLUSTER (4 Incidents, 15 Reports)
        # Lat: 28.5520, Lon: 77.1990 (~900m away from Hotspot A)
        # =========================================================================
        lat_b, lon_b = 28.5520, 77.1990

        p7_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.HIGH,
            category=IncidentCategory.DRAINAGE.value,
            hazards=["Standing water", "Hydroplaning"],
            confidence=0.89,
            report_count=5,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=14)
        )
        r7_res = DepartmentRoutingService.route_incident(IncidentCategory.DRAINAGE.value)

        inc7 = Incident(
            id="inc-demo-007-catchbasin",
            title="Overflowing Catch Basin at North Block",
            description="Catch basin blocked with debris causing street flooding.",
            category=IncidentCategory.DRAINAGE.value,
            severity_level=SeverityLevel.HIGH,
            severity_reason="Localized street flooding.",
            confidence=0.89,
            hazards=json.dumps(["Standing water", "Hydroplaning"]),
            evidence_observations=json.dumps(["Water depth 10cm"]),
            recommended_action="Vacuum truck drain clearance.",
            priority_score=p7_res["priority_score"],
            priority_level=p7_res["priority_level"].value,
            priority_reason=p7_res["priority_reason"],
            priority_factors=json.dumps(p7_res["priority_factors"]),
            assigned_department=r7_res["assigned_department"],
            routing_reason=r7_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_b,
            longitude=lon_b,
            address="400 North Block Ave",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=14)
        )

        p8_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.MEDIUM,
            category=IncidentCategory.DRAINAGE.value,
            hazards=["Blocked sidewalk"],
            confidence=0.86,
            report_count=4,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=10)
        )
        r8_res = DepartmentRoutingService.route_incident(IncidentCategory.DRAINAGE.value)

        inc8 = Incident(
            id="inc-demo-008-stormdrain",
            title="Clogged Storm Drain Inlet",
            description="Debris buildup blocking storm inlet beside sidewalk.",
            category=IncidentCategory.DRAINAGE.value,
            severity_level=SeverityLevel.MEDIUM,
            severity_reason="Pedestrian walkway flooding.",
            confidence=0.86,
            hazards=json.dumps(["Blocked sidewalk"]),
            evidence_observations=json.dumps(["Leaves and sediment in grate"]),
            recommended_action="Manual grate clearing.",
            priority_score=p8_res["priority_score"],
            priority_level=p8_res["priority_level"].value,
            priority_reason=p8_res["priority_reason"],
            priority_factors=json.dumps(p8_res["priority_factors"]),
            assigned_department=r8_res["assigned_department"],
            routing_reason=r8_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_b + 0.0005,
            longitude=lon_b - 0.0004,
            address="420 North Block Ave",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=10)
        )

        p9_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.LOW,
            category=IncidentCategory.DRAINAGE.value,
            hazards=["Pedestrian detour"],
            confidence=0.80,
            report_count=3,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=6)
        )
        r9_res = DepartmentRoutingService.route_incident(IncidentCategory.DRAINAGE.value)

        inc9 = Incident(
            id="inc-demo-009-waterpool",
            title="Standing Water Pool on Pedestrian Path",
            description="Poor grading causing persistent 3-inch puddle.",
            category=IncidentCategory.DRAINAGE.value,
            severity_level=SeverityLevel.LOW,
            severity_reason="Pedestrian inconvenience.",
            confidence=0.80,
            hazards=json.dumps(["Pedestrian detour"]),
            evidence_observations=json.dumps(["Puddle 2m wide"]),
            recommended_action="Pavement regrading.",
            priority_score=p9_res["priority_score"],
            priority_level=p9_res["priority_level"].value,
            priority_reason=p9_res["priority_reason"],
            priority_factors=json.dumps(p9_res["priority_factors"]),
            assigned_department=r9_res["assigned_department"],
            routing_reason=r9_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_b - 0.0004,
            longitude=lon_b + 0.0005,
            address="450 North Block Ave",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=6)
        )

        p10_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.MEDIUM,
            category=IncidentCategory.WATER_LEAK.value,
            hazards=["Water loss"],
            confidence=0.87,
            report_count=3,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=4)
        )
        r10_res = DepartmentRoutingService.route_incident(IncidentCategory.WATER_LEAK.value)

        inc10 = Incident(
            id="inc-demo-010-valveleak",
            title="Leaking Water Main Valve Box",
            description="Water valve box bubbling clean water into street gutter.",
            category=IncidentCategory.WATER_LEAK.value,
            severity_level=SeverityLevel.MEDIUM,
            severity_reason="Potable water waste.",
            confidence=0.87,
            hazards=json.dumps(["Water loss"]),
            evidence_observations=json.dumps(["Slow trickle from valve cover"]),
            recommended_action="Inspect valve seal gasket.",
            priority_score=p10_res["priority_score"],
            priority_level=p10_res["priority_level"].value,
            priority_reason=p10_res["priority_reason"],
            priority_factors=json.dumps(p10_res["priority_factors"]),
            assigned_department=r10_res["assigned_department"],
            routing_reason=r10_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=lat_b + 0.0003,
            longitude=lon_b + 0.0003,
            address="410 North Block Ave",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=4)
        )

        db.add_all([inc7, inc8, inc9, inc10])
        db.flush()

        # Seed 15 total reports for Hotspot B
        reps_b = [
            Report(id=f"rep-b1-{i}", citizen_id=f"citizen-b-{i}", description=f"Catchbasin flood #{i}", latitude=lat_b, longitude=lon_b, incident_id=inc7.id)
            for i in range(1, 6)
        ] + [
            Report(id=f"rep-b2-{i}", citizen_id=f"citizen-b-{i+5}", description=f"Clogged stormdrain #{i}", latitude=lat_b + 0.0005, longitude=lon_b - 0.0004, incident_id=inc8.id)
            for i in range(1, 5)
        ] + [
            Report(id=f"rep-b3-{i}", citizen_id=f"citizen-b-{i+9}", description=f"Puddle report #{i}", latitude=lat_b - 0.0004, longitude=lon_b + 0.0005, incident_id=inc9.id)
            for i in range(1, 4)
        ] + [
            Report(id=f"rep-b4-{i}", citizen_id=f"citizen-b-{i+12}", description=f"Valve leak #{i}", latitude=lat_b + 0.0003, longitude=lon_b + 0.0003, incident_id=inc10.id)
            for i in range(1, 4)
        ]
        db.add_all(reps_b)


        # =========================================================================
        # NON-HOTSPOT 1: ISOLATED INCIDENTS (Far apart, 1-2 reports each)
        # =========================================================================
        p11_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.LOW,
            category=IncidentCategory.PUBLIC_PROPERTY.value,
            hazards=[],
            confidence=0.90,
            report_count=1,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=3)
        )
        r11_res = DepartmentRoutingService.route_incident(IncidentCategory.PUBLIC_PROPERTY.value)

        inc11 = Incident(
            id="inc-demo-011-bench",
            title="Peeling Paint on Park Bench at East Park",
            description="Peeling green paint on wooden park bench.",
            category=IncidentCategory.PUBLIC_PROPERTY.value,
            severity_level=SeverityLevel.LOW,
            severity_reason="Cosmetic park furniture wear.",
            confidence=0.90,
            hazards=json.dumps([]),
            evidence_observations=json.dumps(["Flaking paint on bench slats"]),
            recommended_action="Sand and repaint bench.",
            priority_score=p11_res["priority_score"],
            priority_level=p11_res["priority_level"].value,
            priority_reason=p11_res["priority_reason"],
            priority_factors=json.dumps(p11_res["priority_factors"]),
            assigned_department=r11_res["assigned_department"],
            routing_reason=r11_res["routing_reason"],
            status=IncidentStatus.SUBMITTED,
            latitude=28.5680, # ~2.5km away
            longitude=77.2100,
            address="East Park Promenade",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=3)
        )

        p12_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.MEDIUM,
            category=IncidentCategory.STREETLIGHT.value,
            hazards=["Dark sidewalk"],
            confidence=0.88,
            report_count=1,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=2)
        )
        r12_res = DepartmentRoutingService.route_incident(IncidentCategory.STREETLIGHT.value)

        inc12 = Incident(
            id="inc-demo-012-lamp",
            title="Single Streetlight Outage at Market Road",
            description="One streetlight lamp unlit beside residential driveway.",
            category=IncidentCategory.STREETLIGHT.value,
            severity_level=SeverityLevel.MEDIUM,
            severity_reason="Reduced nighttime sidewalk visibility.",
            confidence=0.88,
            hazards=json.dumps(["Dark sidewalk"]),
            evidence_observations=json.dumps(["Sodium lamp unlit"]),
            recommended_action="Replace bulb fixture.",
            priority_score=p12_res["priority_score"],
            priority_level=p12_res["priority_level"].value,
            priority_reason=p12_res["priority_reason"],
            priority_factors=json.dumps(p12_res["priority_factors"]),
            assigned_department=r12_res["assigned_department"],
            routing_reason=r12_res["routing_reason"],
            status=IncidentStatus.RESOLVED,
            latitude=28.5200, # ~2.8km away
            longitude=77.1700,
            address="800 Market Road",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=2)
        )

        db.add_all([inc11, inc12])
        db.flush()

        rep11 = Report(id="rep-iso-1", citizen_id="citizen-iso-1", description="Peeling bench paint", latitude=28.5680, longitude=77.2100, incident_id=inc11.id)
        rep12 = Report(id="rep-iso-2", citizen_id="citizen-iso-2", description="Lamp out at Market Road", latitude=28.5200, longitude=77.1700, incident_id=inc12.id)
        db.add_all([rep11, rep12])


        # =========================================================================
        # NON-HOTSPOT 2: SINGLE INCIDENT WITH 15 REPORTS (RULE VERIFICATION)
        # 1 Incident + 15 Reports MUST NOT BECOME A HOTSPOT (Requires >= 2 Incidents)
        # =========================================================================
        p13_res = PriorityEngine.evaluate_priority(
            severity=SeverityLevel.CRITICAL,
            category=IncidentCategory.ROAD_HAZARD.value,
            hazards=["Sinkhole risk"],
            confidence=0.96,
            report_count=15,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=20)
        )
        r13_res = DepartmentRoutingService.route_incident(IncidentCategory.ROAD_HAZARD.value)

        inc13 = Incident(
            id="inc-demo-013-singledup",
            title="Single Sinkhole Cavity on South Street",
            description="Highly reported single sinkhole cavity on South Street.",
            category=IncidentCategory.ROAD_HAZARD.value,
            severity_level=SeverityLevel.CRITICAL,
            severity_reason="Deep pavement depression.",
            confidence=0.96,
            hazards=json.dumps(["Sinkhole risk"]),
            evidence_observations=json.dumps(["Pavement cavity 80cm deep"]),
            recommended_action="Emergency street crew backfill.",
            priority_score=p13_res["priority_score"],
            priority_level=p13_res["priority_level"].value,
            priority_reason=p13_res["priority_reason"],
            priority_factors=json.dumps(p13_res["priority_factors"]),
            assigned_department=r13_res["assigned_department"],
            routing_reason=r13_res["routing_reason"],
            status=IncidentStatus.IN_PROGRESS,
            latitude=28.5100, # ~3.2km away
            longitude=77.2150,
            address="1200 South St",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=20)
        )
        db.add(inc13)
        db.flush()

        # Seed 15 citizen reports for this single incident
        reps_single = [
            Report(id=f"rep-single-{i}", citizen_id=f"citizen-s-{i}", description=f"Sinkhole report #{i}", latitude=28.5100, longitude=77.2150, incident_id=inc13.id)
            for i in range(1, 16)
        ]
        db.add_all(reps_single)


        # Seed Sample Notifications
        n1 = Notification(
            id="notif-demo-001",
            recipient_type="DISPATCHER",
            recipient_id="admin-dispatcher",
            incident_id=inc1.id,
            work_order_id=wo1.id,
            channel="IN_APP",
            event_type="INCIDENT_PRIORITY_ALERT",
            title=f"P1 ALERT: {inc1.title}",
            message=f"P1 Critical incident requires attention. Priority Score: {inc1.priority_score}/100. Dept: {inc1.assigned_department}. Reports: 5.",
            status="DELIVERED",
            provider="DEMO",
            is_read=False,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        )
        n2 = Notification(
            id="notif-demo-002",
            recipient_type="CITIZEN",
            recipient_id="citizen-alice",
            incident_id=inc12.id,
            work_order_id=None,
            channel="IN_APP",
            event_type="VERIFICATION_REQUIRED",
            title="Repair Completed - Verification Requested",
            message=f"The reported streetlight issue '{inc12.title}' has been marked resolved. Please review repair evidence and verify.",
            status="DELIVERED",
            provider="DEMO",
            is_read=False,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=18)
        )
        db.add_all([n1, n2])

        db.commit()
        print("Successfully seeded Phase 7 Competition-Hardened demo data!")
        print(f"Incidents: {db.query(Incident).count()}")
        print(f"Reports: {db.query(Report).count()}")
        print(f"Work Orders: {db.query(WorkOrder).count()}")
        print(f"Notifications: {db.query(Notification).count()}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
