const { test, expect } = require('@playwright/test');

test('中文搜索URL状态保持测试', async ({ page }) => {
  const consoleLogs = [];

  page.on('console', msg => {
    const text = msg.text();
    consoleLogs.push({ type: msg.type(), text });
  });

  console.log('\n========== 中文搜索URL状态保持测试 ==========\n');

  // 1. 访问交换机列表
  console.log('1. 访问交换机列表页面');
  await page.goto('http://localhost:3000/#/instance/bk_switch');
  await page.waitForTimeout(3000);

  // 2. 选择搜索字段
  console.log('2. 选择搜索字段');
  const fieldSelector = page.locator('.filter-selector .bk-select');
  await fieldSelector.click();
  await page.waitForTimeout(500);
  const options = page.locator('.bk-options .bk-option');
  await options.first().click();
  await page.waitForTimeout(500);

  // 3. 输入中文关键词
  const chineseKeyword = '服务器';
  console.log(`3. 输入中文关键词: "${chineseKeyword}"`);
  const searchInput = page.locator('.filter-value input');
  await searchInput.fill(chineseKeyword);
  await page.waitForTimeout(300);

  // 4. 点击搜索
  console.log('4. 点击搜索按钮');
  const searchButton = page.locator('.search-btn');
  await searchButton.click();
  await page.waitForTimeout(3000);

  // 5. 获取URL
  const urlAfterSearch = page.url();
  console.log(`5. 搜索后URL: ${urlAfterSearch}`);

  // 验证URL包含中文编码
  const urlObj = new URL(urlAfterSearch);
  const hashParams = urlObj.hash.split('?')[1] || '';
  console.log(`   Hash参数: ${hashParams}`);

  // 6. 刷新页面
  console.log('6. 刷新页面...');
  await page.reload({ waitUntil: 'networkidle' });

  // 等待Vue组件完全渲染
  console.log('7. 等待Vue组件渲染...');
  await page.waitForTimeout(5000);

  // 8. 打印所有console日志
  console.log('\n   Console日志:');
  consoleLogs.forEach(log => {
    console.log(`   [${log.type}] ${log.text}`);
  });

  // 9. 尝试多种方式获取输入框的值
  console.log('\n8. 检查状态恢复:');

  // 方式1: 使用inputValue
  const inputValue1 = await searchInput.inputValue();
  console.log(`   inputValue(): "${inputValue1}"`);

  // 方式2: 使用evaluate获取value属性
  const inputValue2 = await searchInput.evaluate(el => el.value);
  console.log(`   evaluate(value): "${inputValue2}"`);

  // 方式3: 获取输入框的textContent
  const textContent = await searchInput.textContent();
  console.log(`   textContent: "${textContent}"`);

  // 方式4: 检查Vue组件实例的数据
  const vueData = await page.evaluate(() => {
    const app = document.querySelector('#app');
    if (app && app.__vue__) {
      return {
        hasVue: true,
        // 尝试获取Vue组件实例
      };
    }
    return { hasVue: false };
  });
  console.log(`   Vue实例: ${vueData.hasVue ? '存在' : '不存在'}`);

  // 等待input可见
  await searchInput.waitFor({ state: 'visible', timeout: 5000 });
  const isVisible = await searchInput.isVisible();
  console.log(`   输入框可见: ${isVisible ? '是' : '否'}`);

  // 最终检查
  const restoredValue = inputValue1 || inputValue2;
  const stateRestored = restoredValue === chineseKeyword;
  console.log(`\n   最终恢复值: "${restoredValue}"`);
  console.log(`   期望值: "${chineseKeyword}"`);
  console.log(`   状态恢复: ${stateRestored ? '✅ 成功' : '❌ 失败'}`);

  // 总结
  console.log('\n========== 测试总结 ==========\n');
  console.log('URL保存中文:', urlAfterSearch.includes('%') ? '✅ 正常' : '⚠️ 可能有问题');
  console.log('状态恢复:', stateRestored ? '✅ 成功' : '❌ 失败');
});
