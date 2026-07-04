# =============================================
# find_hardcoded.py - 酒店管理 HTML 硬编码数据检测工具
# 扫描 HTML 中所有可能的硬编码数字，定位需要替换的位置
# 用于配合 clean_hardcoded.py 使用
# =============================================
import re
html = open('outputs/html/hotel-management.html', 'r', encoding='utf-8').read()
# 只扫描 HTML 部分，跳过 <script> 标签
parts = html.split('<script>')
html_part = parts[0]

lines = html_part.split('\n')
for i, l in enumerate(lines, 1):
    l = l.strip()
    if not l or l.startswith('<!--'):
        continue
    # 查找标签间的数字内容（带中文单位的）
    nums = re.findall(r'>(\d+[.,]?\d*[%万元倍月间夜点人]*?)<', l)
    for n in nums:
        digits = ''.join(c for c in n if c.isdigit())
        if digits and len(digits) >= 2 and n not in ['0','1','2','3','4','5','6','7','8','9']:
            ctx = l[:150]
            print(f'  行 {i}: {ctx}')
