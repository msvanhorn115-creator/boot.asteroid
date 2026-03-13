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

- `Left` / `Right`: rotate
- `Up` / `Down`: thrust forward / reverse
- `Space`: fire
- `F`: fire missile
- `T`: targeting computer lock
- `W`: sublight warp boost
- `V`: toggle cloak
- `E`: dock/land or interact
- `C`: claim nearby site
- `M`: open map tab
- `I`: open cargo tab
- `S`: open status tab
- `B`: open build tab
- `Tab` / `Shift+Tab`: cycle pause tabs
- `Esc`: pause
- `D`: dev god mode

## Notes

- This project is a script-based game prototype, not a packaged Python library.
- Running with `python main.py` is the intended workflow.
- World seed can be set with `ASTEROID_WORLD_SEED`.
- `scripts/validate_map_parity.py` checks map tile routing.
- `scripts/smoke_overlay_flow.py` runs a non-interactive overlay/input smoke check for pause, map, cargo, and status routing.

Example:

```bash
ASTEROID_WORLD_SEED=1337 python main.py
```
