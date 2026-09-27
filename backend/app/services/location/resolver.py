"""Multi-signal location resolution and jurisdiction routing for SPANDAN AI."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from app.core.logging import get_logger
from app.services.location.schemas import LocationInput, LocationResolution

logger = get_logger(__name__)

# Sample Civic Jurisdictions Database (Ward-level mappings for demo & scalability)
CIVIC_LOCALITY_MAP = {
    "gandhi nagar": {"ward": "Ward 12", "city": "Hyderabad", "district": "Hyderabad", "jurisdiction_id": "WARD-12"},
    "station road": {"ward": "Ward 12", "city": "Hyderabad", "district": "Hyderabad", "jurisdiction_id": "WARD-12"},
    "ramalayam": {"ward": "Ward 12", "city": "Hyderabad", "district": "Hyderabad", "jurisdiction_id": "WARD-12"},
    "nehru nagar": {"ward": "Ward 07", "city": "Hyderabad", "district": "Hyderabad", "jurisdiction_id": "WARD-07"},
    "market yard": {"ward": "Ward 07", "city": "Hyderabad", "district": "Hyderabad", "jurisdiction_id": "WARD-07"},
    "madhapur": {"ward": "Ward 104", "city": "Hyderabad", "district": "Hyderabad", "jurisdiction_id": "GHMC-104"},
    "hitech city": {"ward": "Ward 104", "city": "Hyderabad", "district": "Hyderabad", "jurisdiction_id": "GHMC-104"},
    "kukatpally": {"ward": "Ward 118", "city": "Hyderabad", "district": "Medchal-Malkajgiri", "jurisdiction_id": "GHMC-118"},
    "t nagar": {"ward": "Ward 134", "city": "Chennai", "district": "Chennai", "jurisdiction_id": "GCC-134"},
    "ramapuram": {"ward": "Ward 154", "city": "Chennai", "district": "Chennai", "jurisdiction_id": "GCC-154"},
    "koramangala": {"ward": "Ward 151", "city": "Bengaluru", "district": "Bengaluru Urban", "jurisdiction_id": "BBMP-151"},
    "indiranagar": {"ward": "Ward 80", "city": "Bengaluru", "district": "Bengaluru Urban", "jurisdiction_id": "BBMP-80"},
    "whitefield": {"ward": "Ward 84", "city": "Bengaluru", "district": "Bengaluru Urban", "jurisdiction_id": "BBMP-84"},
    "mg road": {"ward": "Ward 111", "city": "Bengaluru", "district": "Bengaluru Urban", "jurisdiction_id": "BBMP-111"},
    "besant road": {"ward": "Ward 22", "city": "Vijayawada", "district": "NTR", "jurisdiction_id": "VMC-22"},
    "benz circle": {"ward": "Ward 31", "city": "Vijayawada", "district": "NTR", "jurisdiction_id": "VMC-31"},
}


class LocationResolver(Protocol):
    async def resolve(self, location_input: LocationInput) -> LocationResolution: ...


class LocalCivicResolver:
    """Deterministic local resolver matching civic localities, wards, and GPS ranges."""

    def __init__(self, jurisdictions_file: Path | None = None) -> None:
        self.jurisdictions_file = jurisdictions_file
        self._load_prototype_jurisdictions()

    def _load_prototype_jurisdictions(self) -> None:
        self.known_places: dict[str, dict[str, str]] = dict(CIVIC_LOCALITY_MAP)
        if self.jurisdictions_file and self.jurisdictions_file.exists():
            try:
                data = json.loads(self.jurisdictions_file.read_text(encoding="utf-8"))
                for item in data.get("items", []):
                    ward_id = item.get("id")
                    ward_name = item.get("name", ward_id)
                    for loc in item.get("localities", []):
                        self.known_places[loc.lower().strip()] = {
                            "ward": ward_name,
                            "city": "Sample City",
                            "district": "Central",
                            "jurisdiction_id": ward_id,
                        }
                    for lm in item.get("landmarks", []):
                        self.known_places[lm.lower().strip()] = {
                            "ward": ward_name,
                            "city": "Sample City",
                            "district": "Central",
                            "jurisdiction_id": ward_id,
                        }
            except Exception as exc:
                logger.warning("could not load jurisdictions file", extra={"error": str(exc)})

    async def resolve(self, location_input: LocationInput) -> LocationResolution:
        # 1. GPS Input
        if location_input.latitude is not None and location_input.longitude is not None:
            lat = round(location_input.latitude, 4)
            lng = round(location_input.longitude, 4)
            # Fictional bounding resolution for demo
            if 17.3 <= lat <= 17.5 and 78.3 <= lng <= 78.6:
                return LocationResolution(
                    latitude=lat,
                    longitude=lng,
                    state="Telangana",
                    district="Hyderabad",
                    city="Hyderabad",
                    ward="Ward 12",
                    locality="Gandhi Nagar Locality",
                    raw_location=f"GPS: {lat}, {lng}",
                    source="GPS",
                    confidence=0.95,
                    needs_confirmation=False,
                    jurisdiction_id="WARD-12",
                    formatted_address=f"Gandhi Nagar, Ward 12, Hyderabad ({lat}, {lng})",
                )
            if 12.9 <= lat <= 13.1 and 80.1 <= lng <= 80.3:
                return LocationResolution(
                    latitude=lat,
                    longitude=lng,
                    state="Tamil Nadu",
                    district="Chennai",
                    city="Chennai",
                    ward="Ward 154",
                    locality="Ramapuram",
                    raw_location=f"GPS: {lat}, {lng}",
                    source="GPS",
                    confidence=0.95,
                    needs_confirmation=False,
                    jurisdiction_id="GCC-154",
                    formatted_address=f"Ramapuram, Ward 154, Chennai ({lat}, {lng})",
                )
            return LocationResolution(
                latitude=lat,
                longitude=lng,
                raw_location=f"GPS: {lat}, {lng}",
                source="GPS",
                confidence=0.85,
                needs_confirmation=False,
                jurisdiction_id="WARD-12",
                formatted_address=f"Coordinates ({lat}, {lng})",
            )

        # 2. Text / Voice Input Landmark Matching
        raw = (location_input.text or "").strip()
        if not raw:
            return LocationResolution(
                source=location_input.source,
                confidence=0.5,
                needs_confirmation=True,
                raw_location="Not specified",
                formatted_address="Civic Locality Not Specified",
                jurisdiction_id="WARD-12",
            )

        raw_lower = raw.lower()
        for place, details in self.known_places.items():
            if place in raw_lower:
                return LocationResolution(
                    city=details.get("city", "Hyderabad"),
                    district=details.get("district", "Hyderabad"),
                    ward=details.get("ward", "Ward 12"),
                    locality=place.title(),
                    raw_location=raw,
                    source=location_input.source,
                    confidence=0.92,
                    needs_confirmation=False,
                    jurisdiction_id=details.get("jurisdiction_id", "WARD-12"),
                    formatted_address=f"{place.title()}, {details.get('ward')}, {details.get('city')}",
                )

        # 3. Fallback for unrecognized local address
        return LocationResolution(
            raw_location=raw,
            locality=raw,
            ward="Ward 12",
            city="Hyderabad",
            district="Hyderabad",
            source=location_input.source,
            confidence=0.72,
            needs_confirmation=True,
            jurisdiction_id="WARD-12",
            formatted_address=f"{raw} (Pending Authority Verification)",
        )


class CachedLocationResolver:
    """Wraps any location resolver with an in-memory LRU cache."""

    def __init__(self, inner: LocationResolver, max_cache_size: int = 500) -> None:
        self._inner = inner
        self._cache: dict[str, LocationResolution] = {}
        self._max_size = max_cache_size

    async def resolve(self, location_input: LocationInput) -> LocationResolution:
        cache_key = f"{location_input.source}:{location_input.latitude}:{location_input.longitude}:{location_input.text}"
        if cache_key in self._cache:
            logger.debug("location resolution cache hit", extra={"key": cache_key})
            return self._cache[cache_key]

        res = await self._inner.resolve(location_input)
        if len(self._cache) >= self._max_size:
            # Evict oldest entry
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[cache_key] = res
        return res
