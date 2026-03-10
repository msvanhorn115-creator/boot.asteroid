import sys
from pathlib import Path

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from map_panel import get_map_cells, map_sector_at_point, map_tile_parity_ok


def run_checks():
    panel_rects = [
        pygame.Rect(70, 50, 1280 - 140, 720 - 100),
        pygame.Rect(50, 40, 1100, 620),
        pygame.Rect(20, 20, 900, 520),
    ]
    active_sectors = [
        (0, 0),
        (1, 1),
        (-3, 2),
        (12, -7),
    ]

    for panel_rect in panel_rects:
        for active_sector in active_sectors:
            if not map_tile_parity_ok(panel_rect, active_sector):
                raise SystemExit(
                    f"FAIL: parity mismatch for panel={panel_rect} active_sector={active_sector}"
                )

            cells = get_map_cells(panel_rect, active_sector)
            for cell in cells:
                center = cell["rect"].center
                resolved = map_sector_at_point(panel_rect, active_sector, center)
                if resolved != cell["sector"]:
                    raise SystemExit(
                        "FAIL: center mismatch "
                        f"panel={panel_rect} active={active_sector} expected={cell['sector']} got={resolved}"
                    )

    print("PASS: map tile parity is 1:1 across tested layouts/sectors")


if __name__ == "__main__":
    run_checks()
