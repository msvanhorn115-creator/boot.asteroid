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

    raise ValueError(f"Unknown upgrade key: {upgrade_key}")
