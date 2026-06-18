#!/usr/bin/env python3
"""检查 bk-table 的 DOM 结构和样式"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://localhost:8080/#/resource/instance/bk_slb_listener", wait_until="networkidle")
        await page.wait_for_timeout(5000)

        result = await page.evaluate("""() => {
            const info = {};
            
            // 检查 $APP.height
            const appHeight = window.__VUE__?.$store?.state?.global?.appHeight || 'unknown';
            info.appHeight = appHeight;
            info.windowInnerHeight = window.innerHeight;
            
            // 检查表格容器结构
            const table = document.querySelector('.models-table');
            if (table) {
                info.tableMaxHeight = window.getComputedStyle(table).maxHeight;
                info.tableHeight = table.offsetHeight;
                
                // 获取所有子元素
                const children = Array.from(table.children);
                info.tableChildren = children.map(c => c.className || c.tagName);
                
                // 检查 bk-table-body-wrapper
                const bodyWrapper = table.querySelector('.bk-table-body-wrapper');
                if (bodyWrapper) {
                    info.bodyWrapperHeight = bodyWrapper.offsetHeight;
                    info.bodyWrapperMaxHeight = window.getComputedStyle(bodyWrapper).maxHeight;
                }
                
                // 检查分页
                const pagination = table.querySelector('.bk-table-pagination-wrapper');
                if (pagination) {
                    info.paginationHeight = pagination.offsetHeight;
                }
            }
            
            // 检查 general-model-layout
            const layout = document.querySelector('.general-model-layout');
            if (layout) {
                info.layoutHeight = layout.offsetHeight;
                info.layoutStyle = window.getComputedStyle(layout).display;
            }
            
            return info;
        }""")

        print("\n===== 表格结构分析 =====")
        for key, value in result.items():
            print(f"  {key}: {value}")

        await browser.close()

asyncio.run(main())
