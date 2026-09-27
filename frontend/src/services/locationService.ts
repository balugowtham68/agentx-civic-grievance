/**
 * Live GPS Geolocation and Reverse Geocoding Service for SPANDAN AI.
 * Automatically fetches high-precision device GPS coordinates and
 * resolves them into exact civic addresses (Street, Colony, Ward, City).
 */

export interface LiveLocationResult {
  latitude: number;
  longitude: number;
  accuracy: number;
  formattedAddress: string;
  shortAddress: string;
  road?: string;
  colony?: string;
  ward?: string;
  city?: string;
  state?: string;
  postcode?: string;
}

export async function fetchLiveDeviceLocation(): Promise<LiveLocationResult> {
  if (!navigator.geolocation) {
    throw new Error("Geolocation is not supported by your browser.");
  }

  // 1. Acquire high-accuracy GPS coordinates from hardware
  const position = await new Promise<GeolocationPosition>((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    });
  });

  const lat = position.coords.latitude;
  const lng = position.coords.longitude;
  const accuracy = Math.round(position.coords.accuracy);

  // 2. Reverse Geocode coordinates into exact street & colony name
  let formattedAddress = `GPS: ${lat.toFixed(5)}° N, ${lng.toFixed(5)}° E`;
  let shortAddress = `GPS: ${lat.toFixed(5)}° N, ${lng.toFixed(5)}° E`;
  let road: string | undefined;
  let colony: string | undefined;
  let ward: string | undefined;
  let city: string | undefined;
  let state: string | undefined;
  let postcode: string | undefined;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`,
      {
        headers: { "User-Agent": "SpandanAI-CivicGrievance/1.0" },
        signal: controller.signal,
      }
    );
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      const addr = data.address || {};
      road = addr.road || addr.street;
      colony = addr.suburb || addr.neighbourhood || addr.residential || addr.subdivision;
      city = addr.city || addr.town || addr.municipality || addr.village;
      state = addr.state;
      postcode = addr.postcode;

      // Extract ward if available in display name or address
      const wardMatch = data.display_name?.match(/Ward\s+\d+[^,]*/i);
      if (wardMatch) {
        ward = wardMatch[0].trim();
      }

      // Build clean short address for input field (e.g. "HITEC City-Madhapur Road, Kothaguda, Hyderabad")
      const shortParts = [road, colony, city].filter(Boolean);
      if (shortParts.length > 0) {
        shortAddress = shortParts.join(", ");
      }

      // Build comprehensive civic address with ward & postal code
      const fullParts = [
        road,
        colony,
        ward,
        city,
        state,
        postcode ? `PIN: ${postcode}` : null,
      ].filter(Boolean);

      if (fullParts.length > 0) {
        formattedAddress = fullParts.join(", ");
      }
    }
  } catch (err) {
    console.warn("Reverse geocode network fetch failed, using fallback:", err);
    // Fallback: Check backend local civic resolver
    try {
      const bRes = await fetch(`/api/v1/location/reverse?lat=${lat}&lng=${lng}`);
      if (bRes.ok) {
        const bData = await bRes.json();
        if (bData.formatted_address) {
          formattedAddress = bData.formatted_address;
          shortAddress = bData.locality || bData.city || formattedAddress;
          ward = bData.ward;
          city = bData.city;
        }
      }
    } catch {
      // Keep GPS fallback
    }
  }

  return {
    latitude: lat,
    longitude: lng,
    accuracy,
    formattedAddress,
    shortAddress,
    road,
    colony,
    ward,
    city,
    state,
    postcode,
  };
}
