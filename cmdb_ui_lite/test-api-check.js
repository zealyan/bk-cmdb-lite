const { chromium } = require('playwright');

async function testAPIAndBrowser() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const errors = [];
  const apiCalls = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  
  page.on('request', request => {
    const url = request.url();
    if (url.includes('/api/') || url.includes('localhost:8000')) {
      apiCalls.push({
        url: url,
        method: request.method(),
        resourceType: request.resourceType()
      });
    }
  });
  
  page.on('response', response => {
    const url = response.url();
    if (url.includes('/api/') || url.includes('localhost:8000')) {
      console.log(`✅ ${response.status()} - ${url}`);
    }
  });
  
  page.on('pageerror', err => {
    errors.push(`Page Error: ${err.message}`);
  });
  
  try {
    console.log('='.repeat(60));
    console.log('测试1: 访问前端页面');
    console.log('='.repeat(60));
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0', timeout: 10000 });
    console.log('✅ 页面加载成功');
    
    await page.waitForTimeout(2000);
    
    console.log('\n' + '='.repeat(60));
    console.log('测试2: 检查页面标题');
    console.log('='.repeat(60));
    const title = await page.title();
    console.log(`页面标题: ${title}`);
    
    console.log('\n' + '='.repeat(60));
    console.log('测试3: 检查Vue应用挂载');
    console.log('='.repeat(60));
    const appContent = await page.$eval('#app', el => el.innerHTML.substring(0, 200));
    console.log(`App内容: ${appContent.substring(0, 100)}...`);
    
    console.log('\n' + '='.repeat(60));
    console.log('测试4: 检查API调用');
    console.log('='.repeat(60));
    if (apiCalls.length > 0) {
      console.log(`发现 ${apiCalls.length} 个API请求`);
      apiCalls.forEach(call => {
        console.log(`  - ${call.method} ${call.url}`);
      });
    } else {
      console.log('⚠️ 未发现任何API请求');
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('测试5: 检查JavaScript错误');
    console.log('='.repeat(60));
    if (errors.length > 0) {
      console.log(`发现 ${errors.length} 个JavaScript错误:`);
      errors.forEach(err => {
        console.log(`  ❌ ${err}`);
      });
    } else {
      console.log('✅ 没有JavaScript错误');
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('测试6: 检查模型列表数据');
    console.log('='.repeat(60));
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });
    await page.waitForTimeout(3000);
    
    const hasContent = await page.evaluate(() => {
      const body = document.body.innerText;
      return body.includes('交换机') || body.includes('负载均衡') || body.includes('bk_switch') || body.includes('bk_slb');
    });
    
    console.log(`页面包含模型数据: ${hasContent ? '✅ 是' : '❌ 否'}`);
    
  } catch (error) {
    console.error('测试失败:', error.message);
  } finally {
    await browser.close();
  }
}

testAPIAndBrowser().catch(console.error);
