#!/usr/bin/env python3
"""测量 SLB 监听器页面的分页组件与窗口底部的距离（延迟后测量）"""
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
        
        # 等待更长时间让 Vue 组件完全渲染
        await page.wait_for_timeout(5000)

        measurements = await page.evaluate("""() => {
            const result = {};
            result.windowInnerHeight = window.innerHeight;
            result.windowInnerWidth = window.innerWidth;

            const viewsLayout = document.querySelector('.views-layout');
            const table = document.querySelector('.models-table');
            const pagination = document.querySelector('.bk-table-pagination-wrapper');

            if (viewsLayout) {
                const r = viewsLayout.getBoundingClientRect();
                result.viewsLayoutHeight = Math.round(r.height);
            }
            if (table) {
                const r = table.getBoundingClientRect();
                result.tableTop = Math.round(r.top);
                result.tableHeight = Math.round(r.height);
                result.tableBottom = Math.round(r.bottom);
            }
            if (pagination) {
                const r = pagination.getBoundingClientRect();
                result.paginationBottom = Math.round(r.bottom);
            }

            if (pagination) {
                const r = pagination.getBoundingClientRect();
                result.paginationDistanceToBottom = Math.round(window.innerHeight - r.bottom);
            }

            return result;
        }""")

        print("\n===== 页面测量结果（5秒后）=====")
        for key, value in measurements.items():
            print(f"  {key}: {value}")

        await page.screenshot(path="/workspace/cmdb_ui_lite/slb_listener_final.png", full_page=False)
        print("\n截图已保存")

        await browser.close()

asyncio.run(main())
