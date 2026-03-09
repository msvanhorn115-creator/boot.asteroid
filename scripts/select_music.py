import shutil
import sys
from pathlib import Path

BASE = Path("assets/audio")
PRESETS = {
    "v1": BASE / "arcade_loop_v1_chill.wav",
    "v2": BASE / "arcade_loop_v2_fast.wav",
    "v3": BASE / "arcade_loop_v3_tense.wav",
}
TARGET = BASE / "arcade_loop.wav"


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in PRESETS:
        print("Usage: python scripts/select_music.py v1|v2|v3")
        return 1

    src = PRESETS[sys.argv[1]]
    if not src.exists():
        print(f"Missing source file: {src}")
        return 1

    shutil.copyfile(src, TARGET)
    print(f"Selected {sys.argv[1]} -> {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
