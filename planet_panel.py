import pygame
from ui_theme import UI_COLORS, draw_button, draw_close_button, draw_panel
from resources import get_metal_color


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
        "Freight": "#d2646c",
        "Charter": "#d0d0d8",
        "Priority": "#e2e2ea",
        "Survey": "#b8b8c6",
        "Courier": "#ccccd8",
        "Medical": "#c6c6d2",
        "Relief": "#cf6b73",
        "Engineering": "#c4c4d0",
        "Transport": "#d6d6e0",
        "Diplomatic": "#dcdce6",
        "Evacuation": "#d15862",
        "Science": "#bcbcc8",
    }
    return mission_colors.get(mission, "#c8c8d2")


def _draw_metal_chip(screen, x, y, metal_type, hud_font):
    metal_color = get_metal_color(metal_type)
    chip_rect = pygame.Rect(x, y, 18, 18)
    pygame.draw.circle(screen, (18, 24, 36), chip_rect.center, 9)
    pygame.draw.circle(screen, metal_color, chip_rect.center, 7)
    pygame.draw.circle(screen, (232, 238, 247), chip_rect.center, 9, 1)
    label = hud_font.render(metal_type, True, metal_color)
    screen.blit(label, (x + 26, y - 1))


def _draw_contract_market_tag(screen, x, y, metal_type, hud_font):
    metal_color = get_metal_color(metal_type)
    pygame.draw.circle(screen, (16, 24, 38), (x + 7, y + 7), 7)
    pygame.draw.circle(screen, metal_color, (x + 7, y + 7), 5)
    pygame.draw.circle(screen, (232, 238, 247), (x + 7, y + 7), 7, 1)
    label = hud_font.render(f"{metal_type} market", True, metal_color)
    screen.blit(label, (x + 18, y - 2))


def _missing_requirements(player, job):
    req = job.get("requirements", {})
    missing = []

    need_cargo = int(req.get("cargo", 0))
    have_cargo = player.get_cargo_capacity_units()
    if have_cargo < need_cargo:
        missing.append(f"Cargo {have_cargo}/{need_cargo}")

    need_acc = int(req.get("accommodations", 0))
    have_acc = player.get_accommodations_capacity()
    if have_acc < need_acc:
        missing.append(f"Accom {have_acc}/{need_acc}")

    need_engine = int(req.get("engine", 0))
    have_engine = player.engine_tuning_level
    if have_engine < need_engine:
        missing.append(f"Engine L{have_engine}/{need_engine}")

    need_scanner = int(req.get("scanner", 0))
    have_scanner = player.scanner_level
    if have_scanner < need_scanner:
        missing.append(f"Scanner L{have_scanner}/{need_scanner}")

    return missing


def resolve_planet_click(mouse_pos, planet_ui):
    if planet_ui.get("close") and planet_ui["close"].collidepoint(mouse_pos):
        return "close"
    if planet_ui.get("trade") and planet_ui["trade"].collidepoint(mouse_pos):
        return "trade"
    if planet_ui.get("undock") and planet_ui["undock"].collidepoint(mouse_pos):
        return "undock"
    if planet_ui.get("deliver_contract") and planet_ui["deliver_contract"].collidepoint(mouse_pos):
        return "deliver_contract"

    for idx in range(3):
        key = f"job_{idx}"
        rect = planet_ui.get(key)
        if rect and rect.collidepoint(mouse_pos) and not planet_ui.get(f"job_disabled_{idx}", False):
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
    owner_label="Unknown",
    player_controls=False,
    settlement_happiness=None,
):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["accent_alt"])
    contract_font = pygame.font.Font(None, max(16, hud_font.get_height() - 4))
    content_left = panel_rect.x + 20
    content_right = panel_rect.right - 20
    content_width = panel_rect.width - 40
    column_gap = 24
    left_col_width = max(280, min(380, (content_width - column_gap) // 2))
    right_col_x = content_left + left_col_width + column_gap
    right_col_width = content_right - right_col_x
    contract_max_width = max(280, right_col_width)

    title = panel_font.render("Planet Trade Hub", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 18))
    planet_ui["close"] = pygame.Rect(panel_rect.right - 54, panel_rect.y + 16, 34, 34)
    draw_close_button(screen, planet_ui["close"])
    owner_color = UI_COLORS["ok"] if player_controls else UI_COLORS["warn"]
    owner_label_text = _truncate_to_width(
        f"Owner: {owner_label}",
        hud_font,
        max(120, panel_rect.width - 360),
    )
    owner_text = hud_font.render(owner_label_text, True, owner_color)
    owner_x = max(panel_rect.x + 260, planet_ui["close"].x - owner_text.get_width() - 18)
    screen.blit(owner_text, (owner_x, panel_rect.y + 24))
    metal_price = metal_prices.get(planet.accepted_metal, 0)
    buys_prefix = hud_font.render("Buys:", True, UI_COLORS["ok"])
    screen.blit(buys_prefix, (panel_rect.x + 20, panel_rect.y + 52))
    _draw_metal_chip(screen, panel_rect.x + 72, panel_rect.y + 52, planet.accepted_metal, hud_font)
    price_suffix = hud_font.render(f"at {metal_price} gold/unit", True, UI_COLORS["ok"])
    screen.blit(price_suffix, (panel_rect.x + 210, panel_rect.y + 52))
    if not player_controls:
        claim_hint = hud_font.render("Press C to claim planet (hostiles must be cleared)", True, UI_COLORS["warn"])
        screen.blit(claim_hint, (panel_rect.x + 20, panel_rect.y + 72))
    elif settlement_happiness is not None:
        score = max(0.0, float(settlement_happiness))
        mood_color = UI_COLORS["ok"] if score >= 1.0 else UI_COLORS["warn"]
        mood_line = hud_font.render(f"Settlement happiness: {score:.2f}", True, mood_color)
        screen.blit(mood_line, (panel_rect.x + 20, panel_rect.y + 72))

    cargo_prefix = hud_font.render(
        f"You carry: {player.metals.get(planet.accepted_metal, 0)}",
        True,
        UI_COLORS["muted"],
    )
    screen.blit(cargo_prefix, (panel_rect.x + 20, panel_rect.y + 104))
    _draw_metal_chip(screen, panel_rect.x + 156, panel_rect.y + 104, planet.accepted_metal, hud_font)

    market_title = panel_font.render("Market Actions", True, UI_COLORS["accent_alt"])
    market_top = panel_rect.y + 126
    screen.blit(market_title, (content_left, market_top))

    market_lines = [
        f"Accepted metal: {planet.accepted_metal}",
        f"Unit price: {metal_price} gold",
        f"Cargo on hand: {player.metals.get(planet.accepted_metal, 0)} units",
    ]
    for idx, line in enumerate(market_lines):
        screen.blit(hud_font.render(line, True, UI_COLORS["muted"]), (content_left, market_top + 28 + idx * 22))

    trade_y = market_top + 108
    planet_ui["trade"] = pygame.Rect(content_left, trade_y, left_col_width, 38)
    draw_button(screen, planet_ui["trade"], "Sell Accepted Metal", panel_font, active=True, tone="alt")

    jobs_title = panel_font.render("Local Contracts", True, UI_COLORS["accent"])
    jobs_x = right_col_x
    jobs_top = market_top
    screen.blit(jobs_title, (jobs_x, jobs_top))

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
        screen.blit(active_surface, (jobs_x, jobs_top + 24))

        if active_sector == active_contract["target_sector"]:
            planet_ui["deliver_contract"] = pygame.Rect(jobs_x, jobs_top + 48, contract_max_width, 34)
            draw_button(
                screen,
                planet_ui["deliver_contract"],
                "Deliver Active Contract",
                contract_font,
                active=True,
            )

    for idx in range(3):
        planet_ui[f"job_{idx}"] = None
        planet_ui[f"job_disabled_{idx}"] = False

    job_row_height = 108
    jobs_top = jobs_top + 94
    jobs_bottom_limit = panel_rect.bottom - 74
    visible_rows = max(1, min(3, (jobs_bottom_limit - jobs_top) // job_row_height))

    for idx, job in enumerate(jobs[:visible_rows]):
        is_active = active_contract == job
        at_destination_sector = active_sector == job["target_sector"]
        at_origin = (
            active_sector == job.get("origin_sector") and docked_context == job.get("origin")
        )
        missing = _missing_requirements(player, job)
        missing_requirements = len(missing) > 0

        if is_active and at_destination_sector:
            action_label = "Deliver"
        elif is_active and at_origin:
            action_label = "Accepted"
        elif is_active:
            action_label = "Accepted"
        elif missing_requirements:
            action_label = "Locked"
        else:
            action_label = "Accept"

        y = jobs_top + idx * job_row_height
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
        _draw_contract_market_tag(screen, jobs_x + contract_max_width - 126, y + 2, planet.accepted_metal, contract_font)
        screen.blit(dest, (jobs_x, y + 20))

        if missing:
            req_text = _truncate_to_width(
                "Need: " + ", ".join(missing),
                contract_font,
                contract_max_width,
            )
            req_color = UI_COLORS["warn"]
        else:
            req_text = "Requirements: ready"
            req_color = UI_COLORS["ok"]
        req_line = contract_font.render(req_text, True, req_color)
        screen.blit(req_line, (jobs_x, y + 40))

        key = f"job_{idx}"
        planet_ui[f"job_disabled_{idx}"] = (action_label == "Locked")
        planet_ui[key] = pygame.Rect(jobs_x, y + 68, contract_max_width, 34)
        draw_button(screen, planet_ui[key], action_label, contract_font, active=(action_label == "Deliver"))

    planet_ui["undock"] = pygame.Rect(content_left, panel_rect.bottom - 60, 260, 40)
    draw_button(screen, planet_ui["undock"], "Take Off", hud_font)
