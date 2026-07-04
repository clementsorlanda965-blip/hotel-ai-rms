import json, urllib.request, os, time

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

os.makedirs('output/frames', exist_ok=True)

STYLE = "Ming Dynasty historical drama cinematography, ancient Chinese palace, dark moody atmosphere, volumetric lighting, film grain, photorealistic"

for i, scene in enumerate(scenes):
    visual = scene['visual']
    prompt_en = f"{visual}, {STYLE}, 9:16 vertical"
    encoded = urllib.parse.quote(prompt_en)
    
    # Try multiple free endpoints
    urls = [
        f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={42+i}",
        f"https://pollinations.ai/p/{encoded}?width=1080&height=1920",
    ]
    
    out_path = f'output/frames/scene_{i:02d}.png'
    success = False
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/*'
            })
            data = urllib.request.urlopen(req, timeout=60).read()
            if len(data) > 1000:
                with open(out_path, 'wb') as f:
                    f.write(data)
                size_kb = len(data) / 1024
                print(f'  [{i+1}/{len(scenes)}] {visual[:25]} -> {size_kb:.0f}KB OK')
                success = True
                break
        except Exception as e:
            continue
    
    if not success:
        print(f'  [{i+1}/{len(scenes)}] {visual[:25]} -> ALL FAILED')
    else:
        time.sleep(2)

print(f'\nDone: output/frames/')
