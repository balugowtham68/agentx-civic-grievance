# SPANDAN AI — Scalable Autonomous Civic Architecture

> **Core Product Thesis**: *"The citizen submits once. SPANDAN AI continues working after the citizen leaves."*

This document details the event-driven, asynchronous architecture and scalability strategy for the SPANDAN AI autonomous civic grievance redressal platform.

---

## 1. Architectural Philosophy

Traditional civic complaint platforms block citizen requests while running heavyweight classification, translation, and routing pipelines synchronously. This creates high bounce rates on mobile networks and fails gracefully handling multi-lingual voice inputs.

SPANDAN AI flips this model:

```
[ Citizen Input ] (Voice / Regional Text)
       │
       ▼  < 100ms
[ Fast Acknowledgement API ] ──► Returns Tracking ID: SPN-XXXXXX immediately
       │
       ▼ (Asynchronous Event Dispatch)
[ Autonomous Pipeline Workers ] (Multi-stage Background Pipeline)
       │
       ├─► 1. Language & Issue Extraction (Multi-signal Language Fusion)
       ├─► 2. Geolocation & Ward Routing (Multi-signal Civic Resolver)
       ├─► 3. Classification & Civic RAG (Charter-based Department Assignment)
       ├─► 4. Autonomous Petition Drafting (Verified against rules)
       ├─► 5. Government Portal Filing (SLA Clock Initialized)
       └─► 6. Autonomous Watchdog (Continuous SLA Monitoring & Automated Escalation)
```

---

## 2. Event-Driven Architecture

### Domain Events (`app.core.events.schemas`)

All domain transitions emit strongly typed, immutable `DomainEvent` records:

- `complaint.received`
- `intake.completed`
- `location.resolved`
- `classification.completed`
- `draft.generated`
- `complaint.filed`
- `sla.monitored`
- `complaint.escalated`

Each event carries:
- `event_id`: UUIDv4
- `complaint_id`: Target grievance ID
- `occurred_at`: ISO UTC timestamp
- `payload`: Stage-specific structured metadata
- `idempotency_key`: Deduplication key

### Async Event Bus & Job Queue

1. **AsyncEventBus (`app.core.events.bus`)**:
   - In-process, decoupled publisher-subscriber bus.
   - Dispatches handlers asynchronously with non-blocking concurrency.
   - Built-in idempotency deduplication prevents duplicate event execution.

2. **LocalJobQueue (`app.core.events.queue`)**:
   - Concurrency-controlled worker pool (default 2 workers per instance).
   - Exponential backoff retries (3 attempts).
   - Dead-letter queue for unrecoverable failures.
   - Swap-in ready for Celery, Redis Streams, or Apache Kafka.

---

## 3. Fast Acknowledgement Pattern (< 500ms)

When a citizen reports a grievance:
- `POST /api/v1/complaints/submit`:
  - Validates and sanitizes text/audio input.
  - Generates memorable, high-visibility tracking ID: `SPN-XXXXXX` (e.g. `SPN-3B1336`).
  - Persists record with initial status `RECEIVED`.
  - Dispatches `process_complaint` job to the background queue.
  - Returns `FastSubmissionResponse` in **< 100ms**.
- The citizen UI immediately transitions to the live timeline stepper while the background workers autonomously progress the issue through the 6 stages.

---

## 4. Multi-Signal Location Resolution

Civic grievances rarely contain precise GPS coordinates. Citizens mention landmarks, colony names, street names, or regional spelling variations.

SPANDAN AI implements `LocalCivicResolver` (`app.services.location.resolver`):

1. **Precision Ward Geocoding**:
   - Resolves localities across major municipal corporations (GHMC Hyderabad, GCC Chennai, BBMP Bengaluru, VMC Vijayawada).
   - Maps natural colloquial names (e.g., *"మాదాపూర్"*, *"T Nagar"*, *"Koramangala 8th block"*) to official civic Ward IDs and Jurisdictions (`GHMC-104`, `GCC-134`, `BBMP-151`).
2. **LRU Cached Resolver (`CachedLocationResolver`)**:
   - In-memory thread-safe caching of frequently resolved localities.
3. **Citizen Confirmation Option**:
   - Exposes `POST /api/v1/complaints/{id}/location/confirm` allowing citizens to adjust or confirm their resolved ward inline.

---

## 5. Tiered AI Compute Strategy

To minimize latency, cost, and API rate limits, SPANDAN AI applies a 3-tier compute model:

| Tier | Technique | Latency | Cost | Used For |
|---|---|---|---|---|
| **Tier 1: Heuristic / Rule** | Regex, Unicode script detection, N-gram tables | < 5ms | $0 | Fast script detection, common civic keyword matching, local landmark extraction |
| **Tier 2: Lexical / Embedding** | Hashing n-gram embeddings + Cosine similarity | < 25ms | $0 | Knowledge base retrieval, civic charter department routing |
| **Tier 3: Generative LLM** | Gemini (`gemini-3.8-flash`) structured generation | ~ 800ms | Minimal | Code-mixed multi-lingual translation, nuanced formal legal drafting, clarification dialogue |

---

## 6. Autonomous Watchdog & SLA Monitoring

Once a complaint is filed with the civic authority:
1. `WatchdogService` runs periodic cycles evaluating all active complaints against their departmental SLA deadlines.
2. If authority resolution stalls:
   - Evaluates progress milestones (`RECEIVED` → `IN_PROGRESS` → `RESOLVED`).
   - If approaching deadline: emits `sla.warning`.
   - If SLA is breached: triggers automatic formal escalation to senior zonal commissioner and logs an immutable `AuditEvent`.

---

## 7. Production Horizontal Scalability Roadmap

The abstractions in `app.core.events` and `app.core.cache` were designed to allow zero-downtime transition to distributed cloud infrastructure:

```
[ Load Balancer (NGINX / ALB) ]
           │
  ┌────────┴────────┐
  ▼                 ▼
[ SPANDAN Web 1 ] [ SPANDAN Web 2 ]  ──► Fast Acknowledgement (< 100ms)
  │                 │
  └────────┬────────┘
           ▼
[ Distributed Message Broker: Redis Streams / Kafka ]
           │
  ┌────────┴────────┬────────┐
  ▼                 ▼        ▼
[ Worker 1 ]   [ Worker 2 ] [ Watchdog Daemon ]
  │                 │        │
  └────────┬────────┴────────┘
           ▼
[ PostgreSQL Primary + Read Replicas ]
```
