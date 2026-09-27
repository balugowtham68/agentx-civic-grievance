"""Location resolution schemas for SPANDAN AI."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

LocationSource = Literal["GPS", "VOICE", "TEXT", "MANUAL", "INFERRED"]


class LocationResolution(BaseModel):
    """Normalized resolved civic locality."""

    latitude: float | None = None
    longitude: float | None = None
    state: str | None = None
    district: str | None = None
    city: str | None = None
    ward: str | None = None
    locality: str | None = None
    pincode: str | None = None
    source: LocationSource = "TEXT"
    confidence: float = 0.5
    needs_confirmation: bool = False
    display_address: str = ""

    def summary(self) -> str:
        parts = [p for p in [self.locality, self.ward, self.city, self.district, self.state] if p]
        return ", ".join(parts) if parts else (self.display_address or "Unresolved Location")


class LocationConfirmRequest(BaseModel):
    confirmed: bool = True
    locality: str | None = None
    ward: str | None = None
    city: str | None = None


class LocationCorrectRequest(BaseModel):
    state: str | None = None
    district: str | None = None
    city: str | None = None
    ward: str | None = None
    locality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
