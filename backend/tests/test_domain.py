"""Domain rules established in Phase 1: state machine, schemas, reference data,
escalation defaults, agent and provider interfaces."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agents import ALL_AGENTS, AgentContext, BaseAgent, IntakeAgent
from app.core.config import Settings
from app.core.errors import (
    AgentExecutionError,
    InvalidStateTransitionError,
    NotImplementedYetError,
)
from app.core.security import sanitize_text
from app.core.state_machine import (
    ALLOWED_TRANSITIONS,
    can_transition,
    ensure_transition,
)
from app.repositories import ReferenceDataError, ReferenceRepository
from app.schemas.agents import (
    DraftedComplaint,
    FilingRequest,
    IntakeRequest,
    IntakeResponse,
)
from app.schemas.enums import AgentName, AuthorityStatus
from app.schemas.enums import ComplaintStatus as S
from app.schemas.mock_gov import MockGrievanceReceipt
from app.schemas.reference import EscalationPolicy, SLAPolicy
from app.services.ai import (
    AIProviderError,
    GeminiProvider,
    PromptSpec,
    build_ai_provider,
)

REPO_KB = Path(__file__).resolve().parents[2] / "knowledge_base"

# --- State machine ---------------------------------------------------------


def test_every_status_has_a_transition_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(S)


def test_main_lifecycle_path_is_allowed() -> None:
    path = [  # Phase 3: classification runs (CLASSIFYING); Phase 4: drafts are reviewed (DRAFTING)
        S.CREATED, S.UNDERSTOOD, S.CLASSIFYING, S.CLASSIFIED, S.DRAFTING, S.DRAFTED, S.FILED, S.MONITORING,
        S.WARNING, S.BREACHED, S.ESCALATED, S.RESOLVED, S.CLOSED,
    ]
    for current, target in zip(path, path[1:]):
        assert can_transition(current, target), f"{current} -> {target}"


def test_shortcuts_and_exits_from_closed_are_rejected() -> None:
    assert not can_transition(S.CREATED, S.ESCALATED)
    assert not can_transition(S.MONITORING, S.ESCALATED)  # must warn and breach first
    assert not can_transition(S.CLOSED, S.MONITORING)
    with pytest.raises(InvalidStateTransitionError):
        ensure_transition(S.DRAFTED, S.MONITORING)


def test_citizen_correction_and_filing_retry_are_supported() -> None:
    assert can_transition(S.DRAFTED, S.UNDERSTOOD)
    assert can_transition(S.FILING_FAILED, S.FILED)


# --- Reference data and escalation policy ---------------------------------


def test_repository_knowledge_base_config_is_valid() -> None:
    data = ReferenceRepository(REPO_KB).data

    assert {d.id for d in data.departments} >= {"DEPT-ELECTRICAL"}
    assert ReferenceRepository(REPO_KB).sla_policy("SLA-STREETLIGHT").duration_hours == 72


def test_default_terminal_states_exclude_acknowledged() -> None:
    policy = EscalationPolicy(
        id="ESC-T", name="t", categories=["streetlight"],
        levels=[{"level": 1, "target_authority_id": "AUTH-X"}],
    )

    assert policy.terminal_states == [AuthorityStatus.RESOLVED, AuthorityStatus.CLOSED]
    assert AuthorityStatus.ACKNOWLEDGED not in policy.terminal_states
    assert AuthorityStatus.IN_PROGRESS not in policy.terminal_states


def test_configured_demo_policy_does_not_treat_acknowledgement_as_terminal() -> None:
    policy = ReferenceRepository(REPO_KB).escalation_policy_for_category("streetlight")

    assert policy is not None
    assert AuthorityStatus.ACKNOWLEDGED not in policy.terminal_states


def test_policy_validation_rules() -> None:
    with pytest.raises(ValidationError, match="numbered 1..n"):
        EscalationPolicy(
            id="ESC-T", name="t", categories=["x"],
            levels=[{"level": 2, "target_authority_id": "AUTH-X"}],
        )
    with pytest.raises(ValidationError, match="warning_after_hours"):
        SLAPolicy(id="SLA-T", category="x", department_id="D", duration_hours=24, warning_after_hours=24)


def test_broken_reference_fails_fast(tmp_path: Path) -> None:
    import shutil

    kb = tmp_path / "kb"
    shutil.copytree(REPO_KB, kb)
    policies = kb / "timelines" / "sla_policies.json"
    policies.write_text(policies.read_text().replace("DEPT-ELECTRICAL", "DEPT-MISSING"))

    with pytest.raises(ReferenceDataError, match="unknown department DEPT-MISSING"):
        _ = ReferenceRepository(kb).data


def test_app_refuses_to_start_with_missing_knowledge_base(settings: Settings, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    broken = settings.model_copy(update={"knowledge_base_dir": tmp_path / "missing"})
    with pytest.raises(ReferenceDataError):
        with TestClient(create_app(broken)):
            pass


# --- Contracts --------------------------------------------------------------


def _draft() -> DraftedComplaint:
    return DraftedComplaint(
        issue="Streetlight not working", category="streetlight",
        department_id="DEPT-ELECTRICAL", jurisdiction_id="WARD-12",
        location="Near Ramalayam temple", description="d", requested_action="Repair",
        original_text="light not working",
    )


def test_filing_requires_citizen_confirmation() -> None:
    with pytest.raises(ValidationError, match="citizen confirmation"):
        FilingRequest(complaint_id="c1", draft=_draft(), citizen_confirmed=False)
    assert FilingRequest(complaint_id="c1", draft=_draft(), citizen_confirmed=True)


def test_mock_receipt_enforces_tracking_id_format_and_simulation_flag() -> None:
    receipt = MockGrievanceReceipt(tracking_id="CIV-2026-0001", received_at=datetime.now(UTC))
    assert receipt.simulation is True
    with pytest.raises(ValidationError):
        MockGrievanceReceipt(tracking_id="LOCAL-1", received_at=datetime.now(UTC))


def test_intake_response_only_allows_intake_statuses() -> None:
    with pytest.raises(ValidationError):
        IntakeResponse(
            complaint_id="c1", detected_language="te", transcript="t", translated_text="t",
            extracted={}, status=S.ESCALATED,
        )


def test_sanitize_text_keeps_indic_scripts_and_removes_control_chars() -> None:
    assert sanitize_text("नाली\x00 जाम   है\r\n") == "नाली जाम है"


# --- Agents and AI provider -------------------------------------------------


def test_five_agents_have_identity_and_contracts() -> None:
    assert [a.name for a in ALL_AGENTS] == list(AgentName)
    for agent_cls in ALL_AGENTS:
        assert issubclass(agent_cls, BaseAgent)
        assert agent_cls.description and agent_cls.phase >= 2
        assert agent_cls.input_model is not agent_cls.output_model


def test_unimplemented_agent_reports_its_phase_honestly() -> None:
    # Phase 3 implemented Classification (this test used it before); Filing is still Phase 5.
    from app.agents import FilingAgent
    from app.schemas.agents import FilingRequest

    agent = FilingAgent(mock_gov=None, reference=None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedYetError, match="Phase 5"):
        asyncio.run(
            agent.execute(
                FilingRequest(complaint_id="c1", draft=_draft(), citizen_confirmed=True),
                AgentContext("c1"),
            )
        )


def test_agent_rejects_wrong_input_contract() -> None:
    agent = IntakeAgent(ai=GeminiProvider(api_key=None, model="m"))

    with pytest.raises(AgentExecutionError, match="expected IntakeRequest"):
        asyncio.run(agent.execute(_draft(), AgentContext("c1")))  # type: ignore[arg-type]


def test_agent_wraps_unexpected_failures() -> None:
    class Exploding(IntakeAgent):
        async def _run(self, payload, context):  # type: ignore[no-untyped-def]
            raise KeyError("boom")

    with pytest.raises(AgentExecutionError, match="intake agent failed"):
        asyncio.run(
            Exploding(ai=GeminiProvider(None, "m")).execute(
                IntakeRequest(complaint_id="c1", text="hi"), AgentContext("c1")
            )
        )


def test_agent_rejects_wrong_output_contract() -> None:
    class Wrong(IntakeAgent):
        async def _run(self, payload, context):  # type: ignore[no-untyped-def]
            return _draft()

    with pytest.raises(AgentExecutionError, match="expected IntakeResponse"):
        asyncio.run(
            Wrong(ai=GeminiProvider(None, "m")).execute(
                IntakeRequest(complaint_id="c1", text="hi"), AgentContext("c1")
            )
        )


def test_ai_provider_is_built_from_settings_and_fails_safely_without_key() -> None:
    provider = build_ai_provider(Settings(_env_file=None))
    prompt = PromptSpec(name="intake.extract", version="v1", system="s", user="u")

    assert isinstance(provider, GeminiProvider) and not provider.configured
    with pytest.raises(AIProviderError, match="GEMINI_API_KEY"):
        asyncio.run(provider.generate_structured(prompt, DraftedComplaint))
