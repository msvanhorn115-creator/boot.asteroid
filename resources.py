import random

# Grounded sci-fi economy: common industrial metals are frequent and cheap,
# while precious/high-tech metals are rare and valuable.
METAL_ECONOMY = {
    "iron": {"price": 2, "weight": 34},
    "nickel": {"price": 4, "weight": 22},
    "cobalt": {"price": 7, "weight": 15},
    "titanium": {"price": 11, "weight": 11},
    "silver": {"price": 19, "weight": 7},
    "gold": {"price": 32, "weight": 5},
    "platinum": {"price": 52, "weight": 3},
    "iridium": {"price": 78, "weight": 2},
}

METAL_COLORS = {
    "iron": (141, 153, 174),
    "nickel": (165, 177, 195),
    "cobalt": (86, 124, 201),
    "titanium": (171, 190, 209),
    "silver": (205, 216, 228),
    "gold": (236, 192, 74),
    "platinum": (212, 223, 236),
    "iridium": (170, 143, 216),
}

# Collection visibility and clarity:
# terminal nodes always drop, and larger splits can occasionally drop fragments.
TERMINAL_NODE_DROP_CHANCE = 1.0
SPLIT_NODE_DROP_CHANCE = 0.22

_DROP_RATE_MULTIPLIER = 1.0


def set_drop_rate_multiplier(multiplier):
    global _DROP_RATE_MULTIPLIER
    _DROP_RATE_MULTIPLIER = max(0.1, float(multiplier))


def get_terminal_drop_chance():
    return min(1.0, TERMINAL_NODE_DROP_CHANCE * _DROP_RATE_MULTIPLIER)


def get_split_drop_chance():
    return min(1.0, SPLIT_NODE_DROP_CHANCE * _DROP_RATE_MULTIPLIER)


def get_metal_prices():
    return {metal: data["price"] for metal, data in METAL_ECONOMY.items()}


def choose_metal_type(rng=None):
    if rng is None:
        rng = random

    metals = list(METAL_ECONOMY.keys())
    weights = [METAL_ECONOMY[m]["weight"] for m in metals]
    return rng.choices(metals, weights=weights, k=1)[0]


def get_metal_color(metal_type):
    return METAL_COLORS.get(metal_type, (220, 220, 220))
