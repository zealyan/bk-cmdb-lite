#!/usr/bin/env python3
"""测量 SLB 监听器页面的分页组件与窗口底部的距离"""
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
        await page.wait_for_timeout(3000)

        # 等待表格出现
        try:
            await page.wait_for_selector('.bk-table', timeout=10000)
        except Exception as e:
            print(f"等待 .bk-table 超时: {e}")
            await page.screenshot(path='/workspace/cmdb_ui_lite/slb_listener_debug.png')
            print("调试截图已保存")

        await page.wait_for_timeout(2000)

        measurements = await page.evaluate("""() => {
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
        }""")

        print("\n===== 页面测量结果 =====")
        for key, value in measurements.items():
            print(f"  {key}: {value}")

        await page.screenshot(path="/workspace/cmdb_ui_lite/slb_listener_after_fix.png", full_page=False)
        print("\n截图已保存: /workspace/cmdb_ui_lite/slb_listener_after_fix.png")

        await browser.close()

asyncio.run(main())
