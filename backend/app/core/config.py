import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CivicLens API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]
    
    # Database
    DATABASE_URL: str = "sqlite:///./civiclens.db"
    
    # Uploads
    UPLOAD_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads"))
    
    # OpenAI Config Placeholders (for AI phase)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_DEMO_MODE: bool = False

    # Duplicate Detection Config
    DUPLICATE_RADIUS_METERS: float = 100.0
    DUPLICATE_CONFIDENCE_THRESHOLD: float = 0.80
    WEIGHT_SEMANTIC: float = 0.55
    WEIGHT_GEOGRAPHIC: float = 0.35
    WEIGHT_CATEGORY: float = 0.10

    # Priority Scoring Weights (Sum to 1.0)
    PRIORITY_WEIGHT_SEVERITY: float = 0.30
    PRIORITY_WEIGHT_SAFETY_RISK: float = 0.25
    PRIORITY_WEIGHT_REPORT_VOLUME: float = 0.15
    PRIORITY_WEIGHT_DURATION: float = 0.10
    PRIORITY_WEIGHT_PUBLIC_IMPACT: float = 0.10
    PRIORITY_WEIGHT_EVIDENCE_CONFIDENCE: float = 0.10

    # Priority Thresholds
    PRIORITY_P1_THRESHOLD: int = 80
    PRIORITY_P2_THRESHOLD: int = 65
    PRIORITY_P3_THRESHOLD: int = 45

    # Notification & Courier Config
    NOTIFICATION_MODE: str = "demo" # "demo" or "courier"
    COURIER_API_KEY: str = ""
    COURIER_NOTIFICATION_TEMPLATE_ID: str = ""

    # Hotspot Intelligence Config
    HOTSPOT_RADIUS_METERS: float = 250.0
    HOTSPOT_MIN_INCIDENTS: int = 3
    HOTSPOT_MIN_REPORTS: int = 5




    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
