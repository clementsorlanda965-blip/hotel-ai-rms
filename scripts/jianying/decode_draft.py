import base64, gzip, zlib, json

draft_file = r'E:\工作AI\JianyingPro Drafts\.recycle_bin\1月13日 (3)\draft_content.json'
with open(draft_file, 'r', encoding='ascii') as f:
    raw = f.read()

print('Raw size:', len(raw), 'chars')
decoded = base64.b64decode(raw)
print('Decoded size:', len(decoded), 'bytes')

for wbits in [31, 15, -15, 47, 16+gzip.FCOMMENT]:
    try:
        result = zlib.decompress(decoded, wbits)
        print('zlib wbits=%d: SUCCESS (%d bytes)' % (wbits, len(result)))
        data = json.loads(result)
        print('JSON keys:', list(data.keys())[:20])
        if 'tracks' in data:
            print('Tracks:', len(data['tracks']))
        if 'materials' in data:
            for k, v in data['materials'].items():
                if isinstance(v, list):
                    print('materials.%s: %d items' % (k, len(v)))
                elif isinstance(v, dict):
                    print('materials.%s: %d keys' % (k, len(v)))
            # Show first video material as example
            if 'videos' in data['materials'] and len(data['materials']['videos']) > 0:
                vid = data['materials']['videos'][0]
                print('\nSample video material:')
                print(json.dumps(vid, ensure_ascii=False, indent=2)[:500])
        break
    except Exception as e:
        print('zlib wbits=%d: %s' % (wbits, str(e)[:60]))

# Also try gzip
try:
    result = gzip.decompress(decoded)
    print('\ngzip: SUCCESS (%d bytes)' % len(result))
    data = json.loads(result)
    print('JSON keys:', list(data.keys())[:20])
except Exception as e:
    print('\ngzip: %s' % str(e)[:60])
