import logging
from typing import Dict, Any, List, Optional
from app.core.enums import IncidentCategory, SeverityLevel, PriorityLevel

logger = logging.getLogger(__name__)

# Controlled Operational Templates by Category
CATEGORY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ROAD_HAZARD": {
        "action_steps": [
            "Inspect road surface and measure cavity/defect extent",
            "Establish safe perimeter with traffic cones and warning signs",
            "Apply high-durability cold-mix or hot asphalt patch",
            "Compact patch flush with surrounding roadway",
            "Inspect surrounding asphalt for sub-base instability",
            "Collect post-repair completion photographic evidence"
        ],
        "materials": [
            "Cold-mix / hot asphalt compound",
            "Vibratory plate compactor / roller",
            "Safety cones and high-visibility traffic signs",
            "Tack coat emulsion"
        ],
        "safety": [
            "Establish a safe work perimeter prior to equipment deployment",
            "Deploy high-visibility traffic diversion signs 50m upstream",
            "Wear class-3 high-visibility safety vests and steel-toed boots",
            "Ensure safe pedestrian clearance around active compaction area"
        ]
    },
    "STREETLIGHT": {
        "action_steps": [
            "Inspect streetlight pole, housing, and photocell fixture",
            "Isolate electrical circuit before housing access",
            "Replace defective LED luminaire bulb / fixture component",
            "Inspect wire connections and grounding lugs",
            "Restore circuit power and test light illumination",
            "Collect post-repair photo evidence showing operating light"
        ],
        "materials": [
            "Replacement LED street luminaire fixture (100W/150W)",
            "Bucket truck / aerial lift platform",
            "Insulated wire connectors & heat-shrink tubing",
            "Digital multimeter and circuit tester"
        ],
        "safety": [
            "Verify circuit isolation before touching electrical leads",
            "Use insulated tools and arc-flash protective gear",
            "Secure aerial lift outriggers on stable ground before elevating",
            "Set up night-work warning beacons if operating in low visibility"
        ]
    },
    "SANITATION": {
        "action_steps": [
            "Inspect waste accumulation and check for hazardous bio-materials",
            "Deploy sanitation crew and refuse collection vehicle",
            "Clear accumulated litter, overflowing bins, and illegal dumping",
            "Apply disinfectant spray and wash down affected surface area",
            "Verify entire public space is clear of debris",
            "Collect completion photo evidence"
        ],
        "materials": [
            "Rear-loader refuse vehicle / heavy-duty waste bags",
            "Industrial broom, shovels, and litter pickers",
            "Eco-friendly pressure wash washdown disinfectant",
            "Heavy-duty nitrile/leather work gloves"
        ],
        "safety": [
            "Wear puncture-resistant gloves and protective eyewear",
            "Check waste pile for sharp objects or biohazards before manual handling",
            "Maintain safe distance from hydraulic tailgate during compaction",
            "Ensure proper ergonomic lifting techniques for heavy items"
        ]
    },
    "WATER_LEAK": {
        "action_steps": [
            "Locate main line valve and isolate pressurized leak section",
            "Excavate area safely to expose damaged water pipe segment",
            "Replace damaged pipe fitting / clamp ruptured section",
            "Pressurize system and test for continued water leakage",
            "Backfill trench, compact soil, and restore surface pave",
            "Collect completion photo showing dry repaired pipeline"
        ],
        "materials": [
            "Ductile iron repair sleeve / stainless steel pipe clamp",
            "Submersible dewatering pump",
            "Backfill gravel and aggregate sub-base",
            "Pipe wrenches and pressure gauges"
        ],
        "safety": [
            "Inspect trench shoring if excavation exceeds 1.2m depth",
            "Watch for slip hazards on muddy surfaces around leak area",
            "Locate underground electrical/gas utilities prior to digging",
            "Provide safe pedestrian bridge if sidewalk excavation is necessary"
        ]
    },
    "DRAINAGE": {
        "action_steps": [
            "Inspect catch basin grate and storm drain inlet channel",
            "Remove debris, silt, leaves, and trash obstructing grate",
            "Use vacuum jetter truck to clear clogged underground culvert",
            "Verify free-flowing water drainage away from roadway",
            "Re-seat storm drain grate securely",
            "Collect completion photo showing clear drain and no pooling water"
        ],
        "materials": [
            "Vacuum jetter truck / hydro-excavator",
            "Catch basin scoop and heavy-duty debris hooks",
            "High-pressure water nozzle",
            "Replacement cast-iron drainage grate if damaged"
        ],
        "safety": [
            "Do not enter confined catch basin structures without gas testing & safety harness",
            "Secure heavy grates during lifting to prevent pinch injuries",
            "Position vehicle hazard lights and cones on approach lane",
            "Use splash guards when operating high-pressure hydro-jetter"
        ]
    },
    "ELECTRICAL": {
        "action_steps": [
            "Immediately isolate electrical supply and de-energize line section",
            "Set up 10m exclusion safety perimeter around exposed wires/transformer",
            "Inspect damaged utility box, wiring conduit, or spark source",
            "Repair wire insulation, replace fuse/breaker, or re-terminate connections",
            "Conduct insulation resistance testing and restore supply",
            "Collect completion photo showing secured electrical enclosure"
        ],
        "materials": [
            "High-voltage rubber insulating blankets and gloves",
            "Replacement utility box enclosure / breaker panel",
            "Insulated copper wiring and crimp lugs",
            "Voltage detector & megohmmeter"
        ],
        "safety": [
            "Treat all exposed conductors as energized until lockout/tagout is verified",
            "Wear NFPA 70E rated arc-flash suit, face shield, and voltage-rated gloves",
            "Maintain strict exclusion zone for unauthorized personnel",
            "Do not operate in wet standing water near exposed energized sources"
        ]
    },
    "PUBLIC_PROPERTY": {
        "action_steps": [
            "Inspect damaged municipal asset (bench, fence, playground equipment, sign)",
            "Secure loose or broken sharp components to eliminate immediate hazard",
            "Replace broken wooden/metal slats, hardware, or structural posts",
            "Apply protective paint, lacquer, or anti-graffiti coating as needed",
            "Test structural stability and load capacity",
            "Collect completion photo evidence"
        ],
        "materials": [
            "Replacement hardware (bolts, brackets, wooden slats)",
            "Power drill, impact driver, and angle grinder",
            "Outdoor weather-resistant paint or sealer",
            "Barricade tape"
        ],
        "safety": [
            "Wear safety glasses, dust mask, and hearing protection during power tool use",
            "Ensure structural components are fully supported before removing fasteners",
            "Keep work area cordoned off from park visitors and children"
        ]
    },
    "TRAFFIC_SIGNAL": {
        "action_steps": [
            "Deploy temporary portable stop signs / traffic control officer at intersection",
            "Inspect traffic signal cabinet, controller board, and LED signal heads",
            "Diagnose fault (power loss, burnt LED module, misaligned pole)",
            "Replace faulty signal module or recalibrate controller cabinet",
            "Test full signal cycle timing across all directions",
            "Collect completion photo showing operating traffic signal"
        ],
        "materials": [
            "Replacement LED traffic signal head / conflict monitor card",
            "Aerial lift bucket truck",
            "Temporary fold-out STOP signs",
            "Cabinet wiring diagram and signal tester"
        ],
        "safety": [
            "Coordinate with traffic police for intersection control during repair",
            "Wear high-visibility Class-3 safety gear",
            "De-energize signal cabinet prior to replacing internal circuit boards",
            "Ensure bucket truck boom is clear of overhead power lines"
        ]
    },
    "OTHER": {
        "action_steps": [
            "Conduct detailed field inspection of reported site and complaint",
            "Determine appropriate municipal corrective procedure",
            "Execute necessary field repairs or containment actions",
            "Verify site condition is restored to safe public standards",
            "Collect completion photo evidence and document field notes"
        ],
        "materials": [
            "Standard maintenance tool kit",
            "Safety cones and perimeter tape",
            "General repair materials as appropriate"
        ],
        "safety": [
            "Conduct job safety risk assessment prior to starting work",
            "Wear standard Personal Protective Equipment (PPE)",
            "Maintain clear communication with municipal dispatch"
        ]
    }
}


class WorkOrderGenerationService:
    @classmethod
    def generate_plan(
        cls,
        category: str,
        title: str,
        description: str,
        ai_recommended_action: Optional[str],
        hazards: List[str],
        severity: SeverityLevel,
        department: str
    ) -> Dict[str, Any]:
        """
        Generates a structured, actionable field-service WorkOrder plan
        using controlled category templates + incident AI analysis inputs.
        """
        cat_str = category.value if hasattr(category, 'value') else str(category)
        cat_str = cat_str.upper()

        template = CATEGORY_TEMPLATES.get(cat_str, CATEGORY_TEMPLATES["OTHER"])

        # Format actionable step list
        action_steps = list(template["action_steps"])
        if ai_recommended_action:
            action_steps.insert(0, f"Primary Focus: {ai_recommended_action}")

        recommended_action_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(action_steps)])

        # Required materials list
        materials_list = list(template["materials"])
        materials_text = "\n".join([f"• {m}" for m in materials_list])

        # Safety precautions list (augmented by detected hazards)
        safety_list = list(template["safety"])
        if hazards:
            hazard_precautions = [f"SPECIFIC HAZARD MITIGATION: Address {h.lower()}" for h in hazards]
            safety_list.extend(hazard_precautions)

        safety_text = "\n".join([f"⚠ {s}" for s in safety_list])

        return {
            "assigned_department": department,
            "recommended_action": recommended_action_text,
            "required_materials": materials_text,
            "safety_precautions": safety_text,
            "verification_required": True
        }
