import pygame

from constants import (
    UPGRADE_FIRE_RATE_MIN_COOLDOWN,
    UPGRADE_SHIELD_MAX_LEVEL,
    UPGRADE_MULTISHOT_MAX_LEVEL,
    UPGRADE_TARGETING_BEAM_MAX_LEVEL,
    UPGRADE_TARGETING_COMPUTER_MAX_LEVEL,
    UPGRADE_WARP_DRIVE_MAX_LEVEL,
    UPGRADE_SCANNER_MAX_LEVEL,
    UPGRADE_MISSILE_MAX_LEVEL,
    UPGRADE_CLOAK_MAX_LEVEL,
    UPGRADE_CARGO_HOLD_MAX_LEVEL,
    UPGRADE_ACCOMMODATIONS_MAX_LEVEL,
    UPGRADE_ENGINE_TUNING_MAX_LEVEL,
    UPGRADE_WEAPON_AMP_MAX_LEVEL,
    UPGRADE_DEFLECTOR_MAX_LEVEL,
    UPGRADE_MISSILE_PAYLOAD_MAX_LEVEL,
    UPGRADE_AUTO_MINING_MAX_LEVEL,
)


UPGRADE_BUTTON_KEYS = [
    "buy_fire_rate",
    "buy_shield",
    "buy_multishot",
    "buy_targeting_beam",
    "buy_targeting_computer",
    "buy_warp_drive",
    "buy_scanner",
    "buy_missile",
    "buy_cloak",
    "buy_cargo_hold",
    "buy_accommodations",
    "buy_engine_tuning",
    "buy_weapon_amp",
    "buy_deflector",
    "buy_missile_payload",
    "buy_auto_mining",
]


def compute_upgrade_cost_texts(player):
    fire_cost_text = (
        "MAXED"
        if player.shoot_cooldown <= UPGRADE_FIRE_RATE_MIN_COOLDOWN
        else f"{player.get_fire_rate_upgrade_cost()} gold"
    )
    shield_cost_text = (
        "MAXED"
        if player.shield_level >= UPGRADE_SHIELD_MAX_LEVEL
        else f"{player.get_shield_upgrade_cost()} gold"
    )
    multishot_cost_text = (
        "MAXED"
        if player.multishot_level >= UPGRADE_MULTISHOT_MAX_LEVEL
        else f"{player.get_multishot_upgrade_cost()} gold"
    )
    targeting_beam_cost_text = (
        "MAXED"
        if player.targeting_beam_level >= UPGRADE_TARGETING_BEAM_MAX_LEVEL
        else f"{player.get_targeting_beam_upgrade_cost()} gold"
    )
    targeting_computer_cost_text = (
        "MAXED"
        if player.targeting_computer_level >= UPGRADE_TARGETING_COMPUTER_MAX_LEVEL
        else f"{player.get_targeting_computer_upgrade_cost()} gold"
    )
    warp_drive_cost_text = (
        "MAXED"
        if player.warp_drive_level >= UPGRADE_WARP_DRIVE_MAX_LEVEL
        else f"{player.get_warp_drive_upgrade_cost()} gold"
    )
    scanner_cost_text = (
        "MAXED"
        if player.scanner_level >= UPGRADE_SCANNER_MAX_LEVEL
        else f"{player.get_scanner_upgrade_cost()} gold"
    )
    missile_cost_text = (
        "MAXED"
        if player.missile_level >= UPGRADE_MISSILE_MAX_LEVEL
        else f"{player.get_missile_upgrade_cost()} gold"
    )
    cloak_cost_text = (
        "MAXED"
        if player.cloak_level >= UPGRADE_CLOAK_MAX_LEVEL
        else f"{player.get_cloak_upgrade_cost()} gold"
    )
    cargo_hold_cost_text = (
        "MAXED"
        if player.cargo_hold_level >= UPGRADE_CARGO_HOLD_MAX_LEVEL
        else f"{player.get_cargo_hold_upgrade_cost()} gold"
    )
    accommodations_cost_text = (
        "MAXED"
        if player.accommodations_level >= UPGRADE_ACCOMMODATIONS_MAX_LEVEL
        else f"{player.get_accommodations_upgrade_cost()} gold"
    )
    engine_tuning_cost_text = (
        "MAXED"
        if player.engine_tuning_level >= UPGRADE_ENGINE_TUNING_MAX_LEVEL
        else f"{player.get_engine_tuning_upgrade_cost()} gold"
    )
    weapon_amp_cost_text = (
        "MAXED"
        if player.weapon_amp_level >= UPGRADE_WEAPON_AMP_MAX_LEVEL
        else f"{player.get_weapon_amp_upgrade_cost()} gold"
    )
    deflector_cost_text = (
        "MAXED"
        if player.deflector_booster_level >= UPGRADE_DEFLECTOR_MAX_LEVEL
        else f"{player.get_deflector_upgrade_cost()} gold"
    )
    missile_payload_cost_text = (
        "Need missiles"
        if player.missile_level <= 0 and player.missile_payload_level <= 0
        else (
            "MAXED"
            if player.missile_payload_level >= UPGRADE_MISSILE_PAYLOAD_MAX_LEVEL
            else f"{player.get_missile_payload_upgrade_cost()} gold"
        )
    )
    auto_mining_cost_text = (
        "MAXED"
        if player.auto_mining_level >= UPGRADE_AUTO_MINING_MAX_LEVEL
        else f"{player.get_auto_mining_upgrade_cost()} gold"
    )

    return {
        "buy_fire_rate": fire_cost_text,
        "buy_shield": shield_cost_text,
        "buy_multishot": multishot_cost_text,
        "buy_targeting_beam": targeting_beam_cost_text,
        "buy_targeting_computer": targeting_computer_cost_text,
        "buy_warp_drive": warp_drive_cost_text,
        "buy_scanner": scanner_cost_text,
        "buy_missile": missile_cost_text,
        "buy_cloak": cloak_cost_text,
        "buy_cargo_hold": cargo_hold_cost_text,
        "buy_accommodations": accommodations_cost_text,
        "buy_engine_tuning": engine_tuning_cost_text,
        "buy_weapon_amp": weapon_amp_cost_text,
        "buy_deflector": deflector_cost_text,
        "buy_missile_payload": missile_payload_cost_text,
        "buy_auto_mining": auto_mining_cost_text,
    }


def build_upgrade_lines(player):
    return [
        f"Fire Rate L{player.fire_rate_level} | Cooldown: {player.shoot_cooldown:.2f}s",
        f"Shields L{player.shield_level} | Layers: {player.shield_layers}/{player.shield_level}",
        f"Multishot L{player.multishot_level} | Pellets: {len(player.multishot_pattern())}",
        f"Targeting Beam L{player.targeting_beam_level} | Range: {player.get_targeting_beam_range()}",
        f"Targeting Computer L{player.targeting_computer_level} | Lock: {player.get_lock_time_seconds():.2f}s",
        (
            f"Warp Drive L{player.warp_drive_level} | Boost x{player.get_warp_speed_multiplier():.2f}"
            f" | Charge: {player.warp_energy:.1f}/{player.get_warp_capacity_seconds():.1f}s"
        ),
        f"Scanner Array L{player.scanner_level} | Cartography detail +{player.scanner_level}",
        (
            f"Missiles L{player.missile_level} | Cooldown: "
            f"{player.missile_cooldown_seconds():.2f}s"
        ),
        (
            f"Cloak L{player.cloak_level} | Duration: "
            f"{player.get_cloak_capacity_seconds():.1f}s"
        ),
        (
            f"Cargo Hold L{player.cargo_hold_level} | Capacity: "
            f"{player.get_cargo_capacity_units()} units"
        ),
        (
            f"Accommodations L{player.accommodations_level} | Capacity: "
            f"{player.get_accommodations_capacity()}"
        ),
        (
            f"Engine Tuning L{player.engine_tuning_level} | "
            f"Speed x{player.get_engine_speed_multiplier():.2f}"
        ),
        (
            f"Weapon Amp L{player.weapon_amp_level} | "
            f"Laser x{player.get_weapon_amp_multiplier():.2f}"
        ),
        (
            f"Deflector Array L{player.deflector_booster_level} | "
            f"Layers: {player.deflector_layers}/{player.get_deflector_capacity()}"
        ),
        (
            f"Missile Payload L{player.missile_payload_level} | "
            f"DMG: {player.get_missile_damage():.1f} | Splash: {player.get_missile_splash_radius()}"
        ),
        (
            f"Shipboard Miners L{player.auto_mining_level} | "
            f"Drones: {player.get_auto_mining_drone_count()} | Range: {player.get_auto_mining_range():.0f}"
        ),
    ]


def build_upgrade_button_rects(panel_rect):
    col_width = max(220, min(290, panel_rect.width // 2 - 64))
    left_x = panel_rect.x + 20
    right_x = left_x + col_width + 16
    y0 = panel_rect.y + 210
    step = 34

    ordered = [
        "buy_fire_rate",
        "buy_shield",
        "buy_multishot",
        "buy_targeting_beam",
        "buy_targeting_computer",
        "buy_warp_drive",
        "buy_scanner",
        "buy_missile",
        "buy_cloak",
        "buy_cargo_hold",
        "buy_accommodations",
        "buy_engine_tuning",
        "buy_weapon_amp",
        "buy_deflector",
        "buy_missile_payload",
        "buy_auto_mining",
    ]

    rects = {}
    for idx, key in enumerate(ordered):
        col = idx % 2
        row = idx // 2
        x = left_x if col == 0 else right_x
        y = y0 + row * step
        rects[key] = pygame.Rect(x, y, col_width, 30)
    return rects


def build_upgrade_button_labels(cost_texts):
    return {
        "buy_fire_rate": f"Upgrade Fire Rate ({cost_texts['buy_fire_rate']})",
        "buy_shield": f"Upgrade Shields ({cost_texts['buy_shield']})",
        "buy_multishot": f"Upgrade Multishot ({cost_texts['buy_multishot']})",
        "buy_targeting_beam": f"Upgrade Targeting Beam ({cost_texts['buy_targeting_beam']})",
        "buy_targeting_computer": (
            f"Upgrade Targeting Computer ({cost_texts['buy_targeting_computer']})"
        ),
        "buy_warp_drive": f"Upgrade Sublight Warp ({cost_texts['buy_warp_drive']})",
        "buy_scanner": f"Upgrade Scanner Array ({cost_texts['buy_scanner']})",
        "buy_missile": f"Upgrade Missiles ({cost_texts['buy_missile']})",
        "buy_cloak": f"Upgrade Cloak ({cost_texts['buy_cloak']})",
        "buy_cargo_hold": f"Upgrade Cargo Hold ({cost_texts['buy_cargo_hold']})",
        "buy_accommodations": f"Upgrade Accommodations ({cost_texts['buy_accommodations']})",
        "buy_engine_tuning": f"Upgrade Engine Tuning ({cost_texts['buy_engine_tuning']})",
        "buy_weapon_amp": f"Upgrade Weapon Amplifier ({cost_texts['buy_weapon_amp']})",
        "buy_deflector": f"Upgrade Deflector Array ({cost_texts['buy_deflector']})",
        "buy_missile_payload": f"Upgrade Missile Payload ({cost_texts['buy_missile_payload']})",
        "buy_auto_mining": f"Upgrade Shipboard Miners ({cost_texts['buy_auto_mining']})",
    }
