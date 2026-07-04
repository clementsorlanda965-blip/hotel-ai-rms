import json, re
from moviepy import AudioFileClip

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

# Get actual audio duration
audio = AudioFileClip('output/voiceover.mp3')
audio_duration = audio.duration
audio.close()

def smart_split(text, max_chars=12):
    """按标点自然断句，优先在。！？处切，其次在，、处切"""
    # 先按句末标点切
    raw = re.split(r'(?<=[。！？])', text)
    result = []
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(chunk) <= max_chars:
            result.append(chunk)
        else:
            # 按逗号再切
            sub = re.split(r'(?<=[，、；：])', chunk)
            cur = ''
            for s in sub:
                if len(cur) + len(s) <= max_chars:
                    cur += s
                else:
                    if cur:
                        result.append(cur.strip())
                    cur = s
            if cur:
                result.append(cur.strip())
    # 最终兜底：太长的强行切
    final = []
    for r in result:
        if len(r) > max_chars * 2:
            for i in range(0, len(r), max_chars):
                final.append(r[i:i+max_chars])
        else:
            final.append(r)
    return final

# Rebuild subtitles with smart split
subtitles = []
total_chars = sum(len(s['narration']) for s in scenes)
current_time = 0.0

for scene in scenes:
    text = scene['narration']
    scene_duration = (len(text) / total_chars) * audio_duration
    scene_end = current_time + scene_duration
    
    segs = smart_split(text)
    seg_dur = scene_duration / len(segs) if segs else 0
    
    for j, seg in enumerate(segs):
        seg_start = current_time + j * seg_dur
        seg_end = seg_start + seg_dur
        if seg_end - seg_start < 0.4:
            seg_end = seg_start + 0.4
        subtitles.append({
            'text': seg,
            'start': round(seg_start, 2),
            'end': round(min(seg_end, scene_end), 2)
        })
    
    current_time = scene_end

if subtitles:
    subtitles[-1]['end'] = round(audio_duration, 2)

with open('output/subtitles.json', 'w', encoding='utf-8') as f:
    json.dump(subtitles, f, ensure_ascii=False, indent=2)

# Report
print(f'字幕修复完成: {len(subtitles)} 条 (原112条)')
for i, s in enumerate(subtitles[:10]):
    print(f'  [{s["start"]:5.1f}-{s["end"]:5.1f}] {s["text"]}')
print('  ...')
