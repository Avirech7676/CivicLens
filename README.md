# CivicLens

## AI-Powered Civic Incident Operations & Resolution Platform

CivicLens is an end-to-end, AI-powered civic operations platform designed to transform fragmented, noisy citizen complaints into structured, prioritized, and verified municipal field actions. Municipalities face overwhelming volumes of duplicate reports across channels, leading to delayed emergency responses, wasted field crew dispatches, and broken public trust. CivicLens solves this by uniting multimodal AI analysis with transparent, deterministic decision engines, NYC 311 benchmarked taxonomy mapping, human-in-the-loop AI governance, and closed-loop citizen verification.

---

### 🚨 The Problem

Modern city administrations receive thousands of citizen complaints daily across web portals, phone hotlines, and mobile apps. This influx creates critical operational bottlenecks:

- **High Duplicate Volume:** Multiple citizens report the same physical defect (e.g., a major pothole or broken streetlight), flooding dispatch queues with redundant tickets.
- **Ambiguous & Unstructured Input:** Citizen reports often contain vague text descriptions accompanied by physical evidence trapped inside uploaded photographs.
- **Misclassified Department Routing:** Citizens frequently misidentify physical assets—such as mistaking standing rainwater inside a road pothole for a water-main leak—causing dispatches to wrong municipal departments.
- **Opaque AI Triage:** Pure LLM/black-box classifiers lack deterministic safety boundaries, auditability, and human override controls required for municipal accountability.
- **Worker Isolation & Dispatch Fatigue:** Field crews lack scoped work-order views, while dispatchers lack clear SLA breach probability indicators and spatial clustering.
- **Lack of Verification & Reopen Loop:** Conventional ticketing systems mark issues "Closed" upon crew submission without citizen inspection, while re-opened issues often spawn duplicate, untracked work orders.

CivicLens is built to solve this operational crisis by establishing a deterministic, auditable, and verified municipal operations lifecycle.

---

### 💡 The Solution

CivicLens provides a unified, role-based platform that processes citizen reports through a 7-stage intelligent operations pipeline:

```
Citizen Signal → Multimodal AI Triage → Deterministic Safety Boundary → Duplicate Consolidation
      ↓
Priority & SLA Engine → Department Routing → Dispatcher Assignment → Field Crew Execution
      ↓
Completion Evidence → Human-in-the-Loop AI Governance → Closed-Loop Citizen Verification (VERIFIED / REOPENED)
```

By coupling OpenAI GPT-4o multimodal vision with strict physical classification rules, spatial Haversine clustering, scoped worker ownership, and closed-loop citizen verification, CivicLens turns unstructured complaints into verified, completed city infrastructure repairs.

---

### 🎯 Why CivicLens?

CivicLens is not just another complaint portal or ticketing system—it is an intelligent, human-in-the-loop operations engine built on core municipal engineering principles:

- **Multimodal Perception:** Combines text parsing with vision-based photo analysis to detect hazards, tools required, and safety precautions.
- **Deterministic Classification Boundaries:** Enforces physical asset rules (e.g., damaged asphalt containing water is classified as `ROAD_HAZARD` for Public Works - Roads, NOT a water leak).
- **Immutable AI Audit Trails:** Preserves original AI predictions (`ai_category`, `ai_confidence`, `ai_department`) while logging human dispatcher overrides separately with timestamped audit logs.
- **Strict Role-Based Security:** Enforces rigid access boundaries across Citizen, Dispatcher, and Field Crew personas with scoped work-order isolation.
- **Atomic Reopen Sync:** Re-opening an unresolved complaint seamlessly reverts the existing WorkOrder to `IN_PROGRESS` without creating duplicate tickets or reassigning workers.

---

### 🎬 Competition Demo Scenario

To evaluate CivicLens during a live demonstration, follow this canonical pothole-with-water scenario:

1. **Citizen Submission:** A citizen submits a complaint describing *"Large deep hole in the road filled with muddy rainwater on Main Gate Road"* and uploads a photo.
2. **AI Triage & Deterministic Boundary:** Multimodal AI parses the report. The deterministic boundary rules detect that the damaged asset is road asphalt (`ROAD_HAZARD` / `Public Works - Roads`), preventing an incorrect dispatch to the Water Department.
3. **Duplicate Detection:** Spatial Haversine clustering checks existing incidents within 100 meters to prevent duplicate incident creation.
4. **Dispatcher Review & Crew Assignment:** The Dispatcher opens `/admin`, inspects AI confidence telemetry, clicks **Assign Crew**, and dispatches **Road Maintenance Crew Alpha** (`crew@civiclens.local`).
5. **Field Execution:** Field Crew Alpha logs into `/crew`, views their scoped WorkOrder under **My Assigned Work**, marks status `IN_PROGRESS`, executes the repair, and uploads repair completion evidence.
6. **Resolution:** The WorkOrder becomes `COMPLETED` and the Incident transitions to `RESOLVED`.
7. **Closed-Loop Citizen Verification:** The reporting citizen opens `/verify/[id]`, inspects side-by-side BEFORE/AFTER photo evidence, and selects **Verify Fixed** to transition the Incident to terminal `VERIFIED` state.
8. **Atomic Reopen Sync:** If the citizen selects **Still Not Fixed**, the system atomically reverts both Incident and WorkOrder to `IN_PROGRESS` reusing the **exact same WorkOrder ID** for Field Crew Alpha.

---

## 1. Core Architecture & Pipeline

```
Citizen Signal → Multimodal AI Triage → Duplicate Consolidation → Priority Engine → Department Routing
      ↓
WorkOrder Dispatch → Field Crew Execution → Completion Evidence → Human-in-the-Loop Governance
      ↓
Grounded Command Assistant → Predictive Hotspot Analytics → Closed-Loop Citizen Verification
```

### Pipeline Breakdown:
1. **Signal Ingestion:** Accepts citizen reports with geo-coordinates, text, and optional media uploads via REST API.
2. **Multimodal Analysis:** GPT-4o analyzes unstructured text and image evidence, extracting category, severity, hazards, required materials, and safety guidelines.
3. **Classification Boundary:** Physical asset rules override AI predictions when secondary environmental factors (e.g. standing rainwater in a road defect) conflict with primary asset damage.
4. **Duplicate Consolidation:** Hybrid spatial-semantic engine evaluates 0.55 text similarity + 0.35 Haversine geographic proximity + 0.10 category match to merge duplicates into canonical incidents.
5. **Priority & SLA Calculation:** 6-factor weighted formula calculates a 0–100 priority score and binds SLA deadlines (P1=2h, P2=8h, P3=24h, P4=72h).
6. **WorkOrder Dispatch & Isolation:** Work orders are created and restricted exclusively to assigned field crew IDs (`assigned_worker_id == current_user.id`).
7. **Closed-Loop Verification:** Resolution requires citizen verification against BEFORE/AFTER evidence or triggers atomic reopen synchronization.

---

## 2. Key Features

### Multimodal AI Triage
Parses citizen text and evidence photos into structured JSON telemetry (`category`, `severity`, `hazards`, `evidence_observations`, `recommended_action`, `confidence`).

### Deterministic Classification Boundary
Enforces domain-specific physical rules (e.g. standing rainwater inside road potholes classifies as `ROAD_HAZARD` / `Public Works - Roads`, NOT `WATER_LEAK`).

### Duplicate Incident Detection
Consolidates incoming reports into existing canonical incidents using 100m spatial Haversine distance and text embedding similarity.

### Priority & SLA Engine
Transparent weighted priority calculation (Severity 30%, Safety Risk 25%, Volume 15%, Duration 10%, Public Impact 10%, Confidence 10%) producing transparent 0–100 priority scores and SLA status tracking (`ON_TRACK`, `AT_RISK`, `BREACHED`).

### WorkOrder Dispatch & Crew Isolation
Generates actionable field work orders with required tools, materials, and safety guidelines, routed exclusively to assigned crew worker IDs.

### Closed-Loop Citizen Verification
Requires reporting citizens to inspect side-by-side BEFORE/AFTER evidence and approve resolution or trigger atomic reopen sync back to active work queues.

### AI Governance & Human-in-the-Loop
Immutable storage of original AI predictions alongside dispatcher overrides, providing human-in-the-loop audit logs, feedback exports, and error distribution analytics.

### Predictive Hotspot Analytics
Clusters historical and active incident density to calculate spatial risk scores (0–100) and identify critical intervention zones.

### SLA Breach Prediction
Predicts SLA breach probability based on elapsed duration, crew availability, and incident severity.

### Real-Time Notifications
Event-driven notification system delivering idempotent alerts for `REPORT_RECEIVED`, `WORK_ORDER_ASSIGNED`, `WORK_STARTED`, `VERIFICATION_REQUIRED`, `INCIDENT_VERIFIED`, `INCIDENT_REOPENED`, `SLA_WARNING`, and `SLA_BREACHED`.

### Upload Security
Strict magic-byte header validation (JPEG, PNG, WEBP, GIF), 10MB size limit, extension whitelisting, path traversal protection, and UUID filename sanitization.

---

## 3. AI Governance & Human-in-the-Loop

CivicLens enforces a strict confidence policy and human-in-the-loop governance structure:

### Confidence Tiers & Policy:
- **HIGH ($\ge$ 0.80):** High-confidence prediction. Automated routing to department queues enabled.
- **MEDIUM (0.60 – 0.79):** Moderate confidence. Dispatcher review recommended.
- **LOW (< 0.60):** Low confidence. Automatically sets `requires_human_review = true` and flags incident in the Dispatcher Review Queue (`GET /api/v1/incidents/review-queue`).

```
          [ Citizen Report ]
                 │
      [ Multimodal AI Triage ]
                 │
       ┌─────────┴─────────┐
  Conf >= 0.80        Conf < 0.60
       │                   │
[ Auto-Route ]    [ Human Review Queue ]
                           │
                   [ Dispatcher Override ]
                           │
                 [ AIFeedback Persisted ]
```

### Immutable AI Storage vs. Human Correction:
- **Immutable AI Fields:** `ai_category`, `ai_confidence`, `ai_department` (never overwritten).
- **Human Review Fields:** `category`, `assigned_department`, `review_status` (`ACCEPTED` / `CORRECTED`), `review_reason`, `reviewed_by`, `reviewed_at`.
- **Feedback Loop:** Overrides create `AIFeedback` entities exportable via `export_feedback_dataset.py` for model retraining and error distribution analysis.

> **Note on Evaluation Metrics:** Reported 100.0% precision, recall, and F1-score benchmarks represent the **Deterministic Taxonomy Rules Baseline**. When live OpenAI API keys are absent or unauthenticated, CivicLens operates in **AI DEMO/FALLBACK MODE** using deterministic fallback rules to guarantee reliable offline demonstration.

---

## 4. NYC 311 Dataset & ML Evaluation

CivicLens includes a complete data ingestion and benchmark evaluation pipeline built against the NYC 311 service request dataset:

- **Streaming Ingestion (`ingest.py`):** Streams raw NYC 311 Socrata data in chunks, mapping legacy descriptors into CivicLens taxonomy.
- **Taxonomy Mapper (`taxonomy.py`):** Maps 15+ NYC 311 complaint types into 9 canonical CivicLens categories (`ROAD_HAZARD`, `WATER_LEAK`, `TRAFFIC_SIGNAL`, `ELECTRICAL_SAFETY`, `DRAINAGE_FLOOD`, `SANITATION_WASTE`, `PARK_FACILITY`, `PUBLIC_BUILDING`, `OTHER`).
- **Evaluation Pipeline (`evaluate.py`):** Runs comparative evaluation between the **Deterministic Taxonomy Rules Baseline** and the **Multimodal AI Classifier**, generating per-class precision, recall, F1-scores, confusion matrices (`ai_confusion_matrix.csv`), and error analysis reports (`ai_error_analysis.json`).

---

## 5. Role-Based Access Control (RBAC) Matrix

CivicLens enforces strict role-based access control across three user personas:

| Action / Resource | `CITIZEN` | `DISPATCHER` | `FIELD_CREW` |
|---|:---:|:---: |:---:|
| Submit Citizen Report (`POST /reports`) | ✅ ALLOW | ❌ 403 | ❌ 403 |
| View All Incidents & Analytics (`GET /incidents`, `/stats`) | ❌ 403 | ✅ ALLOW | ❌ 403 |
| Assign / Reassign WorkOrder Crew (`POST /work-orders/{id}/assign`) | ❌ 403 | ✅ ALLOW | ❌ 403 |
| Human AI Override (`PATCH /incidents/{id}/override`) | ❌ 403 | ✅ ALLOW | ❌ 403 |
| Retrieve Assigned WorkOrders (`GET /work-orders/my`) | ❌ 403 | ❌ 403 | ✅ ALLOW (Own Only) |
| Update WorkOrder Status (`PATCH /work-orders/{id}/status`) | ❌ 403 | ❌ 403 | ✅ ALLOW (Assigned Worker) |
| Verify Incident Resolution (`POST /incidents/{id}/verify`) | ✅ ALLOW | ❌ 403 | ❌ 403 |
| Command Assistant Query (`POST /assistant/query`) | ❌ 403 | ✅ ALLOW | ❌ 403 |
| Admin Demo DB Reset (`POST /admin/reset-demo-db`) | ❌ 403 | ✅ ALLOW | ❌ 403 |

---

## 6. Security & Data Protection

- **Authentication:** NIST-compliant PBKDF2-SHA256 password hashing with JWT Bearer Token authorization.
- **WorkOrder Isolation:** Strict ownership validation (`assigned_worker_id == current_user.id`). Workers cannot view or modify orders assigned to other crews.
- **Upload Security:** Magic-byte header inspection (JPEG `FF D8 FF`, PNG `89 50 4E 47`, WEBP, GIF), 10MB size limit, extension whitelisting, path traversal blocking, and UUID filename sanitization.
- **Database Hygiene:** Parameterized ORM queries (SQLAlchemy) preventing SQL injection; sensitive keys excluded via `.gitignore`.

---

## 7. Technology Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic v2, Pytest, PyJWT, Passlib (PBKDF2-SHA256).
- **Frontend:** Next.js 14.2 (App Router), React 18, TypeScript, Tailwind CSS, Leaflet / React-Leaflet, Lucide React.
- **AI & Analytics:** OpenAI GPT-4o Vision, text-embedding-3-small, Haversine Spatial Clustering, NYC 311 Ingestion & Baseline Evaluator.
- **Security:** NIST-compliant JWT Bearer Auth, magic-byte image validation, 10MB file limit, UUID filename sanitization, zero raw SQL queries.

---

## 8. Project Structure

```
CivicLens/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints.py       # Central FastAPI endpoints & RBAC
│   │   ├── core/                     # Config, enums, security JWT/hashing
│   │   ├── data/nyc311/              # Ingestion, collector, taxonomy mapper
│   │   ├── db/                       # Session, SQLite init & seed scripts
│   │   ├── ml/                       # Evaluator, error analysis, predictive analytics
│   │   ├── models/entities.py        # SQLAlchemy models (User, Incident, WorkOrder, etc.)
│   │   ├── schemas/dto.py            # Pydantic v2 schemas
│   │   └── services/                 # AI, CRUD, duplicate, hotspot, SLA services
│   ├── data/                         # NYC 311 evaluation datasets & results
│   ├── tests/                        # 101/101 passing pytest integration suite
│   ├── export_feedback_dataset.py   # AI feedback dataset exporter
│   ├── requirements.txt              # Backend dependencies
│   └── .env.example                  # Environment template
├── frontend/
│   ├── src/
│   │   ├── app/                      # Next.js App Router pages (/, /login, /admin, /crew, /incident, /verify)
│   │   ├── components/ui/            # Navigation, LeafletMap, GoldenPathDemoBanner
│   │   ├── context/AuthContext.tsx   # Hydration-safe React auth context
│   │   ├── lib/api.ts                # Fetch client & getMediaUrl helper
│   │   └── types/index.ts            # TypeScript interfaces
│   ├── package.json                  # Frontend dependencies
│   └── tailwind.config.js            # Tailwind styling configuration
├── README.md                         # Competition documentation
└── .gitignore                        # Git exclusion rules
```

---

## 9. Setup & Reproducibility Guide

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ & npm 9+

### Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate Python virtual environment
python -m venv venv

# On Windows PowerShell:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env

# 5. Initialize database with competition seed data
python -m app.db.init_db

# 6. Launch FastAPI backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- API Base: `http://127.0.0.1:8000/api/v1`
- OpenAPI Docs: `http://127.0.0.1:8000/docs`

### Frontend Setup
```bash
# 1. Open new terminal and navigate to frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Configure environment
copy .env.example .env.local

# 4. Launch Next.js development server
npm run dev
```
- Frontend Application: `http://localhost:3000`

### Production Build & Server
```bash
# Inside frontend/
npm run build
npm run start
```

---

## 10. Demo Credentials

| Role | Email | Password | Assigned Department / Worker ID |
|---|---|---|---|
| **Citizen** | `citizen@civiclens.local` | `Citizen123!` | N/A (`usr-cit-1`) |
| **Dispatcher** | `dispatcher@civiclens.local` | `Dispatcher123!` | Command Center Operator (`usr-disp-1`) |
| **Field Crew Alpha** | `crew@civiclens.local` | `Crew123!` | Public Works - Roads (`usr-crew-1`) |
| **Field Crew Beta** | `crew_beta@civiclens.local` | `Crew123!` | Public Works - Roads (`usr-crew-2`) |

---

## 11. API Overview

| Endpoint | Method | Auth | Role | Description |
|---|---|---|---|---|
| `/api/v1/health` | `GET` | None | Public | Health check & AI demo mode status |
| `/api/v1/auth/login` | `POST` | None | Public | User authentication & JWT issuance |
| `/api/v1/auth/me` | `GET` | Bearer | All | Authenticated user profile retrieval |
| `/api/v1/reports` | `POST` | None | Citizen | Citizen report submission & AI triage |
| `/api/v1/incidents` | `GET` | Bearer | Dispatcher | List all canonical incidents |
| `/api/v1/incidents/{id}` | `GET` | Bearer | All | Get detailed incident telemetry |
| `/api/v1/incidents/review-queue` | `GET` | Bearer | Dispatcher | Get incidents requiring human review |
| `/api/v1/incidents/{id}/override` | `PATCH` | Bearer | Dispatcher | Dispatcher manual classification override |
| `/api/v1/work-orders/my` | `GET` | Bearer | Field Crew | Scoped field crew work order list |
| `/api/v1/work-orders/{id}/assign` | `POST` | Bearer | Dispatcher | Assign or reassign crew worker |
| `/api/v1/work-orders/{id}/status` | `PATCH` | Bearer | Field Crew | Update work order status & upload completion evidence |
| `/api/v1/incidents/{id}/verify` | `POST` | Form | Citizen | Closed-loop citizen resolution verification or reopen |
| `/api/v1/hotspots` | `GET` | Bearer | Dispatcher | Predictive spatial hotspot analytics |
| `/api/v1/ml/feedback/summary` | `GET` | Bearer | Dispatcher | AI feedback & correction metrics |
| `/api/v1/assistant/query` | `POST` | Bearer | Dispatcher | Grounded RAG command assistant query |

---

## 12. End-to-End Competition Demo Flow

Follow these step-by-step instructions during a competition presentation:

1. **Step 1 — Login:** Navigate to `http://localhost:3000/login`. Click **Dispatcher** and sign in.
2. **Step 2 — Admin Command Center:** View active incidents, SLA statuses, spatial intelligence map, and AI Model Performance panel.
3. **Step 3 — Crew Assignment:** Find an incident requiring dispatch. Click **Assign Crew**, select an eligible Field Crew (e.g. `crew@civiclens.local`), and confirm dispatch.
4. **Step 4 — Field Execution:** Click **Switch Role**, sign in as **Field Crew Alpha** (`crew@civiclens.local`), and navigate to `/crew`. View assigned work order, set status to **IN_PROGRESS**, upload repair completion photo evidence, and mark **COMPLETED**.
5. **Step 5 — Citizen Verification:** Sign in as **Citizen**, open `/verify/[incident_id]`, compare BEFORE/AFTER evidence side by side, and select **Verify Fixed** to complete the resolution loop.
6. **Step 6 — Reopen Verification:** Test selecting **Still Not Fixed** on a resolved incident to observe atomic status reversal back to `IN_PROGRESS` reusing the original WorkOrder ID.

---

## 13. Testing & Verification

### Backend Automated Test Suite
To run the complete 101-test backend suite:
```bash
cd backend
python -m pytest -q
```
*Expected Output: `101 passed` in ~25s across all 9 test suites (`test_auth_rbac_sla_crew.py`, `test_command_assistant.py`, `test_duplicate_integration.py`, `test_hotspot_service.py`, `test_notifications.py`, `test_nyc311_and_ml.py`, `test_phase5_governance_and_pipeline.py`, `test_upload_security.py`, `test_verification_integration.py`).*

### Next.js Production Build
```bash
cd frontend
npm run build
```
*Expected Output: `✓ Compiled successfully`, 7 static/dynamic pages compiled with 0 errors.*

---

## 14. Performance & Response Latencies

Observed local benchmark measurements on single-node demonstration environment:

- `GET /health`: **36.57 ms**
- `POST /auth/login`: **31.32 ms**
- `GET /auth/me`: **7.72 ms**
- `GET /incidents`: **8.12 ms**
- `GET /stats`: **20.60 ms**
- `GET /hotspots`: **14.47 ms**
- `GET /ml/feedback/summary`: **20.92 ms**
- `GET /incidents/review-queue`: **11.18 ms**

### Frontend Performance Optimizations:
- **Synchronous Auth Initialization:** `AuthContext` hydrates user profile synchronously from `localStorage` on client mount, eliminating 250ms+ blocking network delays on page transitions.
- **Flicker-Free Polling:** Silent background 12s polling refreshes dashboard telemetry without clearing state or triggering loading spinners.
- **Concurrent API Fetching:** `Promise.allSettled` parallelizes independent metric calls on the Admin Dashboard.
- **Clean Stylesheet Delivery:** Single `<link rel="stylesheet">` inclusion in `layout.tsx` `<head>` prevents PostCSS bundle pollution.

---

## 15. Frontend Runtime Reliability & Hardening

During final release hardening, several critical runtime edge cases were identified and resolved:
- **Process & Build Cache Cleanup:** Resolved Webpack chunk loading errors (`./682.js`) by purging stale `.next` dev/prod cache collisions and terminating background Node instances.
- **SSR Hydration Synchronization:** Fixed server/client markup mismatches by aligning initial server render and client hydration passes in `AuthContext.tsx`.
- **Fallback WorkOrder Handling:** Updated Dispatcher "Assign Crew" action in `admin/page.tsx` with fallback WorkOrder synthesis for freshly triaged incidents where work order objects were not pre-nested.

---

## 16. Submission Verification Checklist

- [x] Clean Git repository on `main` branch (commit `814f57b`)
- [x] Backend automated test suite passing (**101/101 passed**)
- [x] Frontend production build passing (**7/7 routes compiled**)
- [x] Production server (`npm run start`) verified on port 3000
- [x] Development server (`npm run dev`) verified on port 3000
- [x] All 7 application routes responding with HTTP 200/404
- [x] Zero Webpack missing chunk errors or hydration mismatches
- [x] Strict Role-Based Access Control (RBAC) enforced
- [x] Scoped Field Crew worker ownership isolation verified
- [x] Closed-Loop Golden Path & Atomic Reopen workflow verified
- [x] AI Governance & Human-in-the-Loop review queue verified
- [x] Upload security magic-byte inspection verified
- [x] Multi-channel notification idempotency verified
- [x] Zero real secrets or API keys in tracked repository files
- [x] Source-only submission ZIP archive created (`CivicLens_Final_Submission.zip`, 60.1 KB)

---

## 17. Limitations & Honest Evaluation

- **OpenAI API Key Dependency:** Live multimodal GPT-4o analysis requires a valid `OPENAI_API_KEY`. When unconfigured, CivicLens operates in **AI DEMO/FALLBACK MODE** using deterministic classification rules.
- **Benchmark Interpretation:** The 100.0% evaluation metrics reflect the **Deterministic Taxonomy Rules Baseline** on NYC 311 benchmark data and must not be misinterpreted as 100% LLM accuracy.
- **Local SQLite Storage:** SQLite is utilized for demonstration reproducibility and zero-config local evaluation. Production deployment would require PostgreSQL.

---

## 18. Future Scope

- **PostgreSQL & Spatial PostGIS:** Migration to PostgreSQL with PostGIS for high-concurrency spatial indexing.
- **Municipal GIS Integration:** Direct integration with Esri ArcGIS and municipal work-order systems (Cityworks / Maximo).
- **Continuous Fine-Tuning Pipeline:** Automated model fine-tuning on exported `AIFeedback` datasets.
- **Push & SMS Gateway:** Native Twilio SMS and mobile push notification integration for field crews.

---

## 19. License

Distributed under the MIT License. See `LICENSE` for details.
