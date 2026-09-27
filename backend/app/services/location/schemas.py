"""Location resolution schemas for SPANDAN AI."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

LocationSource = Literal["GPS", "VOICE", "TEXT", "MANUAL"]


class LocationResolution(BaseModel):
    """Normalized civic location and jurisdiction resolution."""

    latitude: float | None = None
    longitude: float | None = None
    state: str = "Telangana"
    district: str | None = None
    city: str | None = None
    ward: str | None = None
    locality: str | None = None
    raw_location: str | None = None
    source: LocationSource = "TEXT"
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    needs_confirmation: bool = False
    jurisdiction_id: str | None = None
    formatted_address: str = ""


class LocationInput(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    text: str | None = None
    source: LocationSource = "TEXT"
