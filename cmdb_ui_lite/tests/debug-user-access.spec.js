const { test, expect } = require('@playwright/test');

test('Debug User Access Scenario', async ({ page }) => {
  // Enable console logging
  page.on('console', msg => console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`));
  
  // Enable request/response logging
  page.on('request', req => console.log(`[REQUEST] ${req.method()} ${req.url()}`));
  page.on('response', res => console.log(`[RESPONSE] ${res.status()} ${res.url()}`));
  
  // Enable page error logging
  page.on('pageerror', err => console.error(`[PAGE ERROR] ${err}`));

  console.log('Navigating to http://localhost:3000/#/instance/bk_switch');
  
  // Navigate to the page
  await page.goto('http://localhost:3000/#/instance/bk_switch');
  
  console.log('Page loaded, waiting 5 seconds for data to load...');
  
  // Wait for data to load
  await page.waitForTimeout(5000);
  
  // Take screenshot
  await page.screenshot({ path: 'debug-user-access.png', fullPage: true });
  console.log('Screenshot saved as debug-user-access.png');
  
  // Check if table is visible
  const tableVisible = await page.locator('.models-table').isVisible();
  console.log('Table visible:', tableVisible);
  
  // Check for any error messages
  const errorMessage = await page.locator('.bk-message-error, .error, [class*="error"]').first().textContent({ timeout: 2000 }).catch(() => 'No error message found');
  console.log('Error message:', errorMessage);
  
  // Check page content
  const pageContent = await page.content();
  console.log('Page contains "core-switch-01":', pageContent.includes('core-switch-01'));
  
  console.log('Test completed!');
});