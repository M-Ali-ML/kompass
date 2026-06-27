const { test, expect } = require('@playwright/test');
const { BACKEND_URL } = require('../e2e.constants');

// Phase 10 — global profile / settings UI. Opens the settings modal, edits
// preferences, saves, and confirms the values persist across a reload and in
// the backend. Runs after api.spec.js (alphabetical), which asserts the seeded
// profile first, so this test's mutations don't disturb it.

test.describe('Settings / global profile', () => {
  // The CopilotKit dev inspector (<cpk-web-inspector>) renders a full-viewport
  // overlay that can intercept pointer events over the header. Neutralize it so
  // the settings button is clickable in tests.
  const hideInspector = (page) =>
    page.addStyleTag({ content: 'cpk-web-inspector{display:none !important}' });

  test('edit preferences → save → persists across reload', async ({ page, request }) => {
    await page.goto('/');
    await hideInspector(page);

    await page.getByRole('button', { name: 'Travel preferences' }).click();

    const dialog = page.getByRole('dialog', { name: 'Travel preferences' });
    await expect(dialog).toBeVisible();
    // Wait for the profile fetch to populate the form.
    await expect(dialog.getByLabel('Currency')).toBeVisible({ timeout: 15_000 });

    // Change currency and add a vibe tag.
    await dialog.getByLabel('Currency').selectOption('USD');
    const vibeInput = dialog.getByPlaceholder(/foodie/i);
    await vibeInput.fill('beachlife');
    await dialog.getByRole('button', { name: 'Add', exact: true }).click();
    await expect(dialog.getByText('beachlife')).toBeVisible();

    await dialog.getByRole('button', { name: /Save preferences/i }).click();
    await expect(dialog.getByRole('button', { name: /Saved/i })).toBeVisible();

    // Backend reflects the change.
    const profile = await (await request.get(`${BACKEND_URL}/api/profile`)).json();
    expect(profile.currency).toBe('USD');
    expect(profile.vibe_tags).toContain('beachlife');

    // Reopen after a reload — values are restored from the server.
    await page.reload();
    await hideInspector(page);
    await page.getByRole('button', { name: 'Travel preferences' }).click();
    const dialog2 = page.getByRole('dialog', { name: 'Travel preferences' });
    await expect(dialog2.getByLabel('Currency')).toHaveValue('USD', { timeout: 15_000 });
    await expect(dialog2.getByText('beachlife')).toBeVisible();
  });
});
