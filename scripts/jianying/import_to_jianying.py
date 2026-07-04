import os, json, shutil, datetime

locations = [
    os.path.join(os.environ['LOCALAPPDATA'],
                 r'JianyingPro\User Data\Projects\com.lveditor.draft'),
    r'E:\工作AI\JianyingPro Drafts'
]

found_active = None

for loc in locations:
    if not os.path.isdir(loc):
        continue
    for entry in os.listdir(loc):
        full = os.path.join(loc, entry)
        if not os.path.isdir(full) or entry.startswith('.'):
            continue
        meta_file = os.path.join(full, 'draft_meta_info.json')
        if os.path.exists(meta_file):
            mtime = os.path.getmtime(meta_file)
            dt = datetime.datetime.fromtimestamp(mtime)
            resources = os.path.join(full, 'Resources')
            res_count = 0
            if os.path.isdir(resources):
                res_count = len(os.listdir(resources))
            print('[%s] %s (Resources: %d files)' % (dt.strftime('%H:%M:%S'), entry, res_count))
            # Find the most recently modified
            if found_active is None or mtime > found_active[0]:
                found_active = (mtime, full, entry)

if found_active:
    print()
    print('=== MOST RECENT PROJECT ===')
    print('Name:', found_active[2])
    print('Path:', found_active[1])

    # Copy all our assets into the Resources folder
    resources = os.path.join(found_active[1], 'Resources')
    os.makedirs(resources, exist_ok=True)

    src_dirs = [r'E:\工作AI\jianying_assets', r'E:\工作AI\charts\animated']
    copied = 0
    for src_dir in src_dirs:
        if os.path.isdir(src_dir):
            for f in os.listdir(src_dir):
                src = os.path.join(src_dir, f)
                dst = os.path.join(resources, f)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    copied += 1
    print('Copied %d files into Resources/' % copied)
    print()
    print('>>> 请切回剪映，点击「素材库」或「导入」，文件应已出现')
else:
    print('No active project found - please create a new project in 剪映 first')
    print('Then re-run this script')
