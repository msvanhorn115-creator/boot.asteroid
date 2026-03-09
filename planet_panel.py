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


def resolve_planet_click(mouse_pos, planet_ui):
    if planet_ui.get("trade") and planet_ui["trade"].collidepoint(mouse_pos):
        return "trade"
    if planet_ui.get("undock") and planet_ui["undock"].collidepoint(mouse_pos):
        return "undock"

    for idx in range(3):
        key = f"job_{idx}"
        rect = planet_ui.get(key)
        if rect and rect.collidepoint(mouse_pos):
            return f"job:{idx}"

    return None


def draw_planet_panel(
    screen,
    panel_rect,
    player,
    planet,
    metal_prices,
    jobs,
    panel_font,
    hud_font,
    planet_ui,
):
    pygame.draw.rect(screen, "#0f172a", panel_rect)
    pygame.draw.rect(screen, "#f6d365", panel_rect, 2)
    contract_font = pygame.font.Font(None, max(16, hud_font.get_height() - 4))
    contract_max_width = 258

    title = panel_font.render("Planet Trade Hub", True, "white")
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 18))
    sub = hud_font.render(
        f"Buys: {planet.accepted_metal} at {metal_prices.get(planet.accepted_metal, 0)} gold/unit",
        True,
        "#a6e3a1",
    )
    screen.blit(sub, (panel_rect.x + 20, panel_rect.y + 52))

    cargo_line = hud_font.render(
        f"You carry: {player.metals.get(planet.accepted_metal, 0)} {planet.accepted_metal}",
        True,
        "#cbd5e1",
    )
    screen.blit(cargo_line, (panel_rect.x + 20, panel_rect.y + 84))

    planet_ui["trade"] = pygame.Rect(panel_rect.x + 20, panel_rect.y + 116, 300, 36)
    pygame.draw.rect(screen, "#1f2937", planet_ui["trade"])
    pygame.draw.rect(screen, "#f6d365", planet_ui["trade"], 2)
    trade_btn = panel_font.render("Sell Accepted Metal", True, "#f6d365")
    screen.blit(trade_btn, (planet_ui["trade"].x + 24, planet_ui["trade"].y + 6))

    jobs_title = panel_font.render("Local Contracts", True, "#f6d365")
    jobs_x = panel_rect.x + 390
    screen.blit(jobs_title, (jobs_x, panel_rect.y + 126))

    for idx in range(3):
        planet_ui[f"job_{idx}"] = None

    for idx, job in enumerate(jobs[:3]):
        y = panel_rect.y + 162 + idx * 74
        line_text = _truncate_to_width(
            f"{job['mission']}: {job['amount']} {job['unit']} -> {job['reward']} gold",
            contract_font,
            contract_max_width,
        )
        line = contract_font.render(
            line_text,
            True,
            _mission_color(job.get("mission")),
        )
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
        screen.blit(line, (jobs_x, y))
        screen.blit(dest, (jobs_x, y + 20))

        key = f"job_{idx}"
        planet_ui[key] = pygame.Rect(jobs_x, y + 44, 260, 24)
        pygame.draw.rect(screen, "#1f2937", planet_ui[key])
        pygame.draw.rect(screen, "#f6d365", planet_ui[key], 2)
        btn = contract_font.render("Track / Deliver", True, "#f6d365")
        screen.blit(btn, (planet_ui[key].x + 70, planet_ui[key].y + 4))

    planet_ui["undock"] = pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 54, 220, 34)
    pygame.draw.rect(screen, "#1f2937", planet_ui["undock"])
    pygame.draw.rect(screen, "#f6d365", planet_ui["undock"], 2)
    undock_btn = hud_font.render("Take Off", True, "#f6d365")
    screen.blit(undock_btn, (planet_ui["undock"].x + 75, planet_ui["undock"].y + 7))
