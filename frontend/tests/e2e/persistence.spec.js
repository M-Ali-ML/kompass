const { test, expect } = require('@playwright/test');
const { FIXTURE } = require('../e2e.constants');
const { openTrips } = require('./helpers');

// These tests exercise Phase 3 (persistence & session memory) against a seeded
// database, with no LLM involvement. They run in declaration order (workers: 1)
// because the final test mutates the shared seed by deleting a trip.

test.describe('Trips persistence & resume', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // The trips sidebar is collapsed by default; reveal it before asserting.
    await openTrips(page);
    // Wait for the sidebar to finish loading the seeded trips.
    await expect(
      page.locator('aside').getByText(FIXTURE.greece.title)
    ).toBeVisible({ timeout: 15_000 });
  });

  test('renders the app shell and the seeded trip list', async ({ page }) => {
    await expect(page.locator('header')).toContainText('Kompass');
    await expect(page.getByRole('button', { name: 'New Trip' })).toBeVisible();

    const sidebar = page.locator('aside');
    await expect(sidebar.getByText(FIXTURE.greece.title)).toBeVisible();
    await expect(sidebar.getByText(FIXTURE.japan.title)).toBeVisible();
  });

  test('resuming a trip loads its conversation into the chat', async ({ page }) => {
    await page.locator('aside').getByText(FIXTURE.greece.title).click();

    // Assistant reply is unique to the chat (not shown in the sidebar).
    await expect(page.getByText(FIXTURE.greece.assistant)).toBeVisible();
  });

  test('switching trips swaps the visible conversation', async ({ page }) => {
    const sidebar = page.locator('aside');

    await sidebar.getByText(FIXTURE.greece.title).click();
    await expect(page.getByText(FIXTURE.greece.assistant)).toBeVisible();

    await sidebar.getByText(FIXTURE.japan.title).click();
    await expect(page.getByText(FIXTURE.japan.assistant)).toBeVisible();
    await expect(page.getByText(FIXTURE.greece.assistant)).toHaveCount(0);
  });

  test('"New Trip" clears the conversation', async ({ page }) => {
    await page.locator('aside').getByText(FIXTURE.greece.title).click();
    await expect(page.getByText(FIXTURE.greece.assistant)).toBeVisible();

    await page.getByRole('button', { name: 'New Trip' }).click();
    await expect(page.getByText(FIXTURE.greece.assistant)).toHaveCount(0);
  });

  test('deleting a trip removes it from the sidebar', async ({ page }) => {
    const sidebar = page.locator('aside');
    const japanRow = sidebar.locator('li').filter({ hasText: FIXTURE.japan.title });

    await japanRow.hover();
    await japanRow.getByRole('button', { name: 'Delete trip' }).click();

    await expect(sidebar.getByText(FIXTURE.japan.title)).toHaveCount(0);
    // Greece is untouched.
    await expect(sidebar.getByText(FIXTURE.greece.title)).toBeVisible();
  });
});
