import pygame


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


def draw_map_panel(
    screen,
    panel_rect,
    active_sector,
    explored_sectors,
    scanner_level,
    active_contract,
    title_font,
    panel_font,
    hud_font,
):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 205))
    screen.blit(overlay, (0, 0))

    pygame.draw.rect(screen, "#0b1220", panel_rect)
    pygame.draw.rect(screen, "#f6d365", panel_rect, 2)

    title = title_font.render("Sector Map", True, "white")
    screen.blit(title, (panel_rect.x + 24, panel_rect.y + 18))
    hint = hud_font.render("M to close | dark cells are uncharted", True, "#cbd5e1")
    screen.blit(hint, (panel_rect.x + 24, panel_rect.y + 66))

    grid_origin_x = panel_rect.x + 26
    grid_origin_y = panel_rect.y + 100
    cols = 9
    rows = 6
    cell = 70

    current_x, current_y = active_sector
    for gy in range(rows):
        for gx in range(cols):
            sx = current_x + (gx - cols // 2)
            sy = current_y + (gy - rows // 2)
            rect = pygame.Rect(grid_origin_x + gx * cell, grid_origin_y + gy * cell, cell - 6, cell - 6)
            key = (sx, sy)
            snapshot = explored_sectors.get(key)

            if snapshot is None:
                pygame.draw.rect(screen, "#020617", rect)
                pygame.draw.rect(screen, "#111827", rect, 1)
                continue

            density = snapshot.get("asteroid_density", 0)
            shade = min(200, 28 + density * 3)
            color = (shade // 2, shade // 2, min(255, shade))
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, "#334155", rect, 1)

            if snapshot.get("has_station"):
                pygame.draw.circle(screen, "#f6d365", rect.center, 4)
            if snapshot.get("has_planet"):
                pygame.draw.circle(screen, "#60a5fa", (rect.centerx + 11, rect.centery), 4)

            if scanner_level >= 2:
                d_text = hud_font.render(str(density), True, "#e2e8f0")
                screen.blit(d_text, (rect.x + 4, rect.y + 3))

            if (sx, sy) == active_sector:
                pygame.draw.rect(screen, "#22d3ee", rect, 2)

    info_x = panel_rect.x + 680
    info_y = panel_rect.y + 108
    scanner_text = panel_font.render(f"Scanner L{scanner_level}", True, "#93c5fd")
    screen.blit(scanner_text, (info_x, info_y))

    if active_contract:
        target = active_contract["target_sector"]
        target_type = active_contract["target_type"]
        max_info_width = 300
        line1 = hud_font.render("Active Contract", True, "#f6d365")
        contract_line = _truncate_to_width(
            (
                f"{active_contract['mission']}: {active_contract['amount']} "
                f"{active_contract['unit']} -> {active_contract['reward']} gold"
            ),
            hud_font,
            max_info_width,
        )
        line2 = hud_font.render(
            contract_line,
            True,
            _mission_color(active_contract.get("mission")),
        )
        destination_line = _truncate_to_width(
            f"Destination: {target_type} {target[0]},{target[1]}",
            hud_font,
            max_info_width,
        )
        line3 = hud_font.render(destination_line, True, "#a5b4fc")
        dx = target[0] - active_sector[0]
        dy = target[1] - active_sector[1]
        line4 = hud_font.render(f"Offset: {dx:+d}, {dy:+d}", True, "#94a3b8")
        screen.blit(line1, (info_x, info_y + 54))
        screen.blit(line2, (info_x, info_y + 80))
        screen.blit(line3, (info_x, info_y + 102))
        screen.blit(line4, (info_x, info_y + 124))
    else:
        no_contract = hud_font.render("No active contract", True, "#94a3b8")
        screen.blit(no_contract, (info_x, info_y + 70))
