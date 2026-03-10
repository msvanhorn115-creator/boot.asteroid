import random


FACTIONS = {
    "player": {
        "label": "Union",
        "enemy_color": "#60a5fa",
        "speed_mult": 0.95,
        "view_mult": 0.95,
    },
    "crimson": {
        "label": "Crimson Dominion",
        "enemy_color": "#ef4444",
        "speed_mult": 1.05,
        "view_mult": 1.0,
    },
    "jade": {
        "label": "Jade Syndicate",
        "enemy_color": "#10b981",
        "speed_mult": 0.98,
        "view_mult": 1.08,
    },
    "gold": {
        "label": "Aurelian Compact",
        "enemy_color": "#f59e0b",
        "speed_mult": 1.02,
        "view_mult": 0.98,
    },
    "null": {
        "label": "Null Space",
        "enemy_color": "#cbd5e1",
        "speed_mult": 1.0,
        "view_mult": 1.0,
    },
}


def _owner_rng(seed, sector):
    sx, sy = sector
    mixed = (seed * 1103515245) ^ (sx * 73856093) ^ (sy * 19349663) ^ 0x7F4A7C15
    return random.Random(mixed)


def seeded_sector_owner(seed, sector):
    if sector == (0, 0):
        return "player"

    rng = _owner_rng(seed, sector)
    roll = rng.random()
    if roll < 0.2:
        return "null"

    return rng.choice(["crimson", "jade", "gold"])


def faction_profile(faction_key):
    return FACTIONS.get(faction_key, FACTIONS["null"])
