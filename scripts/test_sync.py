import json, urllib.request

BASE = 'http://localhost:8520'

def get(endpoint):
    with urllib.request.urlopen(BASE + endpoint) as r:
        return json.loads(r.read())

def post(endpoint, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + endpoint, data=body,
        headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def put(endpoint, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + endpoint, data=body,
        headers={'Content-Type':'application/json'}, method='PUT')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# Test 1: KPI roundtrip
print("Test 1: KPI roundtrip...")
put('/api/kpi', {'todayRevenue': 200000, 'occ': 80, 'adr': 650})
d = get('/api/dashboard')
assert d['kpi']['todayRevenue'] == 200000
print("  PASS: todayRevenue =", d['kpi']['todayRevenue'])

# Test 2: Empty arrays/lists should NOT overwrite server data
print("Test 2: Empty data protection...")
old_alerts = len(d.get('alerts', []))
post('/api/sync', {
    'kpi': {'todayRevenue': 300000},
    'alerts': [],
    'social': [],
    'channels': []
})
d2 = get('/api/dashboard')
assert len(d2['alerts']) == old_alerts, f"alerts: {len(d2['alerts'])} != {old_alerts}"
assert d2['kpi']['todayRevenue'] == 300000, f"kpi: {d2['kpi']['todayRevenue']}"
print("  PASS: alerts preserved =", len(d2['alerts']), ", KPI merged =", d2['kpi']['todayRevenue'])

# Test 3: KPI deep merge preserves other fields
print("Test 3: KPI deep merge...")
old_occ = d2['kpi'].get('occ', 0)
old_nps = d2['kpi'].get('nps', 0)
post('/api/sync', {'kpi': {'todayRevenue': 400000}})
d3 = get('/api/dashboard')
assert d3['kpi']['todayRevenue'] == 400000
assert d3['kpi'].get('occ') == old_occ, f"occ lost: {d3['kpi'].get('occ')} != {old_occ}"
print("  PASS: KPI deep merge, occ preserved =", d3['kpi'].get('occ'))

print("\nALL TESTS PASSED")
