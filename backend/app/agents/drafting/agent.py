"""Agent 3 - Complaint Drafting (Phase 4).

DraftFactSet (fact-locked Phase 2 + Phase 3 output)
  -> deterministic template draft (always built, offline)
  -> validation
  -> optional AI rewording via the existing AIProvider (never authoritative)
  -> validation of the AI wording + required facts still present
  -> accept (MIXED) or fall back to the template draft (FALLBACK_USED)

The agent never re-classifies, never changes department or jurisdiction, and
never produces tracking IDs or claims of filing, government action or resolution.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.agents.base import AgentContext, BaseAgent
from app.agents.drafting.builder import (
    build_sections,
    chronology,
    compose_body,
    evidence_references,
    supporting_facts,
)
from app.agents.drafting.config import DraftingConfig
from app.agents.drafting.validator import DraftValidator
from app.core.errors import AppError
from app.core.languages import LanguageRegistry
from app.prompts.drafting import AIDraftOutput, drafting_prompt
from app.repositories import ReferenceRepository
from app.schemas.drafting import (
    ComplaintDraft,
    DraftFactSet,
    DraftingRequest,
    DraftingResult,
    DraftOrigin,
    DraftSections,
    DraftValidationStatus,
    ReviewStatus,
)
from app.schemas.enums import AgentName
from app.schemas.intake import ProcessingMode, ProviderTraceStep
from app.services.ai import AIProvider

INSTRUCTION_FLAG = "instruction_like_text"


class DraftValidationError(AppError):
    status_code = 422
    code = "draft_validation_failed"


class DraftingAgent(BaseAgent[DraftingRequest, DraftingResult]):
    name = AgentName.DRAFTING
    description = "Drafts a grounded, reviewable administrative complaint from the classified facts"
    phase = 4
    input_model = DraftingRequest
    output_model = DraftingResult

    def __init__(
        self, ai: AIProvider, reference: ReferenceRepository, config: DraftingConfig, registry: LanguageRegistry
    ) -> None:
        self.ai = ai
        self.reference = reference
        self.config = config
        self.registry = registry

    @property
    def validator(self) -> DraftValidator:
        return DraftValidator(self.config, self.reference.data)

    def language_name(self, code: str) -> str:
        info = self.registry.get(code)
        return info.display_name if info else code

    async def _run(self, payload: DraftingRequest, context: AgentContext) -> DraftingResult:
        facts = payload.facts
        trace: list[ProviderTraceStep] = []
        rejected: list[str] = []

        sections = build_sections(facts, self.config)
        report = self.validator.validate(sections, self.body(sections, facts, statement=False), facts)
        if not report.ok:  # a configuration error, never shipped as a draft
            raise DraftValidationError("The template draft failed validation: " + "; ".join(report.hard + report.soft))
        trace.append(ProviderTraceStep(stage="validation", provider="draft_templates", outcome="used", detail=self.config.version))

        status = DraftValidationStatus.VALID
        mode = ProcessingMode.OFFLINE_RULE
        improved = await self._ai_wording(facts, sections, trace, rejected)
        if improved is not None:
            sections, mode = improved, ProcessingMode.MIXED
        elif rejected:
            status = DraftValidationStatus.FALLBACK_USED

        draft = self.assemble(
            facts, sections, draft_id=payload.draft_id, version=payload.version, origin=DraftOrigin.GENERATED,
            based_on=None, status=status, issues=rejected, mode=mode, draft_language=payload.draft_language,
            created_by="agent", now=context.clock.now(),
        )
        return DraftingResult(draft=draft, provider_trace=trace, rejected_ai_output=rejected)

    # ------------------------------------------------------------------ optional AI

    async def _ai_wording(
        self, facts: DraftFactSet, template: DraftSections, trace: list[ProviderTraceStep], rejected: list[str]
    ) -> DraftSections | None:
        provider = getattr(self.ai, "name", "ai")
        if not getattr(self.ai, "available", False):
            trace.append(ProviderTraceStep(stage="drafting", provider=provider, outcome="unavailable", detail="template wording only"))
            return None
        prompt = drafting_prompt(
            facts={
                "issue": facts.issue.value, "issue_citizen_words": facts.issue.citizen_words,
                "location_citizen_words": facts.location.citizen_words, "resolved_place": facts.resolved_place,
                "duration": facts.duration.value if facts.duration else None,
                "category": facts.category_name, "department": facts.department_name,
                "jurisdiction": facts.jurisdiction_name,
            },
            template_draft=template.model_dump(),
            citizen_statement=facts.original_text,
            reference=facts.service_guideline,
        )
        try:
            output = await self.ai.generate_structured(prompt, AIDraftOutput)
        except Exception as exc:  # noqa: BLE001 - optional step; the template draft stands
            reason = "malformed output" if "validation" in type(exc).__name__.lower() else type(exc).__name__
            trace.append(ProviderTraceStep(stage="drafting", provider=provider, outcome="failed", detail=reason))
            rejected.append(f"AI wording unavailable ({reason}); template draft used")
            return None
        sections = DraftSections(**output.model_dump())
        report = self.validator.validate(sections, self.body(sections, facts, statement=False), facts)
        problems = report.hard + report.soft + [f"drops {m}" for m in self.validator.missing_facts(sections, facts)]
        if problems:
            rejected.extend(f"AI wording rejected: {p}" for p in problems)
            trace.append(ProviderTraceStep(stage="validation", provider=provider, outcome="rejected", detail="; ".join(problems)[:300]))
            return None
        trace.append(ProviderTraceStep(stage="drafting", provider=provider, outcome="used", detail="wording checked against the locked facts"))
        return sections

    # ------------------------------------------------------------------ assembly (shared with citizen edits)

    def body(self, sections: DraftSections, facts: DraftFactSet, *, statement: bool) -> str:
        return compose_body(sections, facts, include_statement=statement, language_name=self.language_name(facts.citizen_language))

    def assemble(
        self,
        facts: DraftFactSet,
        sections: DraftSections,
        *,
        draft_id: str,
        version: int,
        origin: DraftOrigin,
        based_on: int | None,
        status: DraftValidationStatus,
        issues: list[str],
        mode: ProcessingMode,
        draft_language: str,
        created_by: str,
        now: datetime | None = None,
        citizen_added: list[str] | None = None,
    ) -> ComplaintDraft:
        include_statement = INSTRUCTION_FLAG not in facts.safety_flags
        notes: list[str] = []
        if draft_language not in self.config.draft_languages:
            notes.append(
                f"Drafting in {self.language_name(draft_language)} is not available offline; the draft is in English."
            )
        if facts.citizen_language != "en":
            notes.append(
                f"The citizen wrote in {self.language_name(facts.citizen_language)}. The draft is in English and "
                "quotes the citizen's own words; no machine translation was generated."
            )
        if not include_statement:
            notes.append(
                "The citizen's full statement contained instruction-like text, so only the confirmed facts are "
                "used in the draft; the statement stays on the complaint record."
            )
        wording = {
            ProcessingMode.MIXED: "optional AI wording, checked against your confirmed facts",
        }.get(mode, "offline templates (no external AI)")
        explanation = (
            "Draft generated from your confirmed complaint details (Phase 2) and the classification result "
            f"(Phase 3: {facts.category_record_id} → {facts.department_id}"
            + (f", {facts.jurisdiction_id}" if facts.jurisdiction_id else "")
            + f"). Wording: {wording}. No facts were added; category, department and jurisdiction are copied "
            "from the classification and cannot be changed here."
        )
        if origin is DraftOrigin.CITIZEN_EDIT:
            explanation = f"Version {version} contains your own edits of version {based_on}. " + explanation
        return ComplaintDraft(
            draft_id=draft_id,
            complaint_id=facts.complaint_id,
            version=version,
            origin=origin,
            based_on_version=based_on,
            sections=sections,
            body=self.body(sections, facts, statement=include_statement),
            category=facts.category,
            category_name=facts.category_name,
            department_id=facts.department_id,
            department_name=facts.department_name,
            jurisdiction_id=facts.jurisdiction_id,
            jurisdiction_name=facts.jurisdiction_name,
            location={
                "citizen_words": facts.location.citizen_words,
                "citizen_source": facts.location.source,
                "area_given_when_asked": "; ".join(a.citizen_words for a in facts.location_answers) or None,
                "resolved_place": facts.resolved_place,
                "jurisdiction_id": facts.jurisdiction_id,
                "precision": facts.location_precision,
                "basis": "prototype jurisdiction configuration (Phase 3)" if facts.jurisdiction_id else None,
            },
            duration=facts.duration.value if facts.duration else None,
            chronology=chronology(facts),
            supporting_facts=supporting_facts(facts),
            evidence_references=evidence_references(facts),
            source_ids=facts.source_ids,
            citizen_statement=facts.original_text if include_statement else None,
            citizen_language=facts.citizen_language,
            draft_language="en",
            language_note=" ".join(notes) or None,
            processing_mode=mode,
            validation_status=status,
            validation_issues=issues,
            citizen_added_information=citizen_added or [],
            review_status=ReviewStatus.PENDING_REVIEW,
            explanation=explanation,
            generated_at=now or datetime.now(UTC),
            created_by=created_by,  # type: ignore[arg-type]
            demo_data=facts.demo_data,
        )
