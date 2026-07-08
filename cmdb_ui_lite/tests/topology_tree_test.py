#!/usr/bin/env python3
"""验证业务拓扑树页面效果"""
import sys
sys.path.insert(0, '/data/user/skills/webapp-testing')

from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 访问业务拓扑页面
        page.goto('http://localhost:3000/#/business/topology')
        
        # 等待页面加载完成
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        
        # 截图保存
        page.screenshot(path='/data/tool/browser_snapshots/business-topology-tree.png', full_page=True)
        
        # 获取页面元素信息
        # 检查拓扑树是否存在
        tree_exists = page.locator('.topology-tree-wrapper').count() > 0
        print(f"拓扑树容器存在: {tree_exists}")
        
        # 检查树节点数量
        tree_nodes = page.locator('.topology-tree-node').count()
        print(f"树节点数量: {tree_nodes}")
        
        # 检查搜索输入框
        search_input = page.locator('.tree-search input').count() > 0
        print(f"搜索输入框存在: {search_input}")
        
        # 检查右侧Tab面板
        tab_panels = page.locator('.bk-tab-panel').count()
        print(f"Tab面板数量: {tab_panels}")
        
        browser.close()
        
        print("\n截图已保存到: /data/tool/browser_snapshots/business-topology-tree.png")

if __name__ == '__main__':
    main()