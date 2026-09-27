# SPANDAN AI — Autonomous Civic Grievance Platform

> **"The citizen submits once. SPANDAN continues working after the citizen leaves."**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Tests](https://img.shields.io/badge/Tests-311%20Passed%20(100%25)-success)](https://pytest.org)

SPANDAN AI (Agent X) is an agentic, multi-tier civic grievance redressal system built for Indian municipalities (e.g., Greater Hyderabad Municipal Corporation). It eliminates administrative friction for citizens while actively enforcing departmental SLAs and executive accountability through autonomous background agents.

---

## 1. System Architecture & Workflow

```mermaid
flowchart TD
    subgraph CitizenExperience ["Citizen Intake & Verification"]
        A["Citizen Voice / Text Input<br/>(Telugu, Tamil, Kannada, Hindi, English)"] --> B["Multi-Signal Language Identification"]
        B --> C["Strict Pre-Validation Engine"]
        C -->|"1. Gibberish / Keyboard Smashing"| V1{"Valid Words?"}
        C -->|"2. Satellite GPS Location"| V2{"Coordinates Present?"}
        C -->|"3. Photographic Evidence"| V3{"Camera Photo Attached?"}
        
        V1 & V2 & V3 -- "All Verified" --> D["PostgreSQL Problem Matcher"]
    end

    subgraph PostgresEngine ["Municipal Database Cross-Check"]
        D --> E["Query Live Complaint Frequencies (PostgreSQL)"]
        D --> F["Match Historical Locality Incidents (ILIKE)"]
        D --> G["Rank Problem-Related Alternatives"]
        D --> H["Generate Bilingual Administrative Draft"]
    end

    subgraph CitizenConfirmation ["Citizen Review & Confirmation"]
        H --> I["Review Problem Options & Confirm Draft UI"]
        I --> J["Citizen Clicks: '✓ Confirm & Lodge Official Grievance'"]
    end

    subgraph AutonomousOrchestration ["Autonomous Background Pipeline"]
        J --> K["Fast Acknowledgement (FastAck: SPN-XXXXXX)"]
        K --> L["Background Autonomous Workflow Pipeline"]
        L --> M["Location Reverse Geocoding (Nominatim)"]
        M --> N["Department Grounding (RAG ChromaDB)"]
        N --> O["Administrative Grievance Filing"]
        O --> P["48-Hour SLA Watchdog Monitoring"]
    end

    subgraph GovernanceWorkflow ["Authority Review & Escalation Workflow"]
        P --> Q["Dispatch Review Email to AUTHORITY_REVIEW_EMAIL<br/>(impardhu3127@gmail.com)"]
        
        Q --> R{"Local Authority Decision"}
        
        R -- "Click ACCEPT" --> S["Status: ACCEPTED_BY_AUTHORITY<br/>(Field Repairs Scheduled)"]
        
        R -- "Click REJECT" --> T["Status: REJECTED &rarr; ESCALATED"]
        T --> U["Dispatch Escalation Email to HIGHER_OFFICIAL_EMAIL<br/>(guttulagowthamgandhi@gmail.com)"]
        
        U --> V{"Higher Official Decision"}
        V -- "Click ACCEPT" --> W["Status: ACCEPTED_BY_HIGHER_AUTHORITY<br/>(Executive Priority Enforcement)"]
    end
```

---

## 2. Core Capabilities

### A. Multi-Signal Language Identification
- Designed specifically for Indian multilingual scenarios: **Telugu, Tamil, Kannada, Hindi, and English**.
- Combines audio signals, n-gram script heuristics, regional vocabulary markers, and fallback LLM verification.
- Gracefully handles accents, dialectal code-switching, and ambient background noise.

### B. Mandatory Verification Engine
- **Gibberish & Nonsense Rejection**: Rejects keyboard smashing, non-words, and irrelevant text with helpful, citizen-friendly prompts.
- **Mandatory Live GPS**: Demands verified satellite coordinates (`latitude`, `longitude`) via device GPS or location picker.
- **Mandatory Photo Proof**: Requires photographic evidence of the hazard before filing.

### C. PostgreSQL Problem Matcher & Database Cross-Check
- Cross-references incoming grievances against real-time database records in PostgreSQL.
- Computes occurrence frequencies across civic categories (Road Damage, Streetlight Outage, Drainage Overflow, Water Supply Leakage, Sanitation, Broken Infrastructure).
- Synthesizes a structured administrative draft including bilingual subjects, jurisdictional routing, SLA resolution timeframes, and formal prayer for relief.

### D. Citizen Draft Confirmation
- The citizen reviews the detected problem, selects from related problem options, inspects the administrative draft, and explicitly clicks **"✓ Confirm & Lodge Official Grievance"**.

### E. Autonomous Background Pipeline & Watchdog
- **Fast Acknowledgement (`FastAck`)**: Returns within 200ms with a unique permanent tracking receipt (`SPN-XXXXXX`).
- Background pipeline executes Intake $\rightarrow$ Location Geocoding $\rightarrow$ RAG Classification $\rightarrow$ Drafting $\rightarrow$ Government Filing $\rightarrow$ SLA Monitoring.
- Watchdog agent continuously tracks the 48-hour resolution clock.

### F. Authority Review & Escalation Workflow
- **Demo Email Configuration**:
  - `AUTHORITY_REVIEW_EMAIL`: Configurable local authority reviewer (`impardhu3127@gmail.com`).
  - `HIGHER_OFFICIAL_EMAIL`: Configurable executive escalation recipient (`guttulagowthamgandhi@gmail.com`).
- **4-Step Governance Flow**:
  1. New complaint filed $\rightarrow$ Review email dispatched to Authority.
  2. Authority clicks **ACCEPT** $\rightarrow$ `ACCEPTED_BY_AUTHORITY`.
  3. Authority clicks **REJECT** $\rightarrow$ `REJECTED` $\rightarrow$ `ESCALATED` $\rightarrow$ Escalation email dispatched to Higher Official.
  4. Higher Official clicks **ACCEPT** $\rightarrow$ `ACCEPTED_BY_HIGHER_AUTHORITY`.
- **Interactive Official Mailbox** (`http://localhost:5173/official-mailbox`):
  - In-app administrative console displaying live incoming emails for both Authority and Higher Official with one-click actions.

---

## 3. Technology Stack

| Layer | Technologies |
| --- | --- |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, Uvicorn, Pydantic v2 |
| **Database** | PostgreSQL 16 (`agentx` database), SQLite (fallback) |
| **Knowledge Base (RAG)** | ChromaDB (embedded), hashing / deterministic vector search |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons |
| **Email & Messaging** | Python `smtplib` (STARTTLS), MIME-multipart, In-App Notification Service |
| **Location & GIS** | OpenStreetMap Nominatim reverse geocoding, satellite GPS resolver |

---

## 4. Getting Started

### Prerequisites
- **Python 3.11+** (Python 3.12 recommended)
- **Node.js 20+** and `npm`
- **PostgreSQL 14+** (running on port 5432)

### 1. Repository Setup & Environment Configuration
```bash
# Clone the repository
git clone https://github.com/balugowtham68/agentx-civic-grievance.git
cd agentx-civic-grievance

# Create .env from template
cp .env.example .env
```

Edit `.env` with your local database URL and email configuration:
```env
APP_ENV=development
LOG_LEVEL=INFO

# PostgreSQL Connection
DATABASE_URL=postgresql://postgres:AgentX2026!@localhost/agentx

# Frontend Origin
FRONTEND_ORIGIN=http://localhost:5173

# Demo Email Configuration
AUTHORITY_REVIEW_EMAIL=impardhu3127@gmail.com
HIGHER_OFFICIAL_EMAIL=guttulagowthamgandhi@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=impardhu3127@gmail.com
SMTP_PASSWORD=mine3127
SMTP_FROM_EMAIL=impardhu3127@gmail.com
APP_BASE_URL=http://localhost:8000
```

> [!TIP]
> **Gmail SMTP Delivery Note**: To deliver emails directly to Gmail inboxes over SMTP, Google requires a **16-character App Password** (created at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)). When using standard passwords, the system uses the built-in **Official Mailbox Portal** (`/official-mailbox`) for live demo execution.

### 2. Backend Installation & Start
```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at: **`http://localhost:8000/docs`**

### 3. Frontend Installation & Start
```bash
cd ../frontend
npm install
npm run dev
```
Frontend Web Portal will be available at: **`http://localhost:5173`**

---

## 5. Live Demo Walkthrough

1. **Citizen Submission**:
   - Open **`http://localhost:5173`**.
   - Speak or type: *"Dangerous broken pothole on 100 Feet Road damaging vehicles"*.
   - Click **"Use Current Location"** (or permit browser GPS).
   - Attach or capture photo proof.
   - Click **"Review & Confirm Draft"**.

2. **PostgreSQL Cross-Check & Citizen Confirmation**:
   - View live database matching statistics and category occurrence badge.
   - Switch between problem-related options (e.g., Road Damage vs Streetlight Outage).
   - Inspect the generated bilingual administrative draft.
   - Click **"✓ Confirm & Lodge Official Grievance"**.

3. **Fast Acknowledgement & Timeline**:
   - A tracking receipt (`SPN-XXXXXX`) is generated instantly.
   - Watch the autonomous pipeline transition stages: `RECEIVED` $\rightarrow$ `UNDERSTOOD` $\rightarrow$ `CLASSIFIED` $\rightarrow$ `DRAFTED` $\rightarrow$ `FILED` $\rightarrow$ `MONITORING`.

4. **Authority Review & Escalation Execution**:
   - Open **Official Mailbox**: **`http://localhost:5173/official-mailbox`**.
   - Under **Local Authority Inbox** (`impardhu3127@gmail.com`):
     - Click **[✓ Accept Complaint]** $\rightarrow$ Status changes to `ACCEPTED_BY_AUTHORITY`.
     - Or click **[✗ Reject & Escalate]** $\rightarrow$ Status changes to `REJECTED` $\rightarrow$ `ESCALATED`.
   - Switch to **Higher Official Escalations Tab** (`guttulagowthamgandhi@gmail.com`):
     - Click **[✓ Accept Escalated Grievance]** $\rightarrow$ Status changes to `ACCEPTED_BY_HIGHER_AUTHORITY`.

---

## 6. Key API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/complaints/detect-options` | Cross-checks PostgreSQL, returns detected problem, options & draft |
| `POST` | `/api/v1/complaints/submit` | Fast acknowledgement endpoint with GPS/photo validation |
| `GET` | `/api/v1/complaints/{id}/timeline` | Returns citizen-friendly multi-stage complaint progress |
| `GET` | `/api/v1/review/{id}/accept` | Authority one-click acceptance endpoint |
| `GET` | `/api/v1/review/{id}/reject` | Authority one-click rejection and escalation trigger |
| `GET` | `/api/v1/review/{id}/higher-accept` | Higher official executive overrule and acceptance endpoint |
| `GET` | `/api/v1/review/{id}/status` | Check review status and available action links |
| `GET` | `/api/v1/review/mailbox` | In-app mail stream for authority and higher official inboxes |
| `GET` | `/health` | Complete system health, database & knowledge-base check |

---

## 7. Verification & Automated Tests

Run the complete backend test suite:
```bash
cd backend
pytest tests/ -v
```

**Results:**
```text
============================= test session starts =============================
collected 311 items

tests/test_app.py ......                                                 [  1%]
tests/test_autonomous_platform.py ...............                        [  6%]
tests/test_classification_api.py ....................................... [ 19%]
tests/test_complaints_api.py ..........                                  [ 26%]
tests/test_config.py ..........                                          [ 29%]
tests/test_domain.py ....................                                [ 36%]
tests/test_drafting_api.py ............................................. [ 54%]
tests/test_end_to_end.py .......                                         [ 61%]
tests/test_intake_api.py ............................................... [ 78%]
tests/test_knowledge_base.py .....................                       [ 95%]
tests/test_language_detection.py .....                                   [ 97%]
tests/test_persistence.py ........                                       [100%]

================= 311 passed, 4 warnings in 78.97s (0:01:18) ==================
```

Frontend production build check:
```bash
cd frontend
npm run build
```
```text
✓ 2210 modules transformed.
dist/index.html                   0.61 kB
dist/assets/index-DML-X4t1.css   48.41 kB
dist/assets/index-CIfMwT1N.js   408.39 kB
✓ built in 314ms
```

---

## 8. License & Acknowledgements

Developed for **Build for Billions — Agentic AI for Billions Hackathon**.  
Designed to bring transparency, accountability, and autonomous execution to citizen grievances across Indian municipalities.
