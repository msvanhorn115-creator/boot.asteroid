import pygame

from ui_theme import UI_COLORS, draw_close_button, draw_panel


def _wrap_text_lines(text, font, max_width):
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_status_panel(
    screen,
    panel_rect,
    player,
    active_contract,
    status_ui,
    hud_font,
    panel_font,
    command_profile=None,
    active_sector=None,
    sector_owner_label=None,
    world_seed=None,
):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["accent_alt"])

    title = panel_font.render("Status", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 16))
    status_ui["close"] = pygame.Rect(panel_rect.right - 54, panel_rect.y + 16, 34, 34)
    draw_close_button(screen, status_ui["close"])

    content_rect = pygame.Rect(panel_rect.x + 24, panel_rect.y + 72, panel_rect.width - 48, panel_rect.height - 102)
    column_gap = 28
    left_col_width = max(300, min(430, (content_rect.width - column_gap) // 2))
    right_col_x = content_rect.x + left_col_width + column_gap

    lines = [
        f"Shields L{player.shield_level} | Layers {player.shield_layers}/{player.shield_level}",
        (
            f"Deflector L{player.deflector_booster_level} | Layers "
            f"{player.deflector_layers}/{player.get_deflector_capacity()} | "
            f"Regen {player.get_deflector_regen_seconds():.1f}s"
        ),
        f"Multishot L{player.multishot_level} | Pellets {len(player.multishot_pattern())}",
        (
            f"Targeting Beam L{player.targeting_beam_level} | "
            f"Computer L{player.targeting_computer_level} | Lock {player.get_lock_time_seconds():.2f}s"
        ),
        f"Weapon Amp L{player.weapon_amp_level} | Laser DMG x{player.get_weapon_amp_multiplier():.2f}",
        f"Engine Tuning L{player.engine_tuning_level} | Thrust x{player.get_engine_speed_multiplier():.2f}",
        (
            f"Warp Drive L{player.warp_drive_level} | Boost x{player.get_warp_speed_multiplier():.2f}"
            f" | Charge {player.warp_energy:.1f}/{player.get_warp_capacity_seconds():.1f}s"
        ),
        f"Scanner L{player.scanner_level} | Missile L{player.missile_level} | Payload L{player.missile_payload_level}",
        f"Missile Damage {player.get_missile_damage():.1f} | Splash {player.get_missile_splash_radius()}",
        (
            f"Shipboard Miners L{player.auto_mining_level} | Drones {player.get_auto_mining_drone_count()} "
            f"| Range {player.get_auto_mining_range():.0f}"
        ),
        (
            f"Combat L{player.combat_level} | XP {player.combat_xp}/"
            f"{player.xp_needed_for_next_combat_level()} | DMG x{player.get_combat_damage_multiplier():.2f}"
        ),
    ]

    if active_sector is not None and sector_owner_label is not None:
        sector_line = f"Sector {active_sector[0]},{active_sector[1]} | Owner {sector_owner_label}"
        if world_seed is not None:
            sector_line += f" | Seed {world_seed}"
        lines.append(sector_line)

    if command_profile is not None:
        lines.append(
            (
                f"Command L{int(command_profile.get('level', 1))} | "
                f"Territory {int(command_profile.get('territory', 1))} | "
                f"Infra {int(command_profile.get('infra', 0))} | "
                f"Defense {int(command_profile.get('defense', 0))}"
            )
        )

    if active_contract is not None:
        lines.append(
            (
                f"Contract: {active_contract['mission']} | {active_contract['amount']} {active_contract['unit']} -> "
                f"{active_contract['target_type']} {active_contract['target_sector'][0]},{active_contract['target_sector'][1]}"
            )
        )

    current_y = content_rect.y
    for line in lines:
        for wrapped in _wrap_text_lines(line, hud_font, left_col_width):
            text = hud_font.render(wrapped, True, UI_COLORS["text"])
            screen.blit(text, (content_rect.x, current_y))
            current_y += text.get_height() + 6
        current_y += 2

    right_title = panel_font.render("Systems Snapshot", True, UI_COLORS["accent_alt"])
    screen.blit(right_title, (right_col_x, content_rect.y))

    summary_lines = [
        f"Gold: {int(player.credits)}",
        f"Cargo Capacity: {player.get_cargo_capacity_units()}",
        f"Passenger Capacity: {player.get_accommodations_capacity()}",
        f"Cloak L{player.cloak_level} | {player.cloak_timer:.1f}/{player.get_cloak_capacity_seconds():.1f}s",
        f"Fire Rate L{player.fire_rate_level} | CD {player.shoot_cooldown:.2f}s",
    ]
    for idx, line in enumerate(summary_lines):
        text = hud_font.render(line, True, UI_COLORS["muted"])
        screen.blit(text, (right_col_x, content_rect.y + 32 + idx * 24))