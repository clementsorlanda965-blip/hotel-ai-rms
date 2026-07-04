"""
大明王朝1566 — 影视剧实景画面 V2 (高精度Prompt)
每个镜头的prompt都精确描述剧中人物、场景、氛围
"""

from diffusers import AutoPipelineForText2Image
from PIL import Image
import torch, json, os

os.makedirs('output/frames', exist_ok=True)

print('加载 SD-Turbo...')
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sd-turbo",
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    variant="fp16"
)
if torch.cuda.is_available():
    pipe = pipe.to("cuda")
    print('  GPU 加速')
else:
    print('  CPU (较慢)')

# 高精度影视剧prompt — 每个镜头精确描述
PROMPTS = [
    # 0: 龙椅空荡朝堂俯瞰
    "A grand empty dragon throne in a vast dark imperial hall, Ming Dynasty Chinese palace, dramatic aerial view from above, ornate golden decorations, eerie emptiness, cinematic lighting, historical drama cinematography, photorealistic, 4K, vertical",

    # 1: 嘉靖炼丹道观
    "Chinese emperor in elaborate golden dragon robes meditating in an ancient Taoist temple, swirling incense smoke, candlelit dark room, Ming Dynasty Jiajing emperor, mysterious sacred atmosphere, cinematic portrait, historical epic film still, 4K, photorealistic",

    # 2: 三足鼎立权力结构
    "Three ancient Chinese officials in different colored robes standing in triangular formation in a dark palace hall, representing three political factions, Ming Dynasty court intrigue, dramatic lighting from above, symbolic power struggle, cinematic, 4K, photorealistic",

    # 3: 严嵩父子权倾朝野
    "Two corrupt Ming Dynasty officials, elderly man and younger man in dark ornate robes, scheming in a shadowy ancient Chinese government hall, sinister expressions, Yan Song and Yan Shifan, dramatic side lighting, historical drama film still, 4K, photorealistic",

    # 4: 清流党朝堂辩论
    "Three righteous Ming Dynasty officials in blue official robes arguing passionately in an ancient Chinese court, pointing and debating, Xu Jie Gao Gong Zhang Juzheng, dramatic warm lighting, historical epic film still, cinematic, 4K, photorealistic",

    # 5: 司礼监太监
    "An elderly wise Ming Dynasty eunuch in ornate blue silk robes standing in the Forbidden City, gentle expression, holding official documents, loyal servant Lu Fang, soft cinematic lighting, Chinese historical drama portrait, 4K, photorealistic",

    # 6: 三方博弈
    "Closeup of an ancient Chinese weiqi go board with black white and red stones forming a tense standoff, candlelit study room, political strategy metaphor, Ming Dynasty, dark atmospheric, cinematic still life photography, 4K",

    # 7: 毁堤淹田浙江
    "Flooded rice paddies in ancient China, peasants in Ming Dynasty clothing struggling in muddy water, dark storm clouds overhead, destroyed dams, dramatic disaster scene, historical epic cinematography, photorealistic, 4K, vertical",

    # 8: 嘉靖独坐道观
    "Chinese emperor Jiajing in simple Taoist robes sitting alone in a dark temple, single candle illuminating his contemplative face, intense chiaroscuro lighting, Ming Dynasty, moment of epiphany, cinematic masterpiece portrait, 4K, photorealistic",

    # 9: 龙袍玉玺朱笔
    "Extreme closeup of imperial yellow dragon robe fabric texture and a jade seal with red ink, a calligraphy brush writing on ancient Chinese document, Ming Dynasty, macro photography, dramatic lighting, cinematic, 4K, photorealistic",

    # 10: 现代办公室权力
    "Modern corporate glass boardroom with executives sitting around a long table, power struggle atmosphere, dramatic lighting through blinds, cinematic wide shot, business thriller style, photorealistic, 4K"
]

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

for i, scene in enumerate(scenes):
    prompt = PROMPTS[i]
    visual = scene['visual']
    emotion = scene.get('emotion', '')
    
    # 情绪增强
    if emotion == 'hook':
        prompt += ", high contrast, dramatic tension"
    elif emotion == '冲突':
        prompt += ", sharp shadows, intense confrontation"
    elif emotion == '顿悟':
        prompt += ", god rays, majestic revelation"
    elif emotion == '激励':
        prompt += ", heroic atmosphere, epic scale"
    
    print(f'[{i+1}/11] {visual}')
    
    image = pipe(prompt=prompt, width=512, height=912,
                 num_inference_steps=3 if torch.cuda.is_available() else 2,
                 guidance_scale=0.0).images[0]
    
    image = image.resize((1080, 1920), Image.LANCZOS)
    out = f'output/frames/scene_{i:02d}.png'
    image.save(out)
    print(f'  -> {os.path.getsize(out)//1024}KB')

print('\n✅ 11张影视剧画面完成!')
