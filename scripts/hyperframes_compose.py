# -*- coding: utf-8 -*-
"""
HyperFrames 合成桥接脚本
读取现有管线输出 (script.json, frames, voiceover, subtitles)
生成 HyperFrames HTML 合成项目 → hyperframes render 出片
"""
import json, os, shutil, subprocess, sys, platform

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')

HF_PROJECT = r'C:\temp_hf\hyperframes'  # 必须用纯ASCII路径，HyperFrames因中文路径启动Chrome失败
HF_ASSETS = os.path.join(HF_PROJECT, 'assets')
HF_FRAMES = os.path.join(HF_ASSETS, 'frames')
HF_COMPOS = os.path.join(HF_PROJECT, 'compositions')
VIDEO_OUT = os.path.join(BASE_DIR, 'outputs', 'video')

# 情绪→颜色映射
EMOTION_COLORS = {
    'hook': '#dc3232', '共鸣': '#648cdc', '冲突': '#dc501e',
    '转折': '#dcb428', '亢奋': '#f02828', '顿悟': '#50a0c8',
    '梗慨': '#a064c8', '激励': '#3cc864', '悬念': '#e08a30'
}

EMOTION_LABELS = {
    'hook': '开篇暴击', '共鸣': '情绪共鸣', '冲突': '矛盾爆发',
    '转折': '剧情转折', '亢奋': '高潮名场面', '顿悟': '深度解构',
    '梗慨': '权力真相', '激励': '结尾升华', '悬念': '悬疑铺垫'
}

TREATMENTS = ['full', 'zoom', 'blur']


def read_inputs():
    with open(os.path.join(OUTPUT_DIR, 'script.json'), 'r', encoding='utf-8') as f:
        scenes = json.load(f)
    subs_path = os.path.join(OUTPUT_DIR, 'subtitles.json')
    subs = []
    if os.path.exists(subs_path):
        with open(subs_path, 'r', encoding='utf-8') as f:
            subs = json.load(f)
    voiceover = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    bgm_path = os.path.join(OUTPUT_DIR, 'bgm.wav')
    return scenes, subs, voiceover, bgm_path


def prepare_assets(scenes, voiceover, bgm_path):
    os.makedirs(HF_FRAMES, exist_ok=True)
    os.makedirs(HF_ASSETS, exist_ok=True)

    for s in scenes:
        src = os.path.join(OUTPUT_DIR, 'frames', f'scene_{s["id"]:02d}.png')
        if os.path.exists(src):
            dst = os.path.join(HF_FRAMES, f'scene_{s["id"]:02d}.png')
            shutil.copy2(src, dst)

    for src_path, name in [(voiceover, 'voiceover.mp3'), (bgm_path, 'bgm.wav')]:
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(HF_ASSETS, name))

    gsap_src = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'hyperframes', 'assets', 'gsap.min.js')
    if os.path.exists(gsap_src):
        shutil.copy2(gsap_src, os.path.join(HF_ASSETS, 'gsap.min.js'))
    else:
        print('警告: 找不到 gsap.min.js，请先下载')
        print(f'  curl.exe -s https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js -o "{gsap_src}"')


def find_scene_for_time(scenes, t):
    for s in scenes:
        if s['start'] <= t < s['end']:
            return s
    return scenes[-1]


def extract_headline(sub):
    kw = sub.get('keywords', [])
    kw_clean = [k for k in kw if k.strip()]
    if kw_clean:
        return kw_clean[0]
    txt = sub['text']
    import re
    parts = re.split(r'[，。！？；、——：]', txt)
    parts = [p.strip() for p in parts if p.strip()]
    if parts and len(parts[-1]) >= 2:
        return parts[-1]
    return txt[-6:] if len(txt) > 6 else txt


def segment_img_html(sub, idx, img_idx, treatment, total_dur):
    seg_start = max(0, sub['start'] - 0.3)
    seg_end = min(total_dur, sub['end'] + 0.3)
    dur = seg_end - seg_start
    return f'''  <div class="clip seg-img-clip {treatment}" id="imgc-{idx}"
    data-start="{seg_start:.1f}" data-duration="{dur:.1f}" data-track-index="0">
    <div class="seg-img-wrap">
      <img class="seg-img" id="si-{idx}"
        src="assets/frames/scene_{img_idx:02d}.png" />
      <div class="seg-vignette"></div>
    </div>
  </div>'''


def segment_text_html(sub, idx, emotion):
    esc = sub['text'].replace("'", "\\'").replace('"', '&quot;')
    headline = extract_headline(sub)
    dur = sub['end'] - sub['start']
    c = EMOTION_COLORS.get(emotion, '#888')
    return f'''  <div class="clip seg-txt-clip" id="txtc-{idx}"
    data-start="{sub['start']:.1f}" data-duration="{dur:.1f}" data-track-index="1">
    <div class="seg-headline-wrapper">
      <div class="seg-headline" id="hl-{idx}">{headline}</div>
    </div>
    <div class="seg-caption" id="cp-{idx}">{esc}</div>
    <div class="seg-badge" id="bd-{idx}" style="color:{c}">● {EMOTION_LABELS.get(emotion, emotion)}</div>
    <div class="seg-accent" style="background:{c}"></div>
  </div>'''


def generate_html(scenes, subs, has_bgm):
    dur_total = scenes[-1]['end'] if scenes else 50
    total_subs = len(subs)

    img_html_list = []
    txt_html_list = []
    gsap_lines = ['    const tl = gsap.timeline({paused: true});']

    for i, sub in enumerate(subs):
        scene = find_scene_for_time(scenes, sub['start'])
        img_idx = scene['id']
        emotion = scene['emotion']
        treatment = TREATMENTS[i % 3]
        dur = sub['end'] - sub['start']
        is_first = (i == 0)
        is_last = (i == total_subs - 1)

        img_html_list.append(segment_img_html(sub, i, img_idx, treatment, dur_total))
        txt_html_list.append(segment_text_html(sub, i, emotion))

        # Image crossfade
        if is_first:
            gsap_lines.append(f'    tl.set("#si-{i}", {{opacity: 1}}, 0);')
        else:
            gsap_lines.append(f'    tl.fromTo("#si-{i}", {{opacity: 0}}, {{opacity: 1, duration: 0.3, ease: "power2.out"}}, {sub["start"] - 0.3:.1f});')
        if not is_last:
            gsap_lines.append(f'    tl.to("#si-{i}", {{opacity: 0, duration: 0.3, ease: "power2.in"}}, {sub["end"] - 0.3:.1f});')

        # Zoom treatment: slow scale up
        if treatment == 'zoom':
            gsap_lines.append(f'    tl.fromTo("#si-{i}", {{scale: 1.0}}, {{scale: 1.25, duration: {dur:.1f}, ease: "none"}}, {sub["start"]:.1f});')

        # Headline: scale + slide up
        gsap_lines.append(f'    tl.fromTo("#hl-{i}",')
        gsap_lines.append(f'      {{opacity: 0, y: 40, scale: 0.8}},')
        gsap_lines.append(f'      {{opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "back.out(1.7)"}},')
        gsap_lines.append(f'      {sub["start"] + 0.1:.1f});')
        gsap_lines.append(f'    tl.to("#hl-{i}", {{opacity: 0, scale: 0.9, duration: 0.2, ease: "power2.in"}}, {sub["end"] - 0.2:.1f});')

        # Caption: fade in
        gsap_lines.append(f'    tl.fromTo("#cp-{i}", {{opacity: 0}}, {{opacity: 1, duration: 0.3, ease: "power2.out"}}, {sub["start"] + 0.25:.1f});')
        gsap_lines.append(f'    tl.to("#cp-{i}", {{opacity: 0, duration: 0.15, ease: "power2.in"}}, {sub["end"] - 0.15:.1f});')

        # Badge: slide from left
        gsap_lines.append(f'    tl.fromTo("#bd-{i}", {{opacity: 0, x: -15}}, {{opacity: 0.6, x: 0, duration: 0.25, ease: "power2.out"}}, {sub["start"] + 0.3:.1f});')
        gsap_lines.append(f'    tl.to("#bd-{i}", {{opacity: 0, duration: 0.1}}, {sub["end"] - 0.1:.1f});')

        # Accent bar: slide in
        gsap_lines.append(f'    tl.fromTo("#txtc-{i} .seg-accent", {{scaleX: 0}}, {{scaleX: 1, duration: 0.35, ease: "power2.out", transformOrigin: "left center"}}, {sub["start"] + 0.15:.1f});')

    gsap_lines.append(f'')
    gsap_lines.append(f'    tl.set({{}}, {{}}, {dur_total});')

    gsap_str = '\n    '.join(gsap_lines).replace('\n    \n', '\n')

    img_html = '\n'.join(img_html_list)
    txt_html = '\n'.join(txt_html_list)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>抖音风格解说</title>
<script src="assets/gsap.min.js"></script>
<style>
  @font-face {{
    font-family: "CN";
    src: local("Microsoft YaHei"), local("SimHei"), local("Noto Sans SC");
    font-weight: normal;
  }}
  @font-face {{
    font-family: "CN";
    src: local("Microsoft YaHei Bold"), local("Microsoft YaHei UI Bold"), local("SimHei");
    font-weight: bold;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 100%; height: 100%; overflow: hidden; background: #0a0a0e; }}

  #root {{
    position: relative;
    width: 1080px;
    height: 1920px;
    overflow: hidden;
    background: #0a0a0e;
  }}

  .seg-img-clip {{ position: absolute; inset: 0; }}
  .seg-img-wrap {{ position: absolute; inset: 0; overflow: hidden; }}
  .seg-img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .seg-vignette {{
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.65) 100%);
    pointer-events: none;
  }}

  .seg-txt-clip {{
    position: absolute; inset: 0;
    pointer-events: none;
  }}

  .seg-headline-wrapper {{
    position: absolute;
    left: 50%; top: 40%;
    transform: translate(-50%, -50%);
    width: 88%;
    text-align: center;
    z-index: 2;
  }}
  .seg-headline {{
    font-family: "CN", sans-serif;
    font-weight: bold;
    font-size: 72px;
    color: #ffffff;
    text-shadow:
      0 2px 12px rgba(0,0,0,0.5),
      0 0 40px rgba(0,0,0,0.3);
    line-height: 1.3;
    letter-spacing: 6px;
  }}

  .seg-caption {{
    position: absolute;
    bottom: 140px;
    left: 50px;
    right: 50px;
    text-align: center;
    font-family: "CN", sans-serif;
    font-size: 30px;
    font-weight: normal;
    color: rgba(255,255,255,0.75);
    text-shadow: 0 1px 10px rgba(0,0,0,0.4);
    line-height: 1.5;
    letter-spacing: 2px;
    z-index: 2;
  }}

  .seg-badge {{
    position: absolute;
    top: 50px;
    left: 40px;
    font-family: "CN", sans-serif;
    font-size: 18px;
    letter-spacing: 3px;
    opacity: 0.6;
    z-index: 2;
    text-shadow: 0 1px 6px rgba(0,0,0,0.3);
  }}

  .seg-accent {{
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 4px;
    z-index: 2;
    transform-origin: left center;
  }}

  .blur .seg-img {{ filter: blur(20px) brightness(0.6); }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="1080" data-height="1920">

{img_html}

{txt_html}

  <audio class="clip" id="voiceover"
    data-start="0" data-duration="{dur_total:.1f}" data-track-index="3"
    src="assets/voiceover.mp3" preload="auto">
  </audio>
  {f'''
  <audio class="clip" id="bgm"
    data-start="0" data-duration="{dur_total:.1f}" data-track-index="4"
    src="assets/bgm.wav" preload="auto" data-volume="0.12">
  </audio>''' if has_bgm else ''}

</div>

<script>
  window.__timelines = window.__timelines || {{}};

  {gsap_str}

  window.__timelines["main"] = tl;
</script>
</body>
</html>'''
    return html


def write_project(scenes, subs, has_bgm):
    os.makedirs(HF_PROJECT, exist_ok=True)
    os.makedirs(HF_COMPOS, exist_ok=True)

    # Index.html
    html = generate_html(scenes, subs, has_bgm)
    with open(os.path.join(HF_PROJECT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)

    # meta.json
    meta = {
        "name": "hyperframes-composition",
        "id": "main",
        "createdAt": None
    }
    with open(os.path.join(HF_PROJECT, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f'项目生成: {HF_PROJECT}')
    print(f'  场景: {len(scenes)}, 字幕: {len(subs)}')


def render():
    os.makedirs(VIDEO_OUT, exist_ok=True)
    output_path = os.path.join(VIDEO_OUT, 'daming_ep1_hf.mp4')

    if sys.platform == 'win32':
        hf_cmd = 'hyperframes.cmd'
    else:
        hf_cmd = 'hyperframes'

    cmd = [hf_cmd, 'render', '--output', output_path, '--quality', 'draft', '--no-browser-gpu']

    print(f'渲染: {output_path}')
    print('请耐心等待 HyperFrames 截帧渲染...')

    env = dict(os.environ)
    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    if os.path.exists(chrome_path):
        env['HYPERFRAMES_BROWSER_PATH'] = chrome_path

    proc = subprocess.Popen(
        cmd, cwd=HF_PROJECT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1
    )
    for line in proc.stdout:
        try:
            decoded = line.decode('utf-8', errors='replace').strip()
            if decoded:
                print(f'  {decoded}')
        except:
            pass
    proc.wait()

    if proc.returncode == 0:
        print(f'完成: {output_path}')
        return True
    else:
        print(f'渲染失败 (code={proc.returncode})')
        return False


def main():
    scenes, subs, voiceover, bgm_path = read_inputs()

    if not os.path.exists(voiceover):
        print(f'错误: 找不到配音文件 {voiceover}')
        print('请先运行 pipeline.py')
        return False

    has_bgm = os.path.exists(bgm_path)

    print(f'输入: {len(scenes)} 场景, {len(subs)} 字幕, 配音: {os.path.getsize(voiceover)/1024/1024:.1f}MB')

    prepare_assets(scenes, voiceover, bgm_path)
    write_project(scenes, subs, has_bgm)
    return render()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
