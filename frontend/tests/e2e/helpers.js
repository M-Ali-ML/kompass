const { expect } = require('@playwright/test');

// The trips sidebar starts collapsed on desktop (and lives in an off-canvas
// drawer on mobile); the header menu button reveals it. Any spec that asserts
// on the sidebar must open it first. Idempotent: returns early if the sidebar
// is already showing, so it's safe to call once per navigation.
//
// Retries the click: on the very first (coldest) load the button is visible in
// the prerendered HTML before React hydration attaches its handler, so a
// too-early click can be swallowed. Re-clicking until the aside appears makes
// the helper robust to that.
async function openTrips(page) {
  const sidebar = page.locator('aside');
  await expect(async () => {
    if (await sidebar.isVisible().catch(() => false)) return;
    await page.getByRole('button', { name: 'Open trips menu' }).click();
    await expect(sidebar).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 15_000 });
  return sidebar;
}

module.exports = { openTrips };
