import json, urllib.request, urllib.parse, os, time

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

os.makedirs('output/frames', exist_ok=True)

STYLE = "Ming Dynasty historical drama cinematography, ancient Chinese palace, dark moody atmosphere, volumetric lighting, film grain, photorealistic, 9:16 vertical composition, trending on artstation"

for i, scene in enumerate(scenes):
    visual = scene['visual']
    emotion = scene['emotion']
    
    # Build prompt
    prompt = f"{visual}, {STYLE}"
    if emotion == 'hook':
        prompt += ", dramatic tension, high contrast"
    elif emotion in ('冲突', '亢奋'):
        prompt += ", intense dramatic lighting, strong shadows"
    elif emotion in ('顿悟', '激励'):
        prompt += ", epic cinematic, god rays, majestic"
    elif emotion == '行动':
        prompt += ", warm inspiring light, call to action"
    
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={42+i}"
    
    out_path = f'output/frames/scene_{i:02d}.png'
    print(f'  [{i+1}/{len(scenes)}] {visual[:30]}...')
    
    try:
        urllib.request.urlretrieve(url, out_path)
        time.sleep(1)  # Rate limit
        size_kb = os.path.getsize(out_path) / 1024
        print(f'    -> {size_kb:.0f}KB ✅')
    except Exception as e:
        print(f'    -> FAILED: {e}')

print(f'\n画面生成完成: output/frames/')
