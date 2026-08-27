/* E2E：URL node 参数联动拓扑树（硬刷新 / 新开窗场景）
 * 打开 #/business/2/index?node=module-141388&page=1
 * 断言：拓扑树逐级展开到 web 模块并选中；主机列表联动展示该模块主机
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  const requests = [];
  page.on('pageerror', e => errors.push(`[pageerror] ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !m.text().includes('Failed to load resource')) errors.push(`[console] ${m.text()}`);
  });
  page.on('request', r => {
    const u = r.url();
    if (u.includes('/topo/instance/path') || u.includes('/topo/instance/children')) {
      requests.push(u.split('/api/v1')[1]);
    }
  });

  try {
    // 登录态注入：路由守卫 ensureAuth() 要求有效 token（localStorage lite_bk_token）
    await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.evaluate(async () => {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bk_user_name: 'admin', bk_password: 'admin' })
      });
      const json = await res.json();
      localStorage.setItem('lite_bk_token', json.data.bk_token);
      localStorage.setItem('lite_bk_user_name', 'admin');
    });

    // 直接带 node 参数导航（等价硬刷新 / 新开窗）
    await page.goto('http://127.0.0.1:3000/business/2/index#/business/2/index?node=module-141388&page=1', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(4000);

    const state = await page.evaluate(() => {
      // 组件根元素为 .tree-layout，其 __vue__ 才是 TopologyTree 实例（$refs.tree 指向 bk-big-tree）
      const vm = document.querySelector('.tree-layout') && document.querySelector('.tree-layout').__vue__;
      if (!vm || !vm.$refs.tree) return { err: 'no tree vm' };
      const tree = vm.$refs.tree;
      const target = tree.getNodeById('module-141388');
      const expandedIds = tree.nodes.filter(n => n.expanded).map(n => n.id);
      const selected = tree.nodes.filter(n => n.selected).map(n => n.id);
      return {
        targetFound: !!target,
        targetSelected: target ? !!target.selected : false,
        selectedIds: selected,
        expandedCount: expandedIds.length,
        hasBizExpanded: expandedIds.includes('biz-2'),
        hasSetExpanded: expandedIds.includes('set-141387'),
        visibleModuleNames: tree.nodes.filter(n => n.visible && n.data.bk_obj_id === 'module').map(n => n.data.bk_inst_name)
      };
    });

    // 主机列表联动：节点信息 / 主机表是否展示 web 模块主机
    const bodyText = await page.evaluate(() => document.body.innerText.replace(/\n+/g, ' | '));
    const hostTableShowsWeb = bodyText.includes('web-server-01');

    console.log('=== URL→node 联动断言 ===');
    console.log(JSON.stringify(state, null, 2));
    console.log('路径展开请求:', requests);
    console.log('主机表包含 web-server-01:', hostTableShowsWeb);
    console.log('JS 错误数:', errors.length, errors.slice(0, 3));

    const pass = state.targetFound
      && state.targetSelected
      && state.selectedIds.includes('module-141388')
      && state.hasBizExpanded
      && state.hasSetExpanded
      && errors.length === 0;
    console.log(pass ? '\n✅ URL-NODE-SYNC PASS' : '\n❌ URL-NODE-SYNC FAIL');
    process.exit(pass ? 0 : 1);
  } catch (e) {
    console.log('❌ E2E ERROR:', e.message);
    console.log('errors:', errors.slice(0, 5));
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
