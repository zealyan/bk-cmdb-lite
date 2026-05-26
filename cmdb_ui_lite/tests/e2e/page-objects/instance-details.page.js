/**
 * 实例详情页面对象
 * Instance Details Page Object
 */
const { BasePage } = require('./base.page');

class InstanceDetailsPage extends BasePage {
  constructor(page) {
    super(page);
    this.selectors = {
      // 页面元素
      pageHeader: '.page-header',
      headerTitle: '.header-title',

      // Tabs
      tabs: '.bk-tab, .bk-tab-panel',
      tabLabel: '.bk-tab-label-item',
      associationTab: '[class*="tab"]:has-text("关联")',

      // 基本信息
      infoCard: '.info-card',
      infoGrid: '.info-grid',
      infoItem: '.info-item',

      // 关联列表
      associationComponent: '.instance-association',
      associationOptions: '.association-options',
      associationList: '.association-list',
      associationGroup: '.association-group',
      groupInfo: '.group-info',
      infoTitle: '.info-title',
      titleText: '.title-text',
      titleCount: '.title-count',
      iconRightShape: '.icon-right-shape',

      // 表格
      associationTable: '.association-table',
      tableHeader: '.bk-table-header-wrapper th',
      tableBody: '.bk-table-body-wrapper tbody tr',

      // 返回按钮
      backButton: '.header-back',

      // 空状态
      emptyState: '.association-empty'
    };
  }

  async navigateToInstance(objId, instId) {
    await this.goto(`/#/instance/${objId}/${instId}`);
    await this.page.waitForTimeout(1000);
  }

  async clickAssociationTab() {
    const tab = await this.page.$(this.selectors.associationTab);
    if (tab) {
      await tab.click();
      await this.page.waitForTimeout(500);
    }
  }

  async clickBack() {
    await this.click(this.selectors.backButton);
    await this.page.waitForTimeout(500);
  }

  async getHeaderTitle() {
    return this.getText(this.selectors.headerTitle);
  }

  async getInfoItems() {
    return this.page.$$eval(this.selectors.infoItem, items =>
      items.map(item => ({
        label: item.querySelector('.info-label')?.textContent?.trim(),
        value: item.querySelector('.info-value')?.textContent?.trim()
      }))
    );
  }

  async getAssociationGroups() {
    return this.page.$$eval(this.selectors.groupInfo, groups =>
      groups.map(group => ({
        title: group.querySelector('.title-text')?.textContent?.trim(),
        count: group.querySelector('.title-count')?.textContent?.trim()
      }))
    );
  }

  async clickAssociationGroup(index = 0) {
    const groups = await this.page.$$(this.selectors.groupInfo);
    if (groups[index]) {
      await groups[index].click();
      await this.page.waitForTimeout(500);
    }
  }

  async getGroupSortState(index = 0) {
    const icon = await this.page.$(
      `${this.selectors.groupInfo}:nth-child(${index + 1}) ${this.selectors.iconRightShape}`
    );
    if (!icon) return null;

    const className = await icon.evaluate(el => el.className);
    return className.includes('is-open') ? 'expanded' : 'collapsed';
  }

  async getAssociationTableData() {
    return this.page.$$eval(this.selectors.tableBody, rows =>
      rows.map(row =>
        Array.from(row.querySelectorAll('td')).map(td => td.textContent.trim())
      )
    );
  }

  async clickAddAssociation() {
    const button = await this.page.$('button:has-text("新增关联")');
    if (button) {
      await button.click();
      await this.page.waitForTimeout(500);
    }
  }

  async isAssociationTabVisible() {
    return this.isVisible(this.selectors.associationTab);
  }

  async isEmptyStateVisible() {
    return this.isVisible(this.selectors.emptyState);
  }
}

module.exports = { InstanceDetailsPage };
