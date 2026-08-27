/* E2E：URL node → 展开父链 → 选中 → 虚拟滚动滚入视图（全量树，4605 节点）
 *
 * 场景：biz3 全量树 4605 节点。目标 module-146000 位于
 * 第 50 个应用系统（sys-141445 → subsys-141845 → set-143029）深处，
 * 展开父链后其行号 ≫ 视口可容纳条数（~21），
 * 若只 setSelected 而不滚动，选中行停在视口外，用户「看不到」。
 *
 * 断言：
 *   1. 目标节点被定位并选中（selected + visible）
 *   2. 父链（biz/sys/subsys/set）均已展开
 *   3. 选中节点在虚拟滚动【视口内】—— 核心：indexList 首尾区间覆盖目标行
 *   4. 选中节点的 DOM 真实渲染在滚动容器可视范围内（getBoundingClientRect）
 */
const { chromium } = require('playwright');

const TARGET = 'module-146000';
const CHAIN = ['biz-3', 'sys-141445', 'subsys-141845', 'set-143029', 'module-146000'];

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(`[pageerror] ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !m.text().includes('Failed to load resource')) {
      errors.push(`[console] ${m.text()}`);
    }
  });

  try {
    // 登录态注入：路由守卫 ensureAuth() 要求有效 token（localStorage lite_bk_token）
    await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    const logged = await page.evaluate(async () => {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bk_user_name: 'admin', bk_password: 'admin' })
      });
      const json = await res.json();
      const token = json && json.data && json.data.bk_token;
      if (!token) return false;
      localStorage.setItem('lite_bk_token', token);
      localStorage.setItem('lite_bk_user_name', 'admin');
      document.cookie = `lite_bk_token=${token}; path=/`;
      return true;
    });
    if (!logged) throw new Error('登录失败，无法获取 token');

    await page.goto(
      `http://127.0.0.1:3000/business/3/index#/business/3/index?node=${TARGET}&page=1`,
      { waitUntil: 'networkidle', timeout: 60000 }
    );
    // 全量树 setData + 展开父链 + 滚动收敛，给足时间
    await page.waitForTimeout(9000);

    const state = await page.evaluate((args) => {
      const { target, chain } = args;
      const layout = document.querySelector('.tree-layout');
      const vm = layout && layout.__vue__;
      if (!vm || !vm.$refs.tree) return { err: 'no tree vm' };
      const tree = vm.$refs.tree;
      const vs = tree.$refs.virtualScroll;
      const node = tree.getNodeById(target);
      const expandedIds = new Set(tree.nodes.filter(n => n.expanded).map(n => n.id));

      // 虚拟滚动视口区间（indexList.value 为 1-based）
      let idxInfo = null;
      if (vs && vs.indexList && vs.indexList.length) {
        const first = vs.indexList[0].value;
        const last = vs.indexList[vs.indexList.length - 1].value;
        const targetRow = tree.visibleNodes.indexOf(node) + 1; // 1-based
        idxInfo = {
          viewportFirst: first,
          viewportLast: last,
          targetRow,
          // 含边界：目标位于虚拟滚动渲染窗口内（首尾边缘也算已滚入视图——
          // 与 scrollNodeIntoView 实际语义一致：目标行已渲染且 DOM 可见）
          inViewport: targetRow >= first && targetRow <= last,
          itemNumber: vs.itemNumber,
          totalNumber: vs.totalNumber
        };
      }

      // 选中行 DOM 是否真实落在滚动容器可视范围
      let domVisible = null;
      const selectedEl = layout.querySelector('.bk-big-tree-node.is-selected');
      const scrollHome = layout.querySelector('.bk-virtual-scroll') || layout.querySelector('.topology-tree');
      if (selectedEl && scrollHome) {
        const r = selectedEl.getBoundingClientRect();
        const c = scrollHome.getBoundingClientRect();
        domVisible = {
          selectedText: selectedEl.innerText.replace(/\s+/g, ' ').trim().slice(0, 30),
          within: r.top >= c.top - 2 && r.bottom <= c.bottom + 2,
          nodeTop: Math.round(r.top),
          containerTop: Math.round(c.top),
          containerBottom: Math.round(c.bottom)
        };
      }

      return {
        targetFound: !!node,
        targetSelected: node ? !!node.selected : false,
        targetVisibleFlag: node ? !!node.visible : false,
        chainExpanded: chain.slice(0, -1).map(id => ({ id, expanded: expandedIds.has(id) })),
        allChainExpanded: chain.slice(0, -1).every(id => expandedIds.has(id)),
        idxInfo,
        domVisible
      };
    }, { target: TARGET, chain: CHAIN });

    console.log('=== URL→展开→选中→滚入视口 断言 (biz3, 4605节点) ===');
    console.log(JSON.stringify(state, null, 2));
    console.log('JS 错误数:', errors.length, errors.slice(0, 3));

    const pass = state.targetFound
      && state.targetSelected
      && state.targetVisibleFlag
      && state.allChainExpanded
      && state.idxInfo && state.idxInfo.inViewport
      && state.domVisible && state.domVisible.within
      && errors.length === 0;

    console.log(pass ? '\nSMOKE PASS ✅' : '\nSMOKE FAIL ❌');
    await browser.close();
    process.exit(pass ? 0 : 1);
  } catch (e) {
    console.error('E2E 异常:', e.message);
    await browser.close();
    process.exit(2);
  }
})();
