const { test, expect } = require('@playwright/test');
const { BACKEND_URL, FIXTURE } = require('../e2e.constants');

// Backend REST contract for Phase 3. Uses a dedicated trip id so it never
// interferes with the UI specs' seeded greece/japan trips.
const API_TRIP_ID = 'e2e-api-trip';

test.describe('Trips & profile REST API', () => {
  test('health check responds ok', async ({ request }) => {
    const res = await request.get(`${BACKEND_URL}/health`);
    expect(res.ok()).toBeTruthy();
    expect(await res.json()).toEqual({ status: 'ok' });
  });

  test('lists the seeded trips', async ({ request }) => {
    const res = await request.get(`${BACKEND_URL}/api/trips`);
    expect(res.ok()).toBeTruthy();
    const { trips } = await res.json();
    const titles = trips.map((t) => t.title);
    expect(titles).toContain(FIXTURE.greece.title);
    expect(titles).toContain(FIXTURE.japan.title);
  });

  test('returns a trip with its messages', async ({ request }) => {
    const res = await request.get(`${BACKEND_URL}/api/trips/e2e-greece`);
    expect(res.ok()).toBeTruthy();
    const trip = await res.json();
    expect(trip.title).toBe(FIXTURE.greece.title);
    const roles = trip.messages.map((m) => m.role);
    expect(roles).toEqual(['user', 'assistant']);
    expect(trip.messages[1].content).toContain(FIXTURE.greece.assistant);
  });

  test('404s for an unknown trip', async ({ request }) => {
    const res = await request.get(`${BACKEND_URL}/api/trips/does-not-exist`);
    expect(res.status()).toBe(404);
  });

  test('creates and deletes a trip', async ({ request }) => {
    const created = await request.post(`${BACKEND_URL}/api/trips`, {
      data: { id: API_TRIP_ID, title: 'API created trip' },
    });
    expect(created.ok()).toBeTruthy();
    expect((await created.json()).id).toBe(API_TRIP_ID);

    const list = await (await request.get(`${BACKEND_URL}/api/trips`)).json();
    expect(list.trips.map((t) => t.id)).toContain(API_TRIP_ID);

    const deleted = await request.delete(`${BACKEND_URL}/api/trips/${API_TRIP_ID}`);
    expect(deleted.ok()).toBeTruthy();

    const after = await (await request.get(`${BACKEND_URL}/api/trips`)).json();
    expect(after.trips.map((t) => t.id)).not.toContain(API_TRIP_ID);
  });

  test('reads and updates the global profile', async ({ request }) => {
    const initial = await (await request.get(`${BACKEND_URL}/api/profile`)).json();
    expect(initial.direct_flights_only).toBe(true);
    expect(initial.vibe_tags).toContain('foodie');

    const updated = await request.put(`${BACKEND_URL}/api/profile`, {
      data: {
        direct_flights_only: false,
        preferred_transit_modes: ['train'],
        hotel_class: '4-star',
        vibe_tags: ['history'],
      },
    });
    expect(updated.ok()).toBeTruthy();
    const body = await updated.json();
    expect(body.hotel_class).toBe('4-star');
    expect(body.preferred_transit_modes).toEqual(['train']);
  });
});
