# =============================================
# clean_hardcoded.py - 酒店管理 HTML 硬编码数据清理工具
# 将 HTML 中的硬编码表格数据替换为动态占位符
# 输入: outputs/html/hotel-management.html
# 输出: 原地覆盖修改
# =============================================
import re

with open('outputs/html/hotel-management.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 替换规则：硬编码数据 → 动态占位符
replacements = [
    # 1. 客源构成 — 替换为动态占位符
    (r'<h3>客源构成</h3><table class="tb"><tr><th>客群</th><th>占比</th><th>平均消费</th><th>复购率</th></tr>.*?</table>',
     '<h3>客源构成</h3><table class="tb"><thead><tr><th>客群</th><th>占比</th><th>平均消费</th><th>复购率</th></tr></thead><tbody id="guest-struct-tbl"><tr><td colspan="4" style="color:var(--tm);padding:20px">— 录入经营数据后生成 —</td></tr></tbody></table>'),

    # 2. 渠道来源分析 — replace
    (r'<h3>渠道来源分析</h3><table class="tb"><tr><th>来源</th><th>新客占比</th><th>复购率</th><th>满意度</th></tr>.*?</table>',
     '<h3>渠道来源分析</h3><table class="tb"><thead><tr><th>来源</th><th>新客占比</th><th>复购率</th><th>满意度</th></tr></thead><tbody id="channel-source-tbl"><tr><td colspan="4" style="color:var(--tm);padding:20px">— 录入渠道数据后生成 —</td></tr></tbody></table>'),

    # 3. 点评统计 — replace
    (r'<h3>点评统计</h3><table class="tb"><tr><th>平台</th><th>总点评</th><th>均分</th><th>回复率</th></tr>.*?</table>',
     '<h3>点评统计</h3><table class="tb"><thead><tr><th>平台</th><th>总点评</th><th>均分</th><th>回复率</th></tr></thead><tbody id="review-stats-tbl"><tr><td colspan="4" style="color:var(--tm);padding:20px">— 无外部接口数据 —</td></tr></tbody></table>'),

    # 4. 各部门人房比 — replace
    (r'<h3>各部门人房比</h3><table class="tb"><tr><th>部门</th><th>编制</th><th>实际</th><th>人房比</th><th>状态</th></tr>.*?</table>',
     '<h3>各部门人房比</h3><table class="tb"><thead><tr><th>部门</th><th>编制</th><th>实际</th><th>人房比</th><th>状态</th></tr></thead><tbody id="staff-ratio-tbl"><tr><td colspan="5" style="color:var(--tm);padding:20px">— 暂无编制数据 —</td></tr></tbody></table>'),

    # 5. 食材成本率趋势 — replace  
    (r'<h3>食材成本率趋势 \(近6个月\)</h3><table class="tb"><tr><th>月份</th><th>成本率</th><th>预算</th><th>差异</th></tr>.*?</table>',
     '<h3>食材成本率趋势 (近6个月)</h3><table class="tb"><thead><tr><th>月份</th><th>成本率</th><th>预算</th><th>差异</th></tr></thead><tbody id="food-trend-tbl"><tr><td colspan="4" style="color:var(--tm);padding:20px">— 录入食材成本后生成趋势 —</td></tr></tbody></table>'),

    # 6. 定价方案对比 — replace
    (r'<h3>定价方案对比</h3><table class="tb"><tr><th>方案</th><th>ADR</th><th>OCC</th><th>RevPAR</th><th>GOP率</th></tr>.*?</table>',
     '<h3>定价方案对比</h3><table class="tb"><thead><tr><th>方案</th><th>ADR</th><th>OCC</th><th>RevPAR</th><th>GOP率</th></tr></thead><tbody id="pricing-compare-tbl"><tr><td colspan="5" style="color:var(--tm);padding:20px">— 录入ADR/OCC后对照竞品生成 —</td></tr></tbody></table>'),

    # 7. NPS — fix the hardcoded text
    (r'贬损者 8% · 被动者 20% · 推荐者',
     '推荐者'),

    # 8. NPS 行业均值 58 — keep as label reference
    (r'行业均值: 58',
     '行业均值: —'),
]

for pattern, replacement in replacements:
    html = re.sub(pattern, replacement, html, flags=re.DOTALL)

with open('outputs/html/hotel-management.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Done. Replacements completed.')
