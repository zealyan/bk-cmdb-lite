#!/usr/bin/env python3
"""检查 $APP.height 的实际值"""
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
            
            // 检查 Vuex store
            const vm = document.getElementById('app')?.__vue__;
            if (vm) {
                info.appHeight = vm.$store?.state?.global?.appHeight;
                info.noticeHeight = vm.$store?.state?.global?.noticeHeight;
            }
            
            // 检查 app 元素
            const app = document.getElementById('app');
            if (app) {
                info.appOffsetHeight = app.offsetHeight;
                info.appClientHeight = app.clientHeight;
                const r = app.getBoundingClientRect();
                info.appRectHeight = Math.round(r.height);
            }
            
            // 检查 views-layout
            const viewsLayout = document.querySelector('.views-layout');
            if (viewsLayout) {
                info.viewsLayoutHeight = viewsLayout.offsetHeight;
                const r = viewsLayout.getBoundingClientRect();
                info.viewsLayoutRectHeight = Math.round(r.height);
            }
            
            return info;
        }""")

        print("\n===== $APP.height 检查 =====")
        for key, value in result.items():
            print(f"  {key}: {value}")

        await browser.close()

asyncio.run(main())
