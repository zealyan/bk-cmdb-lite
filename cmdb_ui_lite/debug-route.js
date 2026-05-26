const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('=== SLB实例详情页关联Tab功能测试 ===\n');

  console.log('1. 访问首页');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  console.log('\n2. 当前URL:', page.url());

  console.log('\n3. 点击资源管理');
  await page.click('text=资源');
  await page.waitForTimeout(2000);
  console.log('URL after click:', page.url());

  console.log('\n4. 点击负载均衡');
  await page.click('text=负载均衡');
  await page.waitForTimeout(2000);
  console.log('URL after click:', page.url());

  console.log('\n5. 查找ID列中的第一个链接并点击');
  // 点击ID列中的链接 (第一个SLB实例)
  const idLinks = page.locator('text=1');
  const linkCount = await idLinks.count();
  console.log('找到"1"的元素数量:', linkCount);

  if (linkCount > 0) {
    await idLinks.first().click();
    await page.waitForTimeout(2000);
    console.log('URL after ID click:', page.url());
  }

  console.log('\n6. 检查Tab');
  const tabs = await page.locator('[role="tab"], .bk-tab-label-item').all();
  console.log('Tab数量:', tabs.length);

  for (let i = 0; i < tabs.length; i++) {
    const text = await tabs[i].textContent();
    console.log(`Tab ${i}: ${text.trim()}`);
  }

  console.log('\n7. 查找"关联"Tab');
  const associationTab = page.locator('[role="tab"], .bk-tab-label-item').filter({ hasText: '关联' });
  const count = await associationTab.count();
  console.log('关联Tab数量:', count);

  if (count > 0) {
    console.log('\n8. 点击关联Tab');
    await associationTab.first().click();
    await page.waitForTimeout(2000);

    const bodyText = await page.textContent('body');
    console.log('包含"SLB后端服务器":', bodyText.includes('SLB后端服务器'));
    console.log('包含"SLB监听器":', bodyText.includes('SLB监听器'));
    console.log('包含"暂无关联关系":', bodyText.includes('暂无关联关系'));

    // 检查关联组
    const groups = await page.locator('.association-group').all();
    console.log('\n关联组数量:', groups.length);

    for (let i = 0; i < groups.length; i++) {
      const groupText = await groups[i].textContent();
      console.log(`\n关联组 ${i + 1}:`);
      console.log(groupText.substring(0, 200));
    }
  } else {
    console.log('\n❌ 未找到关联Tab，尝试其他方式定位...');

    // 尝试查找任何包含"关联"的元素
    const assocElements = await page.locator('text=关联').all();
    console.log('包含"关联"的所有元素:', assocElements.length);

    // 检查当前页面的主要内容
    const mainContent = await page.evaluate(() => {
      const body = document.body;
      return {
        text: body.innerText.substring(0, 1000),
        hasModelDetails: body.innerHTML.includes('model-details-page'),
        hasAssociation: body.innerHTML.includes('instance-association')
      };
    });

    console.log('\n页面内容分析:');
    console.log(JSON.stringify(mainContent, null, 2));
  }

  await browser.close();
})();
