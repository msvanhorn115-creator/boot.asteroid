import pygame
from ui_theme import UI_COLORS, draw_button, draw_panel


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
        "Freight": "#fca5a5",
        "Charter": "#a5b4fc",
        "Priority": "#fef08a",
        "Survey": "#67e8f9",
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
    if planet_ui.get("deliver_contract") and planet_ui["deliver_contract"].collidepoint(mouse_pos):
        return "deliver_contract"

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
    active_contract,
    active_sector,
    docked_context,
    panel_font,
    hud_font,
    planet_ui,
):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["accent_alt"])
    contract_font = pygame.font.Font(None, max(16, hud_font.get_height() - 4))
    contract_max_width = 258

    title = panel_font.render("Planet Trade Hub", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 18))
    sub = hud_font.render(
        f"Buys: {planet.accepted_metal} at {metal_prices.get(planet.accepted_metal, 0)} gold/unit",
        True,
        UI_COLORS["ok"],
    )
    screen.blit(sub, (panel_rect.x + 20, panel_rect.y + 52))

    cargo_line = hud_font.render(
        f"You carry: {player.metals.get(planet.accepted_metal, 0)} {planet.accepted_metal}",
        True,
        UI_COLORS["muted"],
    )
    screen.blit(cargo_line, (panel_rect.x + 20, panel_rect.y + 84))

    left_col_width = max(260, min(360, panel_rect.width // 2 - 56))
    planet_ui["trade"] = pygame.Rect(panel_rect.x + 20, panel_rect.y + 116, left_col_width, 36)
    draw_button(screen, planet_ui["trade"], "Sell Accepted Metal", panel_font, active=True, tone="alt")

    jobs_title = panel_font.render("Local Contracts", True, UI_COLORS["accent"])
    jobs_x = panel_rect.x + panel_rect.width // 2 + 16
    contract_max_width = max(220, panel_rect.right - jobs_x - 20)
    screen.blit(jobs_title, (jobs_x, panel_rect.y + 126))

    planet_ui["deliver_contract"] = None

    if active_contract is not None:
        risk_rating = int(active_contract.get("risk_rating", 1))
        active_line = _truncate_to_width(
            (
                f"Active: {active_contract['mission']} | "
                f"{active_contract.get('tile_distance', 0)} tiles | R{risk_rating}/5"
            ),
            contract_font,
            contract_max_width,
        )
        active_surface = contract_font.render(active_line, True, UI_COLORS["accent"])
        screen.blit(active_surface, (jobs_x, panel_rect.y + 148))

        if active_sector == active_contract["target_sector"]:
            planet_ui["deliver_contract"] = pygame.Rect(jobs_x, panel_rect.y + 172, contract_max_width, 24)
            draw_button(
                screen,
                planet_ui["deliver_contract"],
                "Deliver Active Contract",
                contract_font,
                active=True,
            )

    for idx in range(3):
        planet_ui[f"job_{idx}"] = None

    for idx, job in enumerate(jobs[:3]):
        is_active = active_contract == job
        at_destination_sector = active_sector == job["target_sector"]
        at_origin = (
            active_sector == job.get("origin_sector") and docked_context == job.get("origin")
        )

        if is_active and at_destination_sector:
            action_label = "Deliver"
        elif is_active and at_origin:
            action_label = "Accepted"
        elif is_active:
            action_label = "Accepted"
        else:
            action_label = "Accept"

        y = panel_rect.y + 162 + idx * 74
        line_text = _truncate_to_width(
            (
                f"{job['mission']}: {job['amount']} {job['unit']} | "
                f"{job.get('tile_distance', 0)}t | R{int(job.get('risk_rating', 1))}/5"
            ),
            contract_font,
            contract_max_width,
        )
        line = contract_font.render(
            line_text,
            True,
            _mission_color(job.get("mission")),
        )
        dest_text = _truncate_to_width(
            (
                f"Dest: {job['target_type']} {job['target_sector'][0]},{job['target_sector'][1]}"
                f" -> {job['reward']}g (+{int(job.get('hazard_bonus', 0))} hazard)"
            ),
            contract_font,
            contract_max_width,
        )
        dest = contract_font.render(
            dest_text,
            True,
            UI_COLORS["muted"],
        )
        screen.blit(line, (jobs_x, y))
        screen.blit(dest, (jobs_x, y + 20))

        key = f"job_{idx}"
        planet_ui[key] = pygame.Rect(jobs_x, y + 44, contract_max_width, 24)
        draw_button(screen, planet_ui[key], action_label, contract_font, active=(action_label == "Deliver"))

    planet_ui["undock"] = pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 54, 220, 34)
    draw_button(screen, planet_ui["undock"], "Take Off", hud_font)
