const { test, expect } = require('@playwright/test');

test('Health Check and CORS Test', async ({ page }) => {
  // Enable console logging
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[ERROR] ${msg.text()}`);
    }
  });
  
  // Listen for dialog (alert) events
  let dialogMessage = '';
  page.on('dialog', async dialog => {
    dialogMessage = dialog.message();
    console.log(`[ALERT] ${dialog.message()}`);
    await dialog.accept();
  });

  console.log('Step 1: Testing direct backend health endpoint...');
  const backendHealth = await page.evaluate(async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      return {
        status: response.status,
        data: await response.json()
      };
    } catch (error) {
      return { error: error.message };
    }
  });
  
  console.log('Backend Health Response:', JSON.stringify(backendHealth, null, 2));
  expect(backendHealth.status).toBe(200);
  expect(backendHealth.data.status).toBe('healthy');
  expect(backendHealth.data.cors.allow_origins).toEqual(['*']);

  console.log('\nStep 2: Navigating to frontend homepage...');
  await page.goto('http://localhost:3000/');
  
  // Wait for the alert dialog to appear
  await page.waitForTimeout(2000);
  
  console.log('\nStep 3: Checking alert dialog...');
  console.log('Alert Message:', dialogMessage);
  expect(dialogMessage).toContain('后端服务健康检查结果');
  expect(dialogMessage).toContain('healthy');
  expect(dialogMessage).toContain('CMDB Server Lite');
  
  console.log('\n✓ Health check and CORS test passed!');
});