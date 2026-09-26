"""Builds the Complaint Drafting Agent from settings (existing AIProvider abstraction)."""

from __future__ import annotations

from app.agents.drafting import DraftingAgent
from app.agents.drafting.config import load_drafting_config
from app.core.config import Settings
from app.core.languages import LanguageRegistry
from app.repositories import ReferenceRepository
from app.services.ai import build_ai_provider


def build_drafting_agent(settings: Settings, reference: ReferenceRepository, registry: LanguageRegistry) -> DraftingAgent:
    config = load_drafting_config()
    missing = {c.category for c in reference.data.active_categories()} - set(config.templates)
    if missing:  # fail at start-up, not during a citizen's session
        raise RuntimeError(f"Drafting templates missing for categories: {sorted(missing)}")
    return DraftingAgent(build_ai_provider(settings), reference, config, registry)
