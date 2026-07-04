# =============================================
# step4_srt.py - 视频流水线第4步：SRT字幕生成
# 将 subtitles.json 转为标准 SRT 字幕文件 (output/subtitles.srt)
# =============================================
import json
with open('output/subtitles.json','r',encoding='utf-8') as f:
    subs = json.load(f)
def srt_t(s):
    h=int(s//3600); m=int((s%3600)//60); sec=int(s%60); ms=int((s%1)*1000)
    return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'
with open('output/subtitles.srt','w',encoding='utf-8') as f:
    for i,sub in enumerate(subs,1):
        f.write(f'{i}\n{srt_t(sub["start"])} --> {srt_t(sub["end"])}\n{sub["text"]}\n\n')
print(f'[4/6] SRT字幕: {len(subs)} 条')
