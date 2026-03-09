# boot.asteroid

Small Pygame space-mining/combat prototype with sector exploration, contracts, and scanner/map systems.

## Requirements

- Python 3.13+
- `venv` support (on Ubuntu/WSL: `sudo apt install python3-venv`)

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Controls

- `W`/`A`/`S`/`D`: thrust and rotate
- `Space`: fire
- `Left Shift`: sublight warp boost (when unlocked)
- `E`: dock/land or interact
- `M`: open/close map overlay
- `Esc`: pause
- `Q`: quit

## Notes

- This project is a script-based game prototype, not a packaged Python library.
- Running with `python main.py` is the intended workflow.
- World seed can be set with `ASTEROID_WORLD_SEED`.

Example:

```bash
ASTEROID_WORLD_SEED=1337 python main.py
```
