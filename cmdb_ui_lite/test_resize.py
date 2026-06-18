#!/usr/bin/env python3
"""测试屏幕尺寸变化时表格高度的响应"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # 测试不同屏幕尺寸
        for height in [800, 900, 1000, 1200]:
            page = await browser.new_page(viewport={"width": 1440, "height": height})
            await page.goto("http://localhost:8080/#/resource/instance/bk_slb_listener", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            result = await page.evaluate("""() => {
                const info = {};
                info.windowInnerHeight = window.innerHeight;
                info.appHeight = window.__VUE__?.$store?.state?.global?.appHeight || 'unknown';
                
                const table = document.querySelector('.models-table');
                if (table) {
                    info.tableMaxHeight = window.getComputedStyle(table).maxHeight;
                    info.tableHeight = table.offsetHeight;
                }
                
                const pagination = document.querySelector('.bk-table-pagination-wrapper');
                if (pagination) {
                    const r = pagination.getBoundingClientRect();
                    info.paginationBottom = Math.round(r.bottom);
                    info.paginationDistanceToBottom = Math.round(window.innerHeight - r.bottom);
                }
                
                return info;
            }""")
            
            print(f"\n===== 屏幕高度 {height}px =====")
            for key, value in result.items():
                print(f"  {key}: {value}")
            
            await page.close()
        
        await browser.close()

asyncio.run(main())
