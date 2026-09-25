AGENT X 🤖

The AI That Doesn't Stop When the Citizen Leaves

AGENT X is an Autonomous Civic Grievance Redressal Agent that helps citizens report civic problems through voice or text and autonomously manages the grievance lifecycle after submission.

It combines multilingual citizen intake, AI-based classification and reasoning, complaint drafting, mock grievance filing, persistent complaint state, SLA monitoring, autonomous delay detection, configured escalation, and an explainable audit trail.

The core idea is simple:

Don't just help citizens file complaints. Continue working after they leave.

🚀 Key Features

Voice and text-based grievance intake

Multilingual / vernacular citizen interaction

Natural-language issue, location, duration, and entity extraction

Missing-information detection

AI-based grievance classification

Responsible department identification

Jurisdiction reasoning

RAG-powered civic knowledge retrieval

Structured complaint drafting

Mock government grievance filing

Tracking ID generation

Persistent complaint state

SLA tracking and time-accelerated simulation

Autonomous Watchdog for continuous monitoring

SLA approaching and breach detection

Configured automatic escalation

Explainable decision and escalation reasons

Persistent audit trail

Citizen complaint tracking

Human-authority resolution workflow

🧠 Tech Stack

Frontend

React

Vite

Tailwind CSS

Voice / Text interaction

Complaint tracking and audit visualization

Backend

Python

FastAPI

Pydantic

SQLite / persistent application state

APScheduler

AI / Agentic Layer

Gemini API

Citizen Intake Agent

Classification & Reasoning Agent

Complaint Drafting Agent

Filing Agent

Autonomous Watchdog Agent

RAG / Knowledge

ChromaDB

Vector embeddings

Civic rules

Department mappings

Jurisdiction mappings

Service timelines

Escalation policies

Voice / Language

Whisper and/or Web Speech

Translation layer where required

Integration

Mock Government Grievance API

🤖 Five-Agent Architecture

1. Citizen Intake Agent

Accepts natural voice or text complaints and extracts:

Issue

Location

Duration

Language

Relevant entities

Missing information

2. Classification & Reasoning Agent

Determines:

Grievance category

Responsible department

Jurisdiction

Applicable civic information

Service timeline

Missing information

Uses the configured civic knowledge base through RAG.

3. Complaint Drafting Agent

Converts natural citizen language into a structured administrative complaint while preserving the citizen's intended meaning.

4. Filing Agent

Submits the structured complaint to the Mock Government Grievance API, receives a tracking ID, persists the complaint state, and starts SLA tracking.

5. Autonomous Watchdog

The core differentiator of AGENT X.

It continuously evaluates:

Complaint status

Authority action

SLA progression

Approaching deadlines

SLA breaches

Configured escalation conditions

It can trigger configured escalation workflows and record the reason in the audit trail.

🔄 Workflow

Citizen Voice / Text
        ↓
Citizen Intake Agent
        ↓
Understand Issue + Extract Information
        ↓
Classification & Reasoning
        ↓
RAG Knowledge Retrieval
        ↓
Department + Jurisdiction + SLA
        ↓
Complaint Drafting Agent
        ↓
Mock Government Filing
        ↓
Tracking ID
        ↓
Persistent Complaint State
        ↓
SLA Clock
        ↓
Autonomous Watchdog
        ↓
Status Monitoring
        ↓
SLA Approaching / SLA Breach
        ↓
Configured Escalation
        ↓
Human Authority
        ↓
Resolution / Update
        ↓
Explainable Audit Trail

svg

⏱️ Autonomous SLA Monitoring

Unlike a conventional grievance system where the citizen repeatedly checks the status, AGENT X continues monitoring after filing.

For the hackathon demonstration, SLA progression is time-accelerated/simulated.

Day 0
Complaint Filed
Tracking ID Generated
SLA Started
     ↓
Day 2
No Qualifying Action
SLA Approaching
Warning Generated
     ↓
Day 3
SLA Breached
     ↓
Configured Escalation
     ↓
Human Authority

🚨 Automatic Escalation

Escalation is driven by configured policies and conditions, not unrestricted AI authority.

Example:

Complaint unresolved
        +
Configured SLA expired
        +
Escalation policy satisfied
        ↓
Automatic Escalation
        ↓
Audit Event
        ↓
Human Authority

An important state distinction is:

ACKNOWLEDGED ≠ RESOLVED

An officer acknowledgement can update the complaint state and create an audit event, but it does not automatically stop escalation if the configured SLA remains unsatisfied.

A configured resolved/closed state can stop further escalation.

🔍 Explainability

AGENT X provides reasons for important decisions.

Why was this department selected?

The complaint was classified as a streetlight
maintenance issue.

The configured civic mapping associates the issue
with the Municipal Electrical Division.

Why was escalation triggered?

The configured SLA deadline expired while the
complaint remained unresolved.

The configured escalation policy conditions
were satisfied.

The system is designed so that important autonomous actions are understandable rather than hidden.

📜 Audit Trail

Major lifecycle events are recorded.

Complaint Created
      ↓
Information Extracted
      ↓
Complaint Classified
      ↓
Department Determined
      ↓
Complaint Drafted
      ↓
Complaint Filed
      ↓
Tracking ID Generated
      ↓
SLA Started
      ↓
Status Monitored
      ↓
SLA Warning
      ↓
SLA Breached
      ↓
Escalation Triggered
      ↓
Authority Update
      ↓
Resolution / Closure

Audit records can contain:

Event type

Timestamp

Complaint ID

Agent / system actor

Reason

Previous state

New state

Relevant metadata

📚 RAG Knowledge Base

The Classification & Reasoning Agent uses a configured civic knowledge base containing information such as:

Civic rules

Department mappings

Issue-to-department mappings

Jurisdiction mappings

Service timelines

Escalation policies

Operational guidelines

Citizen Complaint
        ↓
Issue Classification
        ↓
Knowledge Retrieval
        ↓
Relevant Civic Evidence
        ↓
Reasoned Decision
        ↓
Explainable Result

For the hackathon MVP, controlled/demo civic data may be used.

🌐 Multilingual & Voice-First Interaction

Citizens should not need to understand government terminology or structured forms to report a problem.

AGENT X is designed to support:

Voice input

Text input

Vernacular language input

Speech transcription

Translation where required

Natural-language grievance submission

Example:

"Engal theruvil moondru naatkalaaga street light velai seyyavillai."

The system can extract:

Issue      → Streetlight not functioning
Duration   → 3 days
Language   → Tamil
Location   → Citizen-provided

🏛️ Mock Government API

AGENT X uses a Mock Government Grievance API for the hackathon.

The mock system represents the external grievance authority and supports the demonstration of:

Complaint submission

Tracking ID generation

Complaint status

Authority updates

SLA progression

Resolution

Escalation scenarios

No real government system is required for the prototype.

🏗️ System Architecture

                    Citizen
                       │
                 Voice / Text
                       ↓
             ┌───────────────────┐
             │ Citizen Intake    │
             │      Agent        │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Classification &  │
             │ Reasoning Agent   │
             └─────────┬─────────┘
                       │
                       ├──────────────→ ChromaDB
                       │                RAG / Civic KB
                       ↓
             ┌───────────────────┐
             │ Complaint         │
             │ Drafting Agent    │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Filing Agent      │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Mock Government   │
             │ Grievance API     │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Persistent State  │
             │ Complaint + SLA   │
             │ + Audit Events    │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ Autonomous        │
             │ Watchdog          │
             └─────────┬─────────┘
                       ↓
             ┌───────────────────┐
             │ SLA / Decision    │
             │ Evaluation        │
             └──────┬───────┬────┘
                    │       │
                 Warning   Breach
                    │       ↓
                    │  Configured
                    │  Escalation
                    │       ↓
                    └──→ Human Authority
                              ↓
                     Resolution / Update
                              ↓
                    Explainable Audit Trail

svg

📊 Complaint State Model

A complaint maintains persistent state throughout its lifecycle.

CREATED
   ↓
UNDERSTOOD
   ↓
CLASSIFIED
   ↓
DRAFTED
   ↓
FILED
   ↓
MONITORING
   ├──→ WARNING
   │
   ├──→ BREACHED
   │       ↓
   │   ESCALATED
   │
   └──→ RESOLVED
           ↓
         CLOSED

The exact state machine may evolve during implementation while preserving the core grievance lifecycle.

🗃️ Core Data

A complaint can contain:

Complaint
├── complaint_id
├── tracking_id
├── citizen_input
├── language
├── issue
├── location
├── duration
├── category
├── department
├── jurisdiction
├── drafted_complaint
├── status
├── sla_start
├── sla_deadline
├── escalation_state
├── created_at
└── updated_at

Audit events can contain:

AuditEvent
├── event_id
├── complaint_id
├── event_type
├── timestamp
├── actor
├── reason
├── previous_state
├── new_state
└── metadata

🛠️ Getting Started

Clone

git clone https://github.com/YOUR-USERNAME/agentx-civic-grievance.git
cd agentx-civic-grievance

Backend

cd backend
python -m venv .venv

Activate the environment:

Windows

.venv\Scripts\activate

Linux / macOS

source .venv/bin/activate

Install dependencies when the backend requirements are available:

pip install -r requirements.txt

Run the FastAPI application:

uvicorn app.main:app --reload

Frontend

cd frontend
npm install
npm run dev

Environment Variables

Create a local .env file.

Example:

GEMINI_API_KEY=
DATABASE_URL=

Never commit .env or API keys.

Use .env.example to document required variables.

📁 Project Structure

agentx-civic-grievance/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── intake/
│   │   │   ├── classification/
│   │   │   ├── drafting/
│   │   │   ├── filing/
│   │   │   └── watchdog/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── database/
│   │   └── main.py
│   │
│   └── tests/
│
├── knowledge_base/
│   ├── departments/
│   ├── jurisdictions/
│   ├── rules/
│   ├── timelines/
│   └── escalation/
│
├── scripts/
├── docs/
├── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml

🎯 Hackathon Problem

Build for Billions — Agent AI for Billions

Autonomous Civic Grievance Redressal

Citizens may know that they have a problem but not know:

Which department is responsible.

Which category to select.

Which jurisdiction applies.

How to structure the complaint.

What to do when the authority does not act.

How to escalate after a delay.

AGENT X addresses the complete operational lifecycle rather than functioning only as a conversational interface.

🧪 MVP Scope

The 24-hour hackathon MVP focuses on a functional end-to-end demonstration:

Voice/text intake

Multilingual interaction for selected languages

Information extraction

Department classification

Jurisdiction reasoning

RAG-based civic knowledge

Complaint drafting

Mock grievance filing

Tracking ID

Persistent complaint state

Time-accelerated SLA monitoring

Autonomous Watchdog

Configured automatic escalation

Explainability

Audit trail

🎬 Demo Scenario

A citizen reports:

"Engal theruvil moondru naatkalaaga street light velai seyyavillai."

AGENT X demonstrates:

1. Citizen submits voice/text
              ↓
2. Intake Agent understands complaint
              ↓
3. Issue + duration + location extracted
              ↓
4. Classification Agent identifies department
              ↓
5. RAG retrieves supporting civic information
              ↓
6. Drafting Agent creates structured complaint
              ↓
7. Filing Agent submits to Mock Government API
              ↓
8. Tracking ID generated
              ↓
9. SLA clock starts
              ↓
10. Watchdog monitors complaint
              ↓
11. SLA approaching → warning
              ↓
12. SLA breached → configured escalation
              ↓
13. Human authority receives escalation
              ↓
14. Audit trail explains the complete lifecycle

🛡️ Safe-by-Design

AGENT X operates using constrained autonomy.

Predefined civic rules and mappings

Configured SLA timelines

Configured escalation policies

No unrestricted autonomous authority

Human authority remains responsible for resolution

Important actions are logged

Important decisions are explainable

Input is validated and sanitized

Real government integration is not required for the prototype

AGENT X does not claim that the AI itself physically resolves civic problems.

👥 Team

Team AGENT X

Member

Contribution

GOWTHAM BALU

Team Lead, AI Architecture, Agent Orchestration, LLM Integration

GUTTULA GOWTHAM GANDHI

AI/ML, RAG, Classification & Reasoning

KURELLA PARDHU

Backend, FastAPI, Mock API, Persistent State

NEDAM HARSHAVARDHAN

Frontend, UX, Voice/Text, Tracking & Audit UI

K. LAKSHMI NARASIMHA CHARAN

Watchdog, SLA Monitoring, Escalation, Testing & Integration

🗺️ Roadmap

Phase 1 — Foundation & Architecture

Phase 2 — Citizen Intake Agent

Phase 3 — RAG + Classification + Reasoning

Phase 4 — Complaint Drafting

Phase 5 — Mock Government Filing + Tracking

Phase 6 — Persistent State + Audit Foundation

Phase 7 — Autonomous Watchdog + SLA Monitoring

Phase 8 — Configured Automatic Escalation

Phase 9 — Frontend Dashboard + Explainability

Phase 10 — Full Integration + Testing + Demo Hardening

🌱 Future Scalability

AGENT X can be extended to support:

More municipalities

More departments

More civic issue categories

More languages

More jurisdiction mappings

More escalation policies

Additional grievance systems

The underlying workflow can also be adapted to other domains that require autonomous case follow-through:

Understand
    ↓
Classify
    ↓
Act
    ↓
Monitor
    ↓
Detect Delay
    ↓
Escalate
    ↓
Explain

⚠️ Limitations

AGENT X is a hackathon prototype and not a production government deployment.

For the MVP:

Language coverage may be limited to selected languages.

Jurisdiction may use sample wards/landmarks rather than live GPS.

Civic knowledge may use controlled/demo rules.

Government interaction is represented through a mock API.

SLA timelines are accelerated for demonstration.

Escalation targets are configured for the prototype.

These are demo-scope implementation choices and do not change the core autonomous grievance follow-through concept.

📌 Project Status

🚧 Hackathon MVP — In Development

Built for Build for Billions — Agent AI for Billions.

📜 References

Government grievance systems and public grievance workflow references used during problem analysis

Civic rules, mappings, jurisdictions, and service timelines used by the configured prototype knowledge base

Hackathon problem statement and submitted AGENT X proposal

🤖 AGENT X

Understand. Classify. Draft. File. Monitor. Decide. Escalate. Explain.

The AI doesn't just answer the citizen. It continues working after the citizen leaves.
