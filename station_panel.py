import pygame

from upgrade_ui import (
    UPGRADE_BUTTON_KEYS,
    build_upgrade_button_labels,
    build_upgrade_button_rects,
    compute_upgrade_cost_texts,
)


def _truncate_to_width(text, font, max_width):
    if font.size(text)[0] <= max_width:
        return text

    suffix = "..."
    trimmed = text
    while trimmed and font.size(trimmed + suffix)[0] > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + suffix) if trimmed else suffix


def _mission_color(mission):
    mission_colors = {
        "Courier": "#93c5fd",
        "Medical": "#86efac",
        "Relief": "#f9a8d4",
        "Engineering": "#fdba74",
        "Transport": "#c4b5fd",
        "Diplomatic": "#fef08a",
        "Evacuation": "#fca5a5",
        "Science": "#67e8f9",
    }
    return mission_colors.get(mission, "#cbd5e1")


def resolve_station_click(mouse_pos, station_tab, station_ui):
    if station_ui["undock"] and station_ui["undock"].collidepoint(mouse_pos):
        return "undock"

    for idx in range(3):
        key = f"job_{idx}"
        rect = station_ui.get(key)
        if rect and rect.collidepoint(mouse_pos):
            return f"job:{idx}"

    for key in UPGRADE_BUTTON_KEYS:
        rect = station_ui.get(key)
        if rect and rect.collidepoint(mouse_pos):
            return key

    return None


def draw_station_panel(
    screen,
    panel_rect,
    player,
    station_tab,
    station_ui,
    metal_prices,
    jobs,
    panel_font,
    hud_font,
):
    pygame.draw.rect(screen, "#10151d", panel_rect)
    pygame.draw.rect(screen, "#f6d365", panel_rect, 2)

    title = panel_font.render("Station Upgrade Bay", True, "white")
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 18))
    safe_text = hud_font.render("Docked: ship is safe, world paused", True, "#a6e3a1")
    screen.blit(safe_text, (panel_rect.x + 20, panel_rect.y + 52))
    station_ui["sell_tab"] = None
    station_ui["upgrade_tab"] = None
    station_ui["sell_all"] = None
    for idx in range(3):
        station_ui[f"job_{idx}"] = None

    left_x = panel_rect.x + 20
    right_x = panel_rect.x + 390
    contract_font = pygame.font.Font(None, max(16, hud_font.get_height() - 4))
    contract_max_width = 258

    cost_texts = compute_upgrade_cost_texts(player)
    summary_lines = [
        f"Fire L{player.fire_rate_level} | CD {player.shoot_cooldown:.2f}s",
        f"Shield L{player.shield_level} | {player.shield_layers}/{player.shield_level}",
        f"Multishot L{player.multishot_level} | {len(player.multishot_pattern())} shots",
        f"Beam L{player.targeting_beam_level} | Computer L{player.targeting_computer_level}",
        (
            f"Warp L{player.warp_drive_level} {player.warp_energy:.1f}/"
            f"{player.get_warp_capacity_seconds():.1f}s"
        ),
        f"Scanner L{player.scanner_level}",
    ]
    for idx, line in enumerate(summary_lines):
        text = hud_font.render(line, True, "white")
        screen.blit(text, (left_x, panel_rect.y + 126 + idx * 20))

    upgrade_button_rects = build_upgrade_button_rects(panel_rect)
    upgrade_button_labels = build_upgrade_button_labels(cost_texts)

    for key in UPGRADE_BUTTON_KEYS:
        station_ui[key] = upgrade_button_rects[key]
        pygame.draw.rect(screen, "#1f2937", station_ui[key])
        pygame.draw.rect(screen, "#f6d365", station_ui[key], 2)
        label_surface = hud_font.render(upgrade_button_labels[key], True, "#f6d365")
        screen.blit(label_surface, (station_ui[key].x + 10, station_ui[key].y + 9))

    jobs = jobs or []
    jobs_title = panel_font.render("Jobs", True, "#f6d365")
    screen.blit(jobs_title, (right_x, panel_rect.y + 126))
    for idx, job in enumerate(jobs[:3]):
        line_text = _truncate_to_width(
            f"{job['mission']}: {job['amount']} {job['unit']} -> {job['reward']} gold",
            contract_font,
            contract_max_width,
        )
        text = contract_font.render(
            line_text,
            True,
            _mission_color(job.get("mission")),
        )
        y = panel_rect.y + 162 + idx * 74
        screen.blit(text, (right_x, y))
        dest_text = _truncate_to_width(
            f"Dest: {job['target_type']} {job['target_sector'][0]},{job['target_sector'][1]}",
            contract_font,
            contract_max_width,
        )
        dest = contract_font.render(
            dest_text,
            True,
            "#94a3b8",
        )
        screen.blit(dest, (right_x, y + 20))

        key = f"job_{idx}"
        station_ui[key] = pygame.Rect(right_x, y + 44, 260, 24)
        pygame.draw.rect(screen, "#1f2937", station_ui[key])
        pygame.draw.rect(screen, "#f6d365", station_ui[key], 2)
        btn = contract_font.render("Track / Deliver", True, "#f6d365")
        screen.blit(btn, (station_ui[key].x + 70, station_ui[key].y + 4))

    station_ui["undock"] = pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 54, 220, 34)
    pygame.draw.rect(screen, "#1f2937", station_ui["undock"])
    pygame.draw.rect(screen, "#f6d365", station_ui["undock"], 2)
    undock_btn = hud_font.render("Undock", True, "#f6d365")
    screen.blit(undock_btn, (station_ui["undock"].x + 78, station_ui["undock"].y + 7))

    dock_help = hud_font.render("Esc pauses game", True, "#f6d365")
    screen.blit(dock_help, (panel_rect.x + 260, panel_rect.bottom - 48))
