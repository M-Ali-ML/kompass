# Kompass App: Design & Styling System (Post-Building)

This document tracks the *actual* implemented design and styling of the Kompass application as of Phase 10.

---

## 1. Current Design Status

The application uses the custom **"Candy" Theme** (a bold, fun, energetic "Joyful Pop" aesthetic) with custom shadows and spring hover transitions.

* **Styling Technology:** Tailwind CSS v4.
* **Global Stylesheet:** [globals.css](../frontend/app/globals.css) containing hex color variables (mapped into Tailwind via `@theme inline`), bouncy spring transitions, tinted pink/purple/blue shadows, and a `shimmer` keyframe.
* **Base Layout:** [layout.js](../frontend/app/layout.js) showing a vertical viewport container with custom header.
* **Component Structure:** Generative-UI tool cards live in `frontend/app/components/tool-cards/` and share a [tool-card.js](../frontend/app/components/tool-card.js) shell; renderers are registered centrally in [use-trip-tools.js](../frontend/app/hooks/use-trip-tools.js).
* **Typography:** DM Sans (Rounded, friendly, bold headings).
* **Color Palette:** Warm Pink-White Background (`#fef7ff`), Hot Pink (`#e040a0`), Purple (`#7c52aa`), Sky Blue (`#0096cc`).

---

## 2. Design System Matrix

| Attribute | Blueprint Target | Currently Implemented | Status |
| :--- | :--- | :--- | :--- |
| **Theme / Vibe** | "Joyful Pop" | "Joyful Pop" | 🟢 Completed |
| **Color Palette** | Hot Pink, Purple, Sky Blue | Primary `#e040a0`, Secondary `#7c52aa`, Accent `#0096cc` | 🟢 Completed |
| **Typography** | DM Sans | DM Sans (imported via Google Fonts) | 🟢 Completed |
| **Corner Radius** | 16px-20px cards, pill-shaped tags | 16px card panels, full rounded tags | 🟢 Completed |
| **Animations** | Bouncy scale-up spring hover | `.bouncy-hover` scale transition | 🟢 Completed |
| **Shadows** | Tinted color shadows | Pink, purple, and blue shadows at 20-35% opacity | 🟢 Completed |

---

## 3. UI Component Status

* **Header/Branding:** Done. [app-header.js](../frontend/app/components/app-header.js) (a client component) displays a pink-shadowed primary button enclosing an animated spinning `Compass` icon next to the "Kompass" title, plus a **gear button** opening the settings modal and (below `lg`) a **hamburger** that toggles the off-canvas trip drawer.
* **Chat Window:** Done. Integrated CopilotKit v2 chat container with travel-specific titles and placeholders.
* **Trip Sidebar:** Done. [trip-sidebar.js](../frontend/app/components/trip-sidebar.js) has two pill tabs — **Trips** (New Trip / click-to-resume / delete) and **Saved** ([saved-list.js](../frontend/app/components/saved-list.js), bookmarked scenarios with destination, date range, a stress dot, and the grand total; click to reopen the detail modal).
* **Preference Badges Card:** Done. [preferences-card.js](../frontend/app/components/tool-cards/preferences-card.js) renders colorful pill tags for direct flights, hotel class, transit modes, vibe tags, and non-default currency.
* **Clarifying-Question Card (HITL):** Done (Phase 10). [clarify-card.js](../frontend/app/components/tool-cards/clarify-card.js) renders the `ask_clarifying_question` human-in-the-loop tool: the question, candy option pills (single- or multi-select), and an always-present "Other" free-text input with a send button. Resolves to a compact "Answered" chip on `complete` (rehydrates on resume).
* **Settings Modal:** Done (Phase 10). [settings-modal.js](../frontend/app/components/settings-modal.js) is a portal modal (mobile bottom-sheet below `sm`) editing the global travel profile — home city input, direct-flights toggle switch, transit-mode chips with glyphs, accommodation-standard select, vibe-tag input/chips, and currency select — with loading/saving/saved/error button states.
* **Search Progress:** Done (Phase 9). [search-progress.js](../frontend/app/components/search-progress.js) is an animated candy-gradient pill that slides across a soft pink track (`progress-slide` keyframes), shown inside every loading tool card beneath a contextual label.
* **Flight & Cheapest-Date Cards:** Done. [flights-card.js](../frontend/app/components/tool-cards/flights-card.js) and [cheapest-dates-card.js](../frontend/app/components/tool-cards/cheapest-dates-card.js) render live results with currency-aware prices and an `≈ approx` badge when data is estimated.
* **Accommodations Card:** Done (Phase 6). [accommodations-card.js](../frontend/app/components/tool-cards/accommodations-card.js) renders live lodging options with nightly + total rates, ratings, amenities, and booking links.
* **Research Card:** Done. [research-card.js](../frontend/app/components/tool-cards/research-card.js) renders the grounded `search_web` answer (used for destination knowledge and ground-transport routing) so it shows as its own card.
* **Travel Scenarios Comparison Cards:** Done (Phase 5). [scenario-comparison-card.js](../frontend/app/components/tool-cards/scenario-comparison-card.js) renders 2-3 side-by-side scenario cards (responsive: row on desktop, stacked on mobile) with: comparison label + date window, hero grand total, Transport/Stay breakdown, a 5-pip stress gauge (calm-green → busy-rose) with a label (Relaxed → Intense), highlight chips, a transport-leg summary line, and a "View details" action. **Best value** (cheapest) and **Lowest stress** badges are derived client-side; a shimmer skeleton shows while the tool streams.
* **Scenario Detail Modal:** Done (Phase 5–7, polished Phase 10). A popup (`ScenarioDetailModal`, a mobile bottom-sheet below `sm`) opened from "View details" or the Saved tab, showing price + stress gauge, cost breakdown bars, stress-factor stat tiles, a per-direction travel timeline (layover/overnight/tight-connection chips, Google Flights / property links), an accommodation list, an expandable **day-by-day itinerary** (controlled `DayRow`s with a day count + **Expand all / Collapse all**), reasoning, a **Save this trip** / **Remove from saved** action, and a **View on map** action.
* **Responsive Pass:** Done (Phase 10). Desktop (`lg`+) keeps the 3-pane split (sidebar · chat · map); below `lg` the chat is full-width, the trip sidebar collapses into a header-toggled off-canvas drawer, and the settings + scenario-detail modals become bottom-sheets.
* **Map Display:** Done (Phase 8). A persistent right-hand split panel ([trip-panel.js](../frontend/app/components/map/trip-panel.js)) shows a compact itinerary summary above an interactive Google Map ([trip-map.js](../frontend/app/components/map/trip-map.js), via `@vis.gl/react-google-maps`). The map plots numbered transit stops + accommodation markers and draws polylines colored per transport mode (geodesic curves for flights), auto-fitting bounds. Coordinates are resolved on the client with the Google Geocoder ([lib/geocode.js](../frontend/app/lib/geocode.js), cached in `localStorage`; IATA codes disambiguated as airports). The active route comes from a shared `MapState` store ([map-context.js](../frontend/app/components/map/map-context.js)) that the scenario cards feed — auto-selecting the best-value scenario and offering "View on map" per card. Needs a browser `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`; without it the panel shows a friendly placeholder. The panel is hidden below the `lg` breakpoint (the chat-side cards remain the mobile experience). Leaflet/react-leaflet remain installed as a possible no-key fallback.
