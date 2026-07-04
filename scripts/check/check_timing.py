# =============================================
# check_timing.py - 视频时间轴检查工具
# 检查音频/视频时长匹配和场景时间分配
# =============================================
import json
from moviepy import AudioFileClip, VideoFileClip

with open('output/script.json','r',encoding='utf-8') as f:
    scenes=json.load(f)
print(f'Script duration: {scenes[-1]["end"]:.0f}s')

a=AudioFileClip('output/voiceover.mp3')
print(f'Audio duration: {a.duration:.1f}s')
a.close()

v=VideoFileClip('output/final.mp4')
print(f'Video duration: {v.duration:.1f}s ({v.w}x{v.h}, {v.fps}fps)')
v.close()

# Check scene durations
total=0
for i,s in enumerate(scenes):
    d=s['end']-s['start']
    total+=d
    print(f'  Scene {i}: {s["start"]:6.1f}-{s["end"]:6.1f} ({d:5.1f}s) [{s["subtitle"]}]')
print(f'Total: {total:.0f}s')
print(f'Audio/Video ratio: {a.duration / total if hasattr(a,"duration") else 0:.2f}')
