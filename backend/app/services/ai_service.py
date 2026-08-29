import os
import base64
import logging
import json
from typing import Optional, Dict, Any, List
from openai import OpenAI
from app.core.config import settings
from app.core.enums import SeverityLevel, IncidentCategory
from app.schemas.dto import IncidentAnalysisResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CivicLens AI, an expert municipal civil infrastructure engineer and incident classification engine.
Your task is to analyze unstructured citizen complaint descriptions and optional photographic evidence to create a structured civic incident analysis.

Categories available:
- ROAD_HAZARD: Potholes, road cracks, manhole cover issues, asphalt damage, debris on roadway.
- STREETLIGHT: Broken light pole, unlit street lamp, flickering bulb.
- SANITATION: Overflowing garbage bins, illegal dumping, litter, uncollected waste.
- WATER_LEAK: Burst pipes, gushing water, leaking fire hydrants, clean water pooling.
- DRAINAGE: Blocked storm drains, standing flood water, clogged catch basins.
- ELECTRICAL: Exposed wires, damaged transformer box, sparks.
- PUBLIC_PROPERTY: Damaged park benches, broken playground equipment, graffiti on municipal property.
- TRAFFIC_SIGNAL: Broken traffic light, missing stop sign, turned signal pole.
- OTHER: Any civic issue not clearly fitting above categories.

Guidelines:
1. Title: Concise, clear (4 to 8 words).
2. Category: Select strictly from the supported categories.
3. Severity Level: LOW, MEDIUM, HIGH, or CRITICAL.
   - CRITICAL: Immediate direct threat to human life or major active flooding/electrical hazard.
   - HIGH: Major safety hazard, potential vehicle damage, blocked active road lane.
   - MEDIUM: Nuisance hazard, moderate infrastructure degradation, non-blocking street issue.
   - LOW: Minor aesthetic or minor property defect without immediate safety risk.
4. Reasoning: Justify severity based on safety risks, accessibility, and observable damage.
5. Hazards: List specific detected physical hazards.
6. Evidence Observations: List concrete factual observations from text/photo. If an image is provided, describe physical evidence seen. If no image, base strictly on text.
7. Confidence: Score 0.0 to 1.0 reflecting support from available evidence (lower confidence if text is vague or evidence is ambiguous).
8. Recommended Action: Actionable first-responder / dispatch instruction for municipal workers.
"""

class AIService:
    @staticmethod
    def _encode_image(image_path: str) -> Optional[str]:
        """Encodes image file to base64 string safely."""
        full_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(image_path))
        if not os.path.exists(full_path):
            full_path = image_path
            
        if not os.path.exists(full_path):
            logger.warning(f"Image path does not exist for encoding: {image_path}")
            return None
        try:
            with open(full_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            return None

    @staticmethod
    def _get_demo_fallback(description: str, image_path: Optional[str] = None) -> IncidentAnalysisResult:
        """Development fallback when AI_DEMO_MODE=true or API key is unconfigured."""
        desc_lower = description.lower()
        
        category = IncidentCategory.ROAD_HAZARD
        title = "Severe Pothole and Road Surface Damage"
        severity = SeverityLevel.HIGH
        hazards = ["Vehicle rim damage risk", "Trip hazard for pedestrians", "Swerving traffic risk"]
        observations = ["Citizen report describes physical cavity/pothole in active roadway"]
        
        if "water" in desc_lower or "pipe" in desc_lower or "leak" in desc_lower:
            category = IncidentCategory.WATER_LEAK
            title = "Pressurized Water Main Leak"
            hazards = ["Erosion of sub-base", "Water waste"]
            observations = ["Report describes water pooling/gushing"]
        elif "light" in desc_lower or "lamp" in desc_lower or "dark" in desc_lower:
            category = IncidentCategory.STREETLIGHT
            title = "Unlit Municipal Streetlight Fixture"
            severity = SeverityLevel.MEDIUM
            hazards = ["Reduced nighttime visibility"]
            observations = ["Streetlight failure reported"]
        elif "trash" in desc_lower or "garbage" in desc_lower or "dump" in desc_lower:
            category = IncidentCategory.SANITATION
            title = "Overflowing Waste Accumulation"
            severity = SeverityLevel.MEDIUM
            hazards = ["Sanitation and vector attraction risk"]
            observations = ["Accumulated trash reported"]

        if image_path:
            observations.append("Photographic evidence attached and logged for field inspection.")

        return IncidentAnalysisResult(
            category=category,
            title=f"[DEMO AI] {title}",
            normalized_description=f"Citizen reports: '{description}'. Analyzed under local DEMO_MODE fallback.",
            severity_level=severity,
            severity_reason="Assessed via DEMO MODE rule-based fallback system.",
            hazards=hazards,
            evidence_observations=observations,
            confidence=0.85 if image_path else 0.70,
            recommended_action="Dispatch field crew to inspect location and apply standard containment."
        )

    @classmethod
    async def analyze_incident(
        cls, 
        description: str, 
        image_path: Optional[str] = None
    ) -> IncidentAnalysisResult:
        """
        Main AI Analysis Engine: Analyzes text and optional image using OpenAI structured outputs.
        """
        # 1. Check Demo Mode or Missing API Key
        if settings.AI_DEMO_MODE or not settings.OPENAI_API_KEY:
            logger.info("Using AI_DEMO_MODE fallback for incident analysis.")
            return cls._get_demo_fallback(description, image_path)

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]

            user_content: List[Dict[str, Any]] = [
                {"type": "text", "text": f"Citizen Complaint Description: {description}"}
            ]

            if image_path:
                base64_img = cls._encode_image(image_path)
                if base64_img:
                    ext = os.path.splitext(image_path)[1].lower()
                    mime_type = "image/png" if ext == ".png" else "image/jpeg"
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_img}"
                        }
                    })

            messages.append({"role": "user", "content": user_content})

            # Call OpenAI Structured Outputs
            completion = client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL,
                messages=messages,
                response_format=IncidentAnalysisResult,
                temperature=0.2
            )

            result = completion.choices[0].message.parsed
            if not result:
                raise ValueError("Received null parsed response from OpenAI API.")

            return result

        except Exception as e:
            logger.error(f"OpenAI API analysis failed: {e}. Falling back to error response.")
            raise RuntimeError(f"AI Analysis Service Failed: {str(e)}")

    @staticmethod
    async def route_department(category: str, description: str) -> str:
        """Determines responsible municipal department via canonical DepartmentRoutingService."""
        from app.services.priority_routing_service import DepartmentRoutingService
        res = DepartmentRoutingService.route_incident(category)
        return res["assigned_department"]

    @staticmethod
    async def generate_work_order(
        incident_id: str,
        title: str,
        category: str,
        description: str,
        department: str
    ) -> Dict[str, Any]:
        """Generates structured work order recommendations."""
        return {
            "incident_id": incident_id,
            "assigned_department": department,
            "recommended_action": f"Dispatch field crew for inspection and repair of {title}.",
            "required_materials": "Standard maintenance kit, traffic cones, protective gear.",
            "safety_precautions": "Position high-visibility signs 50m prior to work zone."
        }
