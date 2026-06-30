import { test, expect } from '@playwright/test';

test.describe('DocsMind AI Workspace E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Mock successful authentication for E2E speed
    await page.addInitScript(() => {
      window.localStorage.setItem('auth_token', 'mock_e2e_token');
    });
  });

  test('should complete a full LangGraph chat cycle', async ({ page }) => {
    await page.goto('/workspace');

    // 1. Verify UI loaded
    await expect(page.getByPlaceholder('Message DocsMind...')).toBeVisible();

    // 2. Submit query
    await page.getByPlaceholder('Message DocsMind...').fill('What are the SLA terms?');
    await page.getByRole('button', { name: /send/i }).click();

    // 3. Verify Agent Timeline appears (LangGraph orchestration)
    const timeline = page.locator('text=Execution Graph');
    await expect(timeline).toBeVisible({ timeout: 5000 });

    // 4. Verify specific nodes execute
    await expect(page.locator('text=planner')).toBeVisible();
    await expect(page.locator('text=retriever')).toBeVisible();

    // 5. Verify final streaming output
    const responseBubble = page.locator('.message-bubble.assistant').last();
    await expect(responseBubble).toContainText('SLA', { timeout: 15000 });

    // 6. Verify Citations rendered
    const citation = page.locator('button.citation-badge').first();
    await expect(citation).toBeVisible();
    
    // 7. Click citation to open preview
    await citation.click();
    await expect(page.locator('.document-preview-panel')).toBeVisible();
  });
});
