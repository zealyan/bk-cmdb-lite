/**
 * 实例列表页面对象
 * Instance List Page Object
 */
const { BasePage } = require('./base.page');

class InstanceListPage extends BasePage {
  constructor(page) {
    super(page);
    this.selectors = {
      // 表格
      table: '.models-table, .bk-table',
      tableBody: '.bk-table-body-wrapper tbody',
      tableHeader: '.bk-table-header-wrapper th',
      tableRow: '.bk-table-body-wrapper tbody tr',

      // 操作按钮
      createButton: 'button:has-text("新建")',
      refreshButton: 'button:has-text("刷新")',

      // 搜索
      searchInput: '.bk-input input',

      // 分页
      pagination: '.bk-pagination, .pagination',
      pageItem: '.bk-page-item, .pagination li',

      // 排序图标
      sortIcon: '.bk-table-sort-caret, .caret-wrapper',

      // 列配置
      columnConfigButton: '.icon-cc-setting',
      columnConfigSideslider: '.bk-sideslider'
    };
  }

  async navigateToModel(modelId) {
    await this.goto(`/#/instance/${modelId}`);
    await this.page.waitForTimeout(1000);
  }

  async getTableHeaders() {
    return this.page.$$eval(this.selectors.tableHeader, ths =>
      ths.map(th => th.textContent.trim())
    );
  }

  async getFirstRowData() {
    const cells = await this.page.$$eval(
      `${this.selectors.tableRow}:first-child td`,
      tds => tds.map(td => td.textContent.trim())
    );
    return cells;
  }

  async clickColumnHeader(columnIndex) {
    const headers = await this.page.$$(this.selectors.tableHeader);
    if (headers[columnIndex]) {
      await headers[columnIndex].click();
      await this.page.waitForTimeout(500);
    }
  }

  async getSortState(columnIndex) {
    const header = await this.page.$(`${this.selectors.tableHeader}:nth-child(${columnIndex + 1})`);
    if (!header) return null;

    const hasAsc = await header.$('.ascending, .asc, .sort-ascending');
    const hasDesc = await header.$('.descending, .desc, .sort-descending');

    if (hasAsc) return 'ascending';
    if (hasDesc) return 'descending';
    return null;
  }

  async search(keyword) {
    await this.page.fill(this.selectors.searchInput, keyword);
    await this.page.waitForTimeout(500);
  }

  async clearSearch() {
    await this.page.fill(this.selectors.searchInput, '');
    await this.page.waitForTimeout(500);
  }

  async clickCreate() {
    await this.click(this.selectors.createButton);
  }

  async clickRefresh() {
    await this.click(this.selectors.refreshButton);
  }

  async goToNextPage() {
    const nextButton = await this.page.$('.bk-page-next, .pagination .next');
    if (nextButton) {
      await nextButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  async goToPrevPage() {
    const prevButton = await this.page.$('.bk-page-prev, .pagination .prev');
    if (prevButton) {
      await prevButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  async clickInstanceId() {
    const idButton = await this.page.$('.bk-table-body-wrapper tbody tr:first-child td:nth-child(2) button');
    if (idButton) {
      await idButton.click();
      await this.page.waitForTimeout(500);
    }
  }
}

module.exports = { InstanceListPage };
