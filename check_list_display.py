#!/usr/bin/env python3
"""检查 list 类型属性在实例列表中的显示"""
from playwright.sync_api import sync_playwright
import time

def handle_console(msg):
    print(f'[Console] {msg.type}: {msg.text}')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 收集控制台日志
    page.on('console', handle_console)
    
    # 访问交换机实例列表页面
    print('\n=== 访问交换机实例列表 ===')
    page.goto('http://localhost:3000/#/instance/bk_switch', wait_until='networkidle')
    time.sleep(3)
    
    # 截图
    page.screenshot(path='/workspace/check_list_display.png', full_page=True)
    print('截图已保存到 /workspace/check_list_display.png')
    
    # 检查表格内容
    print('\n=== 检查表格内容 ===')
    rows = page.locator('.bk-table tbody tr').all()
    print(f'找到 {len(rows)} 行数据')
    
    if len(rows) > 0:
        # 检查第一行的单元格内容
        cells = rows[0].locator('td').all()
        print(f'第一行有 {len(cells)} 个单元格')
        
        for i, cell in enumerate(cells):
            text = cell.inner_text()
            print(f'单元格 {i}: {text[:100] if len(text) > 100 else text}')
    
    # 检查是否有"<no value>"文本
    print('\n=== 检查是否有 <no value> 文本 ===')
    no_value_count = page.locator('text="<no value>"').count()
    print(f'找到 {no_value_count} 个 <no value> 元素')
    
    # 检查所属地域列
    print('\n=== 检查所属地域列 ===')
    region_header = page.locator('th:has-text("所属地域")')
    if region_header.count() > 0:
        print('找到"所属地域"列头')
        # 获取列索引
        header_row = page.locator('thead tr').first
        headers = header_row.locator('th').all()
        region_index = -1
        for i, header in enumerate(headers):
            if '所属地域' in header.inner_text():
                region_index = i
                break
        
        if region_index >= 0:
            print(f'所属地域列索引: {region_index}')
            # 检查该列的数据
            for i, row in enumerate(rows[:5]):  # 检查前5行
                cells = row.locator('td').all()
                if len(cells) > region_index:
                    cell_text = cells[region_index].inner_text()
                    print(f'行 {i} 所属地域: {cell_text}')
    
    browser.close()
    print('\n=== 检查完成 ===')
