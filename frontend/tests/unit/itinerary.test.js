import { describe, it, expect } from "vitest";
import {
  STRESS_LABEL,
  PER_PERSON_MODES,
  formatLegPrice,
  stressTone,
  fmtDay,
  fmtYear,
  fmtTime,
  fmtDuration,
  legMinutes,
  layoverMinutes,
  isTightConnection,
  isOvernightLeg,
  TRIP_GAP_MINUTES,
  splitJourneys,
  journeyMinutes,
  cleanCarrier,
  nightsBetween,
  tripNights,
} from "../../app/lib/itinerary";

describe("stress helpers", () => {
  it("labels every score 1-5", () => {
    expect(STRESS_LABEL[1]).toBe("Relaxed");
    expect(STRESS_LABEL[5]).toBe("Intense");
  });

  it("runs calm-green → busy-rose by score band", () => {
    expect(stressTone(1).pip).toBe("bg-emerald-400");
    expect(stressTone(2).pip).toBe("bg-emerald-400");
    expect(stressTone(3).pip).toBe("bg-amber-400");
    expect(stressTone(4).pip).toBe("bg-rose-400");
    expect(stressTone(5).pip).toBe("bg-rose-400");
  });
});

describe("formatLegPrice", () => {
  it("shows a per-person unit price for groups on per-person modes", () => {
    const leg = { mode: "flight", cost: 200 };
    expect(formatLegPrice(leg, 2, "EUR")).toContain("2×");
    // 200 / 2 = 100 per person
    expect(formatLegPrice(leg, 2, "EUR")).toContain("100");
  });

  it("shows a single figure for solo travelers", () => {
    const leg = { mode: "flight", cost: 200 };
    expect(formatLegPrice(leg, 1, "EUR")).not.toContain("×");
  });

  it("keeps stays (non per-person modes) as a single figure even for groups", () => {
    expect(PER_PERSON_MODES.has("flight")).toBe(true);
    expect(PER_PERSON_MODES.has("car")).toBe(false);
    const leg = { mode: "car", cost: 200 };
    expect(formatLegPrice(leg, 2, "EUR")).not.toContain("×");
  });
});

describe("date / time formatting", () => {
  it("formats year from an ISO date", () => {
    expect(fmtYear("2026-09-04")).toBe(2026);
    expect(fmtYear("")).toBe("");
  });

  it("returns the raw string for an unparseable day", () => {
    expect(fmtDay("not-a-date")).toBe("not-a-date");
    expect(fmtDay("")).toBe("");
  });

  it("formats clock time in 24h", () => {
    // Use a timezone-explicit instant so the test is deterministic.
    expect(fmtTime("2026-09-04T13:05:00Z")).toMatch(/^\d{2}:\d{2}$/);
    expect(fmtTime("")).toBe("");
  });
});

describe("fmtDuration", () => {
  it("formats hours and minutes", () => {
    expect(fmtDuration(90)).toBe("1h 30m");
    expect(fmtDuration(120)).toBe("2h");
    expect(fmtDuration(45)).toBe("45m");
  });

  it("returns empty for non-positive input", () => {
    expect(fmtDuration(0)).toBe("");
    expect(fmtDuration(-10)).toBe("");
    expect(fmtDuration(null)).toBe("");
  });
});

describe("leg + layover math", () => {
  const a = {
    departure_time: "2026-09-04T08:00:00Z",
    arrival_time: "2026-09-04T10:00:00Z",
  };
  const b = {
    departure_time: "2026-09-04T12:00:00Z",
    arrival_time: "2026-09-04T14:00:00Z",
  };

  it("computes leg duration in minutes", () => {
    expect(legMinutes(a)).toBe(120);
  });

  it("computes the layover gap between two legs", () => {
    expect(layoverMinutes(a, b)).toBe(120);
  });

  it("returns 0 for invalid/negative durations", () => {
    expect(legMinutes({ departure_time: "x", arrival_time: "y" })).toBe(0);
    expect(layoverMinutes(b, a)).toBe(0); // b after a → negative gap
  });
});

describe("isTightConnection", () => {
  it("uses a 90m threshold before a flight", () => {
    expect(isTightConnection(60, { mode: "flight" })).toBe(true);
    expect(isTightConnection(120, { mode: "flight" })).toBe(false);
  });

  it("uses a 30m threshold for ground transit", () => {
    expect(isTightConnection(20, { mode: "train" })).toBe(true);
    expect(isTightConnection(45, { mode: "train" })).toBe(false);
  });

  it("is false when there is no gap", () => {
    expect(isTightConnection(0, { mode: "flight" })).toBe(false);
  });
});

describe("isOvernightLeg", () => {
  it("is true when the leg crosses a calendar day", () => {
    expect(
      isOvernightLeg({
        departure_time: "2026-09-04T22:00:00",
        arrival_time: "2026-09-05T06:00:00",
      })
    ).toBe(true);
  });

  it("is false within the same day", () => {
    expect(
      isOvernightLeg({
        departure_time: "2026-09-04T08:00:00",
        arrival_time: "2026-09-04T10:00:00",
      })
    ).toBe(false);
  });
});

describe("splitJourneys + journeyMinutes", () => {
  // Outbound on day 1, a multi-day stay, return on day 8.
  const legs = [
    { departure_time: "2026-09-04T08:00:00Z", arrival_time: "2026-09-04T11:00:00Z" },
    { departure_time: "2026-09-11T16:00:00Z", arrival_time: "2026-09-11T19:00:00Z" },
  ];

  it("splits at trip-length gaps into outbound + return", () => {
    const journeys = splitJourneys(legs);
    expect(journeys).toHaveLength(2);
    expect(journeys[0]).toHaveLength(1);
    expect(journeys[1]).toHaveLength(1);
  });

  it("keeps connecting legs in one journey", () => {
    const connecting = [
      { departure_time: "2026-09-04T08:00:00Z", arrival_time: "2026-09-04T10:00:00Z" },
      { departure_time: "2026-09-04T12:00:00Z", arrival_time: "2026-09-04T15:00:00Z" },
    ];
    const journeys = splitJourneys(connecting);
    expect(journeys).toHaveLength(1);
    expect(journeys[0]).toHaveLength(2);
  });

  it("measures door-to-door minutes for a journey", () => {
    expect(journeyMinutes(legs[0] ? [legs[0]] : [])).toBe(180);
    expect(journeyMinutes([])).toBe(0);
  });

  it("uses a 24h trip-gap threshold", () => {
    expect(TRIP_GAP_MINUTES).toBe(24 * 60);
  });
});

describe("cleanCarrier", () => {
  it("drops placeholders", () => {
    expect(cleanCarrier("TBD")).toBe("");
    expect(cleanCarrier("Flight (Direct)")).toBe("");
    expect(cleanCarrier("")).toBe("");
  });

  it("drops Kiwi routing labels (not real carriers)", () => {
    expect(cleanCarrier("Direct")).toBe("");
    expect(cleanCarrier("via Munich")).toBe("");
    expect(cleanCarrier("via Munich, Vienna")).toBe("");
  });

  it("keeps real airline names", () => {
    expect(cleanCarrier("Aegean Airlines")).toBe("Aegean Airlines");
    // "Viva Aerobus" starts with "Vi" but not the "via " routing prefix.
    expect(cleanCarrier("Viva Aerobus")).toBe("Viva Aerobus");
  });
});

describe("night counting", () => {
  it("counts nights between check-in and check-out", () => {
    expect(nightsBetween("2026-09-04", "2026-09-11")).toBe(7);
    expect(nightsBetween("2026-09-04", "2026-09-04")).toBe(null); // < 1 night
  });

  it("counts trip nights from start/end dates", () => {
    expect(tripNights("2026-09-04", "2026-09-11")).toBe(7);
    expect(tripNights("2026-09-04", "2026-09-04")).toBe(null);
    expect(tripNights("bad", "dates")).toBe(null);
  });
});
