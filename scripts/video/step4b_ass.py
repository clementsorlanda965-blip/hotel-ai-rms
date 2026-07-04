# =============================================
# step4b_ass.py - 视频流水线第4B步：ASS高级字幕生成
# 将 subtitles.json 转为 ASS 字幕格式 (output/subtitles.ass)
# 支持关键词黄色高亮显示
# =============================================
import json
import math

with open('output/subtitles.json', 'r', encoding='utf-8') as f:
    subs = json.load(f)

# Generate ASS subtitle file with yellow keyword highlighting
# ASS format: {\c&HBBGGRR&} for color (BGR hex, so yellow #FFD700 -> &H00D7FF&)

ass_lines = []
ass_lines.append("[Script Info]")
ass_lines.append("Title: 大明王朝1566解说")
ass_lines.append("ScriptType: v4.00+")
ass_lines.append("Collisions: Normal")
ass_lines.append("PlayResX: 720")
ass_lines.append("PlayResY: 1280")
ass_lines.append("")
ass_lines.append("[V4+ Styles]")
ass_lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
ass_lines.append("Style: Default,Microsoft YaHei,38,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,8,10,10,140,1")
ass_lines.append("")

ass_lines.append("[Events]")
ass_lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

for i, sub in enumerate(subs):
    text = sub['text']
    keywords = sub.get('keywords', [])
    start = sub['start']
    end = sub['end']

    def fmt_time(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        cs = int((s - int(s)) * 100)
        return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"

    # Split text at keywords and wrap in yellow color tags
    remaining = text
    result_parts = []
    while remaining:
        best_pos = len(remaining)
        best_kw = None
        for kw in keywords:
            pos = remaining.find(kw)
            if pos != -1 and pos < best_pos:
                best_pos = pos
                best_kw = kw
        if best_kw is not None and best_pos < len(remaining):
            if best_pos > 0:
                result_parts.append(remaining[:best_pos])
            result_parts.append(f"{{\\c&H00D7FF&}}{best_kw}{{\\c}}")
            remaining = remaining[best_pos + len(best_kw):]
        else:
            result_parts.append(remaining)
            remaining = ''

    ass_text = ''.join(result_parts)

    ass_lines.append(
        f"Dialogue: 0,{fmt_time(start)},{fmt_time(end)},Default,,0,0,0,,{ass_text}"
    )

with open('output/subtitles.ass', 'w', encoding='utf-8') as f:
    f.write('\n'.join(ass_lines))

print(f'[4b/6] ASS字幕生成完成: {len(subs)} 条 (关键词已标黄)')
