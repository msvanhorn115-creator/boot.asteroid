def apply_upgrade(player, upgrade_key):
    """Apply an upgrade and return (success, message, event_data)."""

    if upgrade_key == "fire_rate":
        success, message = player.buy_fire_rate_upgrade()
        event_data = {
            "upgrade": "fire_rate",
            "level": player.fire_rate_level,
            "credits_left": player.credits,
            "shoot_cooldown": round(player.shoot_cooldown, 3),
        }
        return success, message, event_data

    if upgrade_key == "shield":
        success, message = player.buy_shield_upgrade()
        event_data = {
            "upgrade": "shield",
            "level": player.shield_level,
            "shield_layers": player.shield_layers,
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "multishot":
        success, message = player.buy_multishot_upgrade()
        event_data = {
            "upgrade": "multishot",
            "level": player.multishot_level,
            "pellets": len(player.multishot_pattern()),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "targeting_beam":
        success, message = player.buy_targeting_beam_upgrade()
        event_data = {
            "upgrade": "targeting_beam",
            "level": player.targeting_beam_level,
            "range": player.get_targeting_beam_range(),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "targeting_computer":
        success, message = player.buy_targeting_computer_upgrade()
        event_data = {
            "upgrade": "targeting_computer",
            "level": player.targeting_computer_level,
            "lock_time": player.get_lock_time_seconds(),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "warp_drive":
        success, message = player.buy_warp_drive_upgrade()
        event_data = {
            "upgrade": "warp_drive",
            "level": player.warp_drive_level,
            "speed_multiplier": player.get_warp_speed_multiplier(),
            "capacity_seconds": player.get_warp_capacity_seconds(),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "scanner":
        success, message = player.buy_scanner_upgrade()
        event_data = {
            "upgrade": "scanner",
            "level": player.scanner_level,
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "missile":
        success, message = player.buy_missile_upgrade()
        event_data = {
            "upgrade": "missile",
            "level": player.missile_level,
            "cooldown": round(player.missile_cooldown_seconds(), 2),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "cloak":
        success, message = player.buy_cloak_upgrade()
        event_data = {
            "upgrade": "cloak",
            "level": player.cloak_level,
            "capacity": round(player.get_cloak_capacity_seconds(), 2),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "cargo_hold":
        success, message = player.buy_cargo_hold_upgrade()
        event_data = {
            "upgrade": "cargo_hold",
            "level": player.cargo_hold_level,
            "capacity": player.get_cargo_capacity_units(),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "accommodations":
        success, message = player.buy_accommodations_upgrade()
        event_data = {
            "upgrade": "accommodations",
            "level": player.accommodations_level,
            "capacity": player.get_accommodations_capacity(),
            "credits_left": player.credits,
        }
        return success, message, event_data

    if upgrade_key == "engine_tuning":
        success, message = player.buy_engine_tuning_upgrade()
        event_data = {
            "upgrade": "engine_tuning",
            "level": player.engine_tuning_level,
            "speed_mult": round(player.get_engine_speed_multiplier(), 2),
            "credits_left": player.credits,
        }
        return success, message, event_data

    raise ValueError(f"Unknown upgrade key: {upgrade_key}")
