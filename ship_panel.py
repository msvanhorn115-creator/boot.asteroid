import pygame

from ui_theme import UI_COLORS, draw_button, draw_panel


def draw_ship_panel(
    screen,
    panel_rect,
    player,
    active_contract,
    ship_tab,
    ship_ui,
    hud_font,
    panel_font,
):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["accent_alt"])

    title = panel_font.render("Ship Systems", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 16))

    ship_ui["tab_inventory"] = pygame.Rect(panel_rect.x + 20, panel_rect.y + 52, 140, 30)
    ship_ui["tab_map"] = pygame.Rect(panel_rect.x + 168, panel_rect.y + 52, 120, 30)
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

    left = panel_rect.x + 24
    top = panel_rect.y + 100
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

    for idx, line in enumerate(lines):
        text = hud_font.render(line, True, UI_COLORS["text"])
        screen.blit(text, (left, top + idx * 30))

    req_title = panel_font.render("Contract Requirements", True, UI_COLORS["accent_alt"])
    screen.blit(req_title, (left, top + 176))

    if active_contract is None:
        no_job = hud_font.render("No active contract", True, UI_COLORS["muted"])
        screen.blit(no_job, (left, top + 206))
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
            screen.blit(text, (left, top + 206 + idx * 24))
