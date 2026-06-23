const { test, expect } = require('@playwright/test');

test.describe('Kompass Math Agent E2E Tests', () => {
  test('should load the chat page and display the welcome message', async ({ page }) => {
    await page.goto('/');
    
    // Check header title exists
    await expect(page.locator('header')).toContainText('Kompass');
    
    // Check initial agent message is visible
    const firstAgentMessage = page.locator('[data-testid="message-agent"]').first();
    await expect(firstAgentMessage).toContainText('Hello! I am the Kompass Math Agent');
  });

  test('should accept user input and get a response from the agent calling the MCP tool', async ({ page }) => {
    await page.goto('/');

    const input = page.locator('#message-input');
    const sendButton = page.locator('#send-button');

    // Type addition query
    await input.fill('What is 15 + 27?');
    await sendButton.click();

    // Verify user message appears in list
    const userMessage = page.locator('[data-testid="message-user"]').first();
    await expect(userMessage).toContainText('What is 15 + 27?');

    // Wait for the agent's response. The agent will run, call calculate_sum, and respond.
    // The response should contain the correct result "42".
    const lastAgentMessage = page.locator('[data-testid="message-agent"]').nth(1);
    await expect(lastAgentMessage).toContainText('42', { timeout: 15000 });
  });
});
