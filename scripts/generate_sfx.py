import math
import os
import random
import struct
import wave

SAMPLE_RATE = 44100


def clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))


def write_wav(path, samples):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = bytearray()
    for s in samples:
        s = int(clamp(s) * 32767)
        pcm.extend(struct.pack("<h", s))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(pcm))


def laser(duration=0.12, f0=1100, f1=420):
    n = int(duration * SAMPLE_RATE)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / max(1, n - 1)
        freq = f0 + (f1 - f0) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        env = (1.0 - t) ** 1.8
        sig = (1.0 if math.sin(phase) >= 0 else -1.0) * env * 0.5
        sig += (random.random() * 2 - 1) * 0.04 * env
        out.append(sig)
    return out


def blip(duration=0.09, freq=900):
    n = int(duration * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        env = math.exp(-8 * t)
        sig = math.sin(2 * math.pi * freq * (i / SAMPLE_RATE)) * env * 0.45
        out.append(sig)
    return out


def explosion(duration=0.26, bright=0.8):
    n = int(duration * SAMPLE_RATE)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / max(1, n - 1)
        env = (1.0 - t) ** 2.2
        freq = 120 + 80 * (1 - t)
        phase += 2 * math.pi * freq / SAMPLE_RATE
        noise = (random.random() * 2 - 1) * env * bright
        tone = math.sin(phase) * env * 0.35
        out.append((noise * 0.55 + tone) * 0.7)
    return out


def coin(duration=0.22):
    n = int(duration * SAMPLE_RATE)
    out = []
    notes = [880, 1320, 1760]
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.exp(-7 * t)
        sig = 0.0
        for idx, f in enumerate(notes):
            offset = idx * 0.035
            if t >= offset:
                tt = t - offset
                e = math.exp(-15 * tt)
                sig += math.sin(2 * math.pi * f * tt) * e * 0.35
        out.append(sig * env)
    return out


def ui_click(duration=0.05):
    n = int(duration * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        env = (1.0 - t)
        sig = math.sin(2 * math.pi * (900 + 500 * t) * (i / SAMPLE_RATE)) * env * 0.3
        out.append(sig)
    return out


def main():
    out = "assets/audio/sfx"
    write_wav(os.path.join(out, "player_shoot.wav"), laser(duration=0.1, f0=1200, f1=420))
    write_wav(os.path.join(out, "enemy_shoot.wav"), laser(duration=0.11, f0=760, f1=260))
    write_wav(os.path.join(out, "asteroid_hit.wav"), explosion(duration=0.16, bright=0.55))
    write_wav(os.path.join(out, "enemy_hit.wav"), blip(duration=0.08, freq=420))
    write_wav(os.path.join(out, "enemy_destroyed.wav"), explosion(duration=0.24, bright=0.9))
    write_wav(os.path.join(out, "pickup.wav"), coin(duration=0.2))
    write_wav(os.path.join(out, "dock.wav"), blip(duration=0.11, freq=660) + blip(duration=0.09, freq=880))
    write_wav(os.path.join(out, "sell.wav"), coin(duration=0.24))
    write_wav(os.path.join(out, "upgrade.wav"), coin(duration=0.28))
    write_wav(os.path.join(out, "pause.wav"), ui_click(duration=0.06))
    write_wav(os.path.join(out, "ui_click.wav"), ui_click(duration=0.045))
    write_wav(os.path.join(out, "player_hit.wav"), explosion(duration=0.3, bright=1.0))
    print("Generated SFX in assets/audio/sfx")


if __name__ == "__main__":
    main()
