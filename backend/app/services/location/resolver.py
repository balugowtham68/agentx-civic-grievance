"""Multi-signal location resolution engine for civic complaints."""

from __future__ import annotations

import re
from typing import Protocol

from app.core.logging import get_logger
from app.services.location.schema import LocationResolution, LocationSource

logger = get_logger(__name__)

# Built-in local gazetteer for high-frequency civic areas
LOCAL_GAZETTEER: list[dict[str, str | float]] = [
    # Hyderabad / Telangana
    {"keyword": "madhapur", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 107 (Madhapur)", "locality": "Madhapur", "lat": 17.4483, "lon": 78.3915},
    {"keyword": "gachibowli", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 105 (Gachibowli)", "locality": "Gachibowli", "lat": 17.4401, "lon": 78.3489},
    {"keyword": "kukatpally", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 114 (Kukatpally)", "locality": "Kukatpally", "lat": 17.4875, "lon": 78.4067},
    {"keyword": "banjara hills", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 93 (Banjara Hills)", "locality": "Banjara Hills", "lat": 17.4156, "lon": 78.4357},
    {"keyword": "jubilee hills", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 94 (Jubilee Hills)", "locality": "Jubilee Hills", "lat": 17.4319, "lon": 78.4073},
    {"keyword": "secunderabad", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 147 (Secunderabad)", "locality": "Secunderabad", "lat": 17.4399, "lon": 78.4983},
    {"keyword": "ameerpet", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 100 (Ameerpet)", "locality": "Ameerpet", "lat": 17.4375, "lon": 78.4483},
    {"keyword": "dilsukhnagar", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 22 (Dilsukhnagar)", "locality": "Dilsukhnagar", "lat": 17.3688, "lon": 78.5247},
    {"keyword": "charminar", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 45 (Charminar)", "locality": "Charminar", "lat": 17.3616, "lon": 78.4747},
    {"keyword": "kondapur", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "ward": "Ward 104 (Kondapur)", "locality": "Kondapur", "lat": 17.4699, "lon": 78.3578},

    # Bengaluru / Karnataka
    {"keyword": "indiranagar", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "ward": "Ward 80 (Indiranagar)", "locality": "Indiranagar", "lat": 12.9784, "lon": 77.6408},
    {"keyword": "koramangala", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "ward": "Ward 151 (Koramangala)", "locality": "Koramangala", "lat": 12.9279, "lon": 77.6271},
    {"keyword": "whitefield", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "ward": "Ward 84 (Whitefield)", "locality": "Whitefield", "lat": 12.9698, "lon": 77.7500},
    {"keyword": "hsr layout", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "ward": "Ward 174 (HSR Layout)", "locality": "HSR Layout", "lat": 12.9121, "lon": 77.6446},
    {"keyword": "jayanagar", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "ward": "Ward 153 (Jayanagar)", "locality": "Jayanagar", "lat": 12.9308, "lon": 77.5838},
    {"keyword": "marathahalli", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "ward": "Ward 85 (Marathahalli)", "locality": "Marathahalli", "lat": 12.9591, "lon": 77.6974},
    {"keyword": "electronic city", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "ward": "Ward 192 (Electronic City)", "locality": "Electronic City", "lat": 12.8452, "lon": 77.6602},

    # Chennai / Tamil Nadu
    {"keyword": "ramapuram", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "ward": "Ward 154 (Ramapuram)", "locality": "Ramapuram", "lat": 13.0312, "lon": 80.1818},
    {"keyword": "anna nagar", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "ward": "Ward 100 (Anna Nagar)", "locality": "Anna Nagar", "lat": 13.0850, "lon": 80.2101},
    {"keyword": "t nagar", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "ward": "Ward 136 (T. Nagar)", "locality": "T. Nagar", "lat": 13.0418, "lon": 80.2341},
    {"keyword": "adyar", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "ward": "Ward 173 (Adyar)", "locality": "Adyar", "lat": 13.0012, "lon": 80.2565},
    {"keyword": "velachery", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "ward": "Ward 178 (Velachery)", "locality": "Velachery", "lat": 12.9815, "lon": 80.2180},
    {"keyword": "mylapore", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "ward": "Ward 124 (Mylapore)", "locality": "Mylapore", "lat": 13.0368, "lon": 80.2676},

    # Delhi / NCR
    {"keyword": "rohini", "city": "Delhi", "district": "North West Delhi", "state": "Delhi", "ward": "Ward 50 (Rohini)", "locality": "Rohini", "lat": 28.7495, "lon": 77.0565},
    {"keyword": "dwarka", "city": "Delhi", "district": "South West Delhi", "state": "Delhi", "ward": "Ward 34 (Dwarka)", "locality": "Dwarka", "lat": 28.5921, "lon": 77.0460},
    {"keyword": "connaught place", "city": "Delhi", "district": "New Delhi", "state": "Delhi", "ward": "Ward 1 (Connaught Place)", "locality": "Connaught Place", "lat": 28.6315, "lon": 77.2167},
    {"keyword": "lajpat nagar", "city": "Delhi", "district": "South Delhi", "state": "Delhi", "ward": "Ward 58 (Lajpat Nagar)", "locality": "Lajpat Nagar", "lat": 28.5677, "lon": 77.2433},

    # Mumbai / Maharashtra
    {"keyword": "andheri", "city": "Mumbai", "district": "Mumbai Suburban", "state": "Maharashtra", "ward": "Ward K-West (Andheri)", "locality": "Andheri", "lat": 19.1136, "lon": 72.8697},
    {"keyword": "bandra", "city": "Mumbai", "district": "Mumbai Suburban", "state": "Maharashtra", "ward": "Ward H-West (Bandra)", "locality": "Bandra", "lat": 19.0596, "lon": 72.8295},
    {"keyword": "dadar", "city": "Mumbai", "district": "Mumbai City", "state": "Maharashtra", "ward": "Ward G-North (Dadar)", "locality": "Dadar", "lat": 19.0178, "lon": 72.8478},
    {"keyword": "colaba", "city": "Mumbai", "district": "Mumbai City", "state": "Maharashtra", "ward": "Ward A (Colaba)", "locality": "Colaba", "lat": 18.9067, "lon": 72.8147},
]


class LocationResolver:
    """Multi-tiered resolver: Cache -> Local Gazetteer -> GPS Bounding Box -> External."""

    def __init__(self) -> None:
        self._cache: dict[str, LocationResolution] = {}

    def resolve(
        self,
        raw_text: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        source: LocationSource = "TEXT",
    ) -> LocationResolution:
        # Check cache
        cache_key = f"{raw_text}:{latitude}:{longitude}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. GPS Coordinate resolution
        if latitude is not None and longitude is not None:
            res = self._resolve_from_coordinates(latitude, longitude, source)
            self._cache[cache_key] = res
            return res

        # 2. Text / Voice location resolution from gazetteer
        if raw_text and raw_text.strip():
            res = self._resolve_from_text(raw_text.strip(), source)
            self._cache[cache_key] = res
            return res

        # 3. Default fallback
        res = LocationResolution(
            source=source,
            confidence=0.2,
            needs_confirmation=True,
            display_address="Location not provided",
        )
        self._cache[cache_key] = res
        return res

    def _resolve_from_text(self, text: str, source: LocationSource) -> LocationResolution:
        normalized = text.lower()

        # Check local gazetteer keywords
        for entry in LOCAL_GAZETTEER:
            kw = str(entry["keyword"]).lower()
            if kw in normalized:
                return LocationResolution(
                    latitude=float(entry["lat"]),
                    longitude=float(entry["lon"]),
                    state=str(entry["state"]),
                    district=str(entry["district"]),
                    city=str(entry["city"]),
                    ward=str(entry["ward"]),
                    locality=str(entry["locality"]),
                    source=source,
                    confidence=0.92,
                    needs_confirmation=False,
                    display_address=f"{entry['locality']}, {entry['city']}, {entry['state']}",
                )

        # Basic heuristic extraction for street / area / colony
        area_match = re.search(r"([A-Za-z0-9\s]+(?:colony|nagar|street|road|ward|lane|cross|layout|enclave))", text, re.I)
        extracted = area_match.group(1).strip() if area_match else text

        return LocationResolution(
            locality=extracted,
            source=source,
            confidence=0.65,
            needs_confirmation=True,
            display_address=extracted,
        )

    def _resolve_from_coordinates(
        self, lat: float, lon: float, source: LocationSource
    ) -> LocationResolution:
        # Match closest known locality within ~5km bounding radius
        best_entry = None
        min_dist_sq = 0.05 ** 2  # approximately 5 km

        for entry in LOCAL_GAZETTEER:
            d_lat = lat - float(entry["lat"])
            d_lon = lon - float(entry["lon"])
            dist_sq = d_lat * d_lat + d_lon * d_lon
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_entry = entry

        if best_entry:
            return LocationResolution(
                latitude=lat,
                longitude=lon,
                state=str(best_entry["state"]),
                district=str(best_entry["district"]),
                city=str(best_entry["city"]),
                ward=str(best_entry["ward"]),
                locality=str(best_entry["locality"]),
                source=source,
                confidence=0.95,
                needs_confirmation=False,
                display_address=f"{best_entry['locality']}, {best_entry['city']}, {best_entry['state']}",
            )

        # Coords provided without close gazetteer match
        return LocationResolution(
            latitude=lat,
            longitude=lon,
            source="GPS",
            confidence=0.75,
            needs_confirmation=True,
            display_address=f"Coordinates: {lat:.4f}, {lon:.4f}",
        )


# Global default instance
location_resolver = LocationResolver()
