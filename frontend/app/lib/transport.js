// Shared per-transport-mode presentation so the scenario cards and the map agree
// on glyphs and colors. Colors are hex (not Tailwind classes) because the map
// draws polylines via the imperative google.maps API.
export const MODE_GLYPH = {
  flight: "✈️",
  train: "🚆",
  bus: "🚌",
  ferry: "🚢",
  car: "🚗",
  other: "🚐",
};

export const MODE_COLOR = {
  flight: "#e040a0", // primary pink
  train: "#7c52aa", // secondary purple
  ferry: "#0096cc", // accent blue
  bus: "#f59e0b", // amber
  car: "#10b981", // emerald
  other: "#807a8a", // muted
};

export const modeColor = (mode) => MODE_COLOR[mode] || MODE_COLOR.other;
export const modeGlyph = (mode) => MODE_GLYPH[mode] || MODE_GLYPH.other;
