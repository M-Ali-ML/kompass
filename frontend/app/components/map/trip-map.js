"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  APIProvider,
  Map,
  AdvancedMarker,
  useMap,
  useMapsLibrary,
} from "@vis.gl/react-google-maps";
import { MapPin, Compass, BedDouble } from "lucide-react";
import { modeColor } from "../../lib/transport";
import { geocodePlace, endpointQuery, accommodationQuery } from "../../lib/geocode";

const MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
// A mapId is required for Advanced Markers; the default cloud-styled id works
// without any cloud configuration.
const MAP_ID = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID";

// Build the ordered list of transit waypoints (each leg's origin then its
// destination, de-duped consecutively) plus the accommodation stays. Each entry
// keeps the geocoder query and the mode of the *incoming* leg so we can color
// connecting lines.
function buildWaypoints(route) {
  if (!route) return { stops: [], stays: [] };
  const context = route.destination || "";
  const stops = [];
  const seen = new Set();

  const pushStop = (place, mode) => {
    const query = endpointQuery(place, { mode, context });
    if (!query) return;
    const dedupeKey = query.toLowerCase();
    if (seen.has(dedupeKey)) return;
    seen.add(dedupeKey);
    stops.push({ label: place, query, mode });
  };

  (route.legs || []).forEach((leg) => {
    pushStop(leg.origin, leg.mode);
    pushStop(leg.destination, leg.mode);
  });

  const stays = (route.accommodations || [])
    .map((s) => ({ name: s.name, location: s.location, query: accommodationQuery(s) }))
    .filter((s) => s.query);

  return { stops, stays };
}

// Resolves every waypoint/stay query to coordinates via the Geocoder library and
// returns the geocoded stops + stays once ready.
function useGeocodedRoute(route) {
  const geocodingLib = useMapsLibrary("geocoding");
  const [state, setState] = useState({ loading: false, stops: [], stays: [] });

  const { stops, stays } = useMemo(() => buildWaypoints(route), [route]);

  // Stable signature so the effect only re-runs when the actual places change.
  const signature = useMemo(
    () => JSON.stringify({ s: stops.map((x) => x.query), a: stays.map((x) => x.query) }),
    [stops, stays]
  );

  useEffect(() => {
    if (!geocodingLib) return;

    let cancelled = false;

    // All setState happens inside this async flow (never synchronously in the
    // effect body) so we don't trigger cascading renders.
    (async () => {
      if (stops.length === 0 && stays.length === 0) {
        if (!cancelled) setState({ loading: false, stops: [], stays: [] });
        return;
      }
      if (!cancelled) setState((prev) => ({ ...prev, loading: true }));

      const geocoder = new geocodingLib.Geocoder();
      const stopResults = await Promise.all(
        stops.map(async (s) => ({ ...s, coords: await geocodePlace(geocoder, s.query) }))
      );
      const stayResults = await Promise.all(
        stays.map(async (s) => ({ ...s, coords: await geocodePlace(geocoder, s.query) }))
      );
      if (cancelled) return;
      setState({
        loading: false,
        stops: stopResults.filter((s) => s.coords),
        stays: stayResults.filter((s) => s.coords),
      });
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geocodingLib, signature]);

  return state;
}

// Draws mode-colored polylines between consecutive transit stops and auto-fits
// the viewport to every plotted point. Rendered as a child of <Map> so it can
// reach the map instance + the imperative maps library.
function RouteLayer({ stops, stays }) {
  const map = useMap();
  // Polyline lives in the "maps" library; LatLngBounds lives in "core".
  const mapsLib = useMapsLibrary("maps");
  const coreLib = useMapsLibrary("core");
  const linesRef = useRef([]);

  useEffect(() => {
    if (!map || !mapsLib || !coreLib) return;

    // Clear any previously drawn lines before redrawing.
    linesRef.current.forEach((l) => l.setMap(null));
    linesRef.current = [];

    for (let i = 0; i < stops.length - 1; i++) {
      const a = stops[i];
      const b = stops[i + 1];
      if (!a.coords || !b.coords) continue;
      // The connecting line's mode is the mode of the leg arriving at b.
      const color = modeColor(b.mode);
      const line = new mapsLib.Polyline({
        path: [a.coords, b.coords],
        geodesic: true,
        strokeColor: color,
        strokeOpacity: b.mode === "flight" ? 0.9 : 0.85,
        strokeWeight: 3,
        map,
      });
      linesRef.current.push(line);
    }

    // Fit bounds to all points (stops + stays).
    const points = [
      ...stops.map((s) => s.coords),
      ...stays.map((s) => s.coords),
    ].filter(Boolean);
    if (points.length === 1) {
      map.setCenter(points[0]);
      map.setZoom(9);
    } else if (points.length > 1) {
      const bounds = new coreLib.LatLngBounds();
      points.forEach((p) => bounds.extend(p));
      map.fitBounds(bounds, 64);
    }

    return () => {
      linesRef.current.forEach((l) => l.setMap(null));
      linesRef.current = [];
    };
  }, [map, mapsLib, coreLib, stops, stays]);

  return null;
}

function MapPanel({ route }) {
  const { loading, stops, stays } = useGeocodedRoute(route);

  return (
    <div className="relative w-full h-full">
      <Map
        mapId={MAP_ID}
        defaultCenter={{ lat: 30, lng: 10 }}
        defaultZoom={3}
        gestureHandling="greedy"
        disableDefaultUI={false}
        className="w-full h-full"
      >
        {stops.map((s, i) => (
          <AdvancedMarker key={`stop-${i}`} position={s.coords} title={s.label}>
            <div
              className="flex items-center justify-center w-7 h-7 rounded-full text-white text-xs font-bold border-2 border-white shadow-md"
              style={{ backgroundColor: modeColor(s.mode) }}
            >
              {i + 1}
            </div>
          </AdvancedMarker>
        ))}
        {stays.map((s, i) => (
          <AdvancedMarker key={`stay-${i}`} position={s.coords} title={s.name}>
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-secondary text-white border-2 border-white shadow-md">
              <BedDouble className="w-3.5 h-3.5" />
            </div>
          </AdvancedMarker>
        ))}
        <RouteLayer stops={stops} stays={stays} />
      </Map>

      {loading && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 px-3 py-1.5 rounded-full bg-surface/90 border border-pink-100 pink-shadow text-xs font-semibold text-foreground/70 inline-flex items-center gap-1.5">
          <Compass className="w-3.5 h-3.5 text-primary animate-spin" /> Mapping the route…
        </div>
      )}
    </div>
  );
}

function Placeholder({ icon: Icon, title, subtitle }) {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center text-center px-6 bg-pink-50/40">
      <div className="p-3 rounded-2xl bg-primary/10 text-primary mb-3">
        <Icon className="w-7 h-7" />
      </div>
      <p className="text-sm font-bold text-foreground">{title}</p>
      {subtitle && <p className="text-xs text-foreground/60 mt-1 max-w-[260px]">{subtitle}</p>}
    </div>
  );
}

// Right-panel interactive map. Renders a friendly placeholder when no API key is
// configured (the app still works without a map) or when no route is selected.
export function TripMap({ route }) {
  if (!MAPS_API_KEY) {
    return (
      <Placeholder
        icon={MapPin}
        title="Map needs a Google Maps API key"
        subtitle="Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY in frontend/.env.local to see your trip on the map."
      />
    );
  }

  if (!route || ((route.legs || []).length === 0 && (route.accommodations || []).length === 0)) {
    return (
      <Placeholder
        icon={Compass}
        title="Your trip will appear here"
        subtitle="Plan or compare a trip in the chat and the route will be drawn on the map."
      />
    );
  }

  return (
    <APIProvider apiKey={MAPS_API_KEY}>
      <MapPanel route={route} />
    </APIProvider>
  );
}
