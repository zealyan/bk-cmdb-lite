#!/usr/bin/env python3
"""调试 calculateTableHeight 是否被调用"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        
        # 收集 console.log
        logs = []
        page.on('console', lambda msg: logs.append(f"[{msg.type()}] {msg.text()}"))
        
        await page.goto("http://localhost:8080/#/resource/instance/bk_slb_listener", wait_until="networkidle")
        await page.wait_for_timeout(5000)

        # 手动调用 calculateTableHeight
        await page.evaluate("""() => {
            const viewsLayout = document.querySelector('.views-layout');
            console.log('[DEBUG] viewsLayout:', viewsLayout);
            if (viewsLayout) {
                console.log('[DEBUG] viewsLayout.height:', viewsLayout.getBoundingClientRect().height);
            }
            
            // 尝试手动触发计算
            const app = document.getElementById('app');
            console.log('[DEBUG] app:', app);
            
            // 检查 tableContentHeight
            const table = document.querySelector('.models-table');
            if (table) {
                console.log('[DEBUG] table.style.maxHeight:', table.style.maxHeight);
            }
        }""")

        await page.wait_for_timeout(1000)

        print("\n===== Console Logs =====")
        for log in logs[-20:]:
            print(log)

        await browser.close()

asyncio.run(main())
