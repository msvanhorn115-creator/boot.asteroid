import random


def raid_settings_for_difficulty(selected_difficulty):
    if selected_difficulty == "easy":
        return {
            "interval_min": 75.0,
            "interval_max": 115.0,
            "waves": 2,
            "wave_size": 2,
            "wave_interval": 8.2,
            "timeout": 120.0,
        }
    if selected_difficulty == "hard":
        return {
            "interval_min": 36.0,
            "interval_max": 66.0,
            "waves": 4,
            "wave_size": 4,
            "wave_interval": 5.0,
            "timeout": 90.0,
        }
    return {
        "interval_min": 52.0,
        "interval_max": 86.0,
        "waves": 3,
        "wave_size": 3,
        "wave_interval": 6.4,
        "timeout": 105.0,
    }


def next_raid_interval_for_difficulty(selected_difficulty, rng=None):
    rng = random if rng is None else rng
    cfg = raid_settings_for_difficulty(selected_difficulty)
    return rng.uniform(cfg["interval_min"], cfg["interval_max"])


def claim_settings_for_difficulty(selected_difficulty):
    if selected_difficulty == "easy":
        return {"duration": 16.0, "waves": 2, "interval": 7.2}
    if selected_difficulty == "hard":
        return {"duration": 26.0, "waves": 4, "interval": 4.2}
    return {"duration": 20.0, "waves": 3, "interval": 5.6}


def difficulty_level_bias_for_difficulty(selected_difficulty):
    if selected_difficulty == "easy":
        return -1
    if selected_difficulty == "hard":
        return 1
    return 0


def enemy_level_for_contact(contact, sector, world_seed, selected_difficulty, sector_hostile_faction_fn):
    faction = contact.get("faction", sector_hostile_faction_fn(sector))
    faction_base = {
        "crimson": 2,
        "jade": 2,
        "gold": 3,
        "player": 1,
        "null": 1,
    }.get(faction, 2)

    cid = contact.get("id", "")
    jitter_seed = (world_seed * 1009) ^ hash(cid) ^ (sector[0] * 92821) ^ (sector[1] * 68917)
    jitter_rng = random.Random(jitter_seed)
    jitter = jitter_rng.choice([-1, 0, 0, 1])

    return max(1, min(10, faction_base + difficulty_level_bias_for_difficulty(selected_difficulty) + jitter))


def asteroid_level_for_radius(radius, selected_difficulty):
    base = 1 if radius <= 20 else (2 if radius <= 40 else 3)
    lvl = base + max(0, difficulty_level_bias_for_difficulty(selected_difficulty))
    return max(1, min(8, lvl))


def enemy_xp_reward(enemy_obj):
    lvl = int(getattr(enemy_obj, "combat_level", 1))
    return 10 + lvl * 8


def asteroid_xp_reward(asteroid_obj):
    lvl = int(getattr(asteroid_obj, "combat_level", 1))
    return 4 + lvl * 4
