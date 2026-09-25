"""ORM models. Importing this package registers every table on Base.metadata.

Departments, jurisdictions, authorities and policies are configuration, not
database rows: they live in knowledge_base/ and are loaded by
app.repositories.reference_repository.
"""

from app.models.audit_event import AuditEvent
from app.models.complaint import Complaint, EscalationRecord, SLARecord

__all__ = ["AuditEvent", "Complaint", "EscalationRecord", "SLARecord"]
