const { test, expect } = require('@playwright/test');

test('测量分页组件与窗口底部的距离', async ({ page }) => {
  // 设置视口为 1440x900
  await page.setViewportSize({ width: 1440, height: 900 });

  // 访问 SLB 监听器页面
  await page.goto('http://localhost:8080/resource/bk_slb_listener', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // 测量页面元素
  const measurements = await page.evaluate(() => {
    const result = {};
    result.windowInnerHeight = window.innerHeight;
    result.windowInnerWidth = window.innerWidth;

    const viewsLayout = document.querySelector('.views-layout');
    const app = document.getElementById('app');
    const breadcrumbs = document.querySelector('.page-breadcrumbs');
    const options = document.querySelector('.models-options');
    const table = document.querySelector('.models-table');
    const pagination = document.querySelector('.bk-table-pagination-wrapper');
    const tableBody = document.querySelector('.bk-table-body-wrapper');
    const tableHeader = document.querySelector('.bk-table-header-wrapper');

    if (app) {
      const r = app.getBoundingClientRect();
      result.appTop = Math.round(r.top);
      result.appHeight = Math.round(r.height);
    }
    if (viewsLayout) {
      const r = viewsLayout.getBoundingClientRect();
      result.viewsLayoutTop = Math.round(r.top);
      result.viewsLayoutHeight = Math.round(r.height);
    }
    if (breadcrumbs) {
      const r = breadcrumbs.getBoundingClientRect();
      result.breadcrumbsTop = Math.round(r.top);
      result.breadcrumbsHeight = Math.round(r.height);
    }
    if (options) {
      const r = options.getBoundingClientRect();
      result.optionsTop = Math.round(r.top);
      result.optionsHeight = Math.round(r.height);
    }
    if (table) {
      const r = table.getBoundingClientRect();
      result.tableTop = Math.round(r.top);
      result.tableHeight = Math.round(r.height);
      result.tableBottom = Math.round(r.bottom);
    }
    if (pagination) {
      const r = pagination.getBoundingClientRect();
      result.paginationTop = Math.round(r.top);
      result.paginationHeight = Math.round(r.height);
      result.paginationBottom = Math.round(r.bottom);
    }
    if (tableBody) {
      const r = tableBody.getBoundingClientRect();
      result.tableBodyTop = Math.round(r.top);
      result.tableBodyHeight = Math.round(r.height);
    }
    if (tableHeader) {
      const r = tableHeader.getBoundingClientRect();
      result.tableHeaderHeight = Math.round(r.height);
    }

    if (pagination) {
      const r = pagination.getBoundingClientRect();
      result.paginationDistanceToBottom = Math.round(window.innerHeight - r.bottom);
    }

    return result;
  });

  console.log('\n===== 页面测量结果 =====');
  for (const [key, value] of Object.entries(measurements)) {
    console.log(`  ${key}: ${value}px`);
  }

  // 截图保存
  await page.screenshot({ path: '/workspace/cmdb_ui_lite/slb_listener_after_fix.png', fullPage: false });
  console.log('\n截图已保存: /workspace/cmdb_ui_lite/slb_listener_after_fix.png');

  // 验证分页距离底部 < 50px
  if (measurements.paginationDistanceToBottom > 50) {
    console.log(`\n❌ 分页距离底部 ${measurements.paginationDistanceToBottom}px，超过 50px`);
  } else {
    console.log(`\n✅ 分页距离底部 ${measurements.paginationDistanceToBottom}px，符合要求 < 50px`);
  }
});
