# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chat.spec.js >> Kompass Math Agent E2E Tests >> should accept user input and get a response from the agent calling the MCP tool
- Location: tests/chat.spec.js:15:3

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: locator('[data-testid="message-agent"]').nth(1)
Expected substring: "42"
Received string:    "The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a few seconds."
Timeout: 15000ms

Call log:
  - Expect "toContainText" with timeout 15000ms
  - waiting for locator('[data-testid="message-agent"]').nth(1)
    25 × locator resolved to <div data-testid="message-agent" class="flex gap-3 max-w-[80%] self-start">…</div>
       - unexpected value "The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a few seconds."

```

```yaml
- text: The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a few seconds.
```

# Test source

```ts
  1  | const { test, expect } = require('@playwright/test');
  2  | 
  3  | test.describe('Kompass Math Agent E2E Tests', () => {
  4  |   test('should load the chat page and display the welcome message', async ({ page }) => {
  5  |     await page.goto('/');
  6  |     
  7  |     // Check header title exists
  8  |     await expect(page.locator('header')).toContainText('Kompass.ai');
  9  |     
  10 |     // Check initial agent message is visible
  11 |     const firstAgentMessage = page.locator('[data-testid="message-agent"]').first();
  12 |     await expect(firstAgentMessage).toContainText('Hello! I am the Kompass Math Agent');
  13 |   });
  14 | 
  15 |   test('should accept user input and get a response from the agent calling the MCP tool', async ({ page }) => {
  16 |     await page.goto('/');
  17 | 
  18 |     const input = page.locator('#message-input');
  19 |     const sendButton = page.locator('#send-button');
  20 | 
  21 |     // Type addition query
  22 |     await input.fill('What is 15 + 27?');
  23 |     await sendButton.click();
  24 | 
  25 |     // Verify user message appears in list
  26 |     const userMessage = page.locator('[data-testid="message-user"]').first();
  27 |     await expect(userMessage).toContainText('What is 15 + 27?');
  28 | 
  29 |     // Wait for the agent's response. The agent will run, call calculate_sum, and respond.
  30 |     // The response should contain the correct result "42".
  31 |     const lastAgentMessage = page.locator('[data-testid="message-agent"]').nth(1);
> 32 |     await expect(lastAgentMessage).toContainText('42', { timeout: 15000 });
     |                                    ^ Error: expect(locator).toContainText(expected) failed
  33 |   });
  34 | });
  35 | 
```