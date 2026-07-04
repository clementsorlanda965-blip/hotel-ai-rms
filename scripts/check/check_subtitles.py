# =============================================
# check_subtitles.py - 字幕自检工具
# 检查字幕时间轴、时长、文字长度等常见问题
# =============================================
import json

with open('output/subtitles.json', 'r', encoding='utf-8') as f:
    subs = json.load(f)

print(f'=== 字幕自检 ({len(subs)}条) ===\n')

# Check for issues
issues = []
prev_end = 0

for i, s in enumerate(subs[:20]):
    dur = s['end'] - s['start']
    gap = s['start'] - prev_end
    flag = ''
    if dur < 0.3:
        flag += ' [太短]'
    if dur > 5:
        flag += ' [太长]'
    if gap > 1.0:
        flag += f' [间隔{gap:.1f}s]'
    if len(s['text']) > 8:
        flag += ' [超8字]'
    if s['start'] < prev_end - 0.1:
        flag += ' [时间重叠]'
    print(f'  [{s["start"]:6.1f}-{s["end"]:6.1f}s | {dur:4.1f}s] {s["text"]}{flag}')
    if flag:
        issues.append(f'#{i} {flag}')
    prev_end = s['end']

if len(subs) > 20:
    print(f'  ...省略 {len(subs)-20} 条 ...')
    # Quick scan remaining
    for i, s in enumerate(subs[20:], 20):
        if len(s['text']) > 8:
            issues.append(f'#{i} [超8字] {s["text"]}')
        if s['end'] - s['start'] > 5:
            issues.append(f'#{i} [太长{s["end"]-s["start"]:.1f}s]')

print(f'\n=== 问题汇总: {len(issues)} 个 ===')
for iss in issues:
    print(f'  {iss}')
if not issues:
    print('  无问题')

# Check last subtitle timing
print(f'\n总时长: {subs[-1]["end"]:.1f}秒')
