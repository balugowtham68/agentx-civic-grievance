"""Location resolution package for SPANDAN AI."""

from pathlib import Path
from app.services.location.resolver import CachedLocationResolver, LocalCivicResolver, LocationResolver
from app.services.location.schemas import LocationInput, LocationResolution, LocationSource

# Default resolver instance
_base_resolver = LocalCivicResolver(Path("knowledge_base/jurisdictions/jurisdictions.json"))
_cached_resolver = CachedLocationResolver(_base_resolver)


def get_location_resolver() -> CachedLocationResolver:
    return _cached_resolver


__all__ = [
    "LocationResolution",
    "LocationInput",
    "LocationSource",
    "LocationResolver",
    "LocalCivicResolver",
    "CachedLocationResolver",
    "get_location_resolver",
]
