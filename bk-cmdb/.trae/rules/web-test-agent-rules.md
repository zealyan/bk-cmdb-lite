# Web 测试智能体规则

## 概述

本规则为智能体提供 Web 测试的标准执行路径和方法，使用项目本地的 Playwright 进行浏览器自动化测试。

---

## 一、测试环境要求

### 1.1 服务依赖

| 服务 | 地址 | 用途 | 启动命令 |
|------|------|------|----------|
| 后端 API | http://localhost:8000 | 提供数据接口 | `cd cmdb_server_lite && python3 main.py` |
| 前端预览 | http://localhost:3000 | Web 页面访问 | `cd cmdb_ui_lite && npx serve -s dist -l 3000` |

### 1.2 工具依赖

| 工具 | 路径 | 版本 |
|------|------|------|
| Playwright | `./node_modules/.bin/playwright` | 1.40+ |
| Firefox | `~/.cache/ms-playwright/firefox-*/firefox/firefox` | 148.0.2 |
| 测试配置 | `playwright.config.js` | - |

---

## 二、智能体执行路径

### 2.1 标准 Web 测试流程

```
1. 确认服务状态
   ↓
2. 检查/安装浏览器依赖
   ↓
3. 编写测试脚本
   ↓
4. 执行测试
   ↓
5. 分析测试结果
   ↓
6. 报告问题或确认通过
```

### 2.2 执行前检查

```bash
# 1. 检查服务状态
curl -s http://localhost:8000/health
curl -s http://localhost:3000/ -o /dev/null -w "%{http_code}"

# 2. 检查 Playwright
cd /workspace/bk-cmdb/cmdb_ui_lite
./node_modules/.bin/playwright --version

# 3. 检查浏览器
ls ~/.cache/ms-playwright/
```

---

## 三、测试脚本编写规范

### 3.1 测试文件位置

```
cmdb_ui_lite/
└── tests/
    ├── demo.spec.js           # 基础测试
    ├── instance-list.spec.js  # 实例列表测试
    └── {feature}.spec.js     # 功能测试
```

### 3.2 标准测试模板

```javascript
const { test, expect } = require('@playwright/test');

test('功能描述', async ({ page }) => {
  // 1. 收集控制台消息
  const consoleMessages = [];
  const consoleErrors = [];
  
  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
    if (msg.type() === 'error') {
      consoleErrors.push(text);
    }
  });
  
  // 2. 执行测试步骤
  console.log('步骤描述...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  
  // 3. 等待必要元素
  await page.waitForTimeout(2000);
  
  // 4. 验证结果
  const title = await page.title();
  expect(title).toBe('CMDB UI Lite');
  
  // 5. 检查控制台错误
  if (consoleErrors.length > 0) {
    console.log('控制台错误:', consoleErrors);
    throw new Error('存在控制台错误');
  }
  
  // 6. 截图保存
  await page.screenshot({ path: 'test-result.png', fullPage: true });
  
  console.log('测试通过');
});
```

### 3.3 常见测试场景

#### 场景 1: 首页加载测试

```javascript
test('首页加载测试', async ({ page }) => {
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  const title = await page.title();
  expect(title).toBe('CMDB UI Lite');
  
  // 验证资源卡片显示
  const cards = page.locator('.resource-card');
  await expect(cards.first()).toBeVisible();
});
```

#### 场景 2: 实例列表数据加载测试

```javascript
test('实例列表数据加载测试', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // 点击交换机卡片
  await page.locator('.resource-card').first().click();
  await page.waitForLoadState('networkidle');
  
  // 验证 Debug 日志
  const debugLogs = [];
  page.on('console', msg => {
    if (msg.text().includes('[DEBUG]')) {
      debugLogs.push(msg.text());
    }
  });
  
  await page.waitForTimeout(3000);
  
  // 验证数据加载
  expect(debugLogs.some(log => log.includes('数据加载完成'))).toBe(true);
});
```

#### 场景 3: 搜索功能测试

```javascript
test('搜索功能测试', async ({ page }) => {
  await page.goto('http://localhost:3000/#/instance/bk_switch');
  await page.waitForLoadState('networkidle');
  
  // 输入搜索关键词
  const searchInput = page.locator('.bk-input input');
  await searchInput.fill('core');
  await searchInput.press('Enter');
  
  await page.waitForTimeout(2000);
  
  // 验证搜索结果
  const rows = page.locator('.bk-table tbody tr');
  const count = await rows.count();
  expect(count).toBeGreaterThan(0);
});
```

#### 场景 4: 详情页测试

```javascript
test('详情页测试', async ({ page }) => {
  await page.goto('http://localhost:3000/#/instance/bk_switch/1');
  await page.waitForLoadState('networkidle');
  
  // 验证基本信息标签页
  const basicTab = page.locator('text=基本信息');
  await expect(basicTab).toBeVisible();
  
  // 验证关联标签页
  const associationTab = page.locator('text=关联');
  await expect(associationTab).toBeVisible();
});
```

---

## 四、执行命令参考

### 4.1 本地 Playwright 命令

```bash
cd /workspace/bk-cmdb/cmdb_ui_lite

# 运行所有测试
./node_modules/.bin/playwright test

# 运行指定测试文件
./node_modules/.bin/playwright test tests/demo.spec.js

# UI 模式运行（可视化）
./node_modules/.bin/playwright test --ui

# 调试模式
./node_modules/.bin/playwright test --debug

# 显示报告
./node_modules/.bin/playwright show-report

# 仅收集测试（不执行）
./node_modules/.bin/playwright test --dry-run
```

### 4.2 服务管理命令

```bash
# 启动后端服务
cd /workspace/bk-cmdb/cmdb_server_lite
python3 main.py

# 启动前端预览
cd /workspace/bk-cmdb/cmdb_ui_lite
npx serve -s dist -l 3000

# 检查服务状态
curl -s http://localhost:8000/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
```

---

## 五、测试配置

### 5.1 Playwright 配置 (playwright.config.js)

```javascript
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30000,
  expect: {
    timeout: 5000
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
});
```

### 5.2 环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `PLAYWRIGHT_BROWSERS_PATH` | `~/.cache/ms-playwright` | 浏览器缓存路径 |

---

## 六、测试结果分析

### 6.1 通过标准

- 无控制台 Error 级别消息
- 页面元素正常显示
- 数据正确加载
- 功能交互正常

### 6.2 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 浏览器无法启动 | 缺少依赖库 | `apt-get install libgtk-3-0 libxcursor1` |
| 页面加载超时 | 服务未启动 | 启动后端/前端服务 |
| 数据未加载 | API 请求失败 | 检查后端服务和控制台错误 |
| 元素未找到 | 选择器错误 | 检查页面 HTML 结构 |

### 6.3 Debug 日志说明

前端代码中的 Debug 日志格式：

```
[DEBUG] {消息内容}
```

常见日志：
- `[DEBUG mounted]` - 组件挂载
- `[DEBUG] 开始加载数据` - 开始请求数据
- `[DEBUG] 属性返回` - 属性 API 返回
- `[DEBUG] 实例返回` - 实例 API 返回
- `[DEBUG] 数据加载完成` - 数据加载完成

---

## 七、智能体任务模板

### 7.1 Web 测试任务

当用户要求执行 Web 测试时，按以下步骤执行：

```
1. 确认服务状态
   - 检查后端: curl http://localhost:8000/health
   - 检查前端: curl http://localhost:3000

2. 如服务未启动，启动服务
   - 后端: cd cmdb_server_lite && python3 main.py &
   - 前端: cd cmdb_ui_lite && npx serve -s dist -l 3000 &

3. 编写测试脚本
   - 在 tests/ 目录下创建测试文件
   - 使用标准测试模板

4. 执行测试
   - ./node_modules/.bin/playwright test {测试文件}

5. 分析结果
   - 检查控制台输出
   - 检查截图

6. 报告结果
   - 列出通过的测试
   - 列出失败的测试
   - 提供错误详情和修复建议
```

### 7.2 快速验证任务

对于简单的功能验证，可以使用快速测试：

```bash
cd /workspace/bk-cmdb/cmdb_ui_lite

# 快速检查 API
curl -s http://localhost:8000/api/models | head -c 200

# 快速检查页面
curl -s http://localhost:3000/ | head -c 500
```

---

## 八、注意事项

1. **始终使用本地 Playwright** - 不要使用 npx，直接使用 `./node_modules/.bin/playwright`
2. **确保服务运行** - 测试前必须确认后端和前端服务正常运行
3. **等待页面加载** - 使用 `waitForLoadState('networkidle')` 等待网络请求完成
4. **捕获控制台错误** - 监听控制台消息，报告所有 Error 级别消息
5. **截图保存** - 重要测试步骤后保存截图便于分析
