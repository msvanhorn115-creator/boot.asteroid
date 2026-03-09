import math
import os
import random
import struct
import wave

SAMPLE_RATE = 44100


def clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))


def midi_to_hz(midi_note):
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def osc_square(phase):
    return 1.0 if math.sin(phase) >= 0 else -1.0


def osc_triangle(phase):
    return (2.0 / math.pi) * math.asin(math.sin(phase))


def osc_saw(phase):
    return 2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0


def adsr(t, a, d, s, r, note_len):
    if t < 0 or t > note_len:
        return 0.0
    if t < a:
        return t / max(1e-6, a)
    t -= a
    if t < d:
        return 1.0 - (1.0 - s) * (t / max(1e-6, d))
    sustain_len = max(0.0, note_len - (a + d + r))
    if t < sustain_len:
        return s
    t -= sustain_len
    if t < r:
        return s * (1.0 - t / max(1e-6, r))
    return 0.0


def render_loop(path, bpm, bars, progression, style_seed=0, intensity=1.0, tension=0.5):
    random.seed(style_seed)

    beats_per_bar = 4
    seconds_per_beat = 60.0 / bpm
    bar_len = beats_per_bar * seconds_per_beat
    total_len = bars * bar_len
    total_samples = int(total_len * SAMPLE_RATE)

    # Build note events: (start_time, midi_note, duration, voice)
    # voice: 0=bass, 1=lead, 2=arp
    events = []

    # Chords in midi root notes (minor-ish arcade mood)
    for bar in range(bars):
        root = progression[bar % len(progression)]
        bar_start = bar * bar_len

        # Bass: eighth-note pulse
        for step in range(8):
            st = bar_start + step * (seconds_per_beat / 2.0)
            dur = seconds_per_beat * 0.45
            note = root - 24 + (12 if step in (3, 7) else 0)
            events.append((st, note, dur, 0))

        # Arp: 16th-note movement
        arp_pattern = [0, 3, 7, 10, 7, 3, 12, 10]
        for step in range(16):
            st = bar_start + step * (seconds_per_beat / 4.0)
            dur = seconds_per_beat * 0.22
            note = root + arp_pattern[step % len(arp_pattern)]
            events.append((st, note, dur, 2))

        # Lead motif on beats 1 and 3, then response
        motif = [12, 10, 7, 3]
        motif_start = bar_start + (seconds_per_beat * (0.0 if bar % 2 == 0 else 0.5))
        for i, interval in enumerate(motif):
            st = motif_start + i * (seconds_per_beat * 0.5)
            dur = seconds_per_beat * (0.35 if i < 2 else 0.25)
            note = root + interval + (12 if bar % 4 == 3 and i == 0 else 0)
            events.append((st, note, dur, 1))

    # Pre-index events by start sample for efficiency
    indexed = []
    for st, note, dur, voice in events:
        indexed.append((int(st * SAMPLE_RATE), note, dur, voice))

    # Global pulse and light filtered noise hats
    pcm = bytearray()
    max_amp = 0.82

    active = []
    event_ptr = 0
    indexed.sort(key=lambda x: x[0])

    for i in range(total_samples):
        t = i / SAMPLE_RATE

        while event_ptr < len(indexed) and indexed[event_ptr][0] <= i:
            st_samp, note, dur, voice = indexed[event_ptr]
            active.append((t, note, dur, voice, random.random() * 6.28))
            event_ptr += 1

        mix = 0.0
        still_active = []

        for note_start, note, dur, voice, phase_offset in active:
            nt = t - note_start
            if nt < 0 or nt > dur:
                continue

            freq = midi_to_hz(note)
            phase = 2.0 * math.pi * freq * nt + phase_offset

            if voice == 0:  # bass
                env = adsr(nt, 0.004, 0.08, 0.55, 0.06, dur)
                sig = 0.65 * osc_square(phase) + 0.35 * osc_triangle(phase * 0.5)
                sig *= env * (0.36 + 0.16 * intensity)
            elif voice == 1:  # lead
                env = adsr(nt, 0.01, 0.12, 0.5, 0.1, dur)
                vibrato = math.sin(2 * math.pi * (5.2 + 1.5 * tension) * nt) * 0.012
                sig = osc_square(phase * (1.0 + vibrato))
                sig += 0.24 * osc_saw(phase * 0.5)
                sig *= env * (0.20 + 0.20 * intensity)
            else:  # arp
                env = adsr(nt, 0.002, 0.04, 0.35, 0.03, dur)
                sig = osc_triangle(phase * (1.0 + 0.02 * tension))
                sig *= env * (0.11 + 0.15 * intensity)

            mix += sig
            still_active.append((note_start, note, dur, voice, phase_offset))

        active = still_active

        # Kick-ish thump on quarter notes
        beat_pos = (t / seconds_per_beat) % 1.0
        kick_env = max(0.0, 1.0 - beat_pos * 10.0)
        kick = math.sin(2 * math.pi * (52 - beat_pos * 28) * t) * kick_env * (0.12 + 0.12 * intensity)

        # Snare-ish noise on beats 2 and 4
        beat_in_bar = (t / seconds_per_beat) % 4.0
        snare_trig = min(abs(beat_in_bar - 1.0), abs(beat_in_bar - 3.0))
        snare_env = max(0.0, 1.0 - snare_trig * 26.0)
        noise = (random.random() * 2.0 - 1.0)
        snare = noise * snare_env * (0.02 + 0.06 * tension)

        # Hi-hat shimmer (very light)
        hat_phase = (t * (10.0 + 2.0 * tension)) % 1.0
        hat_env = 0.4 if hat_phase < 0.06 else 0.08
        hat = (random.random() * 2.0 - 1.0) * hat_env * 0.02

        pulse = 0.96 + 0.04 * math.sin(2 * math.pi * 0.5 * t)
        mix = (mix + kick + snare + hat) * pulse
        mix = clamp(mix * max_amp)

        sample = int(mix * 32767)
        pcm.extend(struct.pack("<h", sample))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(pcm))


if __name__ == "__main__":
    out_dir = os.path.join("assets", "audio")

    # Three flavors for preview
    render_loop(
        os.path.join(out_dir, "arcade_loop_v1_chill.wav"),
        bpm=118,
        bars=8,
        progression=[57, 60, 62, 55],
        style_seed=11,
        intensity=0.55,
        tension=0.35,
    )
    render_loop(
        os.path.join(out_dir, "arcade_loop_v2_fast.wav"),
        bpm=142,
        bars=8,
        progression=[57, 62, 59, 55],
        style_seed=17,
        intensity=0.85,
        tension=0.55,
    )
    render_loop(
        os.path.join(out_dir, "arcade_loop_v3_tense.wav"),
        bpm=136,
        bars=8,
        progression=[57, 56, 62, 55],
        style_seed=29,
        intensity=0.95,
        tension=0.9,
    )

    # Default autoplay target for the game
    render_loop(
        os.path.join(out_dir, "arcade_loop.wav"),
        bpm=142,
        bars=8,
        progression=[57, 62, 59, 55],
        style_seed=17,
        intensity=0.85,
        tension=0.55,
    )

    print("Generated preview loops in assets/audio")
