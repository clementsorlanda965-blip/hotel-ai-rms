"""
酒店管理系统 — 全面集成测试脚本
逐接口、逐数据流验证
"""
import json, urllib.request, sys

BASE = 'http://localhost:8520'
errors = []

def get(endpoint):
    with urllib.request.urlopen(BASE + endpoint, timeout=5) as r:
        return json.loads(r.read())

def post(endpoint, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + endpoint, data=body,
        headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())

def put(endpoint, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + endpoint, data=body,
        headers={'Content-Type':'application/json'}, method='PUT')
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())

def check(label, condition, detail=""):
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}  -  {detail}")
        errors.append((label, detail))

# ============ 第1组：核心 API 可用性 ============
print("\n=== 第1组：核心 API 可用性 ===")
endpoints = ['/api/kpi','/api/channels','/api/pnl','/api/competitors',
             '/api/alerts','/api/social','/api/inhouse','/api/housekeeping',
             '/api/rate-parity','/api/morning-brief','/api/fnb',
             '/api/service-recovery','/api/banquet-calendar','/api/dashboard',
             '/api/ota-directory']
for ep in endpoints:
    try:
        d = get(ep)
        check(ep, d is not None, "无响应")
    except Exception as e:
        check(ep, False, str(e)[:80])

# ============ 第2组：dashboard 数据结构完整性 ============
print("\n=== 第2组：Dashboard 数据结构 ===")
d = get('/api/dashboard')
check('kpi 存在', 'kpi' in d)
check('channels 存在', 'channels' in d and len(d['channels']) > 0, f"channels={len(d.get('channels',[]))}")
check('alerts 存在', 'alerts' in d and len(d['alerts']) > 0, f"alerts={len(d.get('alerts',[]))}")
check('competitors 存在', 'competitors' in d and len(d['competitors']) > 0)
check('pnl 存在', 'pnl' in d and len(d['pnl']) > 0)
check('inhouse 存在', 'inhouse' in d and d['inhouse'].get('total_guests', 0) > 0)
check('housekeeping 存在', 'housekeeping' in d and d['housekeeping'].get('total_rooms', 0) > 0)
check('fnb 存在', isinstance(d.get('fnb'), dict) and len(d.get('fnb', {})) > 0)
check('morning_brief 存在', isinstance(d.get('morning_brief'), dict))
check('service_recovery 存在', isinstance(d.get('service_recovery'), list))
check('banquet_calendar 存在', isinstance(d.get('banquet_calendar'), list) and len(d.get('banquet_calendar', [])) > 0)
check('rate_parity 存在', isinstance(d.get('rate_parity'), list))
check('social 存在', isinstance(d.get('social'), list) and len(d.get('social', [])) > 0)

# ============ 第3组：KPI 数据合理性 ============
print("\n=== 第3组：KPI 数据合理性 ===")
kpi = d['kpi']
check('OCC 合理 (0-100)', 0 < kpi.get('occ', 0) <= 100, f"occ={kpi.get('occ')}")
check('ADR 合理 (>0)', kpi.get('adr', 0) > 0, f"adr={kpi.get('adr')}")
check('RevPAR 合理 (>=0)', kpi.get('revpar', -1) >= 0, f"revpar={kpi.get('revpar')}")
check('NPS 合理 (0-100)', 0 <= kpi.get('nps', -1) <= 100, f"nps={kpi.get('nps')}")

# ============ 第4组：渠道数据合理性 ============
print("\n=== 第4组：渠道数据合理性 ===")
ch = d['channels']
shares = sum(c.get('share', 0) for c in ch)
check('渠道占比总和 ≈ 100%', 95 <= shares <= 105, f"shares={shares:.1f}%")
check('每条渠道有 name', all(c.get('name') for c in ch))
check('每条渠道有 rooms', all(c.get('rooms', 0) > 0 for c in ch))

# ============ 第5组：KPI PUT 写操作 ============
print("\n=== 第5组：KPI 写操作 ===")
try:
    r = put('/api/kpi', {'occ': 75, 'adr': 680})
    check('PUT 成功', r.get('occ') == 75, str(r))
except Exception as e:
    check('PUT 成功', False, str(e)[:80])

# ============ 第6组：sync 接口 ============
print("\n=== 第6组：Sync 接口 ===")
try:
    r = post('/api/sync', {'kpi': {'todayRevenue': 250000, 'occ': 80}})
    check('sync 成功', r.get('success') == True)
    d2 = get('/api/dashboard')
    check('KPI 已同步', d2['kpi']['occ'] == 80, f"occ={d2['kpi']['occ']}")
except Exception as e:
    check('sync 成功', False, str(e)[:80])

# ============ 第7组：channel CRUD ============
print("\n=== 第7组：Channel CRUD ===")
try:
    r = post('/api/channels', {'name': 'TEST渠道', 'rooms': 200, 'adr': 500, 'commission': 10})
    check('POST 添加渠道', r.get('success') == True)
    d3 = get('/api/dashboard')
    found = any(c['name'] == 'TEST渠道' for c in d3['channels'])
    check('渠道出现在 dashboard', found)
    # 清理
    test_idx = next((i for i, c in enumerate(d3['channels']) if c['name'] == 'TEST渠道'), None)
    if test_idx is not None:
        req = urllib.request.Request(BASE + f'/api/channels/{test_idx}', method='DELETE')
        urllib.request.urlopen(req)
        d4 = get('/api/dashboard')
        check('DELETE 删除渠道', not any(c['name'] == 'TEST渠道' for c in d4['channels']))
except Exception as e:
    check('Channel CRUD', False, str(e)[:80])

# ============ 第8组：导入接口健壮性 ============
print("\n=== 第8组：导入接口健壮性 ===")
try:
    # 测试空请求体
    req = urllib.request.Request(BASE + '/api/sync', data=b'{}',
        headers={'Content-Type':'application/json'}, method='POST')
    r = json.loads(urllib.request.urlopen(req).read())
    check('空 sync 不崩溃', 'success' in r, str(r))
except Exception as e:
    check('空 sync 不崩溃', False, str(e)[:80])

try:
    # 测试空 channels POST
    req = urllib.request.Request(BASE + '/api/channels', data=b'{}',
        headers={'Content-Type':'application/json'}, method='POST')
    r = json.loads(urllib.request.urlopen(req).read())
    check('空 channels POST 返回错误', r.get('error'), str(r))
except Exception as e:
    check('空 channels POST 返回错误', '缺少必要字段' in str(e), str(e)[:80])

# ============ 结果汇总 ============
print(f"\n{'='*50}")
print(f"测试完成: {sum(1 for e in errors) if errors else 0} 个失败")
if errors:
    for label, detail in errors:
        print(f"  ❌ {label}: {detail}")
else:
    print("  ✅ 全部通过!")
print(f"{'='*50}")
