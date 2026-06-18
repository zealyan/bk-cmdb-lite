#!/usr/bin/env python3
"""检查面包屑和表格的相对位置"""
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
            
            const viewsLayout = document.querySelector('.views-layout');
            if (viewsLayout) {
                const children = Array.from(viewsLayout.children);
                info.viewsLayoutChildren = children.map(c => ({
                    className: c.className,
                    tagName: c.tagName,
                    top: Math.round(c.getBoundingClientRect().top),
                    bottom: Math.round(c.getBoundingClientRect().bottom),
                    height: Math.round(c.getBoundingClientRect().height)
                }));
            }
            
            const breadcrumbs = document.querySelector('.page-breadcrumbs');
            if (breadcrumbs) {
                info.breadcrumbsParent = breadcrumbs.parentElement.className;
                const r = breadcrumbs.getBoundingClientRect();
                info.breadcrumbsTop = Math.round(r.top);
                info.breadcrumbsBottom = Math.round(r.bottom);
            }
            
            return info;
        }""")

        print("\n===== 布局结构分析 =====")
        for key, value in result.items():
            if isinstance(value, list):
                print(f"  {key}:")
                for child in value:
                    print(f"    - {child['tagName']}.{child['className']}: top={child['top']}, bottom={child['bottom']}, height={child['height']}")
            else:
                print(f"  {key}: {value}")

        await browser.close()

asyncio.run(main())
