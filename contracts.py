import math
import random


def _build_job_requirements(unit_name, amount, tile_distance, risk_rating):
    req = {
        "cargo": 0,
        "accommodations": 0,
        "engine": 0,
        "scanner": 0,
    }

    if unit_name in ("passenger", "team"):
        req["accommodations"] = min(10, max(1, int(amount)))
    else:
        # Cargo ramps by payload first, then distance/risk. This keeps starter jobs
        # available while making larger contracts push upgrades naturally.
        cargo_required = (
            10
            + int(amount) * 8
            + int(tile_distance) * 4
            + max(0, int(risk_rating) - 2) * 6
        )
        req["cargo"] = min(300, max(12, cargo_required))

    # Engine/scanner are soft gates for higher-risk runs, not hard walls for all jobs.
    req["engine"] = 1 if (int(tile_distance) >= 3 and int(risk_rating) >= 3) else 0
    req["scanner"] = 1 if int(risk_rating) >= 3 else 0
    return req


def generate_jobs(origin_type, sector_manager, origin_sector, job_count=3):
    jobs = []
    used_targets = set()

    mission_prefixes = ["Freight", "Courier", "Relief", "Charter", "Priority", "Survey"]
    cargo_adjectives = [
        "sealed",
        "fragile",
        "volatile",
        "medical",
        "industrial",
        "scientific",
        "diplomatic",
        "agri",
        "luxury",
        "emergency",
        "encrypted",
    ]
    cargo_nouns = [
        "supplies",
        "containers",
        "pods",
        "modules",
        "kits",
        "archives",
        "prototypes",
        "passengers",
        "technicians",
        "data cores",
        "relief goods",
    ]
    unit_options = ["crate", "container", "pod", "module", "passenger", "team", "case"]

    destination_pool = []
    for radius in range(2, 13):
        destination_pool = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                sector = (origin_sector[0] + dx, origin_sector[1] + dy)
                tile_distance = abs(dx) + abs(dy)
                if tile_distance <= 0:
                    continue

                if len(sector_manager.get_sector_stations(sector[0], sector[1])) > 0:
                    destination_pool.append((sector, "station", tile_distance))
                if len(sector_manager.get_sector_planets(sector[0], sector[1])) > 0:
                    destination_pool.append((sector, "planet", tile_distance))

        if len(destination_pool) >= max(6, job_count * 2):
            break

    if not destination_pool:
        return jobs

    weighted_pool = []
    for sector, target_type, tile_distance in destination_pool:
        weight = max(1, tile_distance)
        weighted_pool.extend([(sector, target_type, tile_distance)] * weight)

    attempts = 0
    max_attempts = job_count * 20
    while len(jobs) < job_count and attempts < max_attempts:
        attempts += 1
        target_sector, target_type, tile_distance = random.choice(weighted_pool)
        if target_sector == origin_sector:
            continue
        target_key = (target_sector, target_type)
        if target_key in used_targets:
            continue
        used_targets.add(target_key)

        mission = random.choice(mission_prefixes)
        payload = f"{random.choice(cargo_adjectives)} {random.choice(cargo_nouns)}"
        unit_name = random.choice(unit_options)

        base_amount = random.randint(1, 5) if unit_name in ("passenger", "team") else random.randint(2, 9)
        amount = base_amount + max(0, tile_distance // 3)

        risk_seed = tile_distance * 0.75 + random.uniform(0.0, 2.2)
        if unit_name in ("passenger", "team"):
            risk_seed += 0.35
        if "volatile" in payload or "emergency" in payload:
            risk_seed += 0.8

        risk_rating = max(1, min(5, int(math.ceil(risk_seed / 2.2))))
        attack_pressure = min(3.4, 1.0 + risk_rating * 0.24 + tile_distance * 0.06)
        hazard_bonus = risk_rating * 35 + tile_distance * 8

        requirements = _build_job_requirements(unit_name, amount, tile_distance, risk_rating)

        reward_base = (
            130
            + tile_distance * random.randint(85, 150)
            + amount * random.randint(16, 40)
            + hazard_bonus
        )

        # Add clear pay separation for requirement-gated contracts.
        requirement_pressure = (
            (requirements["cargo"] / 300.0) * 0.40
            + (requirements["accommodations"] / 10.0) * 0.34
            + requirements["engine"] * 0.18
            + requirements["scanner"] * 0.14
        )
        reward_multiplier = 1.0 + risk_rating * 0.14 + requirement_pressure
        reward = int(reward_base * reward_multiplier)

        if requirements["engine"] > 0 or requirements["scanner"] > 0:
            reward += 60

        jobs.append(
            {
                "origin": origin_type,
                "origin_sector": origin_sector,
                "mission": mission,
                "payload": payload,
                "amount": amount,
                "unit": unit_name,
                "reward": reward,
                "tile_distance": tile_distance,
                "risk_rating": risk_rating,
                "hazard_bonus": hazard_bonus,
                "attack_pressure": attack_pressure,
                "target_sector": target_sector,
                "target_type": target_type,
                "requirements": requirements,
            }
        )

    return jobs
