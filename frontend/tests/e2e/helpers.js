const { expect } = require('@playwright/test');

// The trips sidebar starts collapsed on desktop (and lives in an off-canvas
// drawer on mobile); the header menu button reveals it. Any spec that asserts
// on the sidebar must open it first. Idempotent: returns early if the sidebar
// is already showing, so it's safe to call once per navigation.
async function openTrips(page) {
  const sidebar = page.locator('aside');
  if (await sidebar.isVisible().catch(() => false)) return sidebar;
  await page.getByRole('button', { name: 'Open trips menu' }).click();
  await expect(sidebar).toBeVisible();
  return sidebar;
}

module.exports = { openTrips };
