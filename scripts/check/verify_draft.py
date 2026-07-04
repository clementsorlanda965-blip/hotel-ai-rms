import os, json

draft_root = os.path.join(os.environ['LOCALAPPDATA'],
                          r'JianyingPro\User Data\Projects\com.lveditor.draft')

with open(os.path.join(draft_root, 'root_meta_info.json'), 'r', encoding='utf-8') as f:
    meta = json.load(f)

print('=== 剪映草稿箱注册表 ===')
print('draft_ids:', meta.get('draft_ids', '?'))
print('all_draft_store:', len(meta.get('all_draft_store', [])), 'entries')
for entry in meta.get('all_draft_store', []):
    print('  -', entry.get('name', '?'), ' (id=', entry.get('id', '?'), ')')

print()
for entry in os.listdir(draft_root):
    full = os.path.join(draft_root, entry)
    if os.path.isdir(full) and not entry.startswith('.'):
        print('===', entry, '===')
        for item in sorted(os.listdir(full)):
            item_path = os.path.join(full, item)
            if os.path.isfile(item_path):
                print('  [FILE]', item, '(', os.path.getsize(item_path), 'bytes)')
            elif os.path.isdir(item_path):
                sub_count = len(os.listdir(item_path))
                print('  [DIR] ', item, '/ (', sub_count, 'files)')
print()
print('=== 请检查剪映草稿箱 ===')
