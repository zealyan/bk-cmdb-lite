/**
 * 页面对象基类
 * Page Object Base Class
 */
class BasePage {
  constructor(page) {
    this.page = page;
    this.baseUrl = process.env.BASE_URL || 'http://localhost:3000';
  }

  async goto(path) {
    await this.page.goto(`${this.baseUrl}${path}`);
    await this.page.waitForLoadState('networkidle');
  }

  async waitForSelector(selector, options = {}) {
    await this.page.waitForSelector(selector, {
      timeout: options.timeout || 10000,
      ...options
    });
  }

  async click(selector, options = {}) {
    await this.waitForSelector(selector);
    await this.page.click(selector, options);
  }

  async getText(selector) {
    await this.waitForSelector(selector);
    return this.page.textContent(selector);
  }

  async getAttribute(selector, attribute) {
    await this.waitForSelector(selector);
    return this.page.getAttribute(selector, attribute);
  }

  async isVisible(selector) {
    const element = await this.page.$(selector);
    return element !== null;
  }
}

module.exports = { BasePage };
