import random


# 15 strategic tile anchors used by both gameplay spawn and scanner intel.
STRATEGIC_TILES = [
    (0.14, 0.14), (0.32, 0.14), (0.50, 0.14), (0.68, 0.14), (0.86, 0.14),
    (0.22, 0.33), (0.50, 0.33), (0.78, 0.33),
    (0.14, 0.52), (0.32, 0.52), (0.50, 0.52), (0.68, 0.52), (0.86, 0.52),
    (0.28, 0.78), (0.72, 0.78),
]


# Pre-arranged "openings" like chess starts: tile index + enemy role.
OPENINGS = [
    [(6, "tank"), (1, "harasser"), (3, "harasser"), (10, "bomber")],
    [(10, "tank"), (5, "harasser"), (7, "harasser"), (1, "bomber"), (3, "bomber")],
    [(6, "harasser"), (9, "tank"), (11, "tank"), (0, "bomber"), (4, "bomber")],
    [(10, "harasser"), (5, "harasser"), (7, "harasser"), (13, "tank"), (14, "tank")],
    [(6, "tank"), (8, "bomber"), (12, "bomber"), (2, "harasser")],
    [(6, "tank"), (10, "tank"), (0, "harasser"), (4, "harasser"), (13, "bomber")],
    [(9, "harasser"), (10, "harasser"), (11, "harasser"), (6, "bomber"), (14, "tank")],
    [(6, "tank"), (5, "bomber"), (7, "bomber"), (9, "harasser"), (11, "harasser")],
]


def _rng_for_sector(world_seed, sector):
    sx, sy = sector
    mixed = (world_seed * 1000003) ^ (sx * 92821) ^ (sy * 68917) ^ 0xA341316C
    return random.Random(mixed)


def _filter_role(role, allow_tank):
    if allow_tank:
        return role
    return "harasser" if role == "tank" else role


def opening_contacts(world_seed, sector, allow_tank=True):
    rng = _rng_for_sector(world_seed, sector)
    opening = OPENINGS[rng.randrange(len(OPENINGS))]

    contacts = []
    for idx, (tile_idx, role) in enumerate(opening):
        tx, ty = STRATEGIC_TILES[tile_idx % len(STRATEGIC_TILES)]
        # Tiny deterministic jitter keeps formations from feeling too rigid.
        jx = rng.uniform(-0.018, 0.018)
        jy = rng.uniform(-0.018, 0.018)
        contacts.append(
            {
                "id": f"{sector[0]}:{sector[1]}:open:{idx}",
                "x": max(0.05, min(0.95, tx + jx)),
                "y": max(0.05, min(0.95, ty + jy)),
                "type": _filter_role(role, allow_tank),
                "alive": True,
                "opening": True,
            }
        )
    return contacts


def reinforcement_contact(world_seed, sector, existing_contacts, allow_tank=True):
    rng = _rng_for_sector(world_seed + 777, sector)

    occupied_tiles = set()
    for c in existing_contacts:
        nearest_idx = min(
            range(len(STRATEGIC_TILES)),
            key=lambda i: abs(STRATEGIC_TILES[i][0] - c.get("x", 0.5)) + abs(STRATEGIC_TILES[i][1] - c.get("y", 0.5)),
        )
        occupied_tiles.add(nearest_idx)

    candidates = [i for i in range(len(STRATEGIC_TILES)) if i not in occupied_tiles]
    if not candidates:
        candidates = list(range(len(STRATEGIC_TILES)))

    tile_idx = rng.choice(candidates)
    tx, ty = STRATEGIC_TILES[tile_idx]
    role = rng.choices(["bomber", "harasser", "tank"], weights=[3, 4, 2], k=1)[0]
    role = _filter_role(role, allow_tank)

    next_id = f"{sector[0]}:{sector[1]}:reinforce:{len(existing_contacts)}"
    return {
        "id": next_id,
        "x": tx,
        "y": ty,
        "type": role,
        "alive": True,
        "opening": False,
    }
