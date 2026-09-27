# SPANDAN AI — Scalability & Production Architecture Guide

## 1. Executive Summary

SPANDAN AI is built on the core principle:
> **"The citizen submits once. SPANDAN continues working after the citizen leaves."**

To maintain this guarantee at state or national scale (serving millions of citizens across regional languages), the platform is structured around an **event-driven, decoupled, asynchronous pipeline**.

This guide outlines the architectural evolution path from the local hackathon deployment to a high-throughput, fault-tolerant distributed system.

---

## 2. Architectural Evolution Overview

```
[Citizen Layer]
  │ Mobile Web / Voice / PWA
  ▼
[Fast API Edge / Load Balancer] (Latency < 200ms)
  │ Immediate Fast Acknowledgement (SPN-XXXXXX)
  ▼
[Distributed Event Bus & Job Queue] (Kafka / Redis Streams)
  │
  ├─► [Intake & Language Workers] (Multi-signal acoustic/script fusion)
  ├─► [Location Resolution Workers] (Hierarchical geospatial gazetteer + reverse geocoding)
  ├─► [Classification & RAG Workers] (ChromaDB / Pinecone vector search + department taxonomy)
  ├─► [Drafting & Validation Workers] (Bilingual template synthesis + administrative fact-lock)
  ├─► [Filing & Lodging Workers] (Idempotent mock government API adapters)
  └─► [SLA Watchdog & Escalation Workers] (Distributed cron + deterministic deadline monitors)
```

---

## 3. Queue & Event Bus Migration

In the local environment, SPANDAN AI uses clean in-process abstractions:
- `LocalAsyncEventBus` (`app.core.events.bus`)
- `AsyncJobQueue` (`app.core.events.queue`)
- `IdempotencyManager` (`app.core.events.idempotency`)

### Production Migration: Apache Kafka & Redis Streams

| Component | Local / Prototype | Production Distributed Target | Rationale |
| :--- | :--- | :--- | :--- |
| **Event Streaming** | `LocalAsyncEventBus` | **Apache Kafka** or **AWS Kinesis** | Partitioning by `complaint_id` guarantees strictly ordered event streams per grievance while allowing parallel processing across partitions. |
| **Job Queue** | `AsyncJobQueue` | **Celery + Redis** or **ARQ / Temporal** | Durable job persistence, priority queues, automated exponential retries, and dead-letter queue (DLQ) support for unhandled exceptions. |
| **Idempotency** | In-Memory Set with Lock | **Redis `SETNX` with TTL (24h)** | Thread-safe, distributed deduplication across hundreds of worker nodes preventing double-filing or duplicate SLA notifications. |

### Event Partitioning & Ordering Guarantee
All domain events carry `complaint_id` as their partition key:
```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "event_type": "complaint.classified",
  "complaint_id": "c-482a-92f1",
  "correlation_id": "req-9812",
  "timestamp": "2026-09-27T07:30:00Z",
  "payload": {
    "department_id": "GHMC_WATER",
    "confidence": 0.94
  }
}
```
Because events for a given `complaint_id` hash to the same Kafka partition, state transitions (`RECEIVED` → `UNDERSTOOD` → `CLASSIFIED` → `DRAFTED` → `FILED` → `MONITORING`) are strictly linear and race-condition free.

---

## 4. Cache & Data Tier Scaling

### 1. Two-Tier Caching Architecture
- **L1 Cache (In-Memory per pod)**: Local LRU cache for static reference schemas, language marker models, and stopword gazetteers (`backend/data/knowledge_base/*.json`).
- **L2 Cache (Distributed Redis Cluster)**:
  - Geospatial Gazetteer bounding boxes (`HYDERABAD_BOUNDS`, `BENGALURU_BOUNDS`, etc.).
  - Rate limiting buckets per citizen IP / device.
  - Active tracking timelines (`GET /api/v1/complaints/{id}/timeline`) cached with 3-second TTL.

### 2. Database Scaling (PostgreSQL)
- **Connection Pooling**: PgBouncer sitting before PostgreSQL handles up to 10,000 idle citizen tracking connections without exhausting database worker threads.
- **Read/Write Splitting**:
  - **Primary Node**: Handles fast intake writes (`INSERT INTO complaints`), state transitions, and audit trail append-only records.
  - **Read Replicas (2–4 nodes)**: Handle citizen tracking lookups (`GET /timeline`, `GET /track/{tracking_id}`) and municipal authority dashboards.
- **Table Partitioning**:
  - `complaints` and `audit_events` partitioned by month and state/jurisdiction (e.g., `complaints_2026_09_telangana`).

---

## 5. Worker Pool Specialization & Auto-Scaling

Rather than running monolithic background workers, worker pods are specialized into three auto-scaling pools based on hardware profile:

### Pool A: Fast ML / Acoustic Workers (CPU-optimized)
- **Workload**: Multi-signal language detection (script ratios, n-gram classifiers, marker heuristics) and audio transcription chunks.
- **Scaling Metric**: Queue depth of `intake.audio.transcribe` (> 100 jobs triggers pod scale-out).

### Pool B: LLM & Semantic Reasoning Workers (I/O-optimized)
- **Workload**: Gemini / LLM calls for complex bilingual drafting, fallback disambiguation, and structured fact extraction.
- **Rate Limit Resilience**: Token bucket rate limiters per provider key; circuit breakers gracefully fallback to deterministic templates if upstream LLM latency exceeds 3.5 seconds.

### Pool C: Watchdog & SLA Monitor Workers (Lightweight Distributed Cron)
- **Workload**: Continuous checking of `deadline_at`, breach warning evaluation, and escalation notifications.
- **Scaling**: Fixed leader-follower pattern (using distributed lock via Redis Redlock) checking complaints in batches of 500 every 60 seconds.

---

## 6. Citizen Fast Acknowledgement Guarantee (< 2 Seconds)

At peak load (e.g., during urban floods or power grid failures), thousands of complaints may arrive concurrently.

To honor the **< 2 second acknowledgement guarantee**:
1. **Intake Endpoint (`POST /api/v1/complaints/submit`)**:
   - Performs zero synchronous LLM calls.
   - Performs zero external API calls.
   - Resolves location against local in-memory gazetteer (< 5ms).
   - Generates persistent `tracking_id` (`SPN-XXXXXX`) in PostgreSQL (< 15ms).
   - Enqueues background job payload to message queue (< 5ms).
   - Emits `202 Accepted` response to citizen in **< 100ms**.
2. **Citizen Experience**:
   - Citizen instantly receives their tracking receipt.
   - Citizen can immediately close the tab or share the tracking ID.
   - Autonomous workers asynchronously execute the heavy reasoning steps.

---

## 7. Privacy, Security & Data Protection

1. **Zero Raw Audio Storage**:
   - Audio recorded for regional voice detection is processed in-memory as streaming buffers and discarded immediately after transcription. No citizen voice recordings are stored permanently on disk.
2. **PII Masking**:
   - Phone numbers and citizen names are tokenized or stored in encrypted columns with access restricted to authorized grievance officers.
3. **Internal Log Hygiene**:
   - Internal LLM reasoning, chain-of-thought, and system prompts are never returned in citizen-facing timeline endpoints (`GET /timeline`). Only verified, citizen-safe progress descriptions are exposed.
