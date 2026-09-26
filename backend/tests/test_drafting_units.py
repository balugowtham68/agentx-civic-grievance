"""Phase 4 - drafting configuration, deterministic builder and validator (no HTTP)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agents.drafting.builder import build_sections, compose_body
from app.agents.drafting.config import CategoryTemplate, load_drafting_config
from app.agents.drafting.validator import DraftValidator
from app.repositories import ReferenceRepository
from app.schemas.drafting import DraftFactSet, DraftSections, LockedFact

KB = Path(__file__).resolve().parents[2] / "knowledge_base"
DATA = ReferenceRepository(KB).data
CONFIG = load_drafting_config()


def facts(**overrides: object) -> DraftFactSet:
    base: dict[str, object] = dict(
        complaint_id="c1",
        original_text="Street light on Main Road has not been working for three days.",
        citizen_language="en",
        issue=LockedFact(value="street light not working", citizen_words="Street light on Main Road has not been working", source="citizen_statement"),
        location=LockedFact(value="on Main Road", citizen_words="on Main Road", source="citizen_statement"),
        duration=LockedFact(value="three days", citizen_words="for three days", source="citizen_statement"),
        category="streetlight", category_record_id="CAT-STREETLIGHT", category_name="Streetlight Maintenance",
        department_id="DEPT-ELECTRICAL", department_name="Electrical Maintenance Department (demo)",
        jurisdiction_id="WARD-7", jurisdiction_name="Ward 7 (demo)", resolved_place="Main Road",
        location_precision="EXACT", source_ids=["CAT-STREETLIGHT", "DEPT-ELECTRICAL", "WARD-7"],
        classification_explanation="…",
    )
    base.update(overrides)
    return DraftFactSet(**base)  # type: ignore[arg-type]


def check(sections: DraftSections, fact_set: DraftFactSet | None = None) -> list[str]:
    fact_set = fact_set or facts()
    report = DraftValidator(CONFIG, DATA).validate(
        sections, compose_body(sections, fact_set, include_statement=False, language_name="English"), fact_set
    )
    return report.hard + report.soft


def test_every_knowledge_base_category_has_a_template_without_facts() -> None:
    assert {c.category for c in DATA.active_categories()} <= set(CONFIG.templates)
    for key, template in CONFIG.templates.items():
        texts = [*template.subject.values(), *template.summary.values(), *template.issue_label.values(), template.requested_action]
        for text in texts:
            assert not re.search(r"\d", text), (key, text)  # no numbers, dates or ids in templates
            for department in DATA.departments:  # department mapping is Phase 3's, never a template's
                assert department.name not in text and department.id not in text


def test_template_placeholders_are_restricted() -> None:
    with pytest.raises(ValidationError, match="unknown placeholder"):
        CategoryTemplate(subject={"default": "x"}, summary={"default": "{ward_number}"}, issue_label={"default": "x"}, requested_action="x")


def test_deterministic_draft_passes_its_own_validator() -> None:
    sections = build_sections(facts(), CONFIG)
    assert sections.summary == "A streetlight on Main Road has reportedly not been functioning for approximately three days."
    assert check(sections) == []
    no_duration = facts(duration=None)
    assert "approximately" not in build_sections(no_duration, CONFIG).summary
    assert check(build_sections(no_duration, CONFIG), no_duration) == []


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        ("The streetlight's electrical circuit has failed.", "cause"),
        ("The damaged streetlight is creating a serious safety hazard.", "severity"),
        ("The streetlight stopped working on 3 March.", "date"),
        ("Inspector Kumar has visited the site.", "official"),
        ("The issue has been resolved by the department.", "resolution"),
        ("Photographs are attached as evidence.", "evidence"),
        ("Fifty residents are affected by the dark street.", "affected people"),
        ("Action has been taken under Section 144 of the Act.", "legal"),
        ("Call 9876543210 or mail ward7@example.org.", "phone number"),
        ("Complaint number CIV-2026-0042 was registered.", "tracking ID"),
    ],
)
def test_unsupported_claims_are_detected(summary: str, expected: str) -> None:
    sections = build_sections(facts(), CONFIG).model_copy(update={"summary": summary})
    issues = check(sections)
    assert any(expected in issue for issue in issues), issues


def test_citizen_stated_details_are_not_flagged() -> None:
    citizen = facts(original_text="The street light on Main Road is dangerous and has not worked for three days.")
    sections = build_sections(citizen, CONFIG).model_copy(update={"summary": "A dangerous streetlight on Main Road has not worked for three days."})
    assert check(sections, citizen) == []


def test_non_english_location_is_quoted_not_translated() -> None:
    tamil = facts(
        citizen_language="ta", original_text="காந்தி நகரில் தெரு விளக்கு மூன்று நாட்களாக எரியவில்லை",
        location=LockedFact(value="காந்தி nagar", citizen_words="காந்தி நகரில்", source="citizen_statement"),
        duration=LockedFact(value="three days", citizen_words="மூன்று நாட்களாக", source="citizen_statement"),
        jurisdiction_id="WARD-12", jurisdiction_name="Ward 12 (demo)", resolved_place="Gandhi Nagar",
    )
    sections = build_sections(tamil, CONFIG)
    assert "“காந்தி நகரில்”" in sections.summary and "Gandhi Nagar, Ward 12 (demo) (WARD-12)" in sections.location_text
    assert check(sections, tamil) == []


def test_safe_administrative_paraphrase_is_accepted_but_new_facts_are_not() -> None:
    base = build_sections(facts(), CONFIG)
    ok = base.model_copy(update={"summary": "The streetlight on Main Road has reportedly been non-functional for approximately three days."})
    assert check(ok) == []
    for invented in ("The streetlight's electrical wiring has failed.", "The streetlight creates a serious safety hazard.",
                     "The pole on Main Road is leaning and the bulb is missing."):
        issues = check(base.model_copy(update={"summary": invented}))
        assert issues, invented


def test_citizen_edit_mode_flags_instead_of_rejecting() -> None:
    fact_set = facts()
    base = build_sections(fact_set, CONFIG)
    validator = DraftValidator(CONFIG, DATA)
    edited = base.model_copy(update={"summary": "It was repaired previously but stopped working again."})
    report = validator.validate(edited, compose_body(edited, fact_set, include_statement=False, language_name="English"),
                                fact_set, mode="citizen_edit")
    assert report.hard == [] and report.soft == [] and report.citizen_added
    filed = base.model_copy(update={"summary": "This complaint has been filed with the ward office."})
    report = validator.validate(filed, compose_body(filed, fact_set, include_statement=False, language_name="English"),
                                fact_set, mode="citizen_edit")
    assert any("filing" in h for h in report.hard)  # the system has not filed anything: never allowed
