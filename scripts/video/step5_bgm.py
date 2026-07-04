# =============================================
# step5_bgm.py - 视频流水线第5步：BGM生成
# 使用 NumPy 程序化生成氛围背景音乐 (output/bgm.wav)
# 四层音效: 低频持续音 + 风噪声纹理 + 心跳脉冲 + 过渡铃音
# =============================================
import os, json, math, struct
import numpy as np

os.makedirs('output', exist_ok=True)

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)
total_dur = scenes[-1]['end']

BGM_OUTPUT = 'output/bgm.wav'

SR = 44100
duration = 200  # long enough to cover entire video without looping
samples = int(duration * SR)

audio = np.zeros(samples, dtype=np.float64)

t = np.arange(samples, dtype=np.float64) / SR

# Layer 1: Deep ambient drone (A minor - 220Hz root)
drone1 = np.sin(2 * np.pi * 55 * t) * 0.12
drone2 = np.sin(2 * np.pi * 110 * t) * 0.08
drone3 = np.sin(2 * np.pi * 165 * t) * 0.06
drone4 = np.sin(2 * np.pi * 220 * t) * 0.04

# Slow amplitude modulation
mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)
drone = (drone1 + drone2 + drone3 + drone4) * mod * 0.6

# Layer 2: Subtle wind texture (filtered noise)
noise = np.random.randn(samples).astype(np.float64)
noise_env = np.exp(-np.abs(np.sin(2 * np.pi * 0.03 * t)) * 3)
wind = noise * noise_env * 0.015

# Layer 3: Sparse low pulses (heartbeat-like, every 8 seconds)
pulse = np.zeros(samples)
for beat_sec in np.arange(0, duration, 8):
    bi = int(beat_sec * SR)
    bl = int(0.15 * SR)
    be = min(bi + bl, samples)
    pulse_t = np.arange(be - bi, dtype=np.float64) / SR
    env = np.exp(-pulse_t * 25)
    pulse[bi:be] = np.sin(2 * np.pi * 45 * pulse_t) * env * 0.06

# Layer 4: Subtle bell-like chime at transitions
chime = np.zeros(samples)
for chime_sec in np.arange(0, duration, 16):
    ci = int(chime_sec * SR)
    cl = int(0.8 * SR)
    ce = min(ci + cl, samples)
    chime_t = np.arange(ce - ci, dtype=np.float64) / SR
    env_ch = np.exp(-chime_t * 5)
    freq = 330 + (chime_sec / duration) * 110
    chime[ci:ce] = np.sin(2 * np.pi * freq * chime_t) * env_ch * 0.03

# Mix
audio = drone + wind + pulse + chime

# Fade in/out
fade_len = int(0.5 * SR)
audio[:fade_len] *= np.linspace(0, 1, fade_len)
audio[-fade_len:] *= np.linspace(1, 0, fade_len)

# Normalize
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = audio / max_val * 0.4

audio_int = (audio * 32767).astype(np.int16)

import wave
with wave.open(BGM_OUTPUT, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(audio_int.tobytes())

print(f'[5/6] BGM: 氛围音生成 ({duration:.0f}秒, {BGM_OUTPUT})')
