from diffusers import AutoPipelineForText2Image
from PIL import Image
import torch, json, os

os.makedirs('output/frames', exist_ok=True)

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

print('Loading SD-Turbo model...')
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sd-turbo",
    torch_dtype=torch.float32,
    variant="fp16"
)
print('Model loaded. Generating images...')

# Scene-specific prompts (English for SD quality)
PROMPTS = [
    "Empty dragon throne room, ancient Chinese imperial palace, Ming Dynasty, aerial view, dark atmospheric, cinematic lighting, historical drama film still, 4K masterpiece",
    "Chinese emperor in Taoist temple, incense smoke swirling, ancient palace interior, Ming Dynasty Jiajing, mysterious moody atmosphere, film still from historical epic, cinematic",
    "Three political factions diagram, ancient Chinese court power structure, dark moody aesthetic, symbolic, Ming Dynasty politics, cinematic composition",
    "Corrupt Ming Dynasty official and his son in ancient Chinese government hall, dark sinister atmosphere, historical drama still, Yan Song, ornate robes, cinematic lighting",
    "Ming Dynasty court officials debating in ancient Chinese government hall, Xu Jie Gao Gong Zhang Juzheng, intense dramatic lighting, historical drama film still, cinematic",
    "Ming Dynasty eunuch official in ornate blue robes, Forbidden City interior, Chinese historical drama, cinematic lighting, wise elderly man, imperial palace",
    "Ancient Chinese chess weiqi board with three colored pieces, strategic political game, dark moody atmosphere, symbolic imagery, Ming Dynasty, cinematic still life",
    "Chinese rural landscape Ming Dynasty, rice paddies destroyed by flood water, dramatic disaster scene, dark sky, historical epic film still, cinematic",
    "Chinese emperor in Taoist robes sitting alone in dark temple, deep contemplation, dramatic chiaroscuro lighting, Ming Dynasty Jiajing, cinematic portrait, 4K",
    "Chinese imperial dragon robe and jade seal closeup, red ink brush on ancient document, Ming Dynasty, cinematic macro photography, dark atmospheric, 4K",
    "Modern corporate office meeting room, power hierarchy, dramatic lighting, business thriller cinematography, power struggle metaphor, cinematic wide shot"
]

for i, scene in enumerate(scenes):
    prompt = PROMPTS[i]
    print(f'  [{i+1}/{len(scenes)}] {scene["visual"][:25]}...')
    
    # Generate at 512x912 (9:16), 2 steps for speed
    image = pipe(
        prompt=prompt,
        width=512,
        height=912,
        num_inference_steps=2,
        guidance_scale=0.0,
    ).images[0]
    
    # Upscale to 1080x1920
    image = image.resize((1080, 1920), resample=Image.LANCZOS)
    
    out_path = f'output/frames/scene_{i:02d}.png'
    image.save(out_path)
    print(f'    -> saved ({os.path.getsize(out_path)//1024}KB)')

print(f'\nDone: {len(scenes)} cinematic images in output/frames/')
