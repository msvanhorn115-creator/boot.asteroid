import pygame

from upgrade_ui import (
    UPGRADE_BUTTON_KEYS,
    build_upgrade_button_labels,
    build_upgrade_button_rects,
    compute_upgrade_cost_texts,
)
from ui_theme import UI_COLORS, draw_button, draw_panel, draw_tag


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


def resolve_station_click(mouse_pos, station_tab, station_ui):
    if station_ui["undock"] and station_ui["undock"].collidepoint(mouse_pos):
        return "undock"
    if station_ui.get("deliver_contract") and station_ui["deliver_contract"].collidepoint(mouse_pos):
        return "deliver_contract"

    for idx in range(3):
        key = f"job_{idx}"
        rect = station_ui.get(key)
        if rect and rect.collidepoint(mouse_pos) and not station_ui.get(f"job_disabled_{idx}", False):
            return f"job:{idx}"

    for key in UPGRADE_BUTTON_KEYS:
        rect = station_ui.get(key)
        if rect and rect.collidepoint(mouse_pos):
            return key

    for key in ("upgrade_station_level", "upgrade_station_laser", "upgrade_station_missile"):
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
    active_contract,
    active_sector,
    docked_context,
    panel_font,
    hud_font,
    owner_label="Unknown",
    player_controls=False,
    station_level=1,
    station_laser=0,
    station_missile=0,
    station_level_cost_text="-",
    station_laser_cost_text="-",
    station_missile_cost_text="-",
):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["panel_border_hot"])

    title = panel_font.render("Station Upgrade Bay", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 18))
    owner_color = UI_COLORS["ok"] if player_controls else UI_COLORS["warn"]
    owner_text = hud_font.render(f"Owner: {owner_label}", True, owner_color)
    screen.blit(owner_text, (panel_rect.x + 300, panel_rect.y + 24))
    safe_text = hud_font.render("Docked: ship is safe, world paused", True, UI_COLORS["ok"])
    screen.blit(safe_text, (panel_rect.x + 20, panel_rect.y + 52))
    if not player_controls:
        claim_hint = hud_font.render("Press C to claim station (hostiles must be cleared)", True, UI_COLORS["warn"])
        screen.blit(claim_hint, (panel_rect.x + 20, panel_rect.y + 72))
    station_ui["sell_tab"] = None
    station_ui["upgrade_tab"] = None
    station_ui["sell_all"] = None
    station_ui["deliver_contract"] = None
    station_ui["upgrade_station_level"] = None
    station_ui["upgrade_station_laser"] = None
    station_ui["upgrade_station_missile"] = None
    for idx in range(3):
        station_ui[f"job_{idx}"] = None
        station_ui[f"job_disabled_{idx}"] = False

    left_x = panel_rect.x + 20
    right_x = panel_rect.x + panel_rect.width // 2 + 16
    contract_font = pygame.font.Font(None, max(16, hud_font.get_height() - 4))
    contract_max_width = max(220, panel_rect.right - right_x - 20)

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
        f"Missiles L{player.missile_level} | CD {player.missile_cooldown_seconds():.2f}s",
        (
            f"Cloak L{player.cloak_level} | "
            f"{player.cloak_timer:.1f}/{player.get_cloak_capacity_seconds():.1f}s"
        ),
    ]
    for idx, line in enumerate(summary_lines):
        text = hud_font.render(line, True, "white")
        screen.blit(text, (left_x, panel_rect.y + 126 + idx * 20))

    upgrade_button_rects = build_upgrade_button_rects(panel_rect)
    upgrade_button_labels = build_upgrade_button_labels(cost_texts)

    for key in UPGRADE_BUTTON_KEYS:
        station_ui[key] = upgrade_button_rects[key]
        draw_button(
            screen,
            station_ui[key],
            upgrade_button_labels[key],
            hud_font,
            active=False,
            tone="alt",
        )

    jobs = jobs or []
    draw_tag(screen, left_x, panel_rect.y + 92, "Ship Systems", hud_font, tone="accent")
    jobs_title = panel_font.render("Contracts", True, UI_COLORS["accent"])
    screen.blit(jobs_title, (right_x, panel_rect.y + 126))

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
        screen.blit(active_surface, (right_x, panel_rect.y + 148))

        if active_sector == active_contract["target_sector"]:
            station_ui["deliver_contract"] = pygame.Rect(right_x, panel_rect.y + 172, contract_max_width, 24)
            draw_button(
                screen,
                station_ui["deliver_contract"],
                "Deliver Active Contract",
                contract_font,
                active=True,
            )

    for idx, job in enumerate(jobs[:3]):
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

        line_text = _truncate_to_width(
            (
                f"{job['mission']}: {job['amount']} {job['unit']} | "
                f"{job.get('tile_distance', 0)}t | R{int(job.get('risk_rating', 1))}/5"
            ),
            contract_font,
            contract_max_width,
        )
        text = contract_font.render(
            line_text,
            True,
            _mission_color(job.get("mission")),
        )
        y = panel_rect.y + 162 + idx * 96
        screen.blit(text, (right_x, y))
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
        screen.blit(dest, (right_x, y + 20))

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
        screen.blit(req_line, (right_x, y + 40))

        key = f"job_{idx}"
        station_ui[f"job_disabled_{idx}"] = (action_label == "Locked")
        station_ui[key] = pygame.Rect(right_x, y + 66, contract_max_width, 24)
        draw_button(screen, station_ui[key], action_label, contract_font, active=(action_label == "Deliver"))

    station_ui["undock"] = pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 54, 220, 34)
    draw_button(screen, station_ui["undock"], "Undock", hud_font)

    if player_controls:
        base_x = panel_rect.x + 20
        base_y = panel_rect.bottom - 178
        sec_title = hud_font.render(
            f"Station L{station_level} | Laser L{station_laser} | Missile L{station_missile}",
            True,
            UI_COLORS["accent_alt"],
        )
        screen.blit(sec_title, (base_x, base_y - 22))

        station_ui["upgrade_station_level"] = pygame.Rect(base_x, base_y, 240, 24)
        station_ui["upgrade_station_laser"] = pygame.Rect(base_x, base_y + 28, 240, 24)
        station_ui["upgrade_station_missile"] = pygame.Rect(base_x, base_y + 56, 240, 24)
        draw_button(
            screen,
            station_ui["upgrade_station_level"],
            f"Station Hull ({station_level_cost_text})",
            contract_font,
            active=False,
        )
        draw_button(
            screen,
            station_ui["upgrade_station_laser"],
            f"Station Laser ({station_laser_cost_text})",
            contract_font,
            active=False,
        )
        draw_button(
            screen,
            station_ui["upgrade_station_missile"],
            f"Station Missile ({station_missile_cost_text})",
            contract_font,
            active=False,
        )

    dock_help = hud_font.render("Esc pauses game", True, UI_COLORS["accent"])
    screen.blit(dock_help, (panel_rect.x + 260, panel_rect.bottom - 48))
