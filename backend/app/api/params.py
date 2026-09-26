"""Shared, validated path parameters for all routes (one definition, no duplicates)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Path

UUID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

ComplaintId = Annotated[str, Path(pattern=UUID_PATTERN, description="Complaint UUID")]
TrackingId = Annotated[str, Path(pattern=r"^CIV-\d{4}-\d{4,}$", description="Tracking ID (issued by filing, Phase 5)")]
