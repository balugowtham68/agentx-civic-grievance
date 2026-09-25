


AGENT X — Autonomous Civic Grievance Redressal Agent
Build for Billions — Agent AI for Billions

AGENT X is an Autonomous Civic Grievance Redressal Agent designed to help citizens report civic problems through natural voice or text input and autonomously manage the grievance lifecycle after submission.

The system is designed around one central idea:

The AI does not just answer the citizen. It continues working after the citizen leaves.

AGENT X combines multilingual citizen intake, AI-based classification and reasoning, complaint drafting, mock grievance filing, persistent complaint state, SLA monitoring, autonomous watchdog behavior, configured escalation, and an explainable audit trail.

📌 Table of Contents
Problem Statement

Why Existing Grievance Workflows Are Insufficient

Our Solution

Core Agentic Lifecycle

Five-Agent Architecture

End-to-End Workflow

Autonomous Watchdog

SLA Monitoring

Automatic Escalation

Explainability and Audit Trail

RAG and Civic Knowledge Base

Multilingual and Voice-First Interaction

Mock Government Integration

System Architecture

Data and State Model

Technology Stack

Project Structure

Team Responsibilities

24-Hour Hackathon MVP

Demo Scenario

Safety and Design Principles

Testing Strategy

Development Roadmap

Git Workflow

Future Scalability

Limitations and Demo Assumptions

Project Status

Team

🚨 Problem Statement
Citizens face difficulty getting everyday civic problems resolved, including:

Potholes

Water leaks

Garbage and sanitation issues

Broken streetlights

Public infrastructure problems

Welfare-service related problems

The challenge is not only submitting a complaint.

Citizens may:

Not know which department or authority is responsible.

Struggle to identify the correct category.

Struggle with jurisdiction and responsible offices.

Have difficulty completing structured forms.

Face language or literacy barriers.

Face accessibility challenges.

Need to repeatedly check complaint status.

Need to repeatedly follow up when authorities do not act within expected timelines.

Lack visibility into why a complaint was routed or escalated.

The submitted project concept identifies a gap between complaint submission/tracking and autonomous follow-through after submission.

AGENT X is designed to provide that follow-through layer.

🔎 Why Existing Grievance Workflows Are Insufficient
A conventional workflow often looks like:

Citizen
   ↓
Submit Complaint
   ↓
Receive Tracking ID
   ↓
Citizen Checks Status
   ↓
Citizen Follows Up
   ↓
Citizen Escalates Manually
The burden of monitoring and follow-up remains largely with the citizen.

AGENT X changes the workflow to:

Citizen
   ↓
Natural Voice / Text Complaint
   ↓
AI Understands
   ↓
AI Classifies
   ↓
AI Drafts
   ↓
System Files
   ↓
System Monitors
   ↓
System Evaluates SLA
   ↓
System Detects Delay
   ↓
System Triggers Configured Escalation
   ↓
Human Authority
   ↓
Resolution / Update
   ↓
Explainable Audit Trail
💡 Our Solution
AGENT X is an agentic AI system that manages the civic grievance lifecycle from citizen input through monitoring and configured escalation.

The system accepts a grievance through voice or text, extracts relevant information, determines the likely category and responsible department, generates a structured complaint, files it through a mock government grievance API, stores the resulting state, and continues monitoring the complaint.

When the configured SLA is approaching or breached, the Autonomous Watchdog evaluates the configured conditions and can trigger an escalation workflow.

The system does not claim to physically resolve the civic problem. Resolution remains with the appropriate human authority.

🔄 Core Agentic Lifecycle
The complete AGENT X lifecycle is:

UNDERSTAND
     ↓
CLASSIFY
     ↓
DRAFT
     ↓
FILE
     ↓
MONITOR
     ↓
DECIDE
     ↓
ESCALATE
     ↓
EXPLAIN
This lifecycle is the foundation of the system.

🤖 Five-Agent Architecture
1. Citizen Intake Agent
Purpose
Understand the citizen's grievance from natural voice or text.

Responsibilities
Accept voice/text input.

Handle supported local/vernacular language input.

Transcribe voice where required.

Translate where required.

Extract issue/problem.

Extract location.

Extract duration.

Extract relevant entities.

Detect missing information.

Request clarification when necessary.

Example
Citizen says:

"Engal theruvil moondru naatkalaaga street light velai seyyavillai."

The system should derive information such as:

Issue: Streetlight not functioning
Duration: 3 days
Language: Tamil
Location: Citizen-provided location
2. Classification & Reasoning Agent
Purpose
Determine what the grievance is, who should handle it, and what configured civic information applies.

Responsibilities
Classify grievance category.

Identify responsible department.

Determine jurisdiction.

Identify missing information.

Retrieve relevant civic rules.

Retrieve department mappings.

Retrieve jurisdiction mappings.

Retrieve service timelines.

Provide reasoning/evidence for classification.

Example
Streetlight Problem
        ↓
Civic Infrastructure
        ↓
Streetlight Maintenance
        ↓
Municipal Electrical Division
The result should be explainable rather than being a black-box routing decision.

3. Complaint Drafting Agent
Purpose
Convert the citizen's natural-language description into a structured administrative complaint.

Responsibilities
Preserve the citizen's intended meaning.

Produce a clear complaint description.

Populate structured fields.

Include relevant category and department.

Prepare the complaint for filing.

Avoid inventing facts that the citizen did not provide.

Example
Issue:
Non-functional public streetlight

Category:
Public Infrastructure

Department:
Municipal Electrical Division

Description:
A public streetlight has not been functioning
for approximately three days and requires
maintenance.
4. Filing Agent
Purpose
Submit the prepared complaint to the hackathon's mock grievance environment.

Responsibilities
Validate the complaint.

Submit through the Mock Government Grievance API.

Receive a tracking ID.

Persist complaint state.

Start the configured SLA clock.

Create a filing audit event.

Example:

Complaint Draft
      ↓
Validation
      ↓
Mock Government API
      ↓
Tracking ID
      ↓
Complaint State Created
      ↓
SLA Started
🛡️ 5. Autonomous Watchdog
The Autonomous Watchdog is the core differentiator of AGENT X.

It is responsible for continuing the workflow after the citizen has submitted the grievance.

The Watchdog observes complaint state over time and evaluates configured conditions.

Responsibilities
Monitor complaint status.

Track SLA timelines.

Detect inactivity.

Detect approaching deadlines.

Detect SLA breaches.

Evaluate configured policies.

Trigger configured escalation.

Record actions in the audit trail.

Provide reasons for warnings and escalation.

Traditional System
Citizen
   ↓
Submit
   ↓
Citizen checks
   ↓
Citizen follows up
AGENT X
Citizen
   ↓
Submit
   ↓
AGENT X continues working
   ↓
Monitor
   ↓
Evaluate
   ↓
Detect delay
   ↓
Warn
   ↓
Escalate
   ↓
Explain
⏱️ SLA Monitoring
The system maintains a configured SLA for a complaint.

The hackathon prototype uses time-accelerated/simulated SLA progression so the entire lifecycle can be demonstrated within the event.

Example:

DAY 0
Complaint Filed
Tracking ID Generated
SLA Started
        ↓
DAY 2
No Qualifying Action
SLA Approaching
Warning Generated
        ↓
DAY 3
SLA Breached
        ↓
Configured Escalation Triggered
The exact SLA values are configuration data for the prototype rather than claims about real government service timelines.

🚨 Automatic Escalation
Escalation is configured and policy-driven.

The AI does not receive unrestricted authority to take arbitrary external actions.

A simplified policy can be represented as:

IF
    complaint is not resolved
AND
    configured SLA deadline has expired
AND
    escalation conditions are satisfied

THEN
    trigger configured escalation
    create audit event
    record explanation
Officer acknowledgement
AGENT X treats:

ACKNOWLEDGED ≠ RESOLVED
An acknowledgement can update the complaint state and create an audit event.

It does not automatically stop escalation if the configured SLA remains unsatisfied.

A configured terminal state such as RESOLVED or CLOSED, or another explicitly configured policy condition, can stop further escalation.

🔍 Explainability and Audit Trail
AGENT X is designed to explain major decisions throughout the lifecycle.

Example: Department Selection
Why was this department selected?

The complaint was classified as a streetlight
maintenance issue.

The configured civic department mapping associates
streetlight maintenance with the Municipal Electrical
Division.
Example: SLA Warning
Why was a warning generated?

The complaint has not reached a qualifying resolution
state and its configured SLA deadline is approaching.
Example: Escalation
Why was escalation triggered?

The complaint remained unresolved after the configured
SLA deadline and the configured escalation policy
conditions were satisfied.
Audit Events
Important events can include:

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
Status Checked
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
Each major event should retain information such as:

Event type

Timestamp

Complaint ID

Agent/component responsible

Reason

Result

Relevant decision metadata

📚 RAG and Civic Knowledge Base
The Classification & Reasoning Agent uses a configured civic knowledge base.

The knowledge base is intended to contain information such as:

Civic service rules

Department mappings

Issue-to-department mappings

Jurisdiction mappings

Service timelines

Escalation policies

Operational guidelines

The RAG layer allows the system to retrieve relevant configured information before making routing or workflow decisions.

Example
Citizen Complaint
       ↓
Issue Classification
       ↓
Retrieve Relevant Civic Knowledge
       ↓
Department / Jurisdiction / SLA Evidence
       ↓
Reasoned Decision
       ↓
Explainable Output
For the hackathon MVP, this knowledge base may contain controlled demo data.

🌐 Multilingual and Voice-First Interaction
AGENT X is designed around accessible citizen interaction.

The proposed interaction supports:

Voice input

Text input

Local/vernacular language input

Transcription

Translation where required

Natural-language grievance submission

The system should convert natural citizen language into structured information without requiring the citizen to understand government forms or departmental terminology.

For the 24-hour MVP, language coverage may be limited to selected languages while keeping the architecture extensible.

🏛️ Mock Government Integration
The hackathon implementation uses a Mock Government Grievance API.

The mock API represents the external grievance authority.

It can provide operations conceptually similar to:

Submit Complaint
      ↓
Generate Tracking ID
      ↓
Get Complaint Status
      ↓
Update Complaint Status
      ↓
Return Authority Information
The mock environment allows AGENT X to demonstrate:

Filing

Tracking IDs

Status changes

SLA progression

No-action scenarios

Warnings

SLA breaches

Escalation

Resolution

No real government system is required for the prototype.

🏗️ System Architecture
                         ┌──────────────────────┐
                         │       CITIZEN        │
                         │    Voice / Text      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   CITIZEN INTAKE     │
                         │        AGENT         │
                         │                      │
                         │ Speech / Text        │
                         │ Language             │
                         │ Extraction           │
                         │ Missing Information  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ CLASSIFICATION &     │
                         │ REASONING AGENT      │
                         │                      │
                         │ Category             │
                         │ Department           │
                         │ Jurisdiction         │
                         │ RAG                  │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │    KNOWLEDGE BASE    │
                         │       ChromaDB       │
                         │                      │
                         │ Rules / Mappings     │
                         │ Jurisdictions        │
                         │ Timelines            │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ COMPLAINT DRAFTING   │
                         │        AGENT         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     FILING AGENT     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ MOCK GOVERNMENT API  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  PERSISTENT STATE    │
                         │                      │
                         │ Complaint State      │
                         │ SLA State            │
                         │ Events               │
                         └──────────┬───────────┘
                                    │
                                    ▼
                  ┌─────────────────────────────────┐
                  │      AUTONOMOUS WATCHDOG        │
                  │                                 │
                  │ Status Monitoring               │
                  │ SLA Monitoring                  │
                  │ Decision Logic                  │
                  │ Delay Detection                 │
                  └───────────────┬─────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
             SLA Approaching               SLA Breach
                    │                           │
                    ▼                           ▼
                WARNING               CONFIGURED ESCALATION
                                                │
                                                ▼
                                      ┌───────────────────┐
                                      │ HUMAN AUTHORITY   │
                                      │                   │
                                      │ Action / Update   │
                                      │ Resolution        │
                                      └─────────┬─────────┘
                                                │
                                                ▼
                                      ┌───────────────────┐
                                      │ AUDIT + EXPLAIN   │
                                      └───────────────────┘
🗃️ Data and State Model
The system maintains persistent state rather than treating each interaction as an isolated chat.

A complaint can conceptually contain:

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
The exact implementation schema may evolve during development while preserving the required lifecycle and persistent state.

🧰 Technology Stack
Frontend
React

Vite

Tailwind CSS

Backend
Python

FastAPI

AI / LLM
Gemini API

Voice / Language
Whisper and/or Web Speech

Translation layer where required

RAG
ChromaDB

Vector embeddings

Persistence
SQLite and/or structured persistent state

Scheduling
APScheduler

External Integration
Mock Government Grievance API

Validation and Security
Input validation

Input sanitization

Environment-based secret management

📁 Project Structure
The repository structure will evolve as implementation proceeds.

A target organization is:

agentx-civic-grievance/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── intake/
│   │   │   ├── classification/
│   │   │   ├── drafting/
│   │   │   ├── filing/
│   │   │   └── watchdog/
│   │   │
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── database/
│   │   ├── core/
│   │   └── main.py
│   │
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── ...
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
├── docs/
│
├── scripts/
│
├── .env.example
├── .gitignore
└── README.md
This structure is a planning target. Implementation phases may adjust individual directories without changing the overall architecture.

🔗 End-to-End API/Data Flow
A typical request should follow a controlled flow:

Frontend
   ↓
FastAPI
   ↓
Intake Service
   ↓
Classification / RAG
   ↓
Drafting Service
   ↓
Filing Service
   ↓
Mock Government API
   ↓
Persistent Complaint State
   ↓
Scheduler / Watchdog
   ↓
Decision / Escalation
   ↓
Audit Event
   ↓
Frontend
The AI model provides intelligence.

The application layer provides:

State

Tools

APIs

Scheduling

Decision logic

Monitoring

External actions

Audit logging

This separation is important because an AI response alone does not constitute an autonomous agent workflow.

🎯 Target Users
Primary Users
Everyday citizens

Urban residents

Rural residents

Peri-urban residents

Vernacular-language speakers

Citizens with limited digital literacy

Senior citizens

Users facing accessibility barriers

Secondary Users
Municipal officers

Ward officers

Maintenance departments

Administrative authorities

🌍 Expected Impact
AGENT X is intended to reduce friction across the grievance lifecycle by:

Making grievance submission more accessible.

Supporting natural voice/text interaction.

Helping citizens who may not know the correct department.

Structuring unstructured complaints.

Reducing repeated manual follow-up.

Making status and SLA progression visible.

Detecting delays automatically.

Triggering configured escalation.

Providing an auditable history of important actions.

🏆 What Makes AGENT X Different?
AGENT X is not another chatbot.

The innovation is the combination of:

Natural Citizen Input
        +
Multilingual Accessibility
        +
Department / Jurisdiction Reasoning
        +
Structured Complaint Drafting
        +
Mock Filing
        +
Persistent State
        +
Autonomous SLA Monitoring
        +
Configured Escalation
        +
Explainable Audit Trail
The most important distinction is that the system is designed to continue operating after complaint submission.

🧪 24-Hour Hackathon MVP
The prototype is intentionally scoped as a functional end-to-end demonstration.

MVP must demonstrate
Voice/text grievance intake architecture

Natural-language understanding

Information extraction

Department classification

Jurisdiction reasoning

RAG / civic knowledge retrieval

Complaint drafting

Mock complaint filing

Tracking ID generation

Persistent complaint state

SLA state

Time-accelerated monitoring

Automatic configured escalation

Explainability

Audit trail

Some capabilities may be implemented with controlled demo data so that the complete lifecycle can be reliably demonstrated within the hackathon.

🎬 Demo Scenario
The primary demonstration uses a streetlight complaint.

Step 1 — Citizen Input
Citizen submits:

"Engal theruvil moondru naatkalaaga street light velai seyyavillai."

Step 2 — Intake
Issue: Streetlight not working
Duration: 3 days
Language: Tamil
Location: Citizen-provided
Step 3 — Classification
Category:
Civic Infrastructure

Issue:
Streetlight Maintenance

Department:
Municipal Electrical Division
Step 4 — Draft
The Drafting Agent generates a structured administrative complaint.

Step 5 — Filing
The complaint is submitted to the Mock Government API.

Tracking ID:
AGX-XXXXXX
Step 6 — SLA Starts
The complaint enters persistent monitoring.

Step 7 — Simulated Day 2
No qualifying action detected.

SLA approaching.

Warning generated.
Step 8 — Simulated Day 3
SLA breached.

Complaint remains unresolved.

Configured escalation conditions satisfied.
Step 9 — Escalation
The configured escalation workflow is triggered.

Step 10 — Explainability
The dashboard shows:

WHY?

The configured SLA deadline expired while
the complaint remained unresolved.

The configured escalation policy was therefore
triggered.
Step 11 — Audit Trail
The complete sequence is displayed to demonstrate that AGENT X acted autonomously after filing.

🔐 Safety and Design Principles
AGENT X follows a constrained autonomy model.

1. Configured Authority
The system operates within predefined:

Rules

Timelines

Department mappings

Jurisdiction mappings

Escalation policies

2. No Unrestricted Authority
The AI should not be allowed to invent arbitrary government actions or escalation targets.

3. Human Resolution
AGENT X does not claim to resolve physical civic problems.

Human authorities remain responsible for actual resolution.

4. Explainability
Important decisions should have an understandable reason.

5. Auditability
Major lifecycle actions should be recorded.

6. Input Validation
User input and external data should be validated and sanitized.

7. Mock External Integration
The hackathon prototype uses a mock government API rather than real government systems.

🧪 Testing Strategy
Testing should cover the complete lifecycle rather than only individual AI outputs.

Unit Testing
Examples:

Input extraction

Classification

RAG retrieval

Draft generation

SLA calculation

State transitions

Escalation conditions

API Testing
Examples:

Complaint creation

Filing

Tracking ID retrieval

Status retrieval

Status update

Audit event creation

Watchdog Testing
Important scenarios:

Complaint Filed
        ↓
No Action
        ↓
SLA Approaching
        ↓
Warning
and:

Complaint Filed
        ↓
No Resolution
        ↓
SLA Breach
        ↓
Escalation
Also test:

Complaint Filed
        ↓
Authority Action
        ↓
Resolved
        ↓
No Escalation
Integration Testing
Verify:

Frontend
   ↓
Backend
   ↓
Agents
   ↓
Database
   ↓
Mock Government API
   ↓
Watchdog
   ↓
Escalation
   ↓
Audit
🗺️ Development Roadmap
Phase 1 — Foundation + Architecture
Establish:

Repository structure

Backend foundation

Frontend foundation

Configuration

Environment handling

Shared contracts

Base data models

Phase 2 — Citizen Intake Agent
Implement:

Voice/text input

Language handling

Transcription

Extraction

Missing-information detection

Phase 3 — RAG + Classification + Reasoning
Implement:

ChromaDB

Knowledge base

Retrieval

Department classification

Jurisdiction reasoning

SLA information retrieval

Phase 4 — Complaint Drafting
Implement:

Structured complaint generation

Validation

Draft preview

Phase 5 — Mock Government Filing
Implement:

Mock government API

Complaint submission

Tracking ID

Filing state

Phase 6 — Persistent State + Audit Foundation
Implement:

Complaint persistence

State transitions

SLA state

Audit events

Phase 7 — Autonomous Watchdog + SLA Monitoring
Implement:

Scheduler

Status monitoring

Time acceleration

SLA approaching detection

SLA breach detection

Phase 8 — Configured Automatic Escalation
Implement:

Escalation policies

Escalation conditions

Authority routing

Escalation events

Human resolution states

Phase 9 — Frontend Dashboard + Explainability
Implement:

Citizen interface

Complaint status

Tracking view

SLA visualization

Escalation view

Audit timeline

Decision explanations

Phase 10 — Full Integration + Testing + Demo Hardening
Implement:

End-to-end integration

Testing

Error handling

Demo data

Demo scenario

UI polish

Presentation readiness

👥 Team Responsibilities
Balu Gowtham — Team Lead
Responsibilities:

System architecture

Agent orchestration

LLM integration

Cross-module integration

Architecture decisions

Final integration

Demo coordination

Guttula Gowtham Gandhi — AI/ML
Responsibilities:

RAG

Knowledge base

Classification

Reasoning

Department mapping

Jurisdiction reasoning

AI evaluation

Kurella Pardhu — Backend
Responsibilities:

FastAPI

Database

Persistent state

Mock Government API

Backend APIs

Service integration

Nedam Harshavardhan — Frontend
Responsibilities:

React interface

Citizen experience

Voice/text UI

Complaint tracking

SLA visualization

Audit timeline

Explainability UI

K. Lakshmi Narasimha Charan — Watchdog / QA
Responsibilities:

Autonomous Watchdog

SLA monitoring

Escalation logic

Scheduler

Integration testing

End-to-end testing

Demo validation

🌿 Git Workflow
The repository uses a feature-branch workflow.

main
 │
 ├── feature/orchestration
 ├── feature/backend
 ├── feature/rag-classification
 ├── feature/frontend
 └── feature/watchdog
Rules
main should remain the stable integration branch.

Each member works primarily on their assigned feature branch.

Changes should be committed in logical units.

Pull Requests should be used to merge completed work.

Do not force-push shared branches.

Do not overwrite another member's work without coordination.

Keep API contracts stable.

Test before merging.

Never commit API keys or secrets.

Use .env locally and .env.example for required variable names.

🔑 Environment Variables
Secrets must never be committed to Git.

Use:

.env
locally and provide:

.env.example
as a template.

Example:

GEMINI_API_KEY=
DATABASE_URL=
The actual environment variables may expand as implementation progresses.

📈 Future Scalability
The architecture is intended to be extensible across:

Additional municipalities

Additional wards

Additional departments

Additional civic issue categories

Additional Indian languages

Additional jurisdiction systems

Additional escalation policies

Additional external grievance systems

The broader agentic workflow can also be adapted to other structured grievance domains where cases require:

UNDERSTAND
    ↓
CLASSIFY
    ↓
ACT
    ↓
MONITOR
    ↓
DETECT DELAY
    ↓
ESCALATE
    ↓
EXPLAIN
⚠️ Limitations and Demo Assumptions
This repository represents a hackathon prototype, not a production government deployment.

For the 24-hour MVP:

Language support may be limited to selected languages.

Jurisdiction may use configured sample wards/landmarks rather than live GPS-based determination.

The knowledge base may use controlled/demo civic rules.

Government interaction is represented through a mock API.

SLA progression may be accelerated for demonstration.

Escalation targets are configured demo authorities.

Real-world government authentication, security, procurement, deployment, and integration are outside the hackathon scope.

These limitations are implementation choices for a reliable demonstration and do not change the core concept of autonomous grievance follow-through.

📊 Success Criteria
The MVP should be considered successful when the team can demonstrate:

Citizen Complaint
      ↓
AI Understands
      ↓
Issue Classified
      ↓
Department Identified
      ↓
Complaint Drafted
      ↓
Complaint Filed
      ↓
Tracking ID Generated
      ↓
State Persisted
      ↓
SLA Started
      ↓
Watchdog Monitors
      ↓
SLA Approaches
      ↓
Warning
      ↓
SLA Breach
      ↓
Automatic Configured Escalation
      ↓
Human Authority
      ↓
Explainable Audit Trail
The key demonstration is that the workflow continues after the citizen submits the complaint.

📌 Project Status
🚧 Hackathon MVP — In Development

Current development is being performed phase-by-phase using a shared GitHub repository.

👨‍💻 Team AGENT X
Member	Role
GOWTHAM BALU	Team Lead / AI Architecture / Orchestration
GUTTULA GOWTHAM GANDHI	AI/ML / RAG / Classification
KURELLA PARDHU	Backend / FastAPI / Mock API
NEDAM HARSHAVARDHAN	Frontend / UX / Tracking
K. LAKSHMI NARASIMHA CHARAN	Watchdog / SLA / Escalation / Testing
🏛️ Build for Billions
AGENT X
Autonomous Civic Grievance Redressal Agent
Understand. Classify. Draft. File. Monitor. Decide. Escalate. Explain.

The AI doesn't just answer the citizen. It continues working after the citizen leaves.
