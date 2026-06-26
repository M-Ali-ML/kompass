// Frontend geocoding helper built on the Google Maps JS `Geocoder`. Resolves the
// itinerary's free-text endpoints (IATA codes, city/port names, hotel names) into
// { lat, lng } coordinates so they can be plotted. Results are cached in-memory
// and in localStorage (coordinates are stable), and concurrent lookups for the
// same query are de-duped so we never hammer the Geocoding API.

const LS_KEY = "kompass:geocode-cache:v1";

const memCache = new Map();
const inFlight = new Map();

let lsLoaded = false;

function loadLocalStorage() {
  if (lsLoaded || typeof window === "undefined") return;
  lsLoaded = true;
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      for (const [k, v] of Object.entries(parsed)) {
        if (v && typeof v.lat === "number" && typeof v.lng === "number") {
          memCache.set(k, v);
        }
      }
    }
  } catch {
    // Corrupt cache is non-fatal — just start fresh.
  }
}

function persistLocalStorage() {
  if (typeof window === "undefined") return;
  try {
    const obj = {};
    for (const [k, v] of memCache.entries()) obj[k] = v;
    window.localStorage.setItem(LS_KEY, JSON.stringify(obj));
  } catch {
    // Quota / serialization issues are non-fatal.
  }
}

// Build a disambiguated geocoder query for an itinerary endpoint. A 3-letter,
// all-caps flight endpoint is almost always an IATA airport code, which geocodes
// poorly on its own ("BER" matches towns), so we append "airport". Other
// endpoints (cities, ports, stations) are geocoded as-is, optionally biased by
// the destination context.
export function endpointQuery(place, { mode, context } = {}) {
  const raw = String(place || "").trim();
  if (!raw) return "";
  if (mode === "flight" && /^[A-Z]{3}$/.test(raw)) {
    return `${raw} airport`;
  }
  if (context && !raw.toLowerCase().includes(String(context).toLowerCase())) {
    return `${raw}, ${context}`;
  }
  return raw;
}

// Query for an accommodation marker: "<name>, <location>" gives the geocoder the
// best chance of pinning the actual property (falling back to the area).
export function accommodationQuery(stay) {
  const name = String(stay?.name || "").trim();
  const location = String(stay?.location || "").trim();
  if (name && location) return `${name}, ${location}`;
  return name || location;
}

// Geocode a single query string using a provided `google.maps.Geocoder`
// instance. Returns { lat, lng } or null. Cached + de-duped by query.
export async function geocodePlace(geocoder, query) {
  const key = String(query || "").trim().toLowerCase();
  if (!key || !geocoder) return null;

  loadLocalStorage();
  if (memCache.has(key)) return memCache.get(key);
  if (inFlight.has(key)) return inFlight.get(key);

  const promise = new Promise((resolve) => {
    geocoder.geocode({ address: query }, (results, status) => {
      if (status === "OK" && results && results[0]) {
        const loc = results[0].geometry.location;
        const coords = { lat: loc.lat(), lng: loc.lng() };
        memCache.set(key, coords);
        persistLocalStorage();
        resolve(coords);
      } else {
        // Cache misses as null so we don't retry hopeless queries every render.
        memCache.set(key, null);
        resolve(null);
      }
    });
  }).finally(() => {
    inFlight.delete(key);
  });

  inFlight.set(key, promise);
  return promise;
}
