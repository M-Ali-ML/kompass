const { test, expect } = require('@playwright/test');

test.describe('Kompass Math Agent E2E Tests', () => {
  test('should load the chat page and verify empty state', async ({ page }) => {
    await page.goto('/');
    
    // Check header title exists
    await expect(page.locator('header')).toContainText('Kompass');
    
    // Check that there are no assistant messages loaded initially
    const assistantMessages = page.locator('.copilotKitAssistantMessage');
    await expect(assistantMessages).toHaveCount(0);
  });

  test('should accept user input and get a response from the agent calling the MCP tool', async ({ page }) => {
    await page.goto('/');

    const input = page.locator('.copilotKitInput textarea');
    const sendButton = page.locator('button[aria-label="Send"]');

    // Type addition query
    await input.fill('What is 15 + 27?');
    await sendButton.click();

    // Verify user message appears in list
    const userMessage = page.locator('.copilotKitUserMessage').first();
    await expect(userMessage).toContainText('What is 15 + 27?');

    // Wait for the agent's response. The agent will run, call calculate_sum, and respond.
    // The response should contain the correct result "42".
    const lastAgentMessage = page.locator('.copilotKitAssistantMessage').last();
    await expect(lastAgentMessage).toContainText('42', { timeout: 15000 });
  });
});
