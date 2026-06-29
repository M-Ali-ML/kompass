const { test, expect } = require('@playwright/test');
const { BACKEND_URL } = require('../e2e.constants');
const { openTrips } = require('./helpers');

// Phase 10 — saved scenarios UI. Seeds one saved scenario via the REST API
// (no LLM), then drives the Saved tab → detail modal → remove flow in the UI.
// Files sort after api.spec.js / persistence.spec.js so the profile/trip
// assertions there see the untouched seed first.

const SAVED = {
  destination: 'Testville Saved E2E',
  label: 'E2E Saved Scenario',
  comparison_label: 'Test Window',
};

test.describe('Saved scenarios', () => {
  test('save via API → appears in Saved tab → open detail → remove', async ({ page, request }) => {
    // Start from a clean slate so a CI retry (which re-creates the scenario)
    // never leaves duplicate rows that break the strict-mode locator below.
    const existing = await (await request.get(`${BACKEND_URL}/api/saved-scenarios`)).json();
    for (const s of existing.saved) {
      await request.delete(`${BACKEND_URL}/api/saved-scenarios/${s.id}`);
    }

    const created = await request.post(`${BACKEND_URL}/api/saved-scenarios`, {
      data: {
        destination: SAVED.destination,
        currency: 'EUR',
        scenario: {
          label: SAVED.label,
          comparison_label: SAVED.comparison_label,
          start_date: '2026-09-04',
          end_date: '2026-09-07',
          stress_score: 2,
          cost_breakdown: { transportation: 200, accommodation: 400, grand_total: 600 },
          stress_factors: {
            layover_count: 0,
            overnight_travel: false,
            tight_connection: false,
            total_travel_hours: 5,
          },
          itinerary: {
            legs: [],
            accommodations: [],
            days: [
              {
                day_number: 1,
                title: 'Arrival',
                description: 'Land and settle in',
                schedule: [
                  { period: 'Evening', activity: 'Dinner by the harbor', location: 'Old Town' },
                ],
              },
            ],
          },
        },
      },
    });
    expect(created.ok()).toBeTruthy();
    const savedId = (await created.json()).id;

    await page.goto('/');

    // The trips sidebar is collapsed by default; reveal it, then switch tabs.
    await openTrips(page);
    await page.locator('aside').getByRole('button', { name: 'Saved', exact: true }).click();

    const savedRow = page.locator('aside').getByText(SAVED.destination);
    await expect(savedRow).toBeVisible({ timeout: 15_000 });

    // Open the detail modal.
    await savedRow.click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(SAVED.label)).toBeVisible();
    await expect(dialog.getByText('Day-by-day itinerary')).toBeVisible();

    // Remove it; the modal closes and the row disappears.
    await dialog.getByRole('button', { name: 'Remove from saved' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.locator('aside').getByText(SAVED.destination)).toHaveCount(0);

    // And it's gone from the backend.
    const after = await request.get(`${BACKEND_URL}/api/saved-scenarios/${savedId}`);
    expect(after.status()).toBe(404);
  });
});
