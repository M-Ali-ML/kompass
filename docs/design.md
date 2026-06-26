# Kompass App: Design & Styling System (Post-Building)

This document tracks the *actual* implemented design and styling of the Kompass application as of Phase 7.

---

## 1. Current Design Status

The application uses the custom **"Candy" Theme** (a bold, fun, energetic "Joyful Pop" aesthetic) with custom shadows and spring hover transitions.

* **Styling Technology:** Tailwind CSS v4.
* **Global Stylesheet:** [globals.css](file:///Users/aly/repos/kompass/frontend/app/globals.css) containing hex color variables (mapped into Tailwind via `@theme inline`), bouncy spring transitions, tinted pink/purple/blue shadows, and a `shimmer` keyframe.
* **Base Layout:** [layout.js](file:///Users/aly/repos/kompass/frontend/app/layout.js) showing a vertical viewport container with custom header.
* **Component Structure:** Generative-UI tool cards live in `frontend/app/components/tool-cards/` and share a [tool-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-card.js) shell; renderers are registered centrally in [use-trip-tools.js](file:///Users/aly/repos/kompass/frontend/app/hooks/use-trip-tools.js).
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

* **Header/Branding:** Done. [app-header.js](file:///Users/aly/repos/kompass/frontend/app/components/app-header.js) displays a pink-shadowed primary button enclosing an animated spinning `Compass` icon, next to "Kompass" title.
* **Chat Window:** Done. Integrated CopilotKit v2 chat container with travel-specific titles and placeholders.
* **Trip Sidebar:** Done. [trip-sidebar.js](file:///Users/aly/repos/kompass/frontend/app/components/trip-sidebar.js) has two pill tabs — **Trips** (New Trip / click-to-resume / delete) and **Saved** ([saved-list.js](file:///Users/aly/repos/kompass/frontend/app/components/saved-list.js), bookmarked scenarios with destination, date range, a stress dot, and the grand total; click to reopen the detail modal).
* **Preference Badges Card:** Done. [preferences-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/preferences-card.js) renders colorful pill tags for direct flights, hotel class, transit modes, vibe tags, and non-default currency.
* **Flight & Cheapest-Date Cards:** Done. [flights-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/flights-card.js) and [cheapest-dates-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/cheapest-dates-card.js) render live results with currency-aware prices and an `≈ approx` badge when data is estimated.
* **Accommodations Card:** Done (Phase 6). [accommodations-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/accommodations-card.js) renders live lodging options with nightly + total rates, ratings, amenities, and booking links.
* **Research Card:** Done. [research-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/research-card.js) renders the grounded `search_web` answer (used for destination knowledge and ground-transport routing) so it shows as its own card.
* **Travel Scenarios Comparison Cards:** Done (Phase 5). [scenario-comparison-card.js](file:///Users/aly/repos/kompass/frontend/app/components/tool-cards/scenario-comparison-card.js) renders 2-3 side-by-side scenario cards (responsive: row on desktop, stacked on mobile) with: comparison label + date window, hero grand total, Transport/Stay breakdown, a 5-pip stress gauge (calm-green → busy-rose) with a label (Relaxed → Intense), highlight chips, a transport-leg summary line, and a "View details" action. **Best value** (cheapest) and **Lowest stress** badges are derived client-side; a shimmer skeleton shows while the tool streams.
* **Scenario Detail Modal:** Done (Phase 5–7). A centered popup (`ScenarioDetailModal`) opened from "View details" or the Saved tab, showing price + stress gauge, cost breakdown bars, stress-factor stat tiles, a per-direction travel timeline (layover/overnight/tight-connection chips, Google Flights / property links), an accommodation list, an expandable **day-by-day itinerary** (`DayRow` with time-blocked schedule items), reasoning, and a **Save this trip** / **Remove from saved** action.
* **Map Display:** Installed Leaflet + react-leaflet, component not yet implemented (Pending in Phase 8).
