# Kompass App: Design & Styling System (Post-Building)

This document tracks the *actual* implemented design and styling of the Kompass application as of Phase 2.

---

## 1. Current Design Status

The application uses the custom **"Candy" Theme** (a bold, fun, energetic "Joyful Pop" aesthetic) with custom shadows and spring hover transitions.

* **Styling Technology:** Tailwind CSS v4.
* **Global Stylesheet:** [globals.css](file:///Users/aly/repos/kompass/frontend/app/globals.css) containing HSL color variables, bouncy transitions, and tinted shadows.
* **Base Layout:** [layout.js](file:///Users/aly/repos/kompass/frontend/app/layout.js) showing a vertical viewport container with custom header.
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

* **Header/Branding:** Done. Displays a pink-shadowed primary button enclosing an animated spinning `Compass` icon, next to "Kompass" title.
* **Chat Window:** Done. Integrated CopilotKit chat container with travel-specific titles and placeholders.
* **Preference Badges Card:** Done. Customized `gather_preferences` tool renderer displaying colorful tags for direct flights, hotel class, transit modes, and vibe tags.
* **Travel Scenarios Comparison Table:** Not yet implemented (Pending in Phase 5).
* **Map Display:** Installed Leaflet, component not yet implemented (Pending in Phase 8).
