"""Agent 2 - Classification & Reasoning (Phase 3).

Confirmed Phase 2 handoff
  -> citizen evidence (original words, confirmed facts, answers to Phase 3 questions)
  -> local civic knowledge retrieval (ChromaDB, local embeddings)      => candidates
  -> deterministic rule validation (configured patterns, suppression, ambiguity groups)
  -> optional AI reasoning (only chooses among validated candidates; KB wins on conflict)
  -> department mapping from the KB (never invented)
  -> jurisdiction from the prototype jurisdiction configuration (never invented)
  -> category-specific required information
  -> evidence validation of the final decision
  -> CLASSIFIED | NEEDS_INFO | AMBIGUOUS | UNSUPPORTED_CLASSIFICATION

The knowledge base and its configured rules are the source of truth. Retrieval
alone never classifies; the optional AI never overrides a configured rule.
"""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.agents.classification.matching import CitizenText, CivicRuleSet, PlaceMatch
from app.core.logging import get_logger
from app.prompts.classification import AIClassificationOutput, classification_prompt
from app.repositories import ReferenceRepository
from app.schemas.classification import (
    Candidate,
    ClassificationAnswer,
    ClassificationEvidence,
    ClassificationRequest,
    ClassificationResult,
    ClassificationStatus,
    ConfidenceState,
    DepartmentAssignment,
    JurisdictionResult,
    JurisdictionStatus,
    LocationPrecision,
    ReasoningStep,
    RequiredInformation,
    RetrievedKnowledge,
    RuleMatch,
    ServiceTimelineRef,
)
from app.schemas.enums import AgentName, ComplaintStatus
from app.schemas.intake import (
    ClarificationQuestion,
    FactSource,
    IntakeHandoff,
    ProcessingMode,
    ProviderTraceStep,
)
from app.schemas.reference import AmbiguityGroup, CivicCategory, ReferenceData
from app.services.ai import AIProvider
from app.services.intake.offline.text import normalise
from app.services.knowledge import CivicKnowledgeBase

logger = get_logger(__name__)

_COMPLAINT_STATUS = {
    ClassificationStatus.CLASSIFIED: ComplaintStatus.CLASSIFIED,
    ClassificationStatus.NEEDS_INFO: ComplaintStatus.NEEDS_INFO,
    ClassificationStatus.AMBIGUOUS: ComplaintStatus.NEEDS_INFO,
    ClassificationStatus.UNSUPPORTED_CLASSIFICATION: ComplaintStatus.NEEDS_REVIEW,
}
DEMO_NOTE = "This is DEMO CIVIC RULE / prototype configuration, not official government policy."


class _Decision:
    """Mutable working state of one classification run."""

    def __init__(self) -> None:
        self.category: CivicCategory | None = None
        self.state = ConfidenceState.UNSUPPORTED
        self.status = ClassificationStatus.UNSUPPORTED_CLASSIFICATION
        self.category_matches: list[RuleMatch] = []
        self.ambiguous_keys: list[str] = []
        self.group: AmbiguityGroup | None = None
        self.from_configured_ambiguity = False
        self.reason = ""
        self.ai_accepted = False
        self.ai_agreed = False


class ClassificationAgent(BaseAgent[ClassificationRequest, ClassificationResult]):
    name = AgentName.CLASSIFICATION
    description = "Grounds category, department and jurisdiction in the configured civic knowledge base"
    phase = 3
    input_model = ClassificationRequest
    output_model = ClassificationResult

    def __init__(self, ai: AIProvider, retriever: CivicKnowledgeBase, reference: ReferenceRepository) -> None:
        self.ai = ai
        self.retriever = retriever
        self.reference = reference
        self._rules: CivicRuleSet | None = None

    @property
    def rules(self) -> CivicRuleSet:
        if self._rules is None:
            self._rules = CivicRuleSet(self.reference.data)
        return self._rules

    # ================================================================== run

    async def _run(self, payload: ClassificationRequest, context: AgentContext) -> ClassificationResult:
        data = self.reference.data
        settings = data.classification
        assert settings is not None  # validated at start-up
        handoff = payload.handoff
        language = handoff.language
        trace: list[ProviderTraceStep] = []
        reasoning: list[ReasoningStep] = []
        category_answers = [a for a in reversed(payload.answers) if a.asked_for == "category"]  # newest first
        locality_answers = [a for a in reversed(payload.answers) if a.asked_for == "locality"]

        # 1. Citizen evidence (authoritative). Translation is only a retrieval aid.
        issue_source = "correction" if handoff.issue.source is FactSource.CITIZEN_CORRECTION else "issue"
        issue_texts = [CitizenText(issue_source, handoff.issue.source_span)]
        if handoff.issue.source is FactSource.CITIZEN_CORRECTION:
            issue_texts.append(CitizenText("correction", handoff.issue.value))
        tiers = [[CitizenText("answer", a.text)] for a in category_answers]
        tiers += [issue_texts, [CitizenText("original_text", handoff.original_text)]]
        citizen_texts = [t for tier in tiers for t in tier] + self._location_texts(handoff, locality_answers)
        reasoning.append(ReasoningStep(step="citizen_evidence", detail=f"Citizen reported: “{handoff.issue.source_span}”."))

        # 2. Local retrieval -> candidates.
        retrieval = settings.retrieval
        queries = [handoff.original_text, handoff.issue.source_span, *(a.text for a in category_answers), handoff.issue.value]
        if handoff.translated_text:
            queries.append(handoff.translated_text)
        retrieved = self.retriever.retrieve(
            queries, top_k=retrieval.top_k, where={"record_type": "category"}, max_chars=retrieval.max_query_chars
        )
        best: dict[str, float] = {}
        for record in retrieved:
            if record.category and record.similarity >= retrieval.min_similarity:
                best[record.category] = max(best.get(record.category, 0.0), record.similarity)
        trace.append(ProviderTraceStep(
            stage="retrieval", provider=f"chromadb:{self.retriever.embedder.name}", outcome="used",
            detail=f"{len(retrieved)} record(s), top_k={retrieval.top_k}",
        ))
        reasoning.append(ReasoningStep(
            step="retrieval",
            detail="Local knowledge search returned: " + (", ".join(sorted(best)) or "no category above the similarity threshold"),
            source_ids=sorted({r.record_id for r in retrieved}),
        ))

        # 3. Deterministic rule validation.
        decision = self._decide(tiers, best, settings.retrieval.suggestion_similarity, settings.retrieval.max_suggestions)
        trace.append(ProviderTraceStep(stage="rules", provider="civic_rules", outcome="used", detail=decision.status.value))

        # 4. Jurisdiction (deterministic) - needed by the AI validation as well.
        jurisdiction, place_matches = self._jurisdiction(handoff, locality_answers, decision.category)

        # 5. Optional AI reasoning - validated, never authoritative.
        rejected_ai: list[str] = []
        await self._ai_step(handoff, payload, decision, retrieved, best, jurisdiction, citizen_texts, trace, reasoning, rejected_ai)

        # Candidates for transparency.
        candidates = self._candidates(decision, best)

        # 6. Department mapping, 7. required information, final status.
        department: DepartmentAssignment | None = None
        required: list[RequiredInformation] = []
        missing: list[str] = []
        questions: list[ClarificationQuestion] = []
        if decision.category is not None:
            jurisdiction, place_matches = self._jurisdiction(handoff, locality_answers, decision.category)
            department = self._department(data, decision.category)
            if department is None:
                decision.status = ClassificationStatus.UNSUPPORTED_CLASSIFICATION
                decision.state = ConfidenceState.UNSUPPORTED
                decision.reason = "the knowledge base has no valid department mapping for this category"
                trace.append(ProviderTraceStep(stage="department_mapping", provider="civic_kb", outcome="rejected",
                                               detail="no configured department"))
            else:
                trace.append(ProviderTraceStep(stage="department_mapping", provider="civic_kb", outcome="used",
                                               detail=department.department_id))
                reasoning.append(ReasoningStep(
                    step="department_mapping",
                    detail=f"{decision.category.display_name} is mapped to {department.name} in the prototype configuration.",
                    source_ids=[decision.category.id, department.department_id],
                ))
                required, missing = self._required(handoff, decision.category, jurisdiction)
                if jurisdiction.status is JurisdictionStatus.UNSUPPORTED:
                    decision.status = ClassificationStatus.UNSUPPORTED_CLASSIFICATION
                    decision.state = ConfidenceState.UNSUPPORTED
                    decision.reason = "the location you gave is outside the configured prototype jurisdictions"
                    # The citizen may still name another place (e.g. a typo); nothing is guessed meanwhile.
                    questions = [self._question("locality", language, issue=handoff.issue.value)]
                elif missing:
                    decision.status = ClassificationStatus.NEEDS_INFO
                    questions = [self._question("locality", language, issue=handoff.issue.value)]
                else:
                    decision.status = ClassificationStatus.CLASSIFIED
            trace.append(ProviderTraceStep(stage="jurisdiction", provider="prototype_jurisdictions",
                                           outcome="used", detail=jurisdiction.status.value))
            reasoning.append(ReasoningStep(
                step="jurisdiction", detail=self._jurisdiction_sentence(jurisdiction),
                source_ids=[jurisdiction.jurisdiction_id] if jurisdiction.jurisdiction_id else [],
            ))
        elif decision.status is ClassificationStatus.AMBIGUOUS:
            questions = [self._ambiguity_question(decision, language)]
        else:
            questions = [self._question("unsupported", language, options=self._all_names(data, language))]

        # Guidelines for the chosen category (provenance for the explanation).
        guidelines: list[RetrievedKnowledge] = []
        if decision.category is not None:
            guidelines = self.retriever.retrieve(
                [handoff.issue.source_span, decision.category.display_name], top_k=2,
                where={"$and": [{"record_type": "guideline"}, {"category": decision.category.category}]},
                max_chars=retrieval.max_query_chars,
            )
        rule_matches = decision.category_matches + [
            RuleMatch(rule_id=m.jurisdiction.id, rule_type="jurisdiction_place", pattern=m.place, language=language,
                      citizen_words=m.words, source=m.source)  # type: ignore[arg-type]
            for m in place_matches
        ]
        evidence = self._evidence(handoff, decision, department, jurisdiction, guidelines, locality_answers)
        if decision.status is ClassificationStatus.CLASSIFIED:
            problems = self._validate_final(data, decision, department, jurisdiction, evidence, citizen_texts)
            if problems:
                rejected_ai.extend(problems)
                decision.status = ClassificationStatus.UNSUPPORTED_CLASSIFICATION
                decision.state = ConfidenceState.UNSUPPORTED
                decision.reason = "the decision could not be traced to your words and the knowledge base"
                questions = []
        if decision.status is ClassificationStatus.CLASSIFIED and jurisdiction.status is not JurisdictionStatus.RESOLVED:
            decision.state = ConfidenceState.PARTIALLY_SUPPORTED

        reasoning.append(ReasoningStep(step="decision", detail=f"{decision.status.value}: {decision.reason or 'all checks passed'}"))
        category = decision.category if decision.status is not ClassificationStatus.UNSUPPORTED_CLASSIFICATION else None
        timeline = self._timeline(data, category)
        mode = ProcessingMode.MIXED if (decision.ai_accepted or decision.ai_agreed) else (
            ProcessingMode.OFFLINE_LOCAL_MODEL if self.retriever.embedder.name.startswith("onnx") else ProcessingMode.OFFLINE_RULE
        )
        result = ClassificationResult(
            complaint_id=handoff.complaint_id,
            status=_COMPLAINT_STATUS[decision.status],
            classification_status=decision.status,
            confidence_state=decision.state,
            category=category.category if category else None,
            category_record_id=category.id if category else None,
            category_name=category.name_in(language) if category else None,
            responsible_department=department if category else None,
            jurisdiction=jurisdiction,
            required_information=required,
            missing_information=missing,
            clarification_questions=questions,
            candidates=candidates,
            rule_matches=rule_matches,
            retrieved_sources=[*retrieved, *guidelines],
            evidence=evidence if category or decision.status is not ClassificationStatus.UNSUPPORTED_CLASSIFICATION else [
                e for e in evidence if e.kind == "citizen"
            ],
            reasoning=reasoning,
            explanation=self._explain(decision, department, jurisdiction, best, questions, language),
            service_guideline=category.service_guideline if category else None,
            service_timeline=timeline,
            processing_mode=mode,
            provider_trace=trace,
            rejected_ai_output=rejected_ai,
            safety_flags=payload.safety_flags,
            language=language,
            answers=payload.answers,
            knowledge_base_version=self.retriever.fingerprint,
            demo_data=not all(s.official for s in data.sources.values()),
        )
        return result

    # ================================================================== category decision

    def _decide(
        self, tiers: list[list[CitizenText]], best: dict[str, float], suggestion_similarity: float, max_suggestions: int
    ) -> _Decision:
        decision = _Decision()
        rules = self.rules
        hits: dict[str, list[RuleMatch]] = {}
        for tier in tiers:  # newest answer first, then the issue words, then the whole statement
            hits = rules.category_matches(tier)
            if hits:
                break
        if hits:
            suppressed = rules.suppressed(set(hits))
            remaining = sorted(k for k in hits if k not in suppressed)
            decision.category_matches = [m for k in sorted(hits) for m in hits[k]] + [
                RuleMatch(rule_id=rules.category(winner).id, rule_type="suppression", category=loser,  # type: ignore[union-attr]
                          pattern=f"{winner} suppresses {loser}", language="en", citizen_words=hits[loser][0].citizen_words,
                          source=hits[loser][0].source)
                for loser, winner in sorted(suppressed.items())
            ]
            if len(remaining) == 1:
                decision.category = rules.category(remaining[0])
                decision.state = ConfidenceState.SUPPORTED if remaining[0] in best else ConfidenceState.PARTIALLY_SUPPORTED
                decision.status = ClassificationStatus.CLASSIFIED
                return decision
            decision.ambiguous_keys = remaining
            decision.group = next(
                (g for g in self.reference.data.ambiguity_groups if set(remaining) <= set(g.categories)), None
            )
            decision.status, decision.state = ClassificationStatus.AMBIGUOUS, ConfidenceState.AMBIGUOUS
            decision.reason = "configured rules for more than one category match your words"
            decision.from_configured_ambiguity = True
            return decision
        all_texts = [t for tier in tiers for t in tier]
        groups = rules.ambiguity_matches(all_texts)
        if groups:
            group, match = groups[0]
            decision.group = group
            decision.ambiguous_keys = list(group.categories)
            decision.category_matches = [match]
            decision.status, decision.state = ClassificationStatus.AMBIGUOUS, ConfidenceState.AMBIGUOUS
            decision.reason = f"“{match.citizen_words}” fits several configured categories"
            decision.from_configured_ambiguity = True
            return decision
        suggestions = [k for k, s in sorted(best.items(), key=lambda kv: -kv[1]) if s >= suggestion_similarity]
        if suggestions:
            decision.ambiguous_keys = suggestions[:max_suggestions]
            decision.status, decision.state = ClassificationStatus.AMBIGUOUS, ConfidenceState.AMBIGUOUS
            decision.reason = "the knowledge search found similar categories, but no configured rule matches your words"
            return decision
        decision.reason = "no configured category matches your words and nothing similar was found"
        return decision

    # ================================================================== optional AI

    async def _ai_step(
        self,
        handoff: IntakeHandoff,
        payload: ClassificationRequest,
        decision: _Decision,
        retrieved: list[RetrievedKnowledge],
        best: dict[str, float],
        jurisdiction: JurisdictionResult,
        citizen_texts: list[CitizenText],
        trace: list[ProviderTraceStep],
        reasoning: list[ReasoningStep],
        rejected: list[str],
    ) -> None:
        provider = f"{getattr(self.ai, 'name', 'ai')}"
        if not getattr(self.ai, "available", False):
            trace.append(ProviderTraceStep(stage="ai_reasoning", provider=provider, outcome="unavailable",
                                           detail="offline classification only"))
            return
        if decision.from_configured_ambiguity:
            trace.append(ProviderTraceStep(stage="ai_reasoning", provider=provider, outcome="skipped",
                                           detail="configured ambiguity must be answered by the citizen"))
            return
        data = self.reference.data
        keys = {m.category for m in decision.category_matches if m.category} | set(best) | set(decision.ambiguous_keys)
        candidates = [c for c in (self.rules.category(k) for k in sorted(keys)) if c is not None]
        prompt = classification_prompt(
            citizen_statements=[handoff.original_text, *(a.text for a in payload.answers)],
            facts={"issue": handoff.issue.value, "location": handoff.location.value,
                   "duration": handoff.duration.value if handoff.duration else None},
            records=[{"id": r.record_id, "category": r.category or "", "content": r.content} for r in retrieved],
            candidates=[{"category": c.category, "name": c.display_name, "department_id": c.department_id} for c in candidates],
            jurisdiction_id=jurisdiction.jurisdiction_id,
        )
        try:
            output = await self.ai.generate_structured(prompt, AIClassificationOutput)
        except Exception as exc:  # noqa: BLE001 - optional step; offline result stands
            detail = "malformed output" if "validation" in type(exc).__name__.lower() else type(exc).__name__
            trace.append(ProviderTraceStep(stage="ai_reasoning", provider=provider, outcome="failed", detail=detail))
            rejected.append(f"AI reasoning failed ({detail}); offline classification kept")
            return
        problems = self._check_ai(output, candidates, retrieved, jurisdiction, citizen_texts, data)
        if decision.status is ClassificationStatus.CLASSIFIED and decision.category is not None:
            if output.category != decision.category.category:
                problems.append(f"AI chose {output.category!r} but the configured rule selects {decision.category.category!r}")
        elif output.classification_status != "CLASSIFIED":
            trace.append(ProviderTraceStep(stage="ai_reasoning", provider=provider, outcome="used",
                                           detail=f"AI also returned {output.classification_status}"))
            return
        if problems:
            rejected.extend(problems)
            trace.append(ProviderTraceStep(stage="ai_reasoning", provider=provider, outcome="rejected", detail="; ".join(problems)[:300]))
            reasoning.append(ReasoningStep(step="ai_reasoning", detail="The optional AI's answer was rejected: " + "; ".join(problems)))
            return
        if decision.status is ClassificationStatus.CLASSIFIED:
            decision.ai_agreed = True
            trace.append(ProviderTraceStep(stage="ai_reasoning", provider=provider, outcome="used", detail="agreed with the configured rule"))
            reasoning.append(ReasoningStep(step="ai_reasoning", detail="The optional AI reached the same category.", source_ids=output.source_ids))
            return
        decision.category = self.rules.category(str(output.category))
        decision.status = ClassificationStatus.CLASSIFIED
        decision.state = ConfidenceState.PARTIALLY_SUPPORTED
        decision.ai_accepted = True
        decision.from_configured_ambiguity = False
        decision.category_matches.append(RuleMatch(
            rule_id=decision.category.id,  # type: ignore[union-attr]
            rule_type="category_pattern", category=output.category, pattern="(AI-selected, evidence verified)",
            language=handoff.language, citizen_words=output.evidence[0], source="original_text",
        ))
        trace.append(ProviderTraceStep(stage="ai_reasoning", provider=provider, outcome="used", detail=f"chose {output.category}"))
        reasoning.append(ReasoningStep(
            step="ai_reasoning",
            detail=f"The optional AI chose {output.category} from the retrieved candidates; checked against your words and the KB.",
            source_ids=output.source_ids,
        ))

    def _check_ai(
        self,
        output: AIClassificationOutput,
        candidates: list[CivicCategory],
        retrieved: list[RetrievedKnowledge],
        jurisdiction: JurisdictionResult,
        citizen_texts: list[CitizenText],
        data: ReferenceData,
    ) -> list[str]:
        problems: list[str] = []
        if output.classification_status != "CLASSIFIED":
            return problems
        by_key = {c.category: c for c in candidates}
        category = by_key.get(output.category or "")
        if category is None:
            problems.append(f"category {output.category!r} is not a validated candidate")
        if output.department_id is not None:
            if output.department_id not in {d.id for d in data.departments}:
                problems.append(f"department {output.department_id!r} does not exist in the knowledge base")
            elif category is not None and output.department_id != category.department_id:
                problems.append(f"department {output.department_id!r} contradicts the configured mapping {category.department_id!r}")
        if output.jurisdiction_id is not None and output.jurisdiction_id != jurisdiction.jurisdiction_id:
            problems.append(f"jurisdiction {output.jurisdiction_id!r} is not supported by the citizen's location")
        known = {r.record_id for r in retrieved}
        unknown = [s for s in output.source_ids if s not in known]
        if unknown:
            problems.append(f"cites records that were not retrieved: {unknown}")
        if category is not None and category.id not in output.source_ids:
            problems.append("does not cite the category record it chose")
        haystack = " ".join(normalise(t.text) for t in citizen_texts)
        quotes = [q for q in output.evidence if q.strip()]
        if not quotes:
            problems.append("gives no citizen evidence")
        for quote in quotes:
            if normalise(quote) not in haystack:
                problems.append(f"evidence {quote!r} is not in the citizen's words")
        return problems

    # ================================================================== jurisdiction & requirements

    @staticmethod
    def _location_texts(handoff: IntakeHandoff, locality_answers: list[ClassificationAnswer]) -> list[CitizenText]:
        source = "correction" if handoff.location.source is FactSource.CITIZEN_CORRECTION else "location"
        texts = [CitizenText("answer", a.text) for a in locality_answers]
        texts.append(CitizenText(source, handoff.location.source_span))
        if handoff.location.source is FactSource.CITIZEN_CORRECTION and handoff.location.value != handoff.location.source_span:
            texts.append(CitizenText(source, handoff.location.value))
        texts += [CitizenText("location", e.source_span) for e in handoff.entities if e.type in {"place", "landmark"}]
        return texts

    def _jurisdiction(
        self, handoff: IntakeHandoff, locality_answers: list[ClassificationAnswer], category: CivicCategory | None
    ) -> tuple[JurisdictionResult, list[PlaceMatch]]:
        rules = self.rules
        texts = self._location_texts(handoff, locality_answers)
        matches: list[PlaceMatch] = []
        for piece in texts:  # newest answer first; the first piece that names a configured place decides
            matches = rules.place_matches(piece)
            if matches:
                break
        location_words = handoff.location.source_span
        latest_answer = locality_answers[0].text if locality_answers else None
        if matches:
            jurisdictions = {m.jurisdiction.id: m.jurisdiction for m in matches}
            first = matches[0]
            precision = LocationPrecision.EXACT if any(m.kind == "locality" for m in matches) else LocationPrecision.LANDMARK
            if len(jurisdictions) > 1:
                return JurisdictionResult(
                    status=JurisdictionStatus.AMBIGUOUS, location_precision=precision,
                    note="The place you named appears in more than one configured ward: " + ", ".join(sorted(jurisdictions)),
                ), matches
            return JurisdictionResult(
                status=JurisdictionStatus.RESOLVED, jurisdiction_id=first.jurisdiction.id, name=first.jurisdiction.name,
                matched_place=first.place, matched_words=first.words, source_id=first.jurisdiction.source_id,
                location_precision=precision,
            ), matches
        # Nothing configured matched: precision from the citizen's words, never invented.
        words = latest_answer or location_words
        if not words:
            precision = LocationPrecision.MISSING
        elif rules.is_vague(words) or (latest_answer is None and handoff.location.quality == "vague"):
            precision = LocationPrecision.VAGUE
        elif rules.has_number(words):
            precision = LocationPrecision.EXACT
        elif rules.has_proximity(words):
            precision = LocationPrecision.LANDMARK
        else:
            precision = LocationPrecision.EXACT
        if category is not None and not category.jurisdiction_required:
            status = JurisdictionStatus.NOT_REQUIRED
        elif latest_answer is not None and precision is not LocationPrecision.VAGUE:
            status = JurisdictionStatus.UNSUPPORTED  # the citizen named a place we do not have configured
        else:
            status = JurisdictionStatus.UNRESOLVED
        return JurisdictionResult(status=status, location_precision=precision, matched_words=None), []

    @staticmethod
    def _required(
        handoff: IntakeHandoff, category: CivicCategory, jurisdiction: JurisdictionResult
    ) -> tuple[list[RequiredInformation], list[str]]:
        items: list[RequiredInformation] = []
        missing: list[str] = []
        items.append(RequiredInformation(field="issue", requirement="REQUIRED", present=True, detail=handoff.issue.value))
        if "location" in category.required_fields:
            specific = jurisdiction.location_precision not in (LocationPrecision.VAGUE, LocationPrecision.MISSING)
            ok = specific or category.location_precision == "any"
            items.append(RequiredInformation(
                field="location", requirement="REQUIRED", present=ok,
                detail=f"{handoff.location.source_span} ({jurisdiction.location_precision.value.lower()})",
            ))
            if not ok:
                missing.append("location_detail")
        if category.jurisdiction_required:
            ok = jurisdiction.status is JurisdictionStatus.RESOLVED
            items.append(RequiredInformation(
                field="jurisdiction", requirement="REQUIRED", present=ok,
                detail=jurisdiction.name or jurisdiction.status.value.lower(),
            ))
            if not ok and jurisdiction.status is not JurisdictionStatus.UNSUPPORTED:
                missing.append("jurisdiction")
        entity_types = {e.type for e in handoff.entities}
        present = {
            "duration": handoff.duration is not None,
            "landmark": jurisdiction.location_precision is LocationPrecision.LANDMARK or "landmark" in entity_types,
            "pole_identifier": "identifier" in entity_types,
        }
        for name in category.optional_fields:
            items.append(RequiredInformation(
                field=name, requirement="OPTIONAL", present=present.get(name, False),
                detail=(handoff.duration.value if name == "duration" and handoff.duration else "not asked (optional)"),
            ))
        return items, missing

    @staticmethod
    def _department(data: ReferenceData, category: CivicCategory) -> DepartmentAssignment | None:
        dept = next((d for d in data.departments if d.id == category.department_id), None)
        if dept is None or category.category not in dept.categories or not dept.source_id:
            return None
        return DepartmentAssignment(
            department_id=dept.id, name=dept.name, source_id=dept.source_id, mapping_record_id=category.id,
            label=data.sources[dept.source_id].label or "DEMO CIVIC RULE",
        )

    @staticmethod
    def _timeline(data: ReferenceData, category: CivicCategory | None) -> ServiceTimelineRef | None:
        if category is None or not category.service_timeline_id:
            return None
        sla = next((p for p in data.sla_policies if p.id == category.service_timeline_id), None)
        return ServiceTimelineRef(policy_id=sla.id, duration_hours=sla.duration_hours) if sla else None

    # ================================================================== evidence & validation

    def _evidence(
        self,
        handoff: IntakeHandoff,
        decision: _Decision,
        department: DepartmentAssignment | None,
        jurisdiction: JurisdictionResult,
        guidelines: list[RetrievedKnowledge],
        locality_answers: list[ClassificationAnswer],
    ) -> list[ClassificationEvidence]:
        evidence = [ClassificationEvidence(kind="citizen", field="issue", text=handoff.issue.source_span, source=handoff.issue.source.value)]
        for match in decision.category_matches:
            if match.rule_type in {"category_pattern", "ambiguity_term"}:
                evidence.append(ClassificationEvidence(
                    kind="citizen", field="category", text=match.citizen_words,
                    source="citizen_clarification" if match.source == "answer" else "citizen_statement",
                ))
        evidence.append(ClassificationEvidence(kind="citizen", field="location", text=handoff.location.source_span, source=handoff.location.source.value))
        if jurisdiction.matched_words and locality_answers and any(
            normalise(jurisdiction.matched_words) in normalise(a.text) for a in locality_answers
        ):
            evidence.append(ClassificationEvidence(kind="citizen", field="location", text=jurisdiction.matched_words, source="citizen_clarification"))
        if decision.category is not None:
            evidence.append(ClassificationEvidence(kind="knowledge", field="category", text=decision.category.display_name, source=decision.category.id))
        if department is not None:
            evidence.append(ClassificationEvidence(kind="knowledge", field="department", text=department.name, source=department.department_id))
        if jurisdiction.jurisdiction_id:
            evidence.append(ClassificationEvidence(
                kind="knowledge", field="jurisdiction", text=f"{jurisdiction.name}: {jurisdiction.matched_place}",
                source=jurisdiction.jurisdiction_id,
            ))
        for record in guidelines[:1]:
            evidence.append(ClassificationEvidence(kind="knowledge", field="guideline", text=record.content[:300], source=record.record_id))
        # de-duplicate, keep order
        seen: set[tuple[str, str, str]] = set()
        unique = []
        for item in evidence:
            key = (item.field, item.text, item.source)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _validate_final(
        self,
        data: ReferenceData,
        decision: _Decision,
        department: DepartmentAssignment | None,
        jurisdiction: JurisdictionResult,
        evidence: list[ClassificationEvidence],
        citizen_texts: list[CitizenText],
    ) -> list[str]:
        """Last check before CLASSIFIED: everything traces to citizen words and KB records."""
        problems: list[str] = []
        category = decision.category
        if category is None or data.category(category.category) is None:
            problems.append("category is not an active configured category")
        if department is None or category is None or department.department_id != category.department_id:
            problems.append("department is not the configured mapping")
        if jurisdiction.jurisdiction_id and jurisdiction.jurisdiction_id not in {j.id for j in data.jurisdictions}:
            problems.append(f"jurisdiction {jurisdiction.jurisdiction_id} is not configured")
        known_sources = {c.id for c in data.categories} | {d.id for d in data.departments} | {j.id for j in data.jurisdictions}
        known_sources |= {d.metadata["record_id"] for d in self.retriever.documents}  # type: ignore[misc]
        haystack = " ".join(normalise(t.text) for t in citizen_texts)
        if not any(e.kind == "citizen" and e.field == "category" for e in evidence):
            problems.append("no citizen evidence supports the category")
        for item in evidence:
            if item.kind == "knowledge" and item.source not in known_sources:
                problems.append(f"unknown knowledge source {item.source}")
            if item.kind == "citizen" and normalise(item.text) not in haystack:
                problems.append(f"citizen evidence {item.text!r} is not in the citizen's words")
        return problems

    # ================================================================== questions & explanation

    def _question(self, kind: str, language: str, **values: str) -> ClarificationQuestion:
        settings = self.reference.data.classification
        assert settings is not None
        templates = settings.questions[kind]
        lang = language if language in templates else "en"
        field = "category" if kind in {"category", "unsupported"} else "locality"
        return ClarificationQuestion(field=field, text=templates[lang].format(**values), language=lang)  # type: ignore[arg-type]

    def _ambiguity_question(self, decision: _Decision, language: str) -> ClarificationQuestion:
        group = decision.group
        if group is not None and set(decision.ambiguous_keys) <= set(group.categories) and len(decision.ambiguous_keys) == len(group.categories):
            lang = language if language in group.question else "en"
            return ClarificationQuestion(field="category", text=group.question[lang], language=lang)
        names = [c.name_in(language) for c in (self.rules.category(k) for k in decision.ambiguous_keys) if c]
        return self._question("category", language, options=self._join(names, language))

    def _all_names(self, data: ReferenceData, language: str) -> str:
        return self._join([c.name_in(language) for c in data.active_categories()], language)

    @staticmethod
    def _join(names: list[str], language: str) -> str:
        if language != "en" or len(names) < 2:
            return ", ".join(names)
        return ", ".join(names[:-1]) + " or " + names[-1]

    def _candidates(self, decision: _Decision, best: dict[str, float]) -> list[Candidate]:
        matched = {m.category for m in decision.category_matches if m.rule_type == "category_pattern" and m.category}
        suppressed = {m.category for m in decision.category_matches if m.rule_type == "suppression" and m.category}
        keys = sorted(set(best) | matched | set(decision.ambiguous_keys), key=lambda k: -best.get(k, 0.0))
        out: list[Candidate] = []
        for key in keys:
            cat = self.rules.category(key)
            if cat is None:
                continue
            if decision.category is not None and key == decision.category.category:
                verdict, reason = "selected", "configured rule matched the citizen's words" + (
                    " and retrieval agreed" if key in best else " (retrieval did not rank it)"
                )
                if decision.ai_accepted:
                    verdict, reason = "selected", "chosen by the optional AI among retrieved candidates; evidence verified"
            elif key in suppressed:
                verdict, reason = "suppressed", "a more specific configured category also matched"
            elif key in decision.ambiguous_keys and decision.status is ClassificationStatus.AMBIGUOUS:
                verdict, reason = ("ambiguous", "fits the citizen's words as well as another category") if key in matched or decision.group else (
                    "suggested", "similar in the knowledge search; the citizen is asked to confirm")
            else:
                verdict, reason = "rejected", "retrieved, but no configured rule matched the citizen's words"
            out.append(Candidate(
                category=key, record_id=cat.id, display_name=cat.display_name, retrieved=key in best,
                best_similarity=best.get(key), rule_matched=key in matched, decision=verdict, reason=reason,  # type: ignore[arg-type]
            ))
        return out

    @staticmethod
    def _jurisdiction_sentence(j: JurisdictionResult) -> str:
        if j.status is JurisdictionStatus.RESOLVED:
            return f"“{j.matched_words}” matches {j.matched_place} in {j.name} ({j.jurisdiction_id}) in the prototype jurisdiction configuration."
        if j.status is JurisdictionStatus.AMBIGUOUS:
            return j.note or "The place matches more than one configured jurisdiction."
        if j.status is JurisdictionStatus.UNSUPPORTED:
            return "The place you gave is not in the configured prototype jurisdictions; no ward was guessed."
        if j.status is JurisdictionStatus.NOT_REQUIRED:
            return "This category does not need a jurisdiction in the prototype configuration."
        precision = {"EXACT": "specific", "LANDMARK": "landmark-based", "VAGUE": "vague", "MISSING": "missing"}[j.location_precision.value]
        return f"The location is {precision}, but it does not match any configured ward, street or landmark, so none was guessed."

    def _explain(
        self,
        decision: _Decision,
        department: DepartmentAssignment | None,
        jurisdiction: JurisdictionResult,
        best: dict[str, float],
        questions: list[ClarificationQuestion],
        language: str,
    ) -> str:
        words = next((m.citizen_words for m in decision.category_matches if m.rule_type == "category_pattern"), None)
        cat = decision.category
        if decision.status is ClassificationStatus.CLASSIFIED and cat is not None and department is not None:
            parts = [f"Your complaint was classified as {cat.display_name} because you reported “{words}”."]
            if decision.ai_accepted:
                parts.append(
                    "No configured phrase matched directly; the optional AI reasoning assistant chose this category "
                    "from the retrieved knowledge-base candidates, and its choice was checked against your words."
                )
            else:
                parts.append(
                    f"This matches the configured {cat.display_name} rule ({cat.id})"
                    + (", and the local civic knowledge search returned the same category." if cat.category in best else ".")
                )
            parts.append(f"In this prototype configuration, {cat.display_name} complaints are handled by {department.name} ({department.department_id}).")
            parts.append(self._jurisdiction_sentence(jurisdiction))
            parts.append(DEMO_NOTE)
            return " ".join(parts)
        if decision.status is ClassificationStatus.NEEDS_INFO and cat is not None:
            need = (
                "a more specific location (area, street, ward or landmark)"
                if jurisdiction.location_precision in (LocationPrecision.VAGUE, LocationPrecision.MISSING)
                else "an area, street, ward or landmark that matches the configured jurisdictions"
            )
            return (
                f"This looks like {cat.display_name}: you reported “{words}”, which matches the configured rule ({cat.id}). "
                f"Before it can be classified, SPANDAN AI needs {need}. {self._jurisdiction_sentence(jurisdiction)}"
            )
        if decision.status is ClassificationStatus.AMBIGUOUS:
            names = [c.display_name for c in (self.rules.category(k) for k in decision.ambiguous_keys) if c]
            return (
                f"Your description could fit more than one civic category ({', '.join(names)}) because {decision.reason}. "
                "SPANDAN AI does not guess: please choose the one that fits."
            )
        if cat is not None:
            return f"This looks like {cat.display_name}, but it cannot be classified: {decision.reason}. Nothing was guessed."
        return f"SPANDAN AI could not match this complaint to a configured civic category: {decision.reason}. Nothing was guessed."
