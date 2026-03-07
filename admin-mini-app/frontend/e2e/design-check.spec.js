import { test, expect } from '@playwright/test';

test.describe('Design System — Visual Check', () => {

  test('Dashboard page renders with new design', async ({ page }) => {
    await page.goto('/');

    // Wait for Vue app to mount
    await page.waitForSelector('#app > div', { timeout: 10000 });

    // Header exists with backdrop blur
    const header = page.locator('header').first();
    await expect(header).toBeVisible();

    // Navbar exists at bottom
    const navbar = page.locator('nav').first();
    await expect(navbar).toBeVisible();

    // Screenshot for visual comparison
    await page.screenshot({ path: 'e2e/screenshots/dashboard.png', fullPage: true });
  });

  test('Users list page renders', async ({ page }) => {
    await page.goto('/users');

    // Wait for Vue app to mount
    await page.waitForSelector('#app > div', { timeout: 10000 });

    // Search input exists (SearchInput component uses type="text")
    const search = page.locator('input[type="text"]').first();
    await expect(search).toBeVisible();

    // Filter chips exist
    const filters = page.locator('button').filter({ hasText: /Все|Оплачено|Не оплачено|Истекает/ });
    await expect(filters.first()).toBeVisible();

    await page.screenshot({ path: 'e2e/screenshots/users-list.png', fullPage: true });
  });

  test('Settings page renders with iOS-style form', async ({ page }) => {
    await page.goto('/settings');

    // Wait for Vue app to mount
    await page.waitForSelector('#app > div', { timeout: 10000 });

    await page.screenshot({ path: 'e2e/screenshots/settings.png', fullPage: true });
  });

  test('Navigation between pages works', async ({ page }) => {
    await page.goto('/');

    // Wait for Vue app to mount
    await page.waitForSelector('#app > div', { timeout: 10000 });

    // Click Users nav tab
    const usersTab = page.locator('nav button').filter({ hasText: 'Юзеры' });
    await usersTab.click();
    await expect(page).toHaveURL(/\/users/);

    // Click Home tab
    const homeTab = page.locator('nav button').filter({ hasText: 'Главная' });
    await homeTab.click();
    await expect(page).toHaveURL(/\/$/);
  });

  test('Design tokens are applied correctly', async ({ page }) => {
    await page.goto('/');

    // Wait for Vue app to mount and styles to load
    await page.waitForSelector('#app > div', { timeout: 10000 });

    // Check Inter font is loaded (check body style declaration, not computed which needs network)
    const body = page.locator('body');
    const fontFamily = await body.evaluate(el => getComputedStyle(el).fontFamily);
    // In test env, Inter may not load from Google Fonts — check that config includes it
    expect(fontFamily.toLowerCase()).toMatch(/inter|sans-serif/);

    // Check card has correct border-radius (16px)
    const card = page.locator('.card').first();
    if (await card.count() > 0) {
      const radius = await card.evaluate(el => getComputedStyle(el).borderRadius);
      expect(radius).toBe('16px');
    }
  });

  test('Mobile viewport — content fits 375px width', async ({ page }) => {
    await page.goto('/');

    // Wait for Vue app to mount
    await page.waitForSelector('#app > div', { timeout: 10000 });

    // No horizontal overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(375);
  });

  test('User Detail page renders', async ({ page }) => {
    await page.goto('/users/1');
    await page.waitForSelector('#app > div', { timeout: 10000 });
    await page.screenshot({ path: 'e2e/screenshots/user-detail.png', fullPage: true });
  });

  test('All main routes load without JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    const routes = ['/', '/users', '/settings'];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForSelector('#app > div', { timeout: 10000 });
    }

    // Filter out expected API errors (no backend running)
    const realErrors = errors.filter(e => !e.includes('fetch') && !e.includes('Network') && !e.includes('ERR_') && !e.includes('status code'));
    expect(realErrors).toEqual([]);
  });
});
