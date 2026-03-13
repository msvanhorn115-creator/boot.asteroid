import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from map_panel import draw_map_panel, get_map_cells, map_tile_parity_ok
from player import Player
from ship_panel import draw_ship_panel, resolve_ship_click
from status_panel import draw_status_panel

def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def check_ship_panel(screen, hud_font, panel_font):
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    player.metals["iron"] = 7
    player.metals["silver"] = 3
    player.accommodations_level = 1
    active_contract = {
        "mission": "Relief Run",
        "amount": 2,
        "unit": "cargo",
        "target_type": "station",
        "target_sector": (1, -1),
    }
    ship_ui = {"close": None}
    panel_rect = pygame.Rect(88, 52, SCREEN_WIDTH - 176, SCREEN_HEIGHT - 104)
    draw_ship_panel(screen, panel_rect, player, active_contract, ship_ui, hud_font, panel_font)

    assert_true(ship_ui.get("close") is not None, "cargo panel close button missing")
    assert_true(ship_ui.get("drop_contract") is not None, "cargo panel contract dump button missing")
    iron_drop = ship_ui.get("drop_metal:iron")
    assert_true(iron_drop is not None, "cargo panel metal jettison button missing")

    assert_true(resolve_ship_click(ship_ui["close"].center, ship_ui) == "close", "cargo close action mismatch")
    assert_true(
        resolve_ship_click(ship_ui["drop_contract"].center, ship_ui) == "drop_contract",
        "cargo contract dump action mismatch",
    )
    assert_true(
        resolve_ship_click(iron_drop.center, ship_ui) == "drop_metal:iron",
        "cargo metal jettison action mismatch",
    )


def check_status_panel(screen, hud_font, panel_font):
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    player.weapon_amp_level = 2
    player.deflector_booster_level = 2
    player.missile_level = 2
    player.missile_payload_level = 1
    player.auto_mining_level = 2
    player.refill_deflector()
    status_ui = {"close": None}
    panel_rect = pygame.Rect(88, 52, SCREEN_WIDTH - 176, SCREEN_HEIGHT - 104)
    draw_status_panel(
        screen,
        panel_rect,
        player,
        active_contract=None,
        status_ui=status_ui,
        hud_font=hud_font,
        panel_font=panel_font,
        command_profile={"level": 3, "territory": 2, "infra": 1, "defense": 1},
        active_sector=(0, 0),
        sector_owner_label="Union",
        world_seed=1337,
    )
    assert_true(status_ui.get("close") is not None, "status panel close button missing")


def check_map_panel(screen, title_font, panel_font, hud_font):
    panel_rect = pygame.Rect(70, 78, SCREEN_WIDTH - 140, SCREEN_HEIGHT - 156)
    active_sector = (0, 0)
    scanner_targets = {(1, 0), (0, 1)}
    ftl_targets = {(2, 0), (0, -1)}
    cells = get_map_cells(
        panel_rect,
        active_sector,
        scanner_target_sectors=scanner_targets,
        ftl_target_sectors=ftl_targets,
    )
    sector_cells = {cell["sector"]: cell for cell in cells}
    assert_true(map_tile_parity_ok(panel_rect, active_sector), "map tile parity failed")
    assert_true(sector_cells[(1, 0)]["in_scan_range"], "scanner target highlight missing")
    assert_true(sector_cells[(2, 0)]["in_ftl_range"], "FTL target highlight missing")

    draw_map_panel(
        screen,
        panel_rect,
        active_sector,
        explored_sectors={},
        scanner_level=3,
        active_contract=None,
        live_sector_intel={},
        scanner_cooldown=0.0,
        title_font=title_font,
        panel_font=panel_font,
        hud_font=hud_font,
        sector_owner_fn=lambda sector: "player" if sector == active_sector else "null",
        owner_label_fn=lambda owner: owner.title(),
        build_status_fn=lambda sector: (f"Sector {sector[0]},{sector[1]}", "#cbd5e1"),
        raided_sectors=set(),
        tactical_visible_sectors={active_sector, (1, 0), (2, 0), (0, 1), (0, -1)},
        scanner_target_sectors=scanner_targets,
        ftl_target_sectors=ftl_targets,
        show_close_button=True,
    )


def check_main_route_wiring():
    main_text = (ROOT / "main.py").read_text()
    required_patterns = {
        "Tab cycle": r"if event\.key == pygame\.K_TAB.*cycle_pause_tab",
        "Map hotkey": r"if event\.key == pygame\.K_m.*open_pause_tab\(\"map\"\)",
        "Cargo hotkey": r"if event\.key == pygame\.K_i.*open_pause_tab\(\"ship\"\)",
        "Status hotkey": r"if event\.key == pygame\.K_s.*open_pause_tab\(\"status\"\)",
        "Build hotkey": r"if event\.key == pygame\.K_b.*open_pause_tab\(\"build\"\)",
        "Interact hotkey": r"if event\.key == pygame\.K_e:.*handle_interact_action\(\)",
        "Touch interact": r"elif action == \"interact\":.*handle_interact_action\(\)",
    }
    for label, pattern in required_patterns.items():
        assert_true(re.search(pattern, main_text, re.DOTALL), f"main route wiring missing: {label}")

    assert_true("def handle_interact_action():" in main_text, "interact handler missing")
    assert_true("nearest_station_in_range()" in main_text, "station interact route missing")
    assert_true("nearest_planet_in_range()" in main_text, "planet interact route missing")


def main():
    pygame.init()
    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        title_font = pygame.font.SysFont("freesansbold", 40)
        panel_font = pygame.font.SysFont("dejavusans", 23)
        hud_font = pygame.font.SysFont("dejavusans", 18)

        check_ship_panel(screen, hud_font, panel_font)
        check_status_panel(screen, hud_font, panel_font)
        check_map_panel(screen, title_font, panel_font, hud_font)
        check_main_route_wiring()
    finally:
        pygame.quit()

    print("overlay smoke checks passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"overlay smoke checks failed: {exc}", file=sys.stderr)
        raise