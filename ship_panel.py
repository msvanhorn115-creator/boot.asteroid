import pygame

from ui_theme import UI_COLORS, draw_button, draw_close_button, draw_panel
from resources import get_metal_color


def _draw_metal_row(screen, x, y, metal_type, amount, font):
    if amount <= 0:
        return

    metal_color = get_metal_color(metal_type)
    pygame.draw.circle(screen, (16, 24, 38), (x + 8, y + 10), 8)
    pygame.draw.circle(screen, metal_color, (x + 8, y + 10), 6)
    pygame.draw.circle(screen, (232, 238, 247), (x + 8, y + 10), 8, 1)

    label = font.render(f"{metal_type}: {amount}", True, metal_color)
    screen.blit(label, (x + 20, y + 1))


def draw_ship_panel(
    screen,
    panel_rect,
    player,
    active_contract,
    ship_tab,
    ship_ui,
    hud_font,
    panel_font,
    command_profile=None,
):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["accent_alt"])

    title = panel_font.render("Ship Systems", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 16))
    ship_ui["close"] = pygame.Rect(panel_rect.right - 54, panel_rect.y + 16, 34, 34)
    draw_close_button(screen, ship_ui["close"])

    content_left = panel_rect.x + 24
    content_right = panel_rect.right - 24
    tab_y = panel_rect.y + 52
    tab_gap = 10
    inventory_w = 156
    map_w = 132
    ship_ui["tab_inventory"] = pygame.Rect(content_left, tab_y, inventory_w, 32)
    ship_ui["tab_map"] = pygame.Rect(content_left + inventory_w + tab_gap, tab_y, map_w, 32)
    draw_button(
        screen,
        ship_ui["tab_inventory"],
        "Inventory",
        hud_font,
        active=(ship_tab == "inventory"),
        tone="accent" if ship_tab == "inventory" else "alt",
    )
    draw_button(
        screen,
        ship_ui["tab_map"],
        "Map",
        hud_font,
        active=(ship_tab == "map"),
        tone="accent" if ship_tab == "map" else "alt",
    )

    if ship_tab != "inventory":
        hint = hud_font.render("Map tab active - full map shown behind this panel", True, UI_COLORS["muted"])
        screen.blit(hint, (panel_rect.x + 20, panel_rect.y + 96))
        return

    content_rect = pygame.Rect(content_left, panel_rect.y + 102, panel_rect.width - 48, panel_rect.height - 132)
    column_gap = 28
    left_col_width = max(300, min(430, (content_rect.width - column_gap) // 2))
    right_col_x = content_rect.x + left_col_width + column_gap

    carrying_passengers = 0
    carrying_cargo = 0
    if active_contract is not None:
        if active_contract.get("unit") in ("passenger", "team"):
            carrying_passengers = int(active_contract.get("amount", 0))
        else:
            carrying_cargo = int(active_contract.get("amount", 0))

    metal_units = player.total_metal_units()
    cargo_used = metal_units + carrying_cargo
    cargo_cap = player.get_cargo_capacity_units()

    left = content_rect.x
    top = content_rect.y
    lines = [
        f"Cargo: {cargo_used}/{cargo_cap} units (metals {metal_units} + contract {carrying_cargo})",
        (
            f"Passengers: {carrying_passengers}/"
            f"{player.get_accommodations_capacity()} accommodations"
        ),
        f"Engine Tuning L{player.engine_tuning_level} | Thrust x{player.get_engine_speed_multiplier():.2f}",
        (
            f"Warp Drive L{player.warp_drive_level} | Boost x{player.get_warp_speed_multiplier():.2f}"
            f" | Charge {player.warp_energy:.1f}/{player.get_warp_capacity_seconds():.1f}s"
        ),
        f"Scanner L{player.scanner_level} | Missile L{player.missile_level} | Cloak L{player.cloak_level}",
    ]

    if command_profile is not None:
        lines.append(
            (
                f"Command L{int(command_profile.get('level', 1))} | "
                f"Territory {int(command_profile.get('territory', 1))} | "
                f"Infra {int(command_profile.get('infra', 0))} | "
                f"Defense {int(command_profile.get('defense', 0))}"
            )
        )

    for idx, line in enumerate(lines):
        text = hud_font.render(line, True, UI_COLORS["text"])
        screen.blit(text, (left, top + idx * 28))

    cargo_mix_title = panel_font.render("Cargo Metals", True, UI_COLORS["accent_alt"])
    screen.blit(cargo_mix_title, (right_col_x, top))

    metals = [(metal_type, amount) for metal_type, amount in player.metals.items() if amount > 0]
    metals.sort(key=lambda pair: pair[1], reverse=True)
    if not metals:
        empty = hud_font.render("No metals in hold", True, UI_COLORS["muted"])
        screen.blit(empty, (right_col_x, top + 30))
    else:
        for idx, (metal_type, amount) in enumerate(metals[:5]):
            _draw_metal_row(screen, right_col_x, top + 30 + idx * 24, metal_type, amount, hud_font)

    req_title = panel_font.render("Contract Requirements", True, UI_COLORS["accent_alt"])
    req_block_top = top + 208
    screen.blit(req_title, (left, req_block_top))

    if active_contract is None:
        no_job = hud_font.render("No active contract", True, UI_COLORS["muted"])
        screen.blit(no_job, (left, req_block_top + 30))
    else:
        req = active_contract.get("requirements", {})
        req_lines = [
            f"Cargo >= {req.get('cargo', 0)}",
            f"Accommodations >= {req.get('accommodations', 0)}",
            f"Engine Tuning >= {req.get('engine', 0)}",
            f"Scanner >= {req.get('scanner', 0)}",
        ]
        for idx, line in enumerate(req_lines):
            text = hud_font.render(line, True, UI_COLORS["muted"])
            screen.blit(text, (left, req_block_top + 30 + idx * 24))
