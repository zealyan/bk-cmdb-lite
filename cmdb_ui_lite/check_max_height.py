#!/usr/bin/env python3
"""检查表格 max-height 是否被正确应用"""
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

        measurements = await page.evaluate("""() => {
            const result = {};
            result.windowInnerHeight = window.innerHeight;
            
            const table = document.querySelector('.models-table');
            if (table) {
                const r = table.getBoundingClientRect();
                result.tableHeight = Math.round(r.height);
                result.tableBottom = Math.round(r.bottom);
                result.tableComputedMaxHeight = window.getComputedStyle(table).maxHeight;
                result.tableComputedHeight = window.getComputedStyle(table).height;
            }
            
            const tableBody = document.querySelector('.bk-table-body-wrapper');
            if (tableBody) {
                const r = tableBody.getBoundingClientRect();
                result.tableBodyHeight = Math.round(r.height);
                result.tableBodyMaxHeight = window.getComputedStyle(tableBody).maxHeight;
            }
            
            const pagination = document.querySelector('.bk-table-pagination-wrapper');
            if (pagination) {
                const r = pagination.getBoundingClientRect();
                result.paginationBottom = Math.round(r.bottom);
                result.paginationDistanceToBottom = Math.round(window.innerHeight - r.bottom);
            }

            // 检查 Vue 组件的 tableContentHeight
            const app = document.getElementById('app');
            if (app && app.__vue__) {
                const vm = app.__vue__.$children.find(c => c.$options.name === 'general-model');
                if (vm) {
                    result.vueTableContentHeight = vm.tableContentHeight;
                    result.vueFilterTagHeight = vm.filterTagHeight;
                }
            }

            return result;
        }""")

        print("\n===== 表格高度检查 =====")
        for key, value in measurements.items():
            print(f"  {key}: {value}")

        await browser.close()

asyncio.run(main())
