# =============================================
# step3_voice.py - 视频流水线第3步：配音合成
# 使用 Edge TTS 将旁白文本转为语音 (output/voiceover.mp3)
# 同时生成字幕分段 (output/subtitles.json)，含关键词标记
# =============================================
import edge_tts
import asyncio
import json, os, re

os.makedirs('output', exist_ok=True)

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

narration_text = '\n'.join(s['narration'] for s in scenes)

async def tts():
    communicate = edge_tts.Communicate(
        text=narration_text,
        voice='zh-CN-YunjianNeural',
        rate='-5%',
        pitch='-3Hz'
    )
    await communicate.save('output/voiceover.mp3')

asyncio.run(tts())

# Get audio duration
try:
    from moviepy import AudioFileClip
    clip = AudioFileClip('output/voiceover.mp3')
    audio_duration = clip.duration
    clip.close()
except Exception:
    import os as _os
    size = _os.path.getsize('output/voiceover.mp3')
    audio_duration = size / (16000 * 2)

print(f'  配音时长: {audio_duration:.1f}秒')

# Generate subtitle segments with keyword marking
subtitles = []
total_chars = sum(len(s['narration']) for s in scenes)
current_time = 0.0

for scene in scenes:
    text = scene['narration']
    keywords = scene.get('keywords', [])
    scene_duration = (len(text) / total_chars) * audio_duration if total_chars > 0 else 0
    scene_end = current_time + scene_duration

    # Split into semantic segments (15-25 chars, break at punctuation)
    segments = []
    buf = ''
    for ch in text:
        buf += ch
        if ch in '。！？\n' and len(buf) >= 12:
            segments.append(buf.strip())
            buf = ''
        elif len(buf) >= 28:
            segments.append(buf.strip())
            buf = ''
    if buf.strip():
        segments.append(buf.strip())

    if not segments:
        segments = [text]

    seg_dur = scene_duration / len(segments)

    for seg in segments:
        if not seg:
            continue
        # Find which keywords appear in this segment
        seg_keywords = [kw for kw in keywords if kw in seg]

        seg_start = current_time + seg_dur * segments.index(seg)
        seg_end = seg_start + seg_dur
        if seg_end - seg_start < 0.5:
            seg_end = seg_start + 0.5

        subtitles.append({
            'text': seg,
            'keywords': seg_keywords,
            'start': round(seg_start, 2),
            'end': round(min(seg_end, scene_end), 2)
        })

    current_time = scene_end

# Fix last subtitle end
if subtitles:
    subtitles[-1]['end'] = round(audio_duration, 2)

with open('output/subtitles.json', 'w', encoding='utf-8') as f:
    json.dump(subtitles, f, ensure_ascii=False, indent=2)

rate = total_chars / audio_duration if audio_duration > 0 else 0
print(f'[3/6] 配音完成: output/voiceover.mp3')
print(f'  字幕分段: {len(subtitles)} 条 (15-25字/段)')
print(f'  语速: {rate:.1f} 字/秒')
total_kw = sum(len(s.get('keywords', [])) for s in subtitles)
print(f'  关键词标记: {total_kw} 处')
