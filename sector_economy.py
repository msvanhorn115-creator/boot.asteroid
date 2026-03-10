import random


def default_sector_economy_state(world_seed, sector):
    sx, sy = sector
    rng = random.Random((world_seed * 2654435761) ^ (sx * 92821) ^ (sy * 68917) ^ 0xC2B2AE35)

    population = 40 + rng.randint(0, 35)
    workers = max(8, int(population * 0.48))

    return {
        "population": population,
        "workers": workers,
        "stability": 1.0,
        "storage": 400,
        "resources": {
            "food": 60 + rng.randint(0, 40),
            "water": 75 + rng.randint(0, 35),
            "medical": 20 + rng.randint(0, 14),
            "accommodations": 45 + rng.randint(0, 24),
            "power": 90 + rng.randint(0, 45),
            "parts": 30 + rng.randint(0, 20),
        },
        "demand": {
            "food": max(8, int(population * 0.24)),
            "water": max(10, int(population * 0.28)),
            "medical": max(2, int(population * 0.05)),
            "accommodations": max(7, int(population * 0.2)),
            "power": max(12, int(population * 0.3)),
        },
        "producers": {
            "hydroponics": 1,
            "condenser": 1,
            "medbay": 1,
            "hab": 1,
            "reactor": 1,
            "fabricator": 1,
        },
        "facilities": {
            "mine": 0,
            "refinery": 0,
            "factory": 0,
            "depot": 0,
        },
        "logistics": {
            "capacity": 0,
            "reliability": 1.0,
            "automation": 0,
        },
        "last_tick": 0.0,
    }


def build_economy_state_cache(sector_economy_states):
    cached = {}
    for sector, state in sector_economy_states.items():
        key = f"{sector[0]},{sector[1]}"
        cached[key] = {
            "population": int(state.get("population", 0)),
            "workers": int(state.get("workers", 0)),
            "stability": float(state.get("stability", 1.0)),
            "storage": int(state.get("storage", 0)),
            "resources": dict(state.get("resources", {})),
            "demand": dict(state.get("demand", {})),
            "producers": dict(state.get("producers", {})),
            "facilities": dict(state.get("facilities", {})),
            "logistics": dict(state.get("logistics", {})),
            "last_tick": float(state.get("last_tick", 0.0)),
        }
    return cached


def restore_economy_states_from_cache(economy_state_cache):
    restored = {}
    for key, raw_state in economy_state_cache.get("sectors", {}).items():
        try:
            sx_text, sy_text = key.split(",", 1)
            sector = (int(sx_text), int(sy_text))
        except (ValueError, TypeError):
            continue

        restored[sector] = {
            "population": int(raw_state.get("population", 0)),
            "workers": int(raw_state.get("workers", 0)),
            "stability": float(raw_state.get("stability", 1.0)),
            "storage": int(raw_state.get("storage", 0)),
            "resources": dict(raw_state.get("resources", {})),
            "demand": dict(raw_state.get("demand", {})),
            "producers": dict(raw_state.get("producers", {})),
            "facilities": dict(raw_state.get("facilities", {})),
            "logistics": dict(raw_state.get("logistics", {})),
            "last_tick": float(raw_state.get("last_tick", 0.0)),
        }
    return restored
