"""Complaint lifecycle state machine (foundation).

Phase 1 defines the allowed transitions and a checker. Later phases call
`ensure_transition` before changing a complaint's status, so an invalid jump
(e.g. CREATED -> ESCALATED) is rejected in one place.
"""

from __future__ import annotations

from app.core.errors import InvalidStateTransitionError
from app.schemas.enums import ComplaintStatus as S

# Authority can close a complaint at any point after it is filed.
_POST_FILING_EXITS = {S.RESOLVED, S.CLOSED}

# Phase 2 (intake): CREATED -> NEEDS_INFO <-> UNDERSTANDING -> UNDERSTOOD (citizen confirms).
# A correction after confirmation reopens the intake (UNDERSTOOD -> UNDERSTANDING/NEEDS_INFO).
# CREATED/NEEDS_INFO -> UNDERSTOOD stay allowed for the generic Phase 1 contract, but the
# intake service only reaches UNDERSTOOD through citizen confirmation.
# Phase 3 (classification): UNDERSTOOD -> CLASSIFYING -> CLASSIFIED | NEEDS_INFO | NEEDS_REVIEW.
# After the citizen answers a Phase 3 question: NEEDS_INFO -> CLASSIFYING -> ... again.
# There is no direct edge into CLASSIFIED: classification must run (CLASSIFYING) first.
ALLOWED_TRANSITIONS: dict[S, frozenset[S]] = {
    S.CREATED: frozenset({S.UNDERSTANDING, S.UNDERSTOOD, S.NEEDS_INFO}),
    S.NEEDS_INFO: frozenset({S.UNDERSTANDING, S.UNDERSTOOD, S.CLASSIFYING}),
    S.UNDERSTANDING: frozenset({S.UNDERSTOOD, S.NEEDS_INFO}),
    S.UNDERSTOOD: frozenset({S.CLASSIFYING, S.NEEDS_INFO, S.UNDERSTANDING}),
    S.CLASSIFYING: frozenset({S.CLASSIFIED, S.NEEDS_INFO, S.NEEDS_REVIEW}),
    S.CLASSIFIED: frozenset({S.DRAFTING, S.NEEDS_INFO, S.NEEDS_REVIEW}),
    # Phase 4: DRAFTING = draft generated, awaiting citizen review; DRAFTED = citizen approved.
    # Editing an approved draft reopens the review (DRAFTED -> DRAFTING).
    S.DRAFTING: frozenset({S.DRAFTED}),
    S.NEEDS_REVIEW: frozenset({S.CLASSIFYING, S.CLOSED}),
    # Citizen correction sends the complaint back through intake.
    S.DRAFTED: frozenset({S.DRAFTING, S.FILED, S.FILING_FAILED, S.UNDERSTOOD}),
    S.FILING_FAILED: frozenset({S.FILED}),
    S.FILED: frozenset({S.MONITORING}),
    S.MONITORING: frozenset({S.WARNING} | _POST_FILING_EXITS),
    S.WARNING: frozenset({S.BREACHED} | _POST_FILING_EXITS),
    S.BREACHED: frozenset({S.ESCALATED} | _POST_FILING_EXITS),
    S.ESCALATED: frozenset(_POST_FILING_EXITS),
    S.RESOLVED: frozenset({S.CLOSED}),
    S.CLOSED: frozenset(),
}

TERMINAL_STATUSES: frozenset[S] = frozenset({S.CLOSED})
ACTIVE_MONITORING_STATUSES: frozenset[S] = frozenset(
    {S.MONITORING, S.WARNING, S.BREACHED, S.ESCALATED}
)


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: S, target: S) -> None:
    if not can_transition(current, target):
        raise InvalidStateTransitionError(
            f"Complaint cannot move from {current.value} to {target.value}"
        )
