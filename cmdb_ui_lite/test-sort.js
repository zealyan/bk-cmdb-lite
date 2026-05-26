const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const baseUrl = 'http://localhost:35845';

  try {
    console.log('='.repeat(60));
    console.log('开始执行表格排序功能测试');
    console.log('='.repeat(60));

    // TC-001: 表格列标题显示排序图标
    console.log('\n' + '-'.repeat(60));
    console.log('执行测试: TC-001 表格列标题显示排序图标');
    console.log('-'.repeat(60));

    await page.goto(`${baseUrl}/#/instance/bk_slb`);
    await page.waitForTimeout(1500);

    const tableHeaders = await page.$$eval('.bk-table-header-wrapper th', ths => {
      return ths.map((th, idx) => ({
        index: idx,
        text: th.textContent.trim().substring(0, 20)
      }));
    });
    console.log('表格列数:', tableHeaders.length);
    console.log('列信息:', tableHeaders);

    const hasSortable = await page.$('.bk-table-sort, .caret-wrapper, [class*="sort"]');
    console.log('是否有排序图标元素:', !!hasSortable);
    console.log('✅ TC-001 完成: 检查表格列');

    // TC-002: 点击列标题触发升序排序
    console.log('\n' + '-'.repeat(60));
    console.log('执行测试: TC-002 点击列标题触发升序排序');
    console.log('-'.repeat(60));

    const getFirstRowText = async () => {
      const row = await page.$('.bk-table-body-wrapper tbody tr:first-child');
      if (!row) return null;
      const cells = await row.$$eval('td', tds => tds.map(td => td.textContent.trim()));
      return cells;
    };

    const beforeSort = await getFirstRowText();
    console.log('排序前第一行数据:', beforeSort);

    const sortableHeader = await page.$('.bk-table-header-wrapper th:nth-child(2)');
    if (sortableHeader) {
      await sortableHeader.click();
      await page.waitForTimeout(800);
    }

    const afterFirstClick = await getFirstRowText();
    console.log('点击后第一行数据:', afterFirstClick);

    const sortIconClass = await page.$eval('.bk-table-header-wrapper th:nth-child(2)', th => {
      const icon = th.querySelector('[class*="sort"], .caret-wrapper, .bk-table-sort');
      return icon ? icon.className : 'no-icon';
    });
    console.log('排序图标class:', sortIconClass);
    console.log('✅ TC-002 完成: 第一次点击排序');

    // TC-003: 再次点击列标题触发降序排序
    console.log('\n' + '-'.repeat(60));
    console.log('执行测试: TC-003 再次点击列标题触发降序排序');
    console.log('-'.repeat(60));

    if (sortableHeader) {
      await sortableHeader.click();
      await page.waitForTimeout(800);
    }

    const afterSecondClick = await getFirstRowText();
    console.log('再次点击后第一行数据:', afterSecondClick);

    const sortIconClass2 = await page.$eval('.bk-table-header-wrapper th:nth-child(2)', th => {
      const icon = th.querySelector('[class*="sort"], .caret-wrapper, .bk-table-sort');
      return icon ? icon.className : 'no-icon';
    });
    console.log('排序图标class:', sortIconClass2);
    console.log('✅ TC-003 完成: 第二次点击排序');

    // TC-004: 点击第三列触发升序排序
    console.log('\n' + '-'.repeat(60));
    console.log('执行测试: TC-004 点击第三列触发升序排序');
    console.log('-'.repeat(60));

    const thirdHeader = await page.$('.bk-table-header-wrapper th:nth-child(3)');
    if (thirdHeader) {
      await thirdHeader.click();
      await page.waitForTimeout(800);
    }

    const thirdHeaderText = await page.$eval('.bk-table-header-wrapper th:nth-child(3)', th => th.textContent.trim());
    console.log('第三列表头:', thirdHeaderText);

    const afterThirdClick = await getFirstRowText();
    console.log('点击第三列后第一行数据:', afterThirdClick);
    console.log('✅ TC-004 完成: 第三列排序');

    // TC-005: 排序后分页保持
    console.log('\n' + '-'.repeat(60));
    console.log('执行测试: TC-005 排序后分页保持');
    console.log('-'.repeat(60));

    await page.click('.bk-table-header-wrapper th:nth-child(2)');
    await page.waitForTimeout(500);

    const pageNext = await page.$('.bk-page-item:nth-last-child(2), .bk-pagination .bk-page-item:nth-last-child(2), [class*="pagination"] [class*="next"]');
    if (pageNext) {
      await pageNext.click();
      await page.waitForTimeout(500);
      console.log('已点击下一页');
    }

    const afterPageChange = await getFirstRowText();
    console.log('翻页后第一行数据:', afterPageChange);
    console.log('✅ TC-005 完成: 分页排序保持');

    // 总结
    console.log('\n' + '='.repeat(60));
    console.log('测试执行完成');
    console.log('='.repeat(60));

  } catch (error) {
    console.error('\n测试过程中出错:', error.message);
    try {
      await page.screenshot({ path: '/workspace/bk-cmdb/cmdb_ui_lite/test-sort-error.png' });
      console.log('截图已保存到: /workspace/bk-cmdb/cmdb_ui_lite/test-sort-error.png');
    } catch (e) {}
  } finally {
    await browser.close();
  }
}

runTests();
