"""
大明王朝1566 — SD-Turbo 影视剧风格画面生成
=============================================
直接在你的终端运行: python gen_drama_stills.py
需要: diffusers, torch, transformers, Pillow
"""

from diffusers import AutoPipelineForText2Image
from PIL import Image
import torch, json, os

os.makedirs('output/frames', exist_ok=True)

print('加载 SD-Turbo 模型...')
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sd-turbo",
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    variant="fp16"
)
if torch.cuda.is_available():
    pipe = pipe.to("cuda")
    print('  使用 GPU 加速')
else:
    print('  使用 CPU (较慢)')

# 每个场景的英文Prompt，对应大明王朝1566的11个镜头
SCENE_PROMPTS = {
    0: "Empty dragon throne in vast imperial hall, Ming Dynasty Chinese palace, aerial view looking down, dark mysterious atmosphere, cinematic lighting, historical drama film still, 4K, photorealistic, vertical composition",
    1: "Chinese emperor Jiajing in Taoist robes meditating, incense smoke swirling in dark temple, ancient Chinese palace interior, Ming Dynasty, moody mysterious atmosphere, film still from historical epic, cinematic, 4K",
    2: "Three political factions diagram, triangular power structure, ancient Chinese court politics, dark moody aesthetic, symbolic composition, Ming Dynasty, three colored forces opposing each other, cinematic",
    3: "Corrupt ancient Chinese official Yan Song and his son Yan Shifan in ornate Ming Dynasty robes, dark government hall, sinister atmosphere, historical drama still, dramatic lighting, photorealistic, 4K",
    4: "Ming Dynasty court officials Xu Jie Gao Gong Zhang Juzheng debating fiercely in ancient Chinese government hall, righteous indignation, dramatic lighting, historical drama film still, cinematic, 4K",
    5: "Elderly Ming Dynasty eunuch official Lu Fang in ornate blue robes, Forbidden City interior, wise expression, Chinese historical drama, cinematic portrait, photorealistic, 4K",
    6: "Ancient Chinese weiqi chess board with black white and red stones, three factions political game, Ming Dynasty, dark atmospheric, symbolic power struggle imagery, cinematic still life",
    7: "Chinese rural landscape Ming Dynasty, rice paddies flooded destroyed by water, dark stormy sky, dramatic disaster scene, historical epic film still, peasants suffering, cinematic, photorealistic, 4K",
    8: "Chinese emperor Jiajing in Taoist robes sitting alone in dark candlelit temple, deep contemplation, dramatic chiaroscuro lighting, Ming Dynasty, cinematic portrait, 4K masterpiece",
    9: "Chinese imperial dragon robe and jade imperial seal extreme closeup, red ink brush on ancient yellow document, Ming Dynasty, cinematic macro photography, dark atmospheric, dramatic lighting, 4K",
    10: "Modern corporate office boardroom, power hierarchy pyramid, dramatic lighting, business thriller cinematography, Chinese corporate politics, wide shot, cinematic, photorealistic"
}

# 情绪风格增强词
EMOTION_STYLE = {
    'hook':    ", high contrast, dramatic tension, intense atmosphere",
    '共鸣':     ", melancholic, emotional, atmospheric haze",
    '冲突':     ", fierce confrontation, dramatic shadows, tension",
    '亢奋':     ", intense energy, powerful, dramatic lighting",
    '转折':     ", moment of change, contemplative, turning point",
    '顿悟':     ", epiphany moment, god rays, majestic revelation",
    '激励':     ", inspiring, uplifting, heroic atmosphere",
    '行动':     ", call to action, warm inspiring light, motivational"
}

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

for i, scene in enumerate(scenes):
    visual = scene['visual']
    emotion = scene.get('emotion', 'hook')
    
    prompt = SCENE_PROMPTS.get(i, f"{visual}, Ming Dynasty Chinese historical drama, cinematic, 4K, photorealistic")
    prompt += EMOTION_STYLE.get(emotion, "")
    
    print(f'\n[{i+1}/{len(scenes)}] {visual}')
    print(f'  Prompt: {prompt[:100]}...')
    
    # 生成 (512x912 竖屏, 2步推理够用)
    image = pipe(
        prompt=prompt,
        width=512,
        height=912,
        num_inference_steps=2,
        guidance_scale=0.0,
    ).images[0]
    
    # 放大到1080x1920
    image = image.resize((1080, 1920), Image.LANCZOS)
    
    out = f'output/frames/scene_{i:02d}.png'
    image.save(out)
    size_kb = os.path.getsize(out) // 1024
    print(f'  -> {out} ({size_kb}KB) ✅')

print(f'\n========================================')
print(f'全部完成! {len(scenes)} 张影视剧风格画面')
print(f'下一步: python output/step6_compose_fast.py')
