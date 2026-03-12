import pygame

from upgrade_ui import (
    UPGRADE_BUTTON_KEYS,
    build_upgrade_button_labels,
    compute_upgrade_cost_texts,
)
from ui_theme import UI_COLORS, draw_button, draw_close_button, draw_panel, draw_tag


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
    if station_ui.get("close") and station_ui["close"].collidepoint(mouse_pos):
        return "close"

    for key in (
        "tab_ship",
        "tab_station",
        "tab_contracts",
        "subtab_primary",
        "subtab_secondary",
    ):
        rect = station_ui.get(key)
        if rect and rect.collidepoint(mouse_pos):
            action = station_ui.get(f"{key}_action")
            if action:
                return f"tab:{action}"

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

    for key in (
        "upgrade_infra_mining",
        "upgrade_infra_drone",
        "upgrade_infra_turret",
        "upgrade_infra_shield",
    ):
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
    infra_mining=0,
    infra_drone=0,
    infra_turret=0,
    infra_shield=0,
    infra_mining_cost_text="-",
    infra_drone_cost_text="-",
    infra_turret_cost_text="-",
    infra_shield_cost_text="-",
):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["panel_border_hot"])

    # Dynamic header layout to prevent overlap
    header_y = panel_rect.y + 18
    title = panel_font.render("Station Upgrade Bay", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, header_y))
    header_y += title.get_height() + 6
    owner_color = UI_COLORS["ok"] if player_controls else UI_COLORS["warn"]
    owner_text = hud_font.render(f"Owner: {owner_label}", True, owner_color)
    screen.blit(owner_text, (panel_rect.x + 20, header_y))
    header_y += owner_text.get_height() + 6
    safe_text = hud_font.render("Docked: ship is safe, world paused", True, UI_COLORS["ok"])
    screen.blit(safe_text, (panel_rect.x + 20, header_y))
    header_y += safe_text.get_height() + 6
    if not player_controls:
        claim_hint = hud_font.render("Press C to claim station (hostiles must be cleared)", True, UI_COLORS["warn"])
        screen.blit(claim_hint, (panel_rect.x + 20, header_y))
        header_y += claim_hint.get_height() + 6
    station_ui["sell_tab"] = None
    station_ui["upgrade_tab"] = None
    station_ui["sell_all"] = None
    station_ui["deliver_contract"] = None
    station_ui["upgrade_station_level"] = None
    station_ui["upgrade_station_laser"] = None
    station_ui["upgrade_station_missile"] = None
    station_ui["upgrade_infra_mining"] = None
    station_ui["upgrade_infra_drone"] = None
    station_ui["upgrade_infra_turret"] = None
    station_ui["upgrade_infra_shield"] = None
    station_ui["tab_ship"] = None
    station_ui["tab_station"] = None
    station_ui["tab_contracts"] = None
    station_ui["subtab_primary"] = None
    station_ui["subtab_secondary"] = None
    station_ui["close"] = pygame.Rect(panel_rect.right - 54, panel_rect.y + 16, 34, 34)
    draw_close_button(screen, station_ui["close"])
    station_ui["tab_ship_action"] = "ship_core"
    station_ui["tab_station_action"] = "station_defense"
    station_ui["tab_contracts_action"] = "contracts_board"
    station_ui["subtab_primary_action"] = None
    station_ui["subtab_secondary_action"] = None
    for idx in range(3):
        station_ui[f"job_{idx}"] = None
        station_ui[f"job_disabled_{idx}"] = False

    active_top = "contracts"
    if str(station_tab).startswith("ship_"):
        active_top = "ship"
    elif str(station_tab).startswith("station_"):
        active_top = "station"

    contract_font = pygame.font.Font(None, max(16, hud_font.get_height() - 4))
    tab_y = header_y + 12
    inner_left = panel_rect.x + 20
    inner_right = panel_rect.right - 20
    tab_gap = 8
    base_tab_w = max(118, min(144, (panel_rect.width - 140) // 6))
    contracts_tab_w = base_tab_w + 18
    subtab_w = max(154, min(176, base_tab_w + 18))
    station_ui["tab_ship"] = pygame.Rect(inner_left, tab_y, base_tab_w, 32)
    station_ui["tab_station"] = pygame.Rect(inner_left + base_tab_w + tab_gap, tab_y, base_tab_w, 32)
    station_ui["tab_contracts"] = pygame.Rect(inner_left + (base_tab_w + tab_gap) * 2, tab_y, contracts_tab_w, 32)
    draw_button(screen, station_ui["tab_ship"], "Ship", hud_font, active=(active_top == "ship"), tone="alt")
    draw_button(screen, station_ui["tab_station"], "Station", hud_font, active=(active_top == "station"), tone="alt")
    draw_button(screen, station_ui["tab_contracts"], "Contracts", hud_font, active=(active_top == "contracts"), tone="alt")

    content_top = tab_y + 48
    content_rect = pygame.Rect(inner_left, content_top, panel_rect.width - 40, panel_rect.bottom - content_top - 72)
    left_col_gap = 20
    left_col_width = max(240, (content_rect.width - left_col_gap) // 2)
    right_col_x = content_rect.right - left_col_width
    contract_max_width = content_rect.width

    if active_top == "ship":
        subtab_left = inner_right - (subtab_w * 2 + tab_gap)
        station_ui["subtab_primary"] = pygame.Rect(subtab_left, tab_y, subtab_w, 32)
        station_ui["subtab_secondary"] = pygame.Rect(subtab_left + subtab_w + tab_gap, tab_y, subtab_w, 32)
        station_ui["subtab_primary_action"] = "ship_core"
        station_ui["subtab_secondary_action"] = "ship_utility"
        draw_button(
            screen,
            station_ui["subtab_primary"],
            "Combat Fit",
            hud_font,
            active=(station_tab == "ship_core"),
        )
        draw_button(
            screen,
            station_ui["subtab_secondary"],
            "Utility Fit",
            hud_font,
            active=(station_tab == "ship_utility"),
        )
    elif active_top == "station":
        subtab_left = inner_right - (subtab_w * 2 + tab_gap)
        station_ui["subtab_primary"] = pygame.Rect(subtab_left, tab_y, subtab_w, 32)
        station_ui["subtab_secondary"] = pygame.Rect(subtab_left + subtab_w + tab_gap, tab_y, subtab_w, 32)
        station_ui["subtab_primary_action"] = "station_defense"
        station_ui["subtab_secondary_action"] = "station_infra"
        draw_button(
            screen,
            station_ui["subtab_primary"],
            "Defense Grid",
            hud_font,
            active=(station_tab == "station_defense"),
        )
        draw_button(
            screen,
            station_ui["subtab_secondary"],
            "Infrastructure",
            hud_font,
            active=(station_tab == "station_infra"),
        )

    cost_texts = compute_upgrade_cost_texts(player)
    upgrade_button_labels = build_upgrade_button_labels(cost_texts)
    for key in UPGRADE_BUTTON_KEYS:
        station_ui[key] = None

    jobs = jobs or []
    if active_top == "ship":
        draw_tag(screen, content_rect.x, content_rect.y + 4, "Ship Systems", hud_font, tone="accent")
        summary_top = content_rect.y + 36
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
        left_summary = summary_lines[:4]
        right_summary = summary_lines[4:]
        for idx, line in enumerate(left_summary):
            text = hud_font.render(line, True, UI_COLORS["muted"])
            screen.blit(text, (content_rect.x, summary_top + idx * 20))
        for idx, line in enumerate(right_summary):
            text = hud_font.render(line, True, UI_COLORS["muted"])
            screen.blit(text, (right_col_x, summary_top + idx * 20))

        keys = [
            "buy_fire_rate",
            "buy_shield",
            "buy_multishot",
            "buy_targeting_beam",
            "buy_targeting_computer",
            "buy_warp_drive",
        ]
        if station_tab == "ship_utility":
            keys = [
                "buy_scanner",
                "buy_missile",
                "buy_cloak",
                "buy_cargo_hold",
                "buy_accommodations",
                "buy_engine_tuning",
            ]

        buttons_top = summary_top + 112
        for idx, key in enumerate(keys):
            col = idx % 2
            row = idx // 2
            bx = content_rect.x if col == 0 else right_col_x
            by = buttons_top + row * 44
            station_ui[key] = pygame.Rect(bx, by, left_col_width, 36)
            draw_button(
                screen,
                station_ui[key],
                upgrade_button_labels[key],
                hud_font,
                active=False,
                tone="alt",
            )

    elif active_top == "station":
        if not player_controls:
            lock_line = hud_font.render("Claim station ownership to access station controls.", True, UI_COLORS["warn"])
            screen.blit(lock_line, (content_rect.x, content_rect.y + 8))
        elif station_tab == "station_infra":
            infra_title = panel_font.render("Infrastructure Upgrades", True, UI_COLORS["accent"])
            screen.blit(infra_title, (content_rect.x, content_rect.y + 4))
            infra_lines = [
                f"Mining Drones L{infra_mining}",
                f"Interceptor Drones L{infra_drone}",
                f"Turret Grid L{infra_turret}",
                f"Shield Net L{infra_shield}",
            ]
            for idx, line in enumerate(infra_lines[:2]):
                screen.blit(hud_font.render(line, True, UI_COLORS["muted"]), (content_rect.x, content_rect.y + 34 + idx * 22))
            for idx, line in enumerate(infra_lines[2:]):
                screen.blit(hud_font.render(line, True, UI_COLORS["muted"]), (right_col_x, content_rect.y + 34 + idx * 22))

            row_y = content_rect.y + 92
            station_ui["upgrade_infra_mining"] = pygame.Rect(content_rect.x, row_y, left_col_width, 36)
            station_ui["upgrade_infra_drone"] = pygame.Rect(content_rect.x, row_y + 46, left_col_width, 36)
            station_ui["upgrade_infra_turret"] = pygame.Rect(right_col_x, row_y, left_col_width, 36)
            station_ui["upgrade_infra_shield"] = pygame.Rect(right_col_x, row_y + 46, left_col_width, 36)
            draw_button(screen, station_ui["upgrade_infra_mining"], f"Mining Drones ({infra_mining_cost_text})", contract_font)
            draw_button(screen, station_ui["upgrade_infra_drone"], f"Interceptor Drones ({infra_drone_cost_text})", contract_font)
            draw_button(screen, station_ui["upgrade_infra_turret"], f"Turret Grid ({infra_turret_cost_text})", contract_font)
            draw_button(screen, station_ui["upgrade_infra_shield"], f"Shield Net ({infra_shield_cost_text})", contract_font)
        else:
            defense_title = panel_font.render("Station Defense", True, UI_COLORS["accent_alt"])
            screen.blit(defense_title, (content_rect.x, content_rect.y + 4))
            defense_lines = [
                f"Station Hull L{station_level}",
                f"Station Laser L{station_laser}",
                f"Missile Battery L{station_missile}",
                "Docked assets remain protected while you are inside.",
            ]
            for idx, line in enumerate(defense_lines[:2]):
                screen.blit(hud_font.render(line, True, UI_COLORS["muted"]), (content_rect.x, content_rect.y + 34 + idx * 22))
            for idx, line in enumerate(defense_lines[2:]):
                screen.blit(hud_font.render(line, True, UI_COLORS["muted"]), (right_col_x, content_rect.y + 34 + idx * 22))

            row_y = content_rect.y + 92
            station_ui["upgrade_station_level"] = pygame.Rect(content_rect.x, row_y, left_col_width, 36)
            station_ui["upgrade_station_laser"] = pygame.Rect(right_col_x, row_y, left_col_width, 36)
            station_ui["upgrade_station_missile"] = pygame.Rect(content_rect.x, row_y + 46, content_rect.width, 36)
            draw_button(screen, station_ui["upgrade_station_level"], f"Station Hull ({station_level_cost_text})", contract_font)
            draw_button(screen, station_ui["upgrade_station_laser"], f"Station Laser ({station_laser_cost_text})", contract_font)
            draw_button(screen, station_ui["upgrade_station_missile"], f"Station Missile ({station_missile_cost_text})", contract_font)

    else:
        jobs_title = panel_font.render("Contracts", True, UI_COLORS["accent"])
        screen.blit(jobs_title, (content_rect.x, content_rect.y + 4))

        cursor_y = content_rect.y + 32
        contracts_bottom_limit = panel_rect.bottom - 74
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
            screen.blit(active_surface, (content_rect.x, cursor_y))
            cursor_y += 24

            if active_sector == active_contract["target_sector"]:
                station_ui["deliver_contract"] = pygame.Rect(content_rect.x, cursor_y, contract_max_width, 32)
                draw_button(screen, station_ui["deliver_contract"], "Deliver Active Contract", contract_font, active=True)
                cursor_y += 40

        visible_rows = max(1, min(3, (contracts_bottom_limit - cursor_y) // 106))
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
            screen.blit(contract_font.render(line_text, True, _mission_color(job.get("mission"))), (content_rect.x, cursor_y))
            dest_text = _truncate_to_width(
                (
                    f"Dest: {job['target_type']} {job['target_sector'][0]},{job['target_sector'][1]}"
                    f" -> {job['reward']}g (+{int(job.get('hazard_bonus', 0))} hazard)"
                ),
                contract_font,
                contract_max_width,
            )
            screen.blit(contract_font.render(dest_text, True, UI_COLORS["muted"]), (content_rect.x, cursor_y + 20))

            if missing:
                req_text = _truncate_to_width("Need: " + ", ".join(missing), contract_font, contract_max_width)
                req_color = UI_COLORS["warn"]
            elif is_active and at_origin:
                req_text = "Contract accepted at this dock"
                req_color = UI_COLORS["muted"]
            else:
                req_text = "Requirements: ready"
                req_color = UI_COLORS["ok"]
            screen.blit(contract_font.render(req_text, True, req_color), (content_rect.x, cursor_y + 40))

            key = f"job_{idx}"
            station_ui[f"job_disabled_{idx}"] = (action_label == "Locked")
            station_ui[key] = pygame.Rect(content_rect.x, cursor_y + 62, contract_max_width, 32)
            draw_button(screen, station_ui[key], action_label, contract_font, active=(action_label == "Deliver"))
            cursor_y += 106

    station_ui["undock"] = pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 60, 260, 40)
    draw_button(screen, station_ui["undock"], "Undock", hud_font)

    dock_help = hud_font.render("Esc pauses game", True, UI_COLORS["accent"])
    screen.blit(dock_help, (panel_rect.right - dock_help.get_width() - 20, panel_rect.bottom - 48))
