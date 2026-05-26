# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: breadcrumb-navigation.spec.js >> 面包屑导航返回时搜索状态保持测试
- Location: tests/breadcrumb-navigation.spec.js:3:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: true
Received: false
```

# Page snapshot

```yaml
- generic [ref=e2]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: 
      - generic [ref=e7]: CMDB
    - navigation [ref=e8]:
      - link "资源" [ref=e9] [cursor=pointer]:
        - /url: "#/resource"
  - generic [ref=e10]:
    - generic [ref=e11]:
      - generic [ref=e12] [cursor=pointer]: 
      - generic [ref=e13]:
        - generic [ref=e14] [cursor=pointer]: 资源
        - generic [ref=e15]: /
        - generic [ref=e16]: 交换机
    - generic [ref=e17]:
      - generic [ref=e18]:
        - generic [ref=e19]:
          - button "新建" [ref=e20] [cursor=pointer]:
            - generic [ref=e21]: 新建
          - button "导入" [ref=e22] [cursor=pointer]:
            - generic [ref=e23]: 导入
          - button "导出" [ref=e24] [cursor=pointer]:
            - generic [ref=e25]: 导出
          - button "批量更新" [ref=e26] [cursor=pointer]:
            - generic [ref=e27]: 批量更新
          - button "删除" [ref=e28] [cursor=pointer]:
            - generic [ref=e29]: 删除
        - generic [ref=e30]:
          - button "刷新" [ref=e31] [cursor=pointer]:
            - generic [ref=e32]: 刷新
          - generic [ref=e34] [cursor=pointer]: 
        - generic [ref=e35]:
          - generic [ref=e37] [cursor=pointer]:
            - generic: 
            - generic "交换机名称" [ref=e40]
          - generic [ref=e42]:
            - textbox "请输入交换机名称" [ref=e43]: 服务器
            - button "" [ref=e44] [cursor=pointer]:
              - generic [ref=e47]: 
          - generic [ref=e51] [cursor=pointer]: 模糊
      - generic [ref=e52]:
        - table [ref=e54]:
          - rowgroup [ref=e65]:
            - row "实例ID 交换机名称 管理IP 型号 厂商 VLAN 所属业务" [ref=e66]:
              - columnheader [ref=e67]
              - columnheader "实例ID" [ref=e68] [cursor=pointer]:
                - generic [ref=e70]: 实例ID
              - columnheader "交换机名称" [ref=e74] [cursor=pointer]:
                - generic [ref=e76]: 交换机名称
              - columnheader "管理IP" [ref=e80] [cursor=pointer]:
                - generic [ref=e82]: 管理IP
              - columnheader "型号" [ref=e86] [cursor=pointer]:
                - generic [ref=e88]: 型号
              - columnheader "厂商" [ref=e92] [cursor=pointer]:
                - generic [ref=e94]: 厂商
              - columnheader "VLAN" [ref=e98] [cursor=pointer]:
                - generic [ref=e100]: VLAN
              - columnheader "所属业务" [ref=e104] [cursor=pointer]:
                - generic [ref=e106]: 所属业务
              - columnheader [ref=e110]
        - generic [ref=e111]:
          - table:
            - rowgroup
          - generic [ref=e114]:
            - img "empty" [ref=e116]
            - generic [ref=e118]: 暂无数据
        - generic [ref=e119]:
          - table [ref=e121]:
            - rowgroup [ref=e132]:
              - row [ref=e133]:
                - columnheader [ref=e134]
                - columnheader [ref=e139] [cursor=pointer]
                - columnheader [ref=e140] [cursor=pointer]
                - columnheader [ref=e141] [cursor=pointer]
                - columnheader [ref=e142] [cursor=pointer]
                - columnheader [ref=e143] [cursor=pointer]
                - columnheader [ref=e144] [cursor=pointer]
                - columnheader [ref=e145] [cursor=pointer]
                - columnheader [ref=e146]
          - generic:
            - table:
              - rowgroup
        - generic [ref=e147]:
          - table [ref=e149]:
            - rowgroup [ref=e160]:
              - row "操作" [ref=e161]:
                - columnheader [ref=e162]
                - columnheader [ref=e163] [cursor=pointer]
                - columnheader [ref=e164] [cursor=pointer]
                - columnheader [ref=e165] [cursor=pointer]
                - columnheader [ref=e166] [cursor=pointer]
                - columnheader [ref=e167] [cursor=pointer]
                - columnheader [ref=e168] [cursor=pointer]
                - columnheader [ref=e169] [cursor=pointer]
                - columnheader "操作" [ref=e170]:
                  - generic [ref=e172]: 操作
          - generic:
            - table:
              - rowgroup
```

# Test source

```ts
  1   | const { test, expect } = require('@playwright/test');
  2   | 
  3   | test('面包屑导航返回时搜索状态保持测试', async ({ page }) => {
  4   |   const consoleLogs = [];
  5   | 
  6   |   page.on('console', msg => {
  7   |     consoleLogs.push({ type: msg.type(), text: msg.text() });
  8   |   });
  9   | 
  10  |   console.log('\n========== 面包屑导航返回测试 ==========\n');
  11  | 
  12  |   // 1. 访问交换机列表
  13  |   console.log('1. 访问交换机列表页面');
  14  |   await page.goto('http://localhost:3000/#/instance/bk_switch');
  15  |   await page.waitForTimeout(3000);
  16  | 
  17  |   // 2. 选择搜索字段
  18  |   console.log('2. 选择搜索字段');
  19  |   const fieldSelector = page.locator('.filter-selector .bk-select');
  20  |   await fieldSelector.click();
  21  |   await page.waitForTimeout(500);
  22  |   const options = page.locator('.bk-options .bk-option');
  23  |   await options.first().click();
  24  |   await page.waitForTimeout(500);
  25  | 
  26  |   // 3. 输入中文关键词并搜索
  27  |   const chineseKeyword = '服务器';
  28  |   console.log(`3. 输入中文关键词: "${chineseKeyword}" 并搜索`);
  29  |   const searchInput = page.locator('.filter-value input');
  30  |   await searchInput.fill(chineseKeyword);
  31  |   await page.waitForTimeout(300);
  32  | 
  33  |   const searchButton = page.locator('.search-btn');
  34  |   await searchButton.click();
  35  |   await page.waitForTimeout(3000);
  36  | 
  37  |   const urlAfterSearch = page.url();
  38  |   console.log(`   搜索后URL: ${urlAfterSearch}`);
  39  | 
  40  |   // 4. 进入详情页
  41  |   console.log('4. 进入详情页');
  42  |   const viewButton = page.locator('.bk-table .bk-button').filter({ hasText: '查看' }).first();
  43  |   const hasViewButton = await viewButton.count() > 0;
  44  | 
  45  |   if (hasViewButton) {
  46  |     await viewButton.click();
  47  |     await page.waitForTimeout(3000);
  48  | 
  49  |     const urlInDetails = page.url();
  50  |     console.log(`   详情页URL: ${urlInDetails}`);
  51  | 
  52  |     // 5. 点击面包屑中的模型名称返回列表
  53  |     console.log('5. 点击面包屑中的模型名称返回列表');
  54  |     const modelNameLink = page.locator('.breadcrumb-item').filter({ hasText: '交换机' });
  55  |     const hasModelLink = await modelNameLink.count() > 0;
  56  | 
  57  |     if (hasModelLink) {
  58  |       await modelNameLink.click();
  59  |       await page.waitForTimeout(3000);
  60  | 
  61  |       const urlAfterReturn = page.url();
  62  |       console.log(`   返回后URL: ${urlAfterReturn}`);
  63  | 
  64  |       // 6. 检查搜索状态是否恢复
  65  |       console.log('6. 检查搜索状态是否恢复');
  66  | 
  67  |       const searchInputAfter = page.locator('.filter-value input');
  68  |       const restoredValue = await searchInputAfter.inputValue();
  69  |       console.log(`   返回后输入框值: "${restoredValue}"`);
  70  | 
  71  |       const stateRestored = restoredValue === chineseKeyword;
  72  |       console.log(`   状态恢复: ${stateRestored ? '✅ 成功' : '❌ 失败'}`);
  73  | 
  74  |       // 总结
  75  |       console.log('\n========== 测试总结 ==========\n');
  76  |       console.log('进入详情页:', '✅ 成功');
  77  |       console.log('面包屑返回:', '✅ 成功');
  78  |       console.log('状态恢复:', stateRestored ? '✅ 成功' : '❌ 失败');
  79  | 
  80  |       expect(stateRestored).toBe(true);
  81  |     } else {
  82  |       console.log('⚠️ 未找到面包屑中的模型名称链接');
  83  |       expect(false).toBe(true);
  84  |     }
  85  |   } else {
  86  |     console.log('⚠️ 未找到查看按钮（可能没有数据）');
> 87  |     expect(false).toBe(true);
      |                   ^ Error: expect(received).toBe(expected) // Object.is equality
  88  |   }
  89  | });
  90  | 
  91  | test('面包屑返回按钮测试', async ({ page }) => {
  92  |   console.log('\n========== 面包屑返回按钮测试 ==========\n');
  93  | 
  94  |   // 1. 访问交换机列表
  95  |   console.log('1. 访问交换机列表');
  96  |   await page.goto('http://localhost:3000/#/instance/bk_switch');
  97  |   await page.waitForTimeout(3000);
  98  | 
  99  |   // 2. 搜索
  100 |   const fieldSelector = page.locator('.filter-selector .bk-select');
  101 |   await fieldSelector.click();
  102 |   await page.waitForTimeout(500);
  103 |   const options = page.locator('.bk-options .bk-option');
  104 |   await options.first().click();
  105 |   await page.waitForTimeout(500);
  106 | 
  107 |   const searchInput = page.locator('.filter-value input');
  108 |   await searchInput.fill('测试');
  109 |   await page.waitForTimeout(300);
  110 | 
  111 |   const searchButton = page.locator('.search-btn');
  112 |   await searchButton.click();
  113 |   await page.waitForTimeout(3000);
  114 | 
  115 |   console.log('2. 搜索完成，URL:', page.url());
  116 | 
  117 |   // 3. 进入详情页
  118 |   console.log('3. 进入详情页');
  119 |   const viewButton = page.locator('.bk-table .bk-button').filter({ hasText: '查看' }).first();
  120 |   await viewButton.click();
  121 |   await page.waitForTimeout(3000);
  122 |   console.log('   详情页URL:', page.url());
  123 | 
  124 |   // 4. 点击返回按钮
  125 |   console.log('4. 点击面包屑返回按钮');
  126 |   const backButton = page.locator('.page-breadcrumbs .icon');
  127 |   await backButton.click();
  128 |   await page.waitForTimeout(3000);
  129 | 
  130 |   console.log('   返回后URL:', page.url());
  131 | 
  132 |   // 5. 检查状态
  133 |   const restoredValue = await searchInput.inputValue();
  134 |   console.log('   输入框值:', restoredValue);
  135 | 
  136 |   const stateRestored = restoredValue === '测试';
  137 |   console.log('   状态恢复:', stateRestored ? '✅ 成功' : '❌ 失败');
  138 | 
  139 |   expect(stateRestored).toBe(true);
  140 | });
  141 | 
```