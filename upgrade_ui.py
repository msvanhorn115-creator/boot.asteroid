import pygame

from constants import (
    UPGRADE_FIRE_RATE_MIN_COOLDOWN,
    UPGRADE_SHIELD_MAX_LEVEL,
    UPGRADE_MULTISHOT_MAX_LEVEL,
    UPGRADE_TARGETING_BEAM_MAX_LEVEL,
    UPGRADE_TARGETING_COMPUTER_MAX_LEVEL,
    UPGRADE_WARP_DRIVE_MAX_LEVEL,
    UPGRADE_SCANNER_MAX_LEVEL,
)


UPGRADE_BUTTON_KEYS = [
    "buy_fire_rate",
    "buy_shield",
    "buy_multishot",
    "buy_targeting_beam",
    "buy_targeting_computer",
    "buy_warp_drive",
    "buy_scanner",
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

    return {
        "buy_fire_rate": fire_cost_text,
        "buy_shield": shield_cost_text,
        "buy_multishot": multishot_cost_text,
        "buy_targeting_beam": targeting_beam_cost_text,
        "buy_targeting_computer": targeting_computer_cost_text,
        "buy_warp_drive": warp_drive_cost_text,
        "buy_scanner": scanner_cost_text,
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
    ]


def build_upgrade_button_rects(panel_rect):
    left_width = max(260, min(360, panel_rect.width // 2 - 56))
    y_starts = {
        "buy_fire_rate": 210,
        "buy_shield": 246,
        "buy_multishot": 282,
        "buy_targeting_beam": 318,
        "buy_targeting_computer": 354,
        "buy_warp_drive": 390,
        "buy_scanner": 426,
    }

    return {
        key: pygame.Rect(panel_rect.x + 20, panel_rect.y + y_value, left_width, 38)
        for key, y_value in y_starts.items()
    }


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
    }
