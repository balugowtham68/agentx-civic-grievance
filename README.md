# SPANDAN AI
## Autonomous Civic Grievance Redressal Agent

> **Submit once. SPANDAN follows through.**

SPANDAN AI is an AI-powered civic grievance redressal system that helps citizens report public issues using **voice or text in regional languages**, understands the complaint, identifies the relevant location and authority, prepares the grievance, submits it into a simulated government workflow, and continues monitoring it after the citizen leaves.

Unlike a traditional chatbot that only answers questions, SPANDAN AI is designed to **take responsibility for the grievance workflow from intake to authority decision and escalation**.

---

# 🚨 Problem

Citizens often face several problems while reporting civic issues:

- They may not know which department is responsible.
- Government portals can be difficult to navigate.
- Many citizens are more comfortable speaking regional languages.
- Location and jurisdiction can be unclear.
- Citizens may not know what happened after submitting a complaint.
- Complaints can remain pending without clear follow-up.
- Escalation often requires additional effort from the citizen.

The problem is therefore not only:

> "How can a citizen submit a complaint?"

It is:

> **"How can a complaint continue moving toward resolution even after the citizen leaves?"**

---

# 💡 Our Solution

SPANDAN AI converts a citizen's voice or text complaint into a structured, trackable grievance workflow.

```text
Citizen
   │
   ├── Voice
   └── Text
        │
        ▼
┌──────────────────────┐
│ Language Detection   │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Complaint Intake     │
│                      │
│ Issue                │
│ Location             │
│ Duration             │
│ Language             │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Location Resolution  │
│ & Jurisdiction       │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Classification       │
│ Department           │
│ Authority            │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Civic RAG            │
│ Rules / SLA /        │
│ Authority Knowledge  │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Complaint Drafting   │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Authority Review     │
└──────────────────────┘
        │
        ├── ACCEPT
        │      │
        │      ▼
        │   Accepted
        │
        └── REJECT
               │
               ▼
          Escalation
               │
               ▼
       Higher Authority
               │
               ▼
            Review
⭐ Core Differentiator

Traditional civic applications generally stop after complaint submission.

SPANDAN AI continues working.

Citizen submits complaint
          ↓
Complaint processed
          ↓
Authority identified
          ↓
Complaint sent for review
          ↓
Authority accepts/rejects
          ↓
If rejected → escalation
          ↓
Higher authority review
          ↓
SLA monitoring
          ↓
Follow-up
Our core idea

"The citizen submits once. SPANDAN continues working after the citizen leaves."

🎯 Hackathon MVP

The current MVP focuses on demonstrating an end-to-end autonomous grievance workflow.

Citizen Side
Voice complaint
Text complaint
Regional language support
Automatic language detection
Manual language selection
Issue extraction
Location extraction
Duration extraction
Location confirmation
Complaint tracking ID
Complaint status
AI Pipeline
Multilingual intake
Language identification
Complaint understanding
Location resolution
Department classification
Jurisdiction identification
Civic knowledge retrieval
Complaint drafting
Workflow
Complaint creation
Authority review
Authority acceptance
Authority rejection
Escalation
Higher authority review
Tracking
SLA monitoring
Watchdog
Audit trail
🌐 Multilingual Experience

SPANDAN AI is designed for citizens who may not prefer English.

Supported languages can include:

English
తెలుగు (Telugu)
தமிழ் (Tamil)
ಕನ್ನಡ (Kannada)
हिन्दी (Hindi)

The system supports both manual language selection and automatic language detection.

Multi-Signal Language Detection

Instead of depending on a single detector, SPANDAN can combine multiple signals.

Voice
  │
  ▼
Audio Language Signal
  │
  ▼
Speech-to-Text
  │
  ▼
Transcript Language Detection
  │
  ├── Script Analysis
  ├── Multilingual Embeddings
  ├── Lightweight Classifier
  └── Linguistic Signals
  │
  ▼
LLM Verification
     (only when ambiguous)
  │
  ▼
Language Fusion
  │
  ▼
Final Language + Confidence
Confidence-based behaviour
High confidence
      ↓
Automatically select language

Medium confidence
      ↓
Ask user for confirmation

Low confidence
      ↓
Show language selector

Explicit user language selection always has priority.

📍 Location Intelligence

Location is critical for civic complaints because different locations can belong to different authorities and jurisdictions.

SPANDAN AI supports multiple location sources:

GPS
 │
 ├──────────────┐
 │              │
Voice         Text
 │              │
 └──────┬───────┘
        │
        ▼
Manual Location
        │
        ▼
┌─────────────────────┐
│ Location Resolver   │
└─────────────────────┘
        │
        ▼
State
District
City
Ward
Locality
Coordinates
Jurisdiction
Confidence

The system should never silently invent a location.

When confidence is low:

"We found Ramapuram, Chennai. Is this correct?"

[ Yes ]

[ Change Location ]
🏛️ Authority Review Workflow

For the hackathon, SPANDAN does not directly submit complaints to a real government system.

Instead, the complaint enters a simulated authority workflow.

Citizen
   ↓
SPANDAN AI
   ↓
Complaint Processing
   ↓
PENDING_AUTHORITY_REVIEW
   ↓
Authority Email
   │
   ├───────────────┐
   │               │
 ACCEPT          REJECT
   │               │
   ▼               ▼
ACCEPTED       REJECTED
                   │
                   ▼
               ESCALATED
                   │
                   ▼
           HIGHER AUTHORITY
                   │
                   ▼
                REVIEW

This allows judges to see a realistic end-to-end workflow without requiring access to actual government infrastructure.

📧 Authority Email Workflow

When a complaint reaches authority review, SPANDAN sends an email containing:

SPANDAN AI — Civic Grievance Review

Tracking ID: SPN-XXXXXX

Issue:
Streetlight not working

Location:
Ramapuram

Department:
Electrical

Jurisdiction:
Ward 12

SLA:
7 days

[ ACCEPT COMPLAINT ]

[ REJECT / ESCALATE ]

The authority can make a decision directly from the email.

🔐 Secure Review Links

Authority actions use secure, one-time review tokens.

Complaint
    ↓
Generate random token
    ↓
Store token
    ↓
Send email
    ↓
Authority clicks link
    ↓
Validate token
    ↓
Perform action
    ↓
Invalidate token

The system should validate:

Token exists
Token has not expired
Token has not already been used
Token belongs to the correct complaint
Requested action is valid

Credentials are never hardcoded into the source code.

🔄 Complaint Lifecycle

The complaint can move through states such as:

CREATED
   ↓
UNDERSTOOD
   ↓
CLASSIFIED
   ↓
DRAFTED
   ↓
PENDING_AUTHORITY_REVIEW
   ↓
ACCEPTED_BY_AUTHORITY
   ↓
IN_PROGRESS
   ↓
MONITORING
   ↓
RESOLVED
   ↓
CLOSED

If the authority rejects the complaint:

PENDING_AUTHORITY_REVIEW
        ↓
     REJECTED
        ↓
    ESCALATED
        ↓
HIGHER_AUTHORITY_REVIEW
        ↓
ACCEPTED_BY_HIGHER_AUTHORITY
        ↓
     IN_PROGRESS

Every important state transition is recorded in the audit trail.

🤖 AI Agents

SPANDAN AI follows an agent-oriented architecture.

1. Intake Agent

Understands citizen input.

Extracts:

Issue
Location
Duration
Language
Missing information
2. Language Detection

Determines the citizen's language using multiple signals.

The system avoids unnecessary LLM calls.

3. Location Resolver

Combines:

GPS
Voice
Text
Manual selection

to identify the relevant jurisdiction.

4. Classification Agent

Determines:

Complaint category
Department
Authority
Jurisdiction
5. Civic RAG

Retrieves relevant civic information such as:

Department responsibilities
Jurisdiction rules
SLA timelines
Escalation rules
Required information
6. Drafting Agent

Converts the structured complaint into a formal grievance.

Example:

Citizen Input:

"Street light near my house has not been working
for the last five days."

↓

Structured Complaint:

Issue:
Streetlight failure

Duration:
5 days

Location:
Ramapuram

Department:
Electrical

↓

Formal Complaint:

A streetlight in Ramapuram has reportedly
remained non-functional for five days.
The issue is affecting visibility and public safety.
7. Filing Agent

Handles submission into the simulated government workflow.

It generates:

Tracking ID
Government reference ID
Submission timestamp
8. Watchdog Agent

The Watchdog continues monitoring after submission.

Complaint Filed
      ↓
SLA Stored
      ↓
Monitoring
      ↓
Warning Deadline
      ↓
Check Status
      ↓
SLA Breach
      ↓
Escalation

The Watchdog does not continuously ask an LLM what to do.

Escalation follows predefined policies.

🧠 Selective AI

SPANDAN does not use an expensive LLM for every operation.

The target architecture is:

Cheap / Deterministic Processing
              ↓
       Confidence Check
              ↓
       Is AI necessary?
          /        \
        No          Yes
        ↓            ↓
     Result       AI / LLM

Examples:

Script detection → deterministic
Known location lookup → local data
SLA calculation → deterministic
Status transition → policy engine
Language ambiguity → LLM verification
Complex complaint understanding → LLM

This reduces unnecessary computation and improves response time.

⚡ Fast User Experience

The citizen should not have to wait for the complete AI pipeline.

Target experience:

Citizen submits
      ↓
Fast acknowledgement
      ↓
Tracking ID
      ↓
Background processing
      ↓
Citizen can leave
      ↓
SPANDAN continues working

The frontend should remain simple.

Citizen interface
SPANDAN AI

How can we help?

        🎤
      SPEAK

or

[ Type your complaint ]

Location:
[ Use my location ]
[ Tell location ]
[ Enter location ]

Language:
[ Auto Detect ]

[ Submit Complaint ]

After submission:

Complaint Received ✓

Tracking ID:
SPN-XXXXXX

SPANDAN AI is processing your complaint.

You can leave this page.
📊 Citizen Tracking

Citizens can use the tracking ID to see the complaint status.

Example:

SPN-2026-001234

✓ Complaint received
✓ Complaint understood
✓ Authority identified
✓ Complaint submitted for review
✓ Authority accepted
● Work in progress
○ Resolution

The citizen does not need to understand the internal AI pipeline.

📝 Audit Trail

Every important action is logged.

Example:

10:30 AM
Complaint received

10:30 AM
Language detected: Telugu

10:31 AM
Issue extracted

10:31 AM
Location resolved

10:31 AM
Department identified

10:32 AM
Complaint drafted

10:32 AM
Authority review requested

10:40 AM
Authority accepted complaint

10:41 AM
Monitoring started

This provides transparency and makes the system easier to demonstrate and debug.

🏗️ Architecture

High-level architecture:

                 CITIZEN
                    │
             Voice / Text
                    │
                    ▼
             ┌─────────────┐
             │   FastAPI   │
             └─────────────┘
                    │
                    ▼
             Intake Service
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
     Language             Location
     Detection            Resolver
          │                   │
          └─────────┬─────────┘
                    ▼
              Classification
                    │
                    ▼
                 Civic RAG
                    │
                    ▼
                Drafting
                    │
                    ▼
                 Filing
                    │
                    ▼
          Authority Review
             │          │
          Accept      Reject
             │          │
             ▼          ▼
        Monitoring   Escalation
             │          │
             └────┬─────┘
                  ▼
              Watchdog
                  │
                  ▼
            Citizen Tracking
📦 Event-Driven Architecture

For larger deployments, the system can evolve toward:

Citizens
   │
   ▼
API Gateway
   │
   ▼
Intake
   │
   ▼
Event / Job Queue
   │
   ├── Language Worker
   ├── Intake Worker
   ├── Location Worker
   ├── Classification Worker
   ├── RAG Worker
   ├── Drafting Worker
   ├── Filing Worker
   └── Watchdog Worker

Workers should remain as stateless as possible.

Persistent complaint state belongs in the database.

The current hackathon prototype does not claim to support billions of users. The architecture is designed so that components can later be replaced with distributed infrastructure.

📈 Scalability Strategy

The system follows several scalability principles:

Stateless workers

Workers should not depend on local process memory for important workflow state.

Asynchronous processing

Long-running operations should run in background jobs.

Selective AI

Use expensive AI only when necessary.

Caching

Stable information such as civic rules and frequently accessed locations can be cached.

Event-driven Watchdog

Avoid continuous polling and unnecessary LLM calls.

Horizontal scaling

Workers can be replicated independently.

Future production infrastructure could include:

Distributed queues
Kafka / Pulsar
Redis
Distributed databases
Kubernetes
Cloud workers
API gateways
Regional deployment
Observability infrastructure

These are future production concerns and are intentionally not required for the hackathon MVP.

🛡️ Safety & Trust

SPANDAN AI follows a constrained-autonomy model.

The AI does not have unrestricted authority.

Important decisions such as:

Status transitions
SLA calculations
Escalation
Authority actions

are controlled by deterministic rules and policies.

The AI can recommend or prepare information, while authority decisions remain explicitly controlled.

🔐 Privacy & Security

Security principles include:

No hardcoded credentials
Environment variables for secrets
Secure review tokens
One-time action links
Token expiration
Input validation
API validation
Audit logging
Least-privilege access
Persistent workflow state
Safe failure handling

Never commit .env files to GitHub.

⚠️ Failure Handling

The complaint should not disappear if a downstream service fails.

Examples:

LLM unavailable

Use deterministic/local fallback where possible.

Speech recognition fails

Ask the citizen to retry or use text.

Location service fails

Allow manual location input.

RAG fails

Continue with safe fallback information where appropriate.

Authority email fails

Keep complaint in:

PENDING_AUTHORITY_REVIEW

and allow retry.

Worker crashes

Persistent workflow state allows the job to be retried.

Duplicate request

Use idempotency to prevent duplicate complaint submission.

🧪 Example Demo
Scenario

A citizen speaks in Tamil:

"எங்கள் தெருவில் தெருவிளக்கு ஐந்து நாட்களாக வேலை செய்யவில்லை."

Meaning:

"The streetlight in our street has not been working for five days."

SPANDAN processes the complaint:

Language:
Tamil

Issue:
Streetlight not working

Duration:
5 days

Location:
Detected / confirmed locality

Department:
Electrical

Jurisdiction:
Relevant municipal authority

Then:

Complaint drafted
       ↓
Tracking ID generated
       ↓
Authority review email
       ↓
Authority accepts
       ↓
Status updated
       ↓
Watchdog starts monitoring

If rejected:

Authority rejects
       ↓
Complaint escalated
       ↓
Higher authority notified
       ↓
Higher authority reviews
🏆 What Makes SPANDAN AI Different?
Traditional chatbot
Citizen
   ↓
Question
   ↓
AI answer
   ↓
Conversation ends
SPANDAN AI
Citizen
   ↓
Complaint
   ↓
Understand
   ↓
Locate
   ↓
Classify
   ↓
Draft
   ↓
Submit
   ↓
Track
   ↓
Monitor
   ↓
Escalate
   ↓
Follow through

The key difference is persistent action after the user's interaction ends.

🛠️ Technology Stack
Frontend
React
TypeScript
Vite
Tailwind CSS
Browser Speech Recognition
Multilingual UI / i18n
Backend
Python
FastAPI
Pydantic
Async processing
AI
Gemini API
Optional AI provider abstraction
Speech-to-text
Multilingual language detection
Embeddings
Lightweight language classifier
LLM verification
Data
PostgreSQL
SQLAlchemy / existing repository layer
ChromaDB / vector store for RAG
Scheduling / Background Work
APScheduler
Background job abstractions
External Simulation
Mock Government API
Authority email workflow
📁 Project Structure
agentx-civic-grievance/
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── i18n/
│       ├── pages/
│       ├── services/
│       ├── types/
│       ├── App.tsx
│       ├── config.ts
│       ├── index.css
│       └── main.tsx
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
│   │   ├── prompts/
│   │   ├── repositories/
│   │   ├── schemas/
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
└── docker-compose.yml
🚀 Running Locally
Backend
cd backend

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

uvicorn app.main:app --reload

Backend:

http://localhost:8000

API documentation:

http://localhost:8000/docs
Frontend

Open another terminal:

cd frontend

npm install

npm run dev

Frontend:

http://localhost:5173
🔑 Environment Variables

Create a local .env file.

Example:

GEMINI_API_KEY=your_gemini_api_key

DATABASE_URL=your_database_url

AUTHORITY_REVIEW_EMAIL=authority@example.com

HIGHER_OFFICIAL_EMAIL=higher@example.com

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_password
SMTP_FROM_EMAIL=your_email@example.com
Important

Never commit .env to GitHub.

Only commit:

.env.example
🧪 Testing

The project should test:

Intake
Text complaints
Voice complaints
Missing information
Regional languages
Language
Telugu
Tamil
Kannada
Hindi
English
Romanized regional languages
Code-mixed language
Short/noisy inputs
Location
GPS
Spoken location
Typed location
Manual location
Low-confidence location
Workflow
Complaint creation
Authority acceptance
Authority rejection
Escalation
Higher authority acceptance
Duplicate requests
Expired review token
Used review token
Watchdog
SLA warning
SLA breach
Escalation
🔮 Future Roadmap
Phase 1 — Hackathon MVP
Voice/text intake
Multilingual support
Location resolution
Classification
Civic RAG
Complaint drafting
Authority review
Email workflow
Tracking
Watchdog
Escalation
Audit trail
Phase 2 — Real Authority Integration

Replace the mock government workflow with real APIs where officially available.

Phase 3 — Officer Workspace

Add:

Officer authentication
Complaint assignment
Officer status updates
Authority dashboard
Workload monitoring
Phase 4 — Google Workspace Integration

Optional integration with:

Google OAuth
Google Workspace
Google Docs
Google Drive
Phase 5 — Large-Scale Deployment

Potential infrastructure:

Distributed event bus
Distributed workers
Regional deployments
Database partitioning
Distributed caching
Autoscaling
Observability
Rate limiting
Notification infrastructure
🎬 Hackathon Demo Flow

A recommended demonstration:

1. Start with the problem

Show how difficult it can be for a citizen to know:

Where should I complain?

Who is responsible?

What happens after I complain?

2. Citizen speaks

Use a regional-language complaint.

Show:

Language detection
Transcript
Issue
Location
Duration
3. Location confirmation

Show:

We found:
Ramapuram, Chennai

Is this correct?

[Yes] [Change]
4. AI processing

Show a simple progress timeline:

✓ Complaint received
✓ Understanding complaint
✓ Identifying authority
✓ Preparing complaint
✓ Sending for authority review
5. Authority receives email

Show the review email:

[ ACCEPT COMPLAINT ]

[ REJECT / ESCALATE ]
6. Accept workflow

Click:

ACCEPT COMPLAINT

Then show:

ACCEPTED_BY_AUTHORITY

and the citizen tracking page updates.

7. Escalation workflow

For the second scenario:

REJECT
   ↓
ESCALATED
   ↓
HIGHER AUTHORITY REVIEW

This demonstrates that SPANDAN doesn't stop after rejection.

8. Watchdog

Show:

SLA:
7 days

Status:
MONITORING

Warning:
Approaching SLA deadline

Then demonstrate an SLA breach and policy-based escalation.

💬 One-Line Pitch

SPANDAN AI is an autonomous civic grievance agent that lets citizens report issues in their own language and continues tracking, monitoring, and escalating the complaint even after they leave.

🎤 Short Hackathon Pitch

"Today, reporting a civic problem is often the easy part. The difficult part is knowing who is responsible, whether the complaint was accepted, and what happens after submission.

SPANDAN AI changes this.

A citizen can simply speak or type a complaint in their own language. SPANDAN understands the issue, resolves the location, identifies the responsible authority, prepares the complaint, sends it for authority review, and gives the citizen a tracking ID.

But our key difference is what happens next.

The citizen can leave.

SPANDAN continues monitoring the complaint, watches the SLA, and escalates it when required.

Submit once. SPANDAN follows through."

⚠️ Project Scope

SPANDAN AI is currently a hackathon prototype.

The government interaction is simulated using an authority-review workflow and email-based approval.

It does not claim to directly operate real government systems or physically resolve civic problems.

In a production deployment, official government APIs, authentication, authority systems, notification infrastructure, legal requirements, and security controls would need to be integrated.

👥 Team

Project: SPANDAN AI
Internal Architecture Name: AGENT X
Domain: AI / Agentic AI / Civic Technology / NLP
Platform: Web Application

🚀 Vision

SPANDAN AI aims to move civic technology from:

"A portal where citizens submit complaints"

to:

"An intelligent system that follows the complaint through its lifecycle."

The long-term goal is a privacy-conscious, multilingual, scalable civic agent that helps citizens navigate complex public-service workflows without requiring them to understand the underlying administrative structure.
  [Phase 1–4 consolidation report](docs/PHASE_1_4_CONSOLIDATION_REPORT.md).
