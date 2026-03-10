import sys
import random
import math
import os
import pygame

from constants import *
from logger import log_state, log_event
from player import Player
from asteroid import Asteroid
from shot import Shot
from enemy import Enemy, SuicideBomber, Harasser, Tank
from station import Station
from planet import Planet
from sector_manager import SectorManager
from resources import get_metal_prices, set_drop_rate_multiplier
from targeting import beam_first_hit
from upgrade_ui import UPGRADE_BUTTON_KEYS
from station_panel import draw_station_panel, resolve_station_click
from planet_panel import draw_planet_panel, resolve_planet_click
from ship_panel import draw_ship_panel
from upgrade_actions import apply_upgrade
from menu_panel import draw_menu_panel
from map_panel import draw_map_panel, map_sector_at_point, map_tile_parity_ok
from ui_theme import UI_COLORS
from audio_manager import AudioManager
from display_setup import init_display, DisplayInitError
from contracts import generate_jobs
from enemy_openings import opening_contacts, reinforcement_contact, STRATEGIC_TILES
from territory import seeded_sector_owner, faction_profile
from game_balance import (
    raid_settings_for_difficulty,
    next_raid_interval_for_difficulty,
    claim_settings_for_difficulty,
    enemy_level_for_contact as compute_enemy_level_for_contact,
    asteroid_level_for_radius as compute_asteroid_level_for_radius,
    enemy_xp_reward as compute_enemy_xp_reward,
    asteroid_xp_reward as compute_asteroid_xp_reward,
)
from sector_economy import (
    default_sector_economy_state as compute_default_sector_economy_state,
    build_economy_state_cache,
    restore_economy_states_from_cache,
)
from constants import (
    STATION_LEVEL_BASE_COST,
    STATION_LEVEL_STEP_COST,
    STATION_LEVEL_MAX,
    STATION_LASER_BASE_COST,
    STATION_LASER_STEP_COST,
    STATION_LASER_MAX,
    STATION_MISSILE_BASE_COST,
    STATION_MISSILE_STEP_COST,
    STATION_MISSILE_MAX,
)
from effects import (
    draw_ship_explosion_fx,
    spawn_metal_pickup_fx,
    spawn_ship_explosion_fx,
    step_and_draw_metal_pickup_fx,
    update_ship_explosion_fx,
)


DIFFICULTY_SETTINGS = {
    "easy": {
        "label": "Easy",
        "asteroid_spawn": 1.05,
        "enemy_spawn": 8.4,
        "asteroid_speed": 0.85,
        "asteroid_max_kind": 2,
        "enemy_speed": 0.88,
        "enemy_health": 0.85,
        "enemy_view": 0.92,
        "enemy_shoot_cooldown": 1.2,
        "enemy_weights": [2, 2, 1],
        "enemy_max_alive": 3,
        "drop_rate": 1.25,
        "sell_multiplier": 1.2,
        "upgrade_cost_multiplier": 0.85,
        "player_shoot_cooldown_multiplier": 0.9,
    },
    "normal": {
        "label": "Normal",
        "asteroid_spawn": ASTEROID_SPAWN_RATE_SECONDS,
        "enemy_spawn": ENEMY_SPAWN_RATE_SECONDS,
        "asteroid_speed": 1.0,
        "asteroid_max_kind": ASTEROID_KINDS,
        "enemy_speed": 1.0,
        "enemy_health": 1.0,
        "enemy_view": 1.0,
        "enemy_shoot_cooldown": 1.0,
        "enemy_weights": [1, 1, 1],
        "enemy_max_alive": 5,
        "drop_rate": 1.0,
        "sell_multiplier": 1.0,
        "upgrade_cost_multiplier": 1.0,
        "player_shoot_cooldown_multiplier": 1.0,
    },
    "hard": {
        "label": "Hard",
        "asteroid_spawn": 0.62,
        "enemy_spawn": 2.8,
        "asteroid_speed": 1.25,
        "asteroid_max_kind": 3,
        "enemy_speed": 1.25,
        "enemy_health": 1.35,
        "enemy_view": 1.2,
        "enemy_shoot_cooldown": 0.75,
        "enemy_weights": [2, 3, 3],
        "enemy_max_alive": 8,
        "drop_rate": 0.85,
        "sell_multiplier": 0.86,
        "upgrade_cost_multiplier": 1.18,
        "player_shoot_cooldown_multiplier": 1.1,
    },
}

BUILD_STATION_COST = 900


def main():
    print("Starting Asteroids")
    print(f"Screen width: {SCREEN_WIDTH}")
    print(f"Screen height: {SCREEN_HEIGHT}")

    pygame.init()
    try:
        screen, selected_video_driver = init_display(SCREEN_WIDTH, SCREEN_HEIGHT)
    except DisplayInitError as exc:
        print("Display initialization failed.")
        if exc.errors:
            print("Tried drivers:", " | ".join(exc.errors))
        print("Try running with: SDL_VIDEODRIVER=wayland or SDL_VIDEODRIVER=x11")
        shutdown_code = 1
        pygame.quit()
        raise SystemExit(shutdown_code)

    print(f"Video driver: {selected_video_driver}")
    pygame.display.set_caption("Asteroid Miner")
    clock = pygame.time.Clock()

    world_seed = int(os.environ.get("ASTEROID_WORLD_SEED", "1337"))
    sector_manager = SectorManager(world_seed, sector_size=SCREEN_WIDTH, sector_height=SCREEN_HEIGHT)

    # Keep audio concerns in one place so gameplay loop state stays focused.
    audio = AudioManager(__file__)

    def play_sfx(name):
        audio.play_sfx(name)

    def draw_hud_chip(text, x, y, color=None):
        fg = UI_COLORS["text"] if color is None else color
        label = hud_font.render(text, True, fg)
        bg_rect = pygame.Rect(x, y, label.get_width() + 16, label.get_height() + 8)
        pygame.draw.rect(screen, (9, 16, 29, 188), bg_rect, border_radius=8)
        pygame.draw.rect(screen, (58, 76, 106), bg_rect, 1, border_radius=8)
        screen.blit(label, (x + 8, y + 4))
        return bg_rect

    hud_font = pygame.font.SysFont("dejavusansmono", 18)
    panel_font = pygame.font.SysFont("dejavusans", 23)
    title_font = pygame.font.SysFont("freesansbold", 40)

    dt = 0.0
    elapsed_time = 0.0

    def shutdown_game(exit_code=0, hard=False):
        audio.shutdown()
        pygame.quit()
        if hard:
            os._exit(exit_code)
        raise SystemExit(exit_code)

    # Background seed data
    bg_rng = random.Random(world_seed ^ 0x51EAD5)

    stars = []
    for _ in range(STAR_COUNT):
        tier_roll = bg_rng.random()
        if tier_roll < 0.72:
            tier = "far"
            size = 1
            depth = bg_rng.uniform(0.16, 0.46)
        elif tier_roll < 0.95:
            tier = "mid"
            size = bg_rng.choice([1, 2])
            depth = bg_rng.uniform(0.42, 0.82)
        else:
            tier = "near"
            size = 2
            depth = bg_rng.uniform(0.78, 1.08)

        stars.append(
            {
                "x": bg_rng.uniform(0, SCREEN_WIDTH),
                "y": bg_rng.uniform(0, SCREEN_HEIGHT),
                "size": size,
                "phase": bg_rng.uniform(0, 6.283),
                "depth": depth,
                "tier": tier,
                "pulse_speed": bg_rng.uniform(0.7, 1.5),
                "hue": bg_rng.choice(
                    [
                        (225, 235, 255),
                        (210, 230, 255),
                        (255, 232, 208),
                        (208, 245, 255),
                    ]
                ),
            }
        )

    stardust = []
    for _ in range(80):
        stardust.append(
            {
                "x": bg_rng.uniform(0, SCREEN_WIDTH),
                "y": bg_rng.uniform(0, SCREEN_HEIGHT),
                "depth": bg_rng.uniform(0.05, 0.22),
                "phase": bg_rng.uniform(0, 6.283),
                "alpha": bg_rng.randint(24, 56),
            }
        )

    shooting_stars = []
    shooting_star_timer = bg_rng.uniform(6.0, 12.0)

    nebula_clouds = []
    for _ in range(NEBULA_CLOUD_COUNT):
        nebula_clouds.append(
            {
                "x": bg_rng.uniform(0, SCREEN_WIDTH),
                "y": bg_rng.uniform(0, SCREEN_HEIGHT),
                "radius": bg_rng.randint(80, 220),
                "depth": bg_rng.uniform(0.08, 0.22),
                "phase": bg_rng.uniform(0, 6.283),
                "color": bg_rng.choice(
                    [
                        (48, 76, 120, 26),
                        (30, 90, 120, 24),
                        (70, 50, 115, 24),
                        (20, 110, 95, 22),
                    ]
                ),
            }
        )

    backdrop_gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for gy in range(SCREEN_HEIGHT):
        t = gy / max(1, SCREEN_HEIGHT - 1)
        r = int(3 + 5 * t)
        g = int(7 + 8 * t)
        b = int(14 + 13 * t)
        pygame.draw.line(backdrop_gradient, (r, g, b), (0, gy), (SCREEN_WIDTH, gy))

    def spawn_shooting_star():
        start_x = bg_rng.uniform(-0.15 * SCREEN_WIDTH, 0.9 * SCREEN_WIDTH)
        start_y = bg_rng.uniform(-0.25 * SCREEN_HEIGHT, 0.2 * SCREEN_HEIGHT)
        direction = pygame.Vector2(bg_rng.uniform(0.75, 1.05), bg_rng.uniform(0.55, 0.9))
        if direction.length_squared() <= 1e-6:
            return
        direction = direction.normalize()
        speed = bg_rng.uniform(460, 700)
        shooting_stars.append(
            {
                "pos": pygame.Vector2(start_x, start_y),
                "vel": direction * speed,
                "life": bg_rng.uniform(0.42, 0.75),
                "max_life": bg_rng.uniform(0.42, 0.75),
                "trail": bg_rng.randint(40, 70),
            }
        )

    def draw_wrapped_circle(target, color, cx, cy, radius):
        wrapped_x = cx % SCREEN_WIDTH
        wrapped_y = cy % SCREEN_HEIGHT
        for dx in (-SCREEN_WIDTH, 0, SCREEN_WIDTH):
            for dy in (-SCREEN_HEIGHT, 0, SCREEN_HEIGHT):
                pygame.draw.circle(
                    target,
                    color,
                    (int(wrapped_x + dx), int(wrapped_y + dy)),
                    radius,
                )

    # Runtime gameplay objects (created on New Game)
    updatable = None
    drawable = None
    asteroids = None
    shots = None
    enemies = None
    stations = None
    planets = None
    player = None
    station_sprites_by_id = {}
    planet_sprites_by_id = {}
    destroyed_seed_asteroids = set()
    world_offset = pygame.Vector2(0, 0)
    active_sector = (0, 0)

    station_message = ""
    station_message_timer = 0.0
    is_docked = False
    docked_context = None
    docked_station = None
    docked_planet = None
    station_tab = "upgrade"
    metal_pickup_fx = []
    ship_explosion_fx = []
    god_mode = False
    selected_difficulty = "normal"
    metal_prices = get_metal_prices()
    active_difficulty = DIFFICULTY_SETTINGS[selected_difficulty]
    enemy_field = None
    base_enemy_spawn_interval = active_difficulty["enemy_spawn"]
    base_enemy_max_alive = active_difficulty["enemy_max_alive"]
    current_enemy_spawn_interval = base_enemy_spawn_interval
    current_enemy_max_alive = base_enemy_max_alive
    station_ui = {
        "sell_tab": None,
        "upgrade_tab": None,
        "sell_all": None,
        "undock": None,
    }
    for key in UPGRADE_BUTTON_KEYS:
        station_ui[key] = None

    planet_ui = {
        "trade": None,
        "undock": None,
    }
    for idx in range(3):
        planet_ui[f"job_{idx}"] = None
    ship_ui = {
        "tab_inventory": None,
        "tab_map": None,
    }

    available_jobs = []
    active_contract = None
    explored_sectors = {}
    live_sector_intel = {}
    persistent_sector_enemies = {}
    scanner_cooldown_timer = 0.0
    scanner_passive_timer = 0.0
    sector_enemy_entry_grace_timer = 0.0
    sector_owner_overrides = {(0, 0): "player"}
    station_owner_overrides = {}
    planet_owner_overrides = {}
    built_stations_by_sector = {}
    station_upgrades = {}
    sector_economy_states = {}
    economy_state_cache = {"version": 1, "sectors": {}}
    station_defense_fire_timer = 0.0
    enemy_station_fire_timer = 0.0
    home_sector = (0, 0)
    home_station_id = None
    home_planet_id = None
    raid_events = {}
    raid_spawn_timer = 50.0
    claim_operation = {
        "active": False,
        "sector": (0, 0),
        "target_kind": None,
        "target_id": None,
        "faction": None,
        "owner": None,
        "progress": 0.0,
        "duration": 20.0,
        "wave_timer": 0.0,
        "wave_interval": 6.0,
        "waves_remaining": 0,
    }
    claim_initiated_targets = set()

    game_state = "menu"  # menu | playing | paused
    has_active_game = False
    targeting_locked_targets = []
    targeting_mode_timer = 0.0
    targeting_mode_duration = 3.0

    menu_ui = {
        "action": None,
        "quit": None,
        "controls": None,
        "audio": None,
        "map": None,
        "music_slider": None,
        "sfx_slider": None,
        "easy": None,
        "normal": None,
        "hard": None,
    }
    show_controls_overlay = False
    show_audio_overlay = False
    show_map_overlay = False
    show_ship_overlay = False
    ship_tab = "inventory"
    audio_slider_dragging = None

    def normalize_in_sector(world_x, world_y, sector_x, sector_y):
        origin_x = sector_x * sector_manager.sector_width
        origin_y = sector_y * sector_manager.sector_height
        nx = (world_x - origin_x) / float(sector_manager.sector_width)
        ny = (world_y - origin_y) / float(sector_manager.sector_height)
        return max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))

    def sector_owner(sector):
        if sector in sector_owner_overrides:
            return sector_owner_overrides[sector]

        # Hostiles can patrol empty sectors, but ownership requires a station.
        stations_data = get_sector_stations_with_built(sector[0], sector[1])
        if not stations_data:
            return "null"

        return station_owner(stations_data[0][0])

    def default_sector_economy_state(sector):
        return compute_default_sector_economy_state(world_seed, sector)

    def ensure_player_sector_economy(sector):
        if sector_owner(sector) != "player":
            return None

        state = sector_economy_states.get(sector)
        if state is None:
            state = default_sector_economy_state(sector)
            sector_economy_states[sector] = state
        return state

    def remove_non_player_sector_economy(sector):
        if sector_owner(sector) != "player":
            sector_economy_states.pop(sector, None)

    def refresh_owned_sector_economy_states():
        owned = {home_sector}
        for sector, owner in sector_owner_overrides.items():
            if owner == "player":
                owned.add(sector)

        for sector in owned:
            ensure_player_sector_economy(sector)

        for sector in list(sector_economy_states.keys()):
            if sector not in owned and sector_owner(sector) != "player":
                sector_economy_states.pop(sector, None)

    def snapshot_economy_state_cache():
        economy_state_cache["sectors"] = build_economy_state_cache(sector_economy_states)

    def load_economy_state_cache():
        sector_economy_states.clear()
        sector_economy_states.update(restore_economy_states_from_cache(economy_state_cache))
        refresh_owned_sector_economy_states()

    def default_site_owner(sector):
        # Sites are always claimed by a faction unless explicitly player-owned.
        # Null/player outcomes are remapped to a deterministic hostile faction.
        seeded = seeded_sector_owner(world_seed, sector)
        if seeded in ("crimson", "jade", "gold"):
            return seeded

        sx, sy = sector
        rng = random.Random((world_seed * 6364136223846793005) ^ (sx * 92821) ^ (sy * 68917) ^ 0xB5297A4D)
        return rng.choice(["crimson", "jade", "gold"])

    def sector_hostile_faction(sector):
        owner = sector_owner(sector)
        if owner in ("crimson", "jade", "gold"):
            return owner
        return default_site_owner(sector)

    def parse_station_sector(station_id):
        parts = station_id.split(":")
        if len(parts) < 2:
            return active_sector
        return int(parts[0]), int(parts[1])

    def parse_planet_sector(planet_id):
        parts = planet_id.split(":")
        if len(parts) < 3:
            return active_sector
        return int(parts[1]), int(parts[2])

    def owner_label(owner_key):
        return faction_profile(owner_key).get("label", owner_key.title())

    def station_owner(station_id):
        if station_id in station_owner_overrides:
            return station_owner_overrides[station_id]
        if home_station_id is not None and station_id == home_station_id:
            return "player"
        return default_site_owner(parse_station_sector(station_id))

    def enemy_station_level(station_id):
        sx, sy = parse_station_sector(station_id)
        diff_bias = 0 if selected_difficulty == "easy" else (1 if selected_difficulty == "normal" else 2)
        rng = random.Random((world_seed * 1597) ^ hash(station_id) ^ (sx * 92821) ^ (sy * 68917))
        lvl = 1 + diff_bias + rng.choice([0, 0, 1, 1, 2])
        return max(1, min(STATION_LEVEL_MAX, lvl))

    def get_station_upgrade_state(station_id):
        state = station_upgrades.get(station_id)
        if state is None:
            if station_owner(station_id) == "player":
                state = {"level": 1, "laser": 0, "missile": 0}
            else:
                lvl = enemy_station_level(station_id)
                state = {
                    "level": lvl,
                    "laser": max(0, min(STATION_LASER_MAX, lvl - 1)),
                    "missile": max(0, min(STATION_MISSILE_MAX, lvl - 1)),
                }
            station_upgrades[station_id] = state
        return state

    def station_level(station_id):
        return int(get_station_upgrade_state(station_id).get("level", 1))

    def station_laser_level(station_id):
        return int(get_station_upgrade_state(station_id).get("laser", 0))

    def station_missile_level(station_id):
        return int(get_station_upgrade_state(station_id).get("missile", 0))

    def station_level_upgrade_cost(station_id):
        lvl = station_level(station_id)
        return STATION_LEVEL_BASE_COST + (lvl - 1) * STATION_LEVEL_STEP_COST

    def station_laser_upgrade_cost(station_id):
        lvl = station_laser_level(station_id)
        return STATION_LASER_BASE_COST + lvl * STATION_LASER_STEP_COST

    def station_missile_upgrade_cost(station_id):
        lvl = station_missile_level(station_id)
        return STATION_MISSILE_BASE_COST + lvl * STATION_MISSILE_STEP_COST

    def fire_station_projectile(station_obj, target_pos, owner, kind, level):
        if station_obj is None or target_pos is None:
            return False

        delta = pygame.Vector2(target_pos) - station_obj.position
        if delta.length_squared() <= 1e-6:
            return False

        direction = delta.normalize()
        if kind == "laser":
            shot = Shot(station_obj.position.x, station_obj.position.y, max(2, SHOT_RADIUS), owner=owner)
            shot.velocity = direction * (PLAYER_SHOOT_SPEED * 1.05)
            shot.life = 1.1
            shot.damage = 0.9 + level * 0.42
        else:
            shot = Shot(station_obj.position.x, station_obj.position.y, SHOT_RADIUS + 2, owner=owner)
            shot.velocity = direction * (PLAYER_SHOOT_SPEED * 0.72)
            shot.life = 1.6
            shot.damage = 1.7 + level * 0.62
            shot.splash_radius = 54 + level * 12
            shot.splash_falloff = 0.5
        return True

    def planet_owner(planet_id):
        if planet_id in planet_owner_overrides:
            return planet_owner_overrides[planet_id]
        if home_planet_id is not None and planet_id == home_planet_id:
            return "player"
        return default_site_owner(parse_planet_sector(planet_id))

    def get_sector_stations_with_built(sector_x, sector_y):
        stations_data = list(sector_manager.get_sector_stations(sector_x, sector_y))
        built = built_stations_by_sector.get((sector_x, sector_y))
        if built is not None:
            stations_data.append(built)
        return stations_data

    def stations_around_with_built(center_sector_x, center_sector_y, radius=1):
        stations_data = []
        for sy in range(center_sector_y - radius, center_sector_y + radius + 1):
            for sx in range(center_sector_x - radius, center_sector_x + radius + 1):
                stations_data.extend(get_sector_stations_with_built(sx, sy))
        return stations_data

    def build_status_for_sector(sector):
        has_station = len(get_sector_stations_with_built(sector[0], sector[1])) > 0
        if has_station:
            return ("Build: this sector already has a station", "#94a3b8")
        if player is None or player.credits < BUILD_STATION_COST:
            return (f"Build: need {BUILD_STATION_COST} gold (press B)", "#fca5a5")
        return (f"Build Station: press B ({BUILD_STATION_COST}g)", "#86efac")

    def raid_settings():
        return raid_settings_for_difficulty(selected_difficulty)

    def next_raid_interval():
        return next_raid_interval_for_difficulty(selected_difficulty)

    def spawn_hostile_wave(target_sector, hostile_faction, count=2, entry_mode="tile"):
        if enemies is None:
            return
        pack = get_persistent_sector_enemies(target_sector)
        contacts = pack.get("contacts", [])
        for _ in range(max(1, int(count))):
            new_contact = reinforcement_contact(world_seed, target_sector, contacts, allow_tank=True)
            new_contact["faction"] = hostile_faction
            new_contact["entry_mode"] = entry_mode
            contacts.append(new_contact)
            if target_sector == active_sector:
                spawn_contact_enemy(new_contact)

    def start_random_raid():
        nonlocal station_message, station_message_timer
        candidates = [
            sector
            for sector, owner in sector_owner_overrides.items()
            if owner == "player" and sector not in raid_events and sector != home_sector
        ]
        if not candidates:
            return False

        target_sector = random.choice(candidates)
        raider = random.choice(["crimson", "jade", "gold"])
        cfg = raid_settings()
        raid_events[target_sector] = {
            "faction": raider,
            "waves_remaining": cfg["waves"],
            "wave_size": cfg["wave_size"],
            "wave_timer": 0.0,
            "wave_interval": cfg["wave_interval"],
            "age": 0.0,
            "timeout": cfg["timeout"],
        }

        station_message = (
            f"Raid alert: {owner_label(raider)} attacking sector "
            f"{target_sector[0]},{target_sector[1]}"
        )
        station_message_timer = 2.4
        play_sfx("pause")
        return True

    def strip_control_in_sector(sector, new_owner):
        if sector == home_sector:
            return
        sector_owner_overrides[sector] = new_owner
        for station_id in list(station_owner_overrides.keys()):
            if parse_station_sector(station_id) == sector:
                station_owner_overrides[station_id] = new_owner
        for planet_id in list(planet_owner_overrides.keys()):
            if parse_planet_sector(planet_id) == sector:
                planet_owner_overrides[planet_id] = new_owner
        remove_non_player_sector_economy(sector)
        snapshot_economy_state_cache()

    def update_raid_events(dt_seconds):
        nonlocal raid_spawn_timer, station_message, station_message_timer

        raid_spawn_timer = max(0.0, raid_spawn_timer - dt_seconds)
        if raid_spawn_timer <= 0.0:
            started = start_random_raid()
            raid_spawn_timer = next_raid_interval()
            if not started:
                raid_spawn_timer = max(18.0, raid_spawn_timer * 0.5)

        resolved = []
        for sector, raid in list(raid_events.items()):
            raid["age"] += dt_seconds

            if sector == active_sector:
                raid["wave_timer"] = max(0.0, raid["wave_timer"] - dt_seconds)
                if raid["waves_remaining"] > 0 and raid["wave_timer"] <= 0.0:
                    spawn_hostile_wave(
                        sector,
                        raid["faction"],
                        count=raid.get("wave_size", 2),
                    )
                    raid["waves_remaining"] -= 1
                    raid["wave_timer"] = raid.get("wave_interval", 6.0)

                pack = get_persistent_sector_enemies(sector)
                live_contacts = [c for c in pack.get("contacts", []) if c.get("alive", False)]
                if raid["waves_remaining"] <= 0 and not live_contacts:
                    resolved.append(sector)
                    station_message = f"Raid repelled in sector {sector[0]},{sector[1]}"
                    station_message_timer = 1.8
                    play_sfx("upgrade")
                    continue

            if raid["age"] >= raid.get("timeout", 100.0):
                strip_control_in_sector(sector, raid["faction"])
                resolved.append(sector)
                if sector == active_sector:
                    load_active_sector_enemies(reset_grace=True)
                station_message = (
                    f"Sector {sector[0]},{sector[1]} lost to {owner_label(raid['faction'])}"
                )
                station_message_timer = 2.2
                play_sfx("player_hit")

        for sector in resolved:
            raid_events.pop(sector, None)

    def claim_settings():
        return claim_settings_for_difficulty(selected_difficulty)

    def enemy_level_for_contact(contact, sector):
        return compute_enemy_level_for_contact(
            contact,
            sector,
            world_seed,
            selected_difficulty,
            sector_hostile_faction,
        )

    def asteroid_level_for_radius(radius):
        return compute_asteroid_level_for_radius(radius, selected_difficulty)

    def enemy_xp_reward(enemy_obj):
        return compute_enemy_xp_reward(enemy_obj)

    def asteroid_xp_reward(asteroid_obj):
        return compute_asteroid_xp_reward(asteroid_obj)

    def award_player_xp(amount):
        nonlocal station_message, station_message_timer
        if player is None:
            return
        gained_levels = player.award_combat_xp(amount)
        if gained_levels > 0:
            station_message = f"Combat level up! L{player.combat_level}"
            station_message_timer = 1.8
            play_sfx("upgrade")

    def cancel_claim(reason_text):
        claim_operation["active"] = False
        claim_operation["target_kind"] = None
        claim_operation["target_id"] = None
        claim_operation["faction"] = None
        claim_operation["owner"] = None
        claim_operation["progress"] = 0.0
        claim_operation["waves_remaining"] = 0
        claim_operation["wave_timer"] = 0.0
        claim_operation["duration"] = 20.0
        claim_operation["wave_interval"] = 6.0
        return reason_text

    def start_claim_operation(target_kind, target_id, owner_key):
        nonlocal is_docked, docked_context, docked_station, docked_planet
        nonlocal station_message, station_message_timer, available_jobs

        if claim_operation["active"]:
            station_message = "Claim already in progress"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return

        target_key = (target_kind, target_id)
        if target_key in claim_initiated_targets:
            station_message = "Claim already initiated here"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return

        settings = claim_settings()
        claim_faction = owner_key if owner_key not in ("player", "null") else "crimson"
        station_tier_bonus = 0
        if target_kind == "station" and target_id:
            station_tier_bonus = max(0, station_level(target_id) - 1)
        claim_operation["active"] = True
        claim_operation["sector"] = active_sector
        claim_operation["target_kind"] = target_kind
        claim_operation["target_id"] = target_id
        claim_operation["faction"] = claim_faction
        claim_operation["owner"] = owner_key
        claim_operation["progress"] = 0.0
        claim_operation["duration"] = settings["duration"]
        claim_operation["wave_interval"] = settings["interval"]
        claim_operation["wave_timer"] = settings["interval"]
        claim_operation["waves_remaining"] = settings["waves"] + min(2, station_tier_bonus)
        claim_initiated_targets.add(target_key)

        # Claiming is an active operation: undock and defend the sector timer.
        is_docked = False
        docked_context = None
        docked_station = None
        docked_planet = None
        available_jobs = []

        spawn_hostile_wave(
            active_sector,
            claim_faction,
            count=2 + min(2, station_tier_bonus),
            entry_mode="offscreen",
        )
        claim_operation["waves_remaining"] = max(0, claim_operation["waves_remaining"] - 1)

        station_message = (
            f"Claim started against {owner_label(owner_key)}. Hold sector for "
            f"{int(claim_operation['duration'])}s"
        )
        station_message_timer = 2.2
        play_sfx("upgrade")

    def complete_claim_operation():
        nonlocal station_message, station_message_timer, available_jobs
        target_kind = claim_operation.get("target_kind")
        target_id = claim_operation.get("target_id")
        claim_sector = claim_operation.get("sector", active_sector)

        if target_kind == "station" and target_id:
            station_owner_overrides[target_id] = "player"
            available_jobs = generate_jobs("station", sector_manager, origin_sector=claim_sector)
        elif target_kind == "planet" and target_id:
            planet_owner_overrides[target_id] = "player"
            available_jobs = generate_jobs("planet", sector_manager, origin_sector=claim_sector)

        sector_owner_overrides[claim_sector] = "player"
        ensure_player_sector_economy(claim_sector)
        snapshot_economy_state_cache()

        if claim_sector == active_sector:
            pack = get_persistent_sector_enemies(claim_sector)
            for contact in pack.get("contacts", []):
                contact["alive"] = False
            for enemy in list(enemies):
                enemy.kill()

        cancel_claim("")
        station_message = "Claim complete. Sector secured by Union"
        station_message_timer = 2.2
        play_sfx("upgrade")

    def capture_sector_snapshot(sector_x, sector_y, visited=False, charted=False):
        stations_data = get_sector_stations_with_built(sector_x, sector_y)
        planets_data = sector_manager.get_sector_planets(sector_x, sector_y)
        asteroid_data = sector_manager.get_sector_asteroids(sector_x, sector_y)

        stations = []
        for _, world_x, world_y in stations_data:
            nx, ny = normalize_in_sector(world_x, world_y, sector_x, sector_y)
            stations.append({"x": nx, "y": ny})

        planets = []
        for _, world_x, world_y, accepted_metal, color in planets_data:
            nx, ny = normalize_in_sector(world_x, world_y, sector_x, sector_y)
            planets.append(
                {
                    "x": nx,
                    "y": ny,
                    "metal": accepted_metal,
                    "color": color,
                }
            )

        asteroid_count = 0
        for asteroid_id, *_ in asteroid_data:
            if asteroid_id in destroyed_seed_asteroids:
                continue
            asteroid_count += 1

        previous = explored_sectors.get((sector_x, sector_y), {})
        explored_sectors[(sector_x, sector_y)] = {
            "has_station": len(stations) > 0,
            "has_planet": len(planets) > 0,
            "asteroid_density": asteroid_count,
            "stations": stations,
            "planets": planets,
            "visited": bool(visited or previous.get("visited", False)),
            "charted": bool(charted or visited or previous.get("charted", False)),
        }

    def scanner_cooldown_for_level(level):
        # L0 no remote scan, L1-L4 progressively faster scans.
        return [999.0, 10.0, 7.0, 5.0, 3.5][max(0, min(4, int(level)))]

    def get_persistent_sector_enemies(sector):
        pack = persistent_sector_enemies.get(sector)
        if pack is None:
            owner = sector_owner(sector)
            hostile_faction = sector_hostile_faction(sector)
            opening_size = max(2, min(5, int(base_enemy_max_alive) - 1))
            contacts = []
            if owner != "player":
                contacts = opening_contacts(world_seed, sector, allow_tank=True)[:opening_size]
                for contact in contacts:
                    contact["faction"] = hostile_faction

            pack = {
                "contacts": contacts,
                "reinforce_timer": 10.0,
                "faction": hostile_faction,
            }
            persistent_sector_enemies[sector] = pack
        return pack

    def enemy_class_for_role(role):
        if role == "bomber":
            return SuicideBomber
        if role == "tank":
            return Tank
        return Harasser

    def spawn_contact_enemy(contact):
        enemy_cls = enemy_class_for_role(contact.get("type", "harasser"))
        target_x = max(24.0, min(SCREEN_WIDTH - 24.0, float(contact.get("x", 0.5)) * SCREEN_WIDTH))
        target_y = max(24.0, min(SCREEN_HEIGHT - 24.0, float(contact.get("y", 0.5)) * SCREEN_HEIGHT))
        ex = target_x
        ey = target_y

        entry_mode = contact.get("entry_mode", "tile")
        if entry_mode == "offscreen":
            # Start beyond view bounds so reinforcements visibly enter the sector.
            entry_margin = 64.0
            entry_rng = random.Random((world_seed * 31337) ^ hash(contact.get("id", "")))
            side = entry_rng.choice(["left", "right", "top", "bottom"])
            if side == "left":
                ex = -entry_margin
                ey = target_y + entry_rng.uniform(-90.0, 90.0)
            elif side == "right":
                ex = SCREEN_WIDTH + entry_margin
                ey = target_y + entry_rng.uniform(-90.0, 90.0)
            elif side == "top":
                ex = target_x + entry_rng.uniform(-120.0, 120.0)
                ey = -entry_margin
            else:
                ex = target_x + entry_rng.uniform(-120.0, 120.0)
                ey = SCREEN_HEIGHT + entry_margin

            ex = max(-entry_margin, min(SCREEN_WIDTH + entry_margin, ex))
            ey = max(-entry_margin, min(SCREEN_HEIGHT + entry_margin, ey))

        if player is not None and entry_mode != "offscreen":
            safe_spawn_radius = max(170.0, player.radius + 120.0)
            spawn_pos = pygame.Vector2(ex, ey)
            if spawn_pos.distance_to(player.position) < safe_spawn_radius:
                # Keep openings tactical but never spawn directly on the ship.
                fallback = None
                farthest_dist = -1.0
                for tx, ty in STRATEGIC_TILES:
                    fx = max(24.0, min(SCREEN_WIDTH - 24.0, tx * SCREEN_WIDTH))
                    fy = max(24.0, min(SCREEN_HEIGHT - 24.0, ty * SCREEN_HEIGHT))
                    d = player.position.distance_to((fx, fy))
                    if d > farthest_dist:
                        farthest_dist = d
                        fallback = (fx, fy)

                if fallback is not None:
                    ex, ey = fallback
                    contact["x"] = ex / float(SCREEN_WIDTH)
                    contact["y"] = ey / float(SCREEN_HEIGHT)

        enemy = enemy_cls(
            ex,
            ey,
            speed_multiplier=active_difficulty["enemy_speed"],
            health_multiplier=active_difficulty["enemy_health"],
            view_multiplier=active_difficulty["enemy_view"],
            shoot_cooldown_multiplier=active_difficulty["enemy_shoot_cooldown"],
        )
        enemy.combat_level = enemy_level_for_contact(contact, active_sector)
        faction_key = contact.get("faction", "null")
        f_profile = faction_profile(faction_key)
        enemy.faction_key = faction_key
        enemy.color_override = f_profile.get("enemy_color", enemy.COLOR)
        enemy.speed_multiplier *= float(f_profile.get("speed_mult", 1.0))
        enemy.view_range *= float(f_profile.get("view_mult", 1.0))
        level_scale = 1.0 + (max(1, enemy.combat_level) - 1) * 0.08
        enemy.health = max(1, int(round(enemy.health * level_scale)))
        enemy.speed_multiplier *= 1.0 + (max(1, enemy.combat_level) - 1) * 0.03
        enemy.view_range *= 1.0 + (max(1, enemy.combat_level) - 1) * 0.02
        enemy.contact_id = contact.get("id")
        if entry_mode == "offscreen":
            enemy.entry_target = pygame.Vector2(target_x, target_y)
            enemy.entry_timer = 4.0
            enemy.no_wrap_timer = 4.0
            enemy.forced_target_timer = 10.0
        return enemy

    def load_active_sector_enemies(reset_grace=False):
        nonlocal sector_enemy_entry_grace_timer
        if enemies is None:
            return

        for enemy in list(enemies):
            enemy.kill()

        pack = get_persistent_sector_enemies(active_sector)
        for contact in pack.get("contacts", []):
            if contact.get("alive", True):
                spawn_contact_enemy(contact)

        if reset_grace:
            # Give room to solve each opening before reinforcements arrive.
            sector_enemy_entry_grace_timer = 14.0
            pack["reinforce_timer"] = max(8.0, current_enemy_spawn_interval * 2.6)

    def update_persistent_sector_enemies(dt_seconds):
        nonlocal sector_enemy_entry_grace_timer
        if player is None:
            return

        if sector_owner(active_sector) == "player":
            return

        pack = get_persistent_sector_enemies(active_sector)
        sector_enemy_entry_grace_timer = max(0.0, sector_enemy_entry_grace_timer - dt_seconds)
        if sector_enemy_entry_grace_timer > 0.0:
            return

        contacts = pack.get("contacts", [])
        alive_contacts = [c for c in contacts if c.get("alive", False)]
        if len(alive_contacts) >= int(current_enemy_max_alive):
            return

        pack["reinforce_timer"] = max(0.0, float(pack.get("reinforce_timer", 0.0)) - dt_seconds)
        if pack["reinforce_timer"] > 0.0:
            return

        new_contact = reinforcement_contact(world_seed, active_sector, contacts, allow_tank=True)
        new_contact["faction"] = pack.get("faction", sector_owner(active_sector))
        contacts.append(new_contact)
        spawn_contact_enemy(new_contact)
        pack["reinforce_timer"] = max(8.0, current_enemy_spawn_interval * 2.6)

    def sync_active_sector_enemies_to_persistent():
        if enemies is None:
            return

        pack = get_persistent_sector_enemies(active_sector)
        contacts = pack.get("contacts", [])
        by_id = {c.get("id"): c for c in contacts}

        for contact in contacts:
            contact["alive"] = False

        for enemy in list(enemies):
            if not enemy.alive():
                continue
            contact_id = getattr(enemy, "contact_id", None)
            if not contact_id:
                continue

            contact = by_id.get(contact_id)
            if contact is None:
                contact = {
                    "id": contact_id,
                    "type": "harasser",
                    "x": 0.5,
                    "y": 0.5,
                    "alive": True,
                    "opening": False,
                }
                contacts.append(contact)
                by_id[contact_id] = contact

            contact["x"] = max(0.0, min(1.0, enemy.position.x / float(SCREEN_WIDTH)))
            contact["y"] = max(0.0, min(1.0, enemy.position.y / float(SCREEN_HEIGHT)))
            contact["alive"] = True

    def scanner_pulse_offsets(level):
        lvl = max(0, min(4, int(level)))
        if lvl <= 1:
            return [(0, 0)]
        if lvl == 2:
            return [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
        return [
            (dx, dy)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
        ]

    def scan_sector(sector):
        if player is None:
            return False

        sx, sy = sector
        snapshot = explored_sectors.get(sector)
        if snapshot is None:
            capture_sector_snapshot(sx, sy, visited=False, charted=True)
            snapshot = explored_sectors.get(sector, {})
        elif not snapshot.get("charted", False):
            capture_sector_snapshot(sx, sy, visited=False, charted=True)
            snapshot = explored_sectors.get(sector, {})

        visited = bool(snapshot.get("visited", False))

        asteroid_points = []
        asteroid_count = 0
        for asteroid_id, world_x, world_y, radius, _, _ in sector_manager.get_sector_asteroids(sx, sy):
            if asteroid_id in destroyed_seed_asteroids:
                continue
            nx, ny = normalize_in_sector(world_x, world_y, sx, sy)
            asteroid_points.append(
                {
                    "x": nx,
                    "y": ny,
                    "r": radius,
                }
            )
            asteroid_count += 1

        enemy_points = []

        if sector == active_sector:
            # Ensure active-sector scan reflects exact live local entities.
            asteroid_points = []
            if asteroids is not None:
                for asteroid in list(asteroids):
                    if not asteroid.alive():
                        continue
                    asteroid_world = asteroid.position + world_offset
                    asx, asy = sector_manager.world_to_sector(asteroid_world)
                    if (asx, asy) != sector:
                        continue
                    anx, any_ = normalize_in_sector(asteroid_world.x, asteroid_world.y, sx, sy)
                    asteroid_points.append({"x": anx, "y": any_, "r": int(asteroid.radius)})
            asteroid_count = len(asteroid_points)

            enemy_points = []
            if enemies is not None:
                for enemy in list(enemies):
                    if not enemy.alive():
                        continue
                    enx = max(0.0, min(1.0, enemy.position.x / float(SCREEN_WIDTH)))
                    eny = max(0.0, min(1.0, enemy.position.y / float(SCREEN_HEIGHT)))
                    enemy_points.append({"x": enx, "y": eny})
        else:
            pack = get_persistent_sector_enemies(sector)
            contacts = pack.get("contacts", [])
            enemy_points = [
                {"x": c.get("x", 0.5), "y": c.get("y", 0.5)}
                for c in contacts
                if c.get("alive", False)
            ]

        live_sector_intel[sector] = {
            "ships": len(enemy_points),
            "asteroids_current": asteroid_count,
            "enemy_points": enemy_points,
            "asteroid_points": asteroid_points,
        }

        if not visited:
            capture_sector_snapshot(sx, sy, visited=False, charted=True)

        return True

    def perform_scanner_pulse(center_sector, force=False):
        nonlocal scanner_cooldown_timer, scanner_passive_timer
        if player is None or player.scanner_level <= 0:
            return 0

        if not force and scanner_cooldown_timer > 0:
            return 0

        scanned = 0
        offsets = scanner_pulse_offsets(player.scanner_level)
        for dx, dy in offsets:
            sector = (center_sector[0] + dx, center_sector[1] + dy)
            if scan_sector(sector):
                scanned += 1

        if not force:
            scanner_cooldown_timer = scanner_cooldown_for_level(player.scanner_level)
            scanner_passive_timer = 0.0
        return scanned

    def apply_scanner_reveal():
        if player is None:
            return
        capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)

    def contract_attack_pressure():
        if active_contract is None:
            return 1.0
        return max(1.0, float(active_contract.get("attack_pressure", 1.0)))

    def try_complete_contract():
        nonlocal active_contract, station_message, station_message_timer, available_jobs
        if active_contract is None:
            station_message = "No active contract selected"
            station_message_timer = 1.2
            return

        if active_sector != active_contract["target_sector"]:
            station_message = (
                f"Wrong sector. Need {active_contract['target_sector'][0]},"
                f"{active_contract['target_sector'][1]}"
            )
            station_message_timer = 1.5
            return

        if docked_context != active_contract["target_type"]:
            station_message = f"Need to dock at a {active_contract['target_type']}"
            station_message_timer = 1.5
            return

        if docked_context == "station" and docked_station is not None:
            if station_owner(docked_station.station_id) != "player":
                station_message = "Claim this station first (press C while docked)"
                station_message_timer = 1.6
                return
        if docked_context == "planet" and docked_planet is not None:
            if planet_owner(docked_planet.planet_id) != "player":
                station_message = "Claim this planet first (press C while docked)"
                station_message_timer = 1.6
                return

        player.credits += active_contract["reward"]
        station_message = f"Delivery complete: +{active_contract['reward']} gold"
        station_message_timer = 1.8
        log_event("contract_complete", **active_contract, total_gold=player.credits)
        active_contract = None
        if docked_context in ("station", "planet"):
            available_jobs = generate_jobs(docked_context, sector_manager, origin_sector=active_sector)

    def handle_job_slot(job_index):
        nonlocal active_contract, station_message, station_message_timer, available_jobs
        if job_index < 0 or job_index >= len(available_jobs):
            return
        selected = available_jobs[job_index]

        if active_contract is not None:
            station_message = "One active contract at a time"
            station_message_timer = 1.5
            return

        if docked_context == "station" and docked_station is not None:
            if station_owner(docked_station.station_id) != "player":
                station_message = "Claim this station first (press C while docked)"
                station_message_timer = 1.6
                return
        if docked_context == "planet" and docked_planet is not None:
            if planet_owner(docked_planet.planet_id) != "player":
                station_message = "Claim this planet first (press C while docked)"
                station_message_timer = 1.6
                return

        req = selected.get("requirements", {})
        missing = []
        if player.get_cargo_capacity_units() < int(req.get("cargo", 0)):
            missing.append(f"Cargo {player.get_cargo_capacity_units()}/{int(req.get('cargo', 0))}")
        if player.get_accommodations_capacity() < int(req.get("accommodations", 0)):
            missing.append(
                f"Accommodations {player.get_accommodations_capacity()}/{int(req.get('accommodations', 0))}"
            )
        if player.engine_tuning_level < int(req.get("engine", 0)):
            missing.append(f"Engine L{player.engine_tuning_level}/{int(req.get('engine', 0))}")
        if player.scanner_level < int(req.get("scanner", 0)):
            missing.append(f"Scanner L{player.scanner_level}/{int(req.get('scanner', 0))}")
        if missing:
            station_message = "Requirements not met: " + ", ".join(missing)
            station_message_timer = 2.2
            play_sfx("ui_click")
            return

        active_contract = selected
        del available_jobs[job_index]
        station_message = (
            f"Accepted: {selected['mission']} ({selected['amount']} {selected['unit']}) -> "
            f"{selected['target_type']} {selected['target_sector'][0]},{selected['target_sector'][1]}"
        )
        station_message_timer = 2.2

    def init_new_game(difficulty_key):
        nonlocal updatable, drawable, asteroids, shots, enemies, stations, planets
        nonlocal player, station_message, station_message_timer
        nonlocal is_docked, docked_context, docked_planet, station_tab, metal_pickup_fx, ship_explosion_fx
        nonlocal docked_station
        nonlocal metal_prices, active_difficulty
        nonlocal targeting_locked_targets, targeting_mode_timer
        nonlocal station_sprites_by_id, planet_sprites_by_id, world_offset, active_sector
        nonlocal destroyed_seed_asteroids
        nonlocal available_jobs, active_contract, explored_sectors, show_map_overlay, show_ship_overlay, ship_tab
        nonlocal live_sector_intel, persistent_sector_enemies, scanner_cooldown_timer, scanner_passive_timer
        nonlocal enemy_field, base_enemy_spawn_interval, base_enemy_max_alive
        nonlocal current_enemy_spawn_interval, current_enemy_max_alive
        nonlocal sector_enemy_entry_grace_timer
        nonlocal sector_owner_overrides, station_owner_overrides, planet_owner_overrides
        nonlocal built_stations_by_sector
        nonlocal raid_events, raid_spawn_timer
        nonlocal home_station_id, home_planet_id
        nonlocal station_upgrades, station_defense_fire_timer, enemy_station_fire_timer
        nonlocal sector_economy_states, economy_state_cache
        nonlocal claim_initiated_targets

        updatable = pygame.sprite.Group()
        drawable = pygame.sprite.Group()
        asteroids = pygame.sprite.Group()
        shots = pygame.sprite.Group()
        enemies = pygame.sprite.Group()
        stations = pygame.sprite.Group()
        planets = pygame.sprite.Group()

        Player.containers = (updatable, drawable)
        Asteroid.containers = (asteroids, updatable, drawable)
        Shot.containers = (shots, updatable, drawable)
        Enemy.containers = (enemies, updatable, drawable)
        Station.containers = (stations, drawable)
        Planet.containers = (planets, drawable)

        settings = DIFFICULTY_SETTINGS[difficulty_key]
        active_difficulty = settings

        set_drop_rate_multiplier(settings["drop_rate"])

        base_prices = get_metal_prices()
        metal_prices = {
            metal: max(1, int(round(price * settings["sell_multiplier"])))
            for metal, price in base_prices.items()
        }

        player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        player.on_shoot = lambda: play_sfx("player_shoot")
        player.configure_difficulty(
            shoot_cooldown_multiplier=settings["player_shoot_cooldown_multiplier"],
            upgrade_cost_multiplier=settings["upgrade_cost_multiplier"],
        )

        enemy_field = None
        base_enemy_spawn_interval = settings["enemy_spawn"]
        base_enemy_max_alive = settings["enemy_max_alive"]
        current_enemy_spawn_interval = base_enemy_spawn_interval
        current_enemy_max_alive = base_enemy_max_alive
        station_sprites_by_id = {}
        planet_sprites_by_id = {}
        destroyed_seed_asteroids = set()
        world_offset = pygame.Vector2(0, 0)
        active_sector = (0, 0)
        sync_station_sectors(force=True)
        sync_planet_sectors(force=True)
        sync_asteroid_sectors(force=True)

        station_message = f"New game: {settings['label']}"
        station_message_timer = 1.8
        is_docked = False
        docked_context = None
        docked_station = None
        docked_planet = None
        station_tab = "upgrade"
        metal_pickup_fx = []
        ship_explosion_fx = []
        targeting_locked_targets = []
        targeting_mode_timer = 0.0
        available_jobs = generate_jobs("station", sector_manager, origin_sector=active_sector)
        active_contract = None
        explored_sectors = {}
        live_sector_intel = {}
        persistent_sector_enemies = {}
        scanner_cooldown_timer = 0.0
        scanner_passive_timer = 0.0
        sector_enemy_entry_grace_timer = 0.0
        sector_owner_overrides = {home_sector: "player"}
        station_owner_overrides = {}
        planet_owner_overrides = {}
        built_stations_by_sector = {}
        station_upgrades = {}
        sector_economy_states = {}
        economy_state_cache = {"version": 1, "sectors": {}}
        station_defense_fire_timer = 0.0
        enemy_station_fire_timer = 0.0

        home_stations = list(sector_manager.get_sector_stations(home_sector[0], home_sector[1]))
        if not home_stations:
            station_id = f"{home_sector[0]}:{home_sector[1]}:home"
            world_x = home_sector[0] * sector_manager.sector_width + sector_manager.sector_width * 0.5
            world_y = home_sector[1] * sector_manager.sector_height + sector_manager.sector_height * 0.5
            built_stations_by_sector[home_sector] = (station_id, world_x, world_y)
            home_station_id = station_id
        else:
            home_station_id = home_stations[0][0]

        home_planets = list(sector_manager.get_sector_planets(home_sector[0], home_sector[1]))
        home_planet_id = home_planets[0][0] if home_planets else None

        if home_station_id is not None:
            station_owner_overrides[home_station_id] = "player"
            station_upgrades[home_station_id] = {"level": 1, "laser": 0, "missile": 0}
        if home_planet_id is not None:
            planet_owner_overrides[home_planet_id] = "player"
        claim_operation.update(
            {
                "active": False,
                "sector": (0, 0),
                "target_kind": None,
                "target_id": None,
                "faction": None,
                "owner": None,
                "progress": 0.0,
                "duration": 20.0,
                "wave_timer": 0.0,
                "wave_interval": 6.0,
                "waves_remaining": 0,
            }
        )
        claim_initiated_targets = set()
        raid_events = {}
        raid_spawn_timer = next_raid_interval()
        refresh_owned_sector_economy_states()
        load_economy_state_cache()
        snapshot_economy_state_cache()
        show_map_overlay = False
        show_ship_overlay = False
        ship_tab = "inventory"
        load_active_sector_enemies(reset_grace=True)
        capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
        apply_scanner_reveal()

    def nearest_enemies_for_lock(max_locks):
        if not player or not enemies or max_locks <= 0:
            return []

        live_enemies = [enemy for enemy in list(enemies) if enemy.alive()]
        live_enemies.sort(key=lambda enemy: player.position.distance_to(enemy.position))
        return live_enemies[:max_locks]

    def sync_station_sectors(force=False):
        nonlocal active_sector, station_sprites_by_id
        if player is None:
            return False

        player_world = player.position + world_offset
        center_sector = sector_manager.world_to_sector(player_world)
        if not force and center_sector == active_sector:
            return False

        previous_sector = active_sector
        active_sector = center_sector
        desired_ids = set()
        stations_data = stations_around_with_built(center_sector[0], center_sector[1], radius=1)
        station_edge_buffer = 120

        for station_id, world_x, world_y in stations_data:
            local_x = world_x - world_offset.x
            local_y = world_y - world_offset.y
            # Keep stations away from screen boundaries to avoid edge pop-in.
            if local_x < station_edge_buffer or local_x > SCREEN_WIDTH - station_edge_buffer:
                continue
            if local_y < station_edge_buffer or local_y > SCREEN_HEIGHT - station_edge_buffer:
                continue

            desired_ids.add(station_id)
            station_sprite = station_sprites_by_id.get(station_id)
            if station_sprite is None or not station_sprite.alive():
                station_sprite = Station(local_x, local_y)
                station_sprite.station_id = station_id
                station_sprites_by_id[station_id] = station_sprite
            else:
                station_sprite.position.update(local_x, local_y)

        for station_id in list(station_sprites_by_id.keys()):
            if station_id not in desired_ids:
                sprite = station_sprites_by_id.pop(station_id)
                if sprite.alive():
                    sprite.kill()

        return previous_sector != active_sector

    def sync_planet_sectors(force=False):
        nonlocal planet_sprites_by_id
        if player is None:
            return

        player_world = player.position + world_offset
        center_sector = sector_manager.world_to_sector(player_world)
        if not force and center_sector == active_sector:
            return

        desired_ids = set()
        planets_data = sector_manager.planets_around(center_sector[0], center_sector[1], radius=1)
        planet_edge_buffer = 140

        for planet_id, world_x, world_y, accepted_metal, color in planets_data:
            local_x = world_x - world_offset.x
            local_y = world_y - world_offset.y
            if local_x < planet_edge_buffer or local_x > SCREEN_WIDTH - planet_edge_buffer:
                continue
            if local_y < planet_edge_buffer or local_y > SCREEN_HEIGHT - planet_edge_buffer:
                continue

            desired_ids.add(planet_id)
            planet_sprite = planet_sprites_by_id.get(planet_id)
            if planet_sprite is None or not planet_sprite.alive():
                planet_sprite = Planet(local_x, local_y, accepted_metal, color)
                planet_sprite.planet_id = planet_id
                planet_sprites_by_id[planet_id] = planet_sprite
            else:
                planet_sprite.position.update(local_x, local_y)

        for planet_id in list(planet_sprites_by_id.keys()):
            if planet_id not in desired_ids:
                sprite = planet_sprites_by_id.pop(planet_id)
                if sprite.alive():
                    sprite.kill()

    def sync_asteroid_sectors(force=False):
        if player is None:
            return
        if not force and active_sector == (0, 0) and not asteroids:
            return

        for asteroid in list(asteroids):
            asteroid.kill()

        asteroid_specs = sector_manager.asteroids_around(active_sector[0], active_sector[1], radius=1)
        safe_spawn_radius = 180
        for asteroid_id, world_x, world_y, radius, vx, vy in asteroid_specs:
            if asteroid_id in destroyed_seed_asteroids:
                continue

            local_x = world_x - world_offset.x
            local_y = world_y - world_offset.y
            if local_x < -280 or local_x > SCREEN_WIDTH + 280:
                continue
            if local_y < -280 or local_y > SCREEN_HEIGHT + 280:
                continue

            # Prevent sector refreshes from spawning junk directly on the ship.
            if player.position.distance_to((local_x, local_y)) < safe_spawn_radius + radius:
                continue

            asteroid = Asteroid(local_x, local_y, radius)
            asteroid.velocity = pygame.Vector2(vx, vy)
            asteroid.wrap_enabled = False
            asteroid.seeded_id = asteroid_id
            asteroid.combat_level = asteroid_level_for_radius(radius)

    def update_world_offset_from_wrap(prev_position, new_position):
        nonlocal station_message, station_message_timer
        wrapped = False

        if prev_position.x > SCREEN_WIDTH * 0.5 and new_position.x < 0:
            world_offset.x += SCREEN_WIDTH
            wrapped = True
        elif prev_position.x < SCREEN_WIDTH * 0.5 and new_position.x > SCREEN_WIDTH:
            world_offset.x -= SCREEN_WIDTH
            wrapped = True

        if prev_position.y > SCREEN_HEIGHT * 0.5 and new_position.y < 0:
            world_offset.y += SCREEN_HEIGHT
            wrapped = True
        elif prev_position.y < SCREEN_HEIGHT * 0.5 and new_position.y > SCREEN_HEIGHT:
            world_offset.y -= SCREEN_HEIGHT
            wrapped = True

        if wrapped:
            sector_changed = sync_station_sectors(force=True)
            sync_planet_sectors(force=True)
            sync_asteroid_sectors(force=True)
            if sector_changed:
                load_active_sector_enemies(reset_grace=True)
                capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
                apply_scanner_reveal()
                station_message = f"Entered sector {active_sector[0]},{active_sector[1]}"
                station_message_timer = 1.3

    def nearest_station_in_range():
        if not player or not stations:
            return None

        candidates = []
        for station in list(stations):
            distance = player.position.distance_to(station.position)
            if distance <= STATION_INTERACT_DISTANCE:
                candidates.append((distance, station))

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def nearest_planet_in_range():
        if not player or not planets:
            return None

        candidates = []
        for planet in list(planets):
            distance = player.position.distance_to(planet.position)
            if distance <= STATION_INTERACT_DISTANCE + 24:
                candidates.append((distance, planet))

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def get_active_contract_planet():
        if active_contract is None or active_contract.get("target_type") != "planet":
            return None

        target_sector = active_contract.get("target_sector")
        if not target_sector:
            return None

        prefix = f"p:{target_sector[0]}:{target_sector[1]}:"
        candidates = [
            planet
            for planet in planet_sprites_by_id.values()
            if getattr(planet, "planet_id", "").startswith(prefix)
        ]
        if not candidates:
            return None

        candidates.sort(key=lambda p: player.position.distance_to(p.position))
        return candidates[0]

    def get_active_contract_station():
        if active_contract is None or active_contract.get("target_type") != "station":
            return None

        target_sector = active_contract.get("target_sector")
        if not target_sector:
            return None

        prefix = f"{target_sector[0]}:{target_sector[1]}:"
        candidates = [
            station
            for station_id, station in station_sprites_by_id.items()
            if station_id.startswith(prefix)
        ]
        if not candidates:
            return None

        candidates.sort(key=lambda s: player.position.distance_to(s.position))
        return candidates[0]

    def get_active_contract_target_object():
        if active_contract is None:
            return None
        if active_contract.get("target_type") == "planet":
            return get_active_contract_planet()
        if active_contract.get("target_type") == "station":
            return get_active_contract_station()
        return None

    def draw_dotted_line(start, end, color, dash=10, gap=7, width=2):
        delta = end - start
        length = delta.length()
        if length <= 0:
            return
        direction = delta.normalize()

        distance = 0.0
        while distance < length:
            seg_start = start + direction * distance
            seg_end = start + direction * min(distance + dash, length)
            pygame.draw.line(
                screen,
                color,
                (int(seg_start.x), int(seg_start.y)),
                (int(seg_end.x), int(seg_end.y)),
                width,
            )
            distance += dash + gap

    def draw_offscreen_arrow(start, end, color, label="Contract", offset_text=None):
        direction = end - start
        if direction.length_squared() <= 0:
            return
        direction = direction.normalize()

        pulse = 0.72 + 0.28 * math.sin(elapsed_time * 6.5)
        glow_color = (
            min(255, int(color[0] * pulse + 22)),
            min(255, int(color[1] * pulse + 22)),
            min(255, int(color[2] * pulse + 22)),
        )

        edge_rect = pygame.Rect(28, 28, SCREEN_WIDTH - 56, SCREEN_HEIGHT - 56)
        intersections = []

        if abs(direction.x) > 1e-6:
            t_left = (edge_rect.left - start.x) / direction.x
            y_left = start.y + direction.y * t_left
            if t_left > 0 and edge_rect.top <= y_left <= edge_rect.bottom:
                intersections.append((t_left, pygame.Vector2(edge_rect.left, y_left)))

            t_right = (edge_rect.right - start.x) / direction.x
            y_right = start.y + direction.y * t_right
            if t_right > 0 and edge_rect.top <= y_right <= edge_rect.bottom:
                intersections.append((t_right, pygame.Vector2(edge_rect.right, y_right)))

        if abs(direction.y) > 1e-6:
            t_top = (edge_rect.top - start.y) / direction.y
            x_top = start.x + direction.x * t_top
            if t_top > 0 and edge_rect.left <= x_top <= edge_rect.right:
                intersections.append((t_top, pygame.Vector2(x_top, edge_rect.top)))

            t_bottom = (edge_rect.bottom - start.y) / direction.y
            x_bottom = start.x + direction.x * t_bottom
            if t_bottom > 0 and edge_rect.left <= x_bottom <= edge_rect.right:
                intersections.append((t_bottom, pygame.Vector2(x_bottom, edge_rect.bottom)))

        if not intersections:
            return

        intersections.sort(key=lambda item: item[0])
        tip = intersections[0][1]

        side = pygame.Vector2(-direction.y, direction.x)
        base = tip - direction * 18
        p1 = tip
        p2 = base + side * 9
        p3 = base - side * 9

        pygame.draw.polygon(
            screen,
            glow_color,
            [(int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), (int(p3.x), int(p3.y))],
        )
        pygame.draw.polygon(
            screen,
            "#0b1220",
            [(int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), (int(p3.x), int(p3.y))],
            1,
        )

        label_pos = tip - direction * 34 + side * 12
        label_text = hud_font.render(label, True, glow_color)
        screen.blit(label_text, (int(label_pos.x), int(label_pos.y)))
        if offset_text:
            offset_surface = hud_font.render(offset_text, True, "#cbd5e1")
            screen.blit(offset_surface, (int(label_pos.x), int(label_pos.y + 16)))

    def contract_target_hint_point(target_obj):
        if target_obj is not None:
            return target_obj.position

        if active_contract is None:
            return None

        target_sector = active_contract.get("target_sector")
        if not target_sector:
            return None

        dx = target_sector[0] - active_sector[0]
        dy = target_sector[1] - active_sector[1]
        if dx == 0 and dy == 0:
            return None

        heading = pygame.Vector2(dx, dy)
        if heading.length_squared() <= 0:
            return None

        heading = heading.normalize()
        reach = max(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.95
        return player.position + heading * reach

    def sell_to_planet(planet):
        nonlocal station_message, station_message_timer
        if planet_owner(planet.planet_id) != "player":
            station_message = "Claim this planet first (press C while docked)"
            station_message_timer = 1.6
            play_sfx("ui_click")
            return
        metal_type = planet.accepted_metal
        unit_price = metal_prices.get(metal_type, 0)
        sold_units, gained = player.sell_metal_type(metal_type, unit_price)
        if sold_units <= 0:
            station_message = f"Planet buys {metal_type}. You have none."
            station_message_timer = 1.6
            play_sfx("ui_click")
            return

        station_message = f"Sold {sold_units} {metal_type} for {gained} gold"
        station_message_timer = 1.8
        log_event(
            "planet_trade",
            metal=metal_type,
            quantity=sold_units,
            gold=gained,
            total_gold=player.credits,
        )
        play_sfx("sell")

    def sell_all_metals():
        nonlocal station_message, station_message_timer
        if docked_station is not None and station_owner(docked_station.station_id) != "player":
            station_message = "Claim this station first (press C while docked)"
            station_message_timer = 1.6
            play_sfx("ui_click")
            return
        projected_credits = player.projected_sell_value(metal_prices)
        sold_metals, credits_gained = player.sell_all_metals(metal_prices)
        total_units = sum(sold_metals.values())
        if total_units > 0:
            play_sfx("sell")
            station_message = f"Sold {total_units} metal for {credits_gained} cr"
            log_event(
                "resources_sold",
                sold_metals=sold_metals,
                credits_gained=credits_gained,
                total_credits=player.credits,
                projected_credits=projected_credits,
            )
        else:
            station_message = "No metals to sell"
            play_sfx("ui_click")
        station_message_timer = 2.0

    def buy_upgrade(upgrade_key):
        nonlocal station_message, station_message_timer
        if docked_station is not None and station_owner(docked_station.station_id) != "player":
            station_message = "Claim this station first (press C while docked)"
            station_message_timer = 1.6
            play_sfx("ui_click")
            return
        success, upgrade_msg, event_data = apply_upgrade(player, upgrade_key)
        station_message = upgrade_msg
        station_message_timer = 2.0
        if success:
            if upgrade_key == "scanner":
                apply_scanner_reveal()
            play_sfx("upgrade")
            log_event("upgrade_bought", **event_data)
        else:
            play_sfx("ui_click")

    def disrupt_cloak_on_interaction():
        nonlocal station_message, station_message_timer
        if player is not None and player.cloak_active:
            player.disable_cloak()
            station_message = "Cloak disrupted"
            station_message_timer = 0.9

    def buy_station_upgrade(kind):
        nonlocal station_message, station_message_timer
        if docked_station is None:
            station_message = "Must be docked at a station"
            station_message_timer = 1.2
            play_sfx("ui_click")
            return
        sid = docked_station.station_id
        if station_owner(sid) != "player":
            station_message = "Claim this station first"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return

        state = get_station_upgrade_state(sid)
        if kind == "level":
            if state["level"] >= STATION_LEVEL_MAX:
                station_message = "Station level maxed"
                station_message_timer = 1.3
                play_sfx("ui_click")
                return
            cost = station_level_upgrade_cost(sid)
            if player.credits < cost:
                station_message = f"Need {cost} gold"
                station_message_timer = 1.2
                play_sfx("ui_click")
                return
            player.credits -= cost
            state["level"] += 1
            station_message = f"Station upgraded to L{state['level']}"
        elif kind == "laser":
            if state["laser"] >= STATION_LASER_MAX:
                station_message = "Station laser maxed"
                station_message_timer = 1.3
                play_sfx("ui_click")
                return
            cost = station_laser_upgrade_cost(sid)
            if player.credits < cost:
                station_message = f"Need {cost} gold"
                station_message_timer = 1.2
                play_sfx("ui_click")
                return
            player.credits -= cost
            state["laser"] += 1
            station_message = f"Station laser upgraded to L{state['laser']}"
        elif kind == "missile":
            if state["missile"] >= STATION_MISSILE_MAX:
                station_message = "Station missile maxed"
                station_message_timer = 1.3
                play_sfx("ui_click")
                return
            cost = station_missile_upgrade_cost(sid)
            if player.credits < cost:
                station_message = f"Need {cost} gold"
                station_message_timer = 1.2
                play_sfx("ui_click")
                return
            player.credits -= cost
            state["missile"] += 1
            station_message = f"Station missile upgraded to L{state['missile']}"
        else:
            return

        station_message_timer = 1.8
        play_sfx("upgrade")

    def undock():
        nonlocal is_docked, docked_context, docked_station, docked_planet, station_message, station_message_timer
        is_docked = False
        docked_context = None
        docked_station = None
        docked_planet = None
        if player.shield_level > 0:
            player.refill_shields()
        station_message = "Undocked"
        station_message_timer = 1.5
        play_sfx("ui_click")

    def apply_player_hit(hit_source):
        nonlocal station_message, station_message_timer
        if god_mode:
            return
        if player.absorb_hit():
            play_sfx("player_hit")
            station_message = f"Shield absorbed hit ({player.shield_layers} layers left)"
            station_message_timer = 1.2
            log_event(
                "shield_hit",
                source=hit_source,
                shield_layers=player.shield_layers,
                shield_level=player.shield_level,
            )
            return
        trigger_player_destroyed()

    def play_player_death_animation():
        nonlocal elapsed_time
        death_time = 0.65
        while death_time > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    shutdown_game(0, hard=True)

            frame_dt = clock.tick(60) / 1000
            death_time -= frame_dt
            elapsed_time += frame_dt

            update_ship_explosion_fx(ship_explosion_fx, frame_dt)

            camera = player.position if player else pygame.Vector2(0, 0)
            draw_background(camera)

            if drawable:
                for obj in drawable:
                    obj.draw(screen)

            draw_ship_explosion_fx(screen, ship_explosion_fx)
            pygame.display.flip()

    def trigger_player_destroyed():
        if player is None:
            shutdown_game(0)
        play_sfx("player_hit")
        log_event("player_hit")
        spawn_ship_explosion_fx(
            ship_explosion_fx,
            player.position,
            player.radius,
            "white",
            burst_scale=1.35,
        )
        player.kill()
        play_player_death_animation()
        print("Game over!")
        shutdown_game(0)

    def update_play_state():
        nonlocal station_message, station_message_timer
        nonlocal targeting_mode_timer, targeting_locked_targets
        nonlocal current_enemy_spawn_interval, current_enemy_max_alive
        nonlocal scanner_cooldown_timer, scanner_passive_timer
        nonlocal station_defense_fire_timer, enemy_station_fire_timer

        if enemy_field is not None:
            pressure = contract_attack_pressure()
            current_enemy_spawn_interval = max(0.55, base_enemy_spawn_interval / pressure)
            current_enemy_max_alive = max(
                1,
                int(round(base_enemy_max_alive * (0.85 + 0.45 * max(0.0, pressure - 1.0)))),
            )
            enemy_field.spawn_interval = current_enemy_spawn_interval
            enemy_field.spawn_tuning["max_alive"] = current_enemy_max_alive

        if player is not None:
            scanner_cooldown_timer = max(0.0, scanner_cooldown_timer - dt)
            update_persistent_sector_enemies(dt)
            sync_active_sector_enemies_to_persistent()
            update_raid_events(dt)

            station_defense_fire_timer = max(0.0, station_defense_fire_timer - dt)
            enemy_station_fire_timer = max(0.0, enemy_station_fire_timer - dt)
            if station_defense_fire_timer <= 0.0 and enemies is not None:
                for station in list(stations) if stations is not None else []:
                    sid = getattr(station, "station_id", "")
                    if parse_station_sector(sid) != active_sector:
                        continue
                    if station_owner(sid) != "player":
                        continue
                    st = get_station_upgrade_state(sid)
                    live_targets = [enemy for enemy in list(enemies) if enemy.alive()]
                    if not live_targets:
                        continue

                    laser_level = int(st.get("laser", 0))
                    missile_level = int(st.get("missile", 0))
                    laser_range = 220 + int(st.get("level", 1)) * 26 + laser_level * 30
                    missile_range = 280 + int(st.get("level", 1)) * 34 + missile_level * 38

                    fired = False
                    if missile_level > 0:
                        missile_targets = [
                            enemy
                            for enemy in live_targets
                            if station.position.distance_to(enemy.position) <= missile_range
                        ]
                        if missile_targets:
                            target = max(
                                missile_targets,
                                key=lambda e: station.position.distance_to(e.position),
                            )
                            fired = fire_station_projectile(
                                station,
                                target.position,
                                "station_missile",
                                "missile",
                                missile_level,
                            )

                    if not fired and laser_level > 0:
                        laser_targets = [
                            enemy
                            for enemy in live_targets
                            if station.position.distance_to(enemy.position) <= laser_range
                        ]
                        if laser_targets:
                            target = min(
                                laser_targets,
                                key=lambda e: station.position.distance_to(e.position),
                            )
                            fired = fire_station_projectile(
                                station,
                                target.position,
                                "station_laser",
                                "laser",
                                laser_level,
                            )

                    if fired:
                        play_sfx("enemy_shoot")
                station_defense_fire_timer = 2.35

            if enemy_station_fire_timer <= 0.0 and player is not None:
                for station in list(stations) if stations is not None else []:
                    sid = getattr(station, "station_id", "")
                    if parse_station_sector(sid) != active_sector:
                        continue
                    if station_owner(sid) == "player":
                        continue

                    st = get_station_upgrade_state(sid)
                    laser_level = int(st.get("laser", 0))
                    missile_level = int(st.get("missile", 0))
                    level = int(st.get("level", 1))
                    distance_to_player = station.position.distance_to(player.position)

                    if player.cloak_active:
                        continue

                    laser_range = 210 + level * 20 + laser_level * 28
                    missile_range = 300 + level * 30 + missile_level * 36

                    fired = False
                    if missile_level > 0 and distance_to_player <= missile_range:
                        fired = fire_station_projectile(
                            station,
                            player.position,
                            "enemy_station_missile",
                            "missile",
                            missile_level,
                        )
                    if not fired and laser_level > 0 and distance_to_player <= laser_range:
                        fired = fire_station_projectile(
                            station,
                            player.position,
                            "enemy_station_laser",
                            "laser",
                            laser_level,
                        )
                enemy_station_fire_timer = 2.8

            if claim_operation["active"]:
                if active_sector != claim_operation["sector"]:
                    station_message = cancel_claim("Claim failed: left target sector")
                    station_message_timer = 1.8
                    play_sfx("ui_click")
                else:
                    claim_operation["progress"] += dt
                    if claim_operation["waves_remaining"] > 0:
                        claim_operation["wave_timer"] = max(0.0, claim_operation["wave_timer"] - dt)
                        if claim_operation["wave_timer"] <= 0.0:
                            extra = 1 if selected_difficulty == "hard" else 0
                            spawn_hostile_wave(
                                active_sector,
                                claim_operation.get("faction", "crimson"),
                                count=2 + extra,
                                entry_mode="offscreen",
                            )
                            claim_operation["waves_remaining"] = max(
                                0,
                                claim_operation["waves_remaining"] - 1,
                            )
                            claim_operation["wave_timer"] = claim_operation["wave_interval"]

                    if claim_operation["progress"] >= claim_operation["duration"]:
                        complete_claim_operation()

            # Passive ping at scanner capstone level.
            if player.scanner_level >= 4:
                scanner_passive_timer += dt
                if scanner_passive_timer >= 9.0:
                    perform_scanner_pulse(active_sector, force=True)
                    scanner_passive_timer = 0.0

        # Scanned sector snapshots are persistent until rescanned.

        if targeting_mode_timer > 0 and player is not None:
            targeting_mode_timer = max(0.0, targeting_mode_timer - dt)
            max_locks = max(0, int(player.targeting_computer_level))

            targeting_locked_targets = [
                enemy for enemy in targeting_locked_targets if enemy.alive()
            ]

            if len(targeting_locked_targets) < max_locks:
                existing_targets = set(targeting_locked_targets)
                for enemy in nearest_enemies_for_lock(max_locks):
                    if enemy in existing_targets:
                        continue
                    targeting_locked_targets.append(enemy)
                    existing_targets.add(enemy)
                    if len(targeting_locked_targets) >= max_locks:
                        break

            targeting_locked_targets.sort(
                key=lambda enemy: player.position.distance_to(enemy.position)
            )

            if targeting_locked_targets and not is_docked:
                primary = targeting_locked_targets[0]
                delta = primary.position - player.position
                if delta.length_squared() > 0:
                    direction = delta.normalize()
                    player.rotation = math.degrees(math.atan2(direction.y, direction.x)) - 90

            if targeting_mode_timer <= 0:
                targeting_locked_targets = []

        if not is_docked:
            prev_player_position = player.position.copy() if player is not None else None
            updatable.update(dt, player)
            if player is not None and prev_player_position is not None:
                update_world_offset_from_wrap(prev_player_position, player.position)
                if sync_station_sectors():
                    sync_planet_sectors(force=True)
                    sync_asteroid_sectors(force=True)
                    load_active_sector_enemies(reset_grace=True)

            for enemy in list(enemies):
                if enemy.collides_with(player):
                    apply_player_hit("enemy_collision")

            for asteroid in list(asteroids):
                if asteroid.collides_with(player):
                    apply_player_hit("asteroid_collision")

            for shot in list(shots):
                if getattr(shot, "owner", None) == "player":
                    for enemy in list(enemies):
                        if enemy.collides_with(shot):
                            shot.kill()
                            damage = player.get_combat_damage() if player is not None else 1.0
                            will_destroy = enemy.health <= damage
                            if will_destroy:
                                play_sfx("enemy_destroyed")
                                spawn_ship_explosion_fx(
                                    ship_explosion_fx,
                                    enemy.position,
                                    enemy.radius,
                                    enemy.COLOR,
                                    burst_scale=1.0,
                                )
                            else:
                                play_sfx("enemy_hit")
                            enemy.take_damage(damage)
                            if will_destroy:
                                award_player_xp(enemy_xp_reward(enemy))
                            break
                elif getattr(shot, "owner", None) == "player_missile":
                    for enemy in list(enemies):
                        if enemy.collides_with(shot):
                            shot.kill()
                            missile_damage = 2.0 + player.missile_level * 0.9
                            missile_damage *= player.get_combat_damage_multiplier()
                            impact_position = enemy.position.copy()
                            will_destroy = enemy.health <= missile_damage
                            if will_destroy:
                                play_sfx("enemy_destroyed")
                                spawn_ship_explosion_fx(
                                    ship_explosion_fx,
                                    impact_position,
                                    enemy.radius,
                                    enemy.COLOR,
                                    burst_scale=1.2,
                                )
                            else:
                                play_sfx("enemy_hit")
                            enemy.take_damage(missile_damage)
                            if will_destroy:
                                award_player_xp(enemy_xp_reward(enemy) + 4)

                            splash_radius = 64 + player.missile_level * 14
                            for splash_target in list(enemies):
                                if not splash_target.alive() or splash_target is enemy:
                                    continue
                                distance = splash_target.position.distance_to(impact_position)
                                if distance > splash_radius:
                                    continue
                                splash_ratio = 1.0 - min(1.0, distance / splash_radius)
                                splash_damage = max(0.2, missile_damage * 0.55 * splash_ratio)
                                splash_kill = splash_target.health <= splash_damage
                                splash_target.take_damage(splash_damage)
                                if splash_kill:
                                    spawn_ship_explosion_fx(
                                        ship_explosion_fx,
                                        splash_target.position,
                                        splash_target.radius,
                                        splash_target.COLOR,
                                        burst_scale=0.9,
                                    )
                                    award_player_xp(enemy_xp_reward(splash_target))

                            spawn_ship_explosion_fx(
                                ship_explosion_fx,
                                impact_position,
                                8 + player.missile_level * 1.2,
                                "#fdba74",
                                burst_scale=1.0,
                            )
                            break
                elif getattr(shot, "owner", None) in ("station_laser", "station_missile"):
                    for enemy in list(enemies):
                        if enemy.collides_with(shot):
                            shot.kill()
                            damage = float(getattr(shot, "damage", 1.0))
                            will_destroy = enemy.health <= damage
                            enemy.take_damage(damage)
                            if will_destroy:
                                spawn_ship_explosion_fx(
                                    ship_explosion_fx,
                                    enemy.position,
                                    enemy.radius,
                                    enemy.COLOR,
                                    burst_scale=0.95,
                                )
                                award_player_xp(enemy_xp_reward(enemy))
                                play_sfx("enemy_destroyed")
                            else:
                                play_sfx("enemy_hit")
                            break
                elif getattr(shot, "owner", None) in ("enemy_station_laser", "enemy_station_missile"):
                    if shot.collides_with(player):
                        shot.kill()
                        apply_player_hit("enemy_station_shot")
                elif getattr(shot, "owner", None) == "enemy":
                    if shot.collides_with(player):
                        shot.kill()
                        apply_player_hit("enemy_shot")

            for asteroid in list(asteroids):
                for shot in list(shots):
                    if asteroid.collides_with(shot):
                        seeded_id = getattr(asteroid, "seeded_id", None)
                        if seeded_id is not None:
                            destroyed_seed_asteroids.add(seeded_id)
                        shot.kill()
                        play_sfx("asteroid_hit")
                        impact_pos = asteroid.position.copy()
                        if getattr(shot, "owner", None) in (
                            "player",
                            "player_missile",
                            "station_laser",
                            "station_missile",
                        ):
                            award_player_xp(asteroid_xp_reward(asteroid))
                        mined_metals = asteroid.split()
                        if mined_metals:
                            player.add_metal_batch(mined_metals)
                            spawn_metal_pickup_fx(metal_pickup_fx, impact_pos, mined_metals)
                            play_sfx("pickup")
                            mined_summary = ", ".join(
                                f"{metal}+{qty}" for metal, qty in mined_metals.items()
                            )
                            station_message = f"Collected {mined_summary}"
                            station_message_timer = 1.4
                            log_event(
                                "resource_mined",
                                metals=mined_metals,
                                total_units=player.total_metal_units(),
                            )
                        break

    def draw_background(camera):
        nonlocal shooting_star_timer

        screen.blit(backdrop_gradient, (0, 0))

        nebula_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for cloud in nebula_clouds:
            drift_x = math.sin(elapsed_time * 0.2 + cloud["phase"]) * NEBULA_DRIFT_SPEED
            drift_y = math.cos(elapsed_time * 0.15 + cloud["phase"]) * (NEBULA_DRIFT_SPEED * 0.6)
            center_x = cloud["x"] - camera.x * cloud["depth"] + drift_x
            center_y = cloud["y"] - camera.y * cloud["depth"] + drift_y
            draw_wrapped_circle(
                nebula_surface,
                cloud["color"],
                center_x,
                center_y,
                cloud["radius"],
            )
        screen.blit(nebula_surface, (0, 0))

        dust_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for dust in stardust:
            sway = math.sin(elapsed_time * 0.14 + dust["phase"]) * 12.0
            dx = (dust["x"] - camera.x * dust["depth"] * 0.07 + sway) % SCREEN_WIDTH
            dy = (dust["y"] - camera.y * dust["depth"] * 0.07) % SCREEN_HEIGHT
            pygame.draw.circle(
                dust_surface,
                (130, 165, 210, dust["alpha"]),
                (int(dx), int(dy)),
                1,
            )
        screen.blit(dust_surface, (0, 0))

        for star in stars:
            twinkle = 0.62 + 0.38 * (
                (math.sin(elapsed_time * STAR_TWINKLE_SPEED * star["pulse_speed"] + star["phase"]) + 1) * 0.5
            )
            base_hue = star["hue"]
            brightness_scale = 0.85 if star["tier"] == "far" else (1.0 if star["tier"] == "mid" else 1.12)
            color = (
                min(255, int(base_hue[0] * twinkle * brightness_scale)),
                min(255, int(base_hue[1] * twinkle * brightness_scale)),
                min(255, int(base_hue[2] * twinkle * brightness_scale)),
            )
            star_x = star["x"] - camera.x * star["depth"] * 0.12
            star_y = star["y"] - camera.y * star["depth"] * 0.12
            pos = (int(star_x % SCREEN_WIDTH), int(star_y % SCREEN_HEIGHT))

            if star["tier"] == "near" and twinkle > 0.9:
                pygame.draw.circle(screen, (color[0], color[1], color[2],), pos, star["size"] + 1, 1)
            pygame.draw.circle(screen, color, pos, star["size"])

        shooting_star_timer -= dt
        if shooting_star_timer <= 0.0:
            spawn_shooting_star()
            shooting_star_timer = bg_rng.uniform(7.0, 16.0)

        for streak in list(shooting_stars):
            streak["life"] -= dt
            if streak["life"] <= 0:
                shooting_stars.remove(streak)
                continue

            streak["pos"] += streak["vel"] * dt
            life_ratio = max(0.0, min(1.0, streak["life"] / streak["max_life"]))
            head = streak["pos"]
            tail = head - streak["vel"].normalize() * streak["trail"]
            color = (int(170 * life_ratio), int(210 * life_ratio), int(255 * life_ratio))
            pygame.draw.line(
                screen,
                color,
                (int(tail.x), int(tail.y)),
                (int(head.x), int(head.y)),
                2,
            )
            pygame.draw.circle(screen, (215, 235, 255), (int(head.x), int(head.y)), 2)

    while True:
        elapsed_time += dt
        update_ship_explosion_fx(ship_explosion_fx, dt)
        if game_state == "playing":
            log_state()

        # Build menu buttons each frame (centered panel)
        menu_panel = pygame.Rect(SCREEN_WIDTH // 2 - 350, SCREEN_HEIGHT // 2 - 280, 700, 560)
        map_panel_rect = pygame.Rect(70, 50, SCREEN_WIDTH - 140, SCREEN_HEIGHT - 100)
        menu_ui["action"] = pygame.Rect(menu_panel.centerx - 110, menu_panel.y + 392, 220, 42)
        menu_ui["quit"] = pygame.Rect(menu_panel.centerx - 110, menu_panel.y + 440, 220, 42)
        menu_ui["controls"] = pygame.Rect(menu_panel.centerx - 110, menu_panel.y + 488, 220, 28)
        menu_ui["audio"] = pygame.Rect(menu_panel.centerx - 110, menu_panel.y + 520, 106, 28)
        menu_ui["map"] = pygame.Rect(menu_panel.centerx + 4, menu_panel.y + 520, 106, 28)
        menu_ui["easy"] = pygame.Rect(menu_panel.x + 125, menu_panel.y + 202, 130, 44)
        menu_ui["normal"] = pygame.Rect(menu_panel.x + 285, menu_panel.y + 202, 130, 44)
        menu_ui["hard"] = pygame.Rect(menu_panel.x + 445, menu_panel.y + 202, 130, 44)

        audio_panel = pygame.Rect(menu_panel.right + 16, menu_panel.y + 56, 280, 230)
        menu_ui["music_slider"] = pygame.Rect(audio_panel.x + 14, audio_panel.y + 98, 252, 18)
        menu_ui["sfx_slider"] = pygame.Rect(audio_panel.x + 14, audio_panel.y + 192, 252, 18)
        audio_toggle_button = pygame.Rect(SCREEN_WIDTH - 62, SCREEN_HEIGHT - 62, 48, 48)

        def set_slider_volume(kind, mouse_x):
            slider_rect = menu_ui["music_slider"] if kind == "music" else menu_ui["sfx_slider"]
            ratio = (mouse_x - slider_rect.x) / max(1, slider_rect.width)
            ratio = max(0.0, min(1.0, ratio))

            if kind == "music":
                audio.set_music_volume(ratio)
            else:
                audio.set_sfx_volume(ratio)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown_game(0, hard=True)

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and audio_toggle_button.collidepoint(event.pos)
            ):
                audio.toggle_all_mute()
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_state == "playing":
                    game_state = "paused"
                    is_docked = False
                    docked_context = None
                    docked_planet = None
                    play_sfx("pause")
                elif game_state in ("menu", "paused"):
                    play_sfx("pause")
                    shutdown_game(0, hard=True)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                if game_state == "playing" and has_active_game:
                    game_state = "paused"
                    show_map_overlay = True
                    show_ship_overlay = False
                    is_docked = False
                    docked_context = None
                    docked_planet = None
                    play_sfx("pause")
                elif game_state in ("menu", "paused") and has_active_game:
                    show_map_overlay = not show_map_overlay
                    if show_map_overlay:
                        show_ship_overlay = False
                    if not show_map_overlay:
                        # Closing map should immediately return to live gameplay.
                        game_state = "playing"
                    play_sfx("ui_click")

            if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                if game_state == "playing" and has_active_game:
                    game_state = "paused"
                    show_ship_overlay = True
                    show_map_overlay = False
                    ship_tab = "inventory"
                    is_docked = False
                    docked_context = None
                    docked_planet = None
                    play_sfx("pause")
                elif game_state in ("menu", "paused") and has_active_game:
                    show_ship_overlay = not show_ship_overlay
                    if show_ship_overlay:
                        show_map_overlay = False
                        ship_tab = "inventory"
                    elif not show_map_overlay:
                        game_state = "playing"
                    play_sfx("ui_click")

            if event.type == pygame.KEYDOWN and game_state == "playing":
                if event.key == pygame.K_d:
                    god_mode = not god_mode
                    state_text = "ON" if god_mode else "OFF"
                    credit_boost = 0
                    upgrades_granted = 0
                    if god_mode and player is not None:
                        if player.credits < 500000:
                            credit_boost += 500000 - player.credits
                            player.credits = 500000

                        needed = player.credits_needed_for_full_upgrades()
                        if needed > player.credits:
                            extra = needed - player.credits
                            credit_boost += extra
                            player.credits += extra

                        before_total = (
                            player.fire_rate_level
                            + player.shield_level
                            + player.multishot_level
                            + player.targeting_beam_level
                            + player.targeting_computer_level
                            + player.warp_drive_level
                            + player.scanner_level
                            + player.missile_level
                            + player.cloak_level
                            + player.cargo_hold_level
                            + player.accommodations_level
                            + player.engine_tuning_level
                        )

                        while player.buy_fire_rate_upgrade()[0]:
                            pass
                        while player.buy_shield_upgrade()[0]:
                            pass
                        while player.buy_multishot_upgrade()[0]:
                            pass
                        while player.buy_targeting_beam_upgrade()[0]:
                            pass
                        while player.buy_targeting_computer_upgrade()[0]:
                            pass
                        while player.buy_warp_drive_upgrade()[0]:
                            pass
                        while player.buy_scanner_upgrade()[0]:
                            pass
                        while player.buy_missile_upgrade()[0]:
                            pass
                        while player.buy_cloak_upgrade()[0]:
                            pass
                        while player.buy_cargo_hold_upgrade()[0]:
                            pass
                        while player.buy_accommodations_upgrade()[0]:
                            pass
                        while player.buy_engine_tuning_upgrade()[0]:
                            pass

                        player.refill_shields()
                        player.warp_energy = player.get_warp_capacity_seconds()
                        apply_scanner_reveal()

                        after_total = (
                            player.fire_rate_level
                            + player.shield_level
                            + player.multishot_level
                            + player.targeting_beam_level
                            + player.targeting_computer_level
                            + player.warp_drive_level
                            + player.scanner_level
                            + player.missile_level
                            + player.cloak_level
                            + player.cargo_hold_level
                            + player.accommodations_level
                            + player.engine_tuning_level
                        )
                        upgrades_granted = max(0, after_total - before_total)

                    station_message = (
                        f"DEV GOD MODE: {state_text} (+{credit_boost} cr, +{upgrades_granted} upgrades)"
                        if god_mode
                        else f"DEV GOD MODE: {state_text}"
                    )
                    station_message_timer = 1.8
                    log_event(
                        "dev_god_mode",
                        enabled=god_mode,
                        credit_boost=credit_boost,
                        upgrades_granted=upgrades_granted,
                    )
                    play_sfx("ui_click")
                elif event.key == pygame.K_t:
                    if player is None or player.targeting_computer_level <= 0:
                        station_message = "Need Targeting Computer upgrade"
                        station_message_timer = 1.4
                        play_sfx("ui_click")
                    elif targeting_mode_timer > 0:
                        targeting_mode_timer = 0.0
                        targeting_locked_targets = []
                        station_message = "Targeting computer OFF"
                        station_message_timer = 1.2
                        play_sfx("ui_click")
                    else:
                        locks = nearest_enemies_for_lock(player.targeting_computer_level)
                        if not locks:
                            station_message = "No enemies to lock"
                            station_message_timer = 1.2
                            play_sfx("ui_click")
                        else:
                            targeting_mode_timer = targeting_mode_duration
                            targeting_locked_targets = locks
                            primary = targeting_locked_targets[0]
                            delta = primary.position - player.position
                            if delta.length_squared() > 0:
                                direction = delta.normalize()
                                player.rotation = math.degrees(math.atan2(direction.y, direction.x)) - 90
                            station_message = f"Targeting ON: {len(targeting_locked_targets)} lock(s)"
                            station_message_timer = 1.4
                            play_sfx("upgrade")
                elif event.key == pygame.K_f:
                    if player is not None and player.shoot_missile():
                        station_message = "Missile away"
                        station_message_timer = 0.8
                        play_sfx("player_shoot")
                    else:
                        station_message = "Missile not ready"
                        station_message_timer = 0.8
                        play_sfx("ui_click")
                elif event.key == pygame.K_v:
                    if player is not None:
                        success, msg = player.toggle_cloak()
                        station_message = msg
                        station_message_timer = 1.2
                        play_sfx("upgrade" if success else "ui_click")
                elif event.key == pygame.K_b and not is_docked:
                    disrupt_cloak_on_interaction()
                    has_station = len(get_sector_stations_with_built(active_sector[0], active_sector[1])) > 0
                    if has_station:
                        station_message = "This sector already has a station"
                        station_message_timer = 1.5
                        play_sfx("ui_click")
                    elif player.credits < BUILD_STATION_COST:
                        station_message = f"Need {BUILD_STATION_COST} gold to build station"
                        station_message_timer = 1.5
                        play_sfx("ui_click")
                    else:
                        sx, sy = active_sector
                        station_id = f"{sx}:{sy}:player"
                        world_x = sx * sector_manager.sector_width + sector_manager.sector_width * 0.5
                        world_y = sy * sector_manager.sector_height + sector_manager.sector_height * 0.5
                        built_stations_by_sector[(sx, sy)] = (station_id, world_x, world_y)
                        station_owner_overrides[station_id] = "player"
                        station_upgrades[station_id] = {"level": 1, "laser": 0, "missile": 0}
                        sector_owner_overrides[(sx, sy)] = "player"
                        ensure_player_sector_economy((sx, sy))
                        snapshot_economy_state_cache()
                        player.credits -= BUILD_STATION_COST
                        sync_station_sectors(force=True)
                        capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
                        station_message = "Station built. Sector is now under your control"
                        station_message_timer = 2.0
                        play_sfx("upgrade")
                elif event.key == pygame.K_c:
                    disrupt_cloak_on_interaction()
                    if claim_operation["active"]:
                        station_message = "Claim already in progress"
                        station_message_timer = 1.5
                        play_sfx("ui_click")
                    elif not is_docked:
                        near_station = nearest_station_in_range()
                        near_planet = nearest_planet_in_range()

                        station_dist = (
                            player.position.distance_to(near_station.position)
                            if near_station is not None
                            else 999999.0
                        )
                        planet_dist = (
                            player.position.distance_to(near_planet.position)
                            if near_planet is not None
                            else 999999.0
                        )

                        if near_station is not None and station_dist <= planet_dist:
                            sid = near_station.station_id
                            owner_key = station_owner(sid)
                            if owner_key == "player":
                                station_message = "Station already under your control"
                                station_message_timer = 1.5
                                play_sfx("ui_click")
                            else:
                                start_claim_operation("station", sid, owner_key)
                        elif near_planet is not None:
                            pid = near_planet.planet_id
                            owner_key = planet_owner(pid)
                            if owner_key == "player":
                                station_message = "Planet already under your control"
                                station_message_timer = 1.5
                                play_sfx("ui_click")
                            else:
                                start_claim_operation("planet", pid, owner_key)
                        else:
                            station_message = "Move within range of a station or planet to claim"
                            station_message_timer = 1.5
                            play_sfx("ui_click")
                    elif docked_context == "station" and docked_station is not None:
                        sid = docked_station.station_id
                        owner_key = station_owner(sid)
                        if owner_key == "player":
                            station_message = "Station already under your control"
                            station_message_timer = 1.5
                            play_sfx("ui_click")
                        else:
                            start_claim_operation("station", sid, owner_key)
                    elif docked_context == "planet" and docked_planet is not None:
                        pid = docked_planet.planet_id
                        owner_key = planet_owner(pid)
                        if owner_key == "player":
                            station_message = "Planet already under your control"
                            station_message_timer = 1.5
                            play_sfx("ui_click")
                        else:
                            start_claim_operation("planet", pid, owner_key)
                if is_docked:
                    # Keep Esc behavior dedicated to pause flow.
                    pass
                elif event.key == pygame.K_e:
                    disrupt_cloak_on_interaction()
                    near_station = nearest_station_in_range()
                    near_planet = nearest_planet_in_range()

                    station_dist = (
                        player.position.distance_to(near_station.position)
                        if near_station is not None
                        else 999999.0
                    )
                    planet_dist = (
                        player.position.distance_to(near_planet.position)
                        if near_planet is not None
                        else 999999.0
                    )

                    if near_station is not None and station_dist <= planet_dist:
                        owner_key = station_owner(near_station.station_id)
                        if owner_key != "player":
                            station_message = (
                                f"Cannot dock at {owner_label(owner_key)} station. "
                                "Claim it first (C)"
                            )
                            station_message_timer = 1.8
                            play_sfx("ui_click")
                            continue
                        is_docked = True
                        docked_context = "station"
                        docked_station = near_station
                        docked_planet = None
                        station_tab = "upgrade"
                        available_jobs = (
                            generate_jobs("station", sector_manager, origin_sector=active_sector)
                            if owner_key == "player"
                            else []
                        )
                        if player.shield_level > 0:
                            player.refill_shields()
                        if owner_key == "player":
                            station_message = "Docked at Union station. Services online."
                        else:
                            station_message = (
                                f"Docked at {owner_label(owner_key)} station. "
                                "Claim with C to enable services"
                            )
                        station_message_timer = 2.0
                        play_sfx("dock")
                    elif near_planet is not None:
                        owner_key = planet_owner(near_planet.planet_id)
                        if owner_key != "player":
                            station_message = (
                                f"Cannot land on {owner_label(owner_key)} planet. "
                                "Claim it first (C)"
                            )
                            station_message_timer = 1.8
                            play_sfx("ui_click")
                            continue
                        is_docked = True
                        docked_context = "planet"
                        docked_station = None
                        docked_planet = near_planet
                        available_jobs = (
                            generate_jobs("planet", sector_manager, origin_sector=active_sector)
                            if owner_key == "player"
                            else []
                        )
                        if owner_key == "player":
                            station_message = f"Landed on Union planet ({near_planet.accepted_metal} market)."
                        else:
                            station_message = (
                                f"Landed on {owner_label(owner_key)} planet. "
                                "Claim with C to unlock market/jobs"
                            )
                        station_message_timer = 2.0
                        play_sfx("dock")

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and game_state == "playing"
                and is_docked
            ):
                upgrade_click_actions = {
                    "buy_fire_rate": lambda: buy_upgrade("fire_rate"),
                    "buy_shield": lambda: buy_upgrade("shield"),
                    "buy_multishot": lambda: buy_upgrade("multishot"),
                    "buy_targeting_beam": lambda: buy_upgrade("targeting_beam"),
                    "buy_targeting_computer": lambda: buy_upgrade("targeting_computer"),
                    "buy_warp_drive": lambda: buy_upgrade("warp_drive"),
                    "buy_missile": lambda: buy_upgrade("missile"),
                    "buy_cloak": lambda: buy_upgrade("cloak"),
                    "buy_cargo_hold": lambda: buy_upgrade("cargo_hold"),
                    "buy_accommodations": lambda: buy_upgrade("accommodations"),
                    "buy_engine_tuning": lambda: buy_upgrade("engine_tuning"),
                }
                mouse_pos = event.pos
                disrupt_cloak_on_interaction()
                if docked_context == "station":
                    station_action = resolve_station_click(mouse_pos, station_tab, station_ui)
                    if station_action == "undock":
                        undock()
                    elif station_action == "deliver_contract":
                        try_complete_contract()
                    elif station_action and station_action.startswith("job:"):
                        handle_job_slot(int(station_action.split(":", 1)[1]))
                    elif station_action == "upgrade_station_level":
                        buy_station_upgrade("level")
                    elif station_action == "upgrade_station_laser":
                        buy_station_upgrade("laser")
                    elif station_action == "upgrade_station_missile":
                        buy_station_upgrade("missile")
                    elif station_action in upgrade_click_actions:
                        upgrade_click_actions[station_action]()
                elif docked_context == "planet" and docked_planet is not None:
                    planet_action = resolve_planet_click(mouse_pos, planet_ui)
                    if planet_action == "undock":
                        undock()
                    elif planet_action == "trade":
                        sell_to_planet(docked_planet)
                    elif planet_action == "deliver_contract":
                        try_complete_contract()
                    elif planet_action and planet_action.startswith("job:"):
                        handle_job_slot(int(planet_action.split(":", 1)[1]))

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and game_state in ("menu", "paused")
            ):
                mouse_pos = event.pos

                map_overlay_active = show_map_overlay or (
                    show_ship_overlay and has_active_game and ship_tab == "map"
                )
                if map_overlay_active and has_active_game and map_panel_rect.collidepoint(mouse_pos):
                    if not map_tile_parity_ok(map_panel_rect, active_sector):
                        station_message = "Map parity error: tile mapping mismatch"
                        station_message_timer = 1.8
                        play_sfx("ui_click")
                        continue

                    scanned_sector = map_sector_at_point(map_panel_rect, active_sector, mouse_pos)
                    if scanned_sector is not None:
                        disrupt_cloak_on_interaction()
                        if player is None or player.scanner_level <= 0:
                            station_message = "Need scanner upgrade to remote scan"
                            station_message_timer = 1.4
                            play_sfx("ui_click")
                            continue

                        if abs(scanned_sector[0] - active_sector[0]) > 1 or abs(scanned_sector[1] - active_sector[1]) > 1:
                            station_message = "Scan range limited to 3x3 around your sector"
                            station_message_timer = 1.4
                            play_sfx("ui_click")
                            continue

                        scanned_count = perform_scanner_pulse(scanned_sector)
                        if scanned_count > 0:
                            station_message = (
                                f"Scan pulse: {scanned_count} sector"
                                f"{'s' if scanned_count != 1 else ''}"
                            )
                            station_message_timer = 1.2
                            play_sfx("upgrade")
                        else:
                            station_message = f"Scanner cooling down: {scanner_cooldown_timer:.1f}s"
                            station_message_timer = 1.1
                            play_sfx("ui_click")
                        continue

                if menu_ui["easy"].collidepoint(mouse_pos):
                    selected_difficulty = "easy"
                    play_sfx("ui_click")
                elif menu_ui["normal"].collidepoint(mouse_pos):
                    selected_difficulty = "normal"
                    play_sfx("ui_click")
                elif menu_ui["hard"].collidepoint(mouse_pos):
                    selected_difficulty = "hard"
                    play_sfx("ui_click")
                elif menu_ui["action"].collidepoint(mouse_pos):
                    play_sfx("ui_click")
                    show_controls_overlay = False
                    show_audio_overlay = False
                    if has_active_game:
                        game_state = "playing"
                    else:
                        init_new_game(selected_difficulty)
                        has_active_game = True
                        game_state = "playing"
                elif menu_ui["quit"].collidepoint(mouse_pos):
                    play_sfx("pause")
                    shutdown_game(0, hard=True)
                elif menu_ui["controls"].collidepoint(mouse_pos):
                    play_sfx("ui_click")
                    show_controls_overlay = not show_controls_overlay
                elif menu_ui["audio"].collidepoint(mouse_pos):
                    play_sfx("ui_click")
                    show_audio_overlay = not show_audio_overlay
                elif menu_ui["map"].collidepoint(mouse_pos) and has_active_game:
                    play_sfx("ui_click")
                    show_map_overlay = not show_map_overlay
                    if show_map_overlay:
                        show_ship_overlay = False
                    if not show_map_overlay:
                        # Closing map from pause/menu resumes the run immediately.
                        game_state = "playing"
                elif show_ship_overlay and ship_ui["tab_inventory"] and ship_ui["tab_inventory"].collidepoint(mouse_pos):
                    ship_tab = "inventory"
                    play_sfx("ui_click")
                elif show_ship_overlay and ship_ui["tab_map"] and ship_ui["tab_map"].collidepoint(mouse_pos):
                    ship_tab = "map"
                    play_sfx("ui_click")
                elif show_audio_overlay and menu_ui["music_slider"].collidepoint(mouse_pos):
                    set_slider_volume("music", mouse_pos[0])
                    audio_slider_dragging = "music"
                    play_sfx("ui_click")
                elif show_audio_overlay and menu_ui["sfx_slider"].collidepoint(mouse_pos):
                    set_slider_volume("sfx", mouse_pos[0])
                    audio_slider_dragging = "sfx"
                    play_sfx("ui_click")

            if (
                event.type == pygame.MOUSEMOTION
                and game_state in ("menu", "paused")
                and show_audio_overlay
                and audio_slider_dragging in ("music", "sfx")
                and pygame.mouse.get_pressed()[0]
            ):
                set_slider_volume(audio_slider_dragging, event.pos[0])

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                audio_slider_dragging = None

        if game_state == "playing" and has_active_game:
            update_play_state()

        if station_message_timer > 0:
            station_message_timer = max(0, station_message_timer - dt)

        # Draw
        camera = player.position if player else pygame.Vector2(0, 0)
        draw_background(camera)

        if has_active_game and drawable:
            for obj in drawable:
                obj.draw(screen)

            if player and player.warp_boosting:
                forward = pygame.Vector2(0, 1).rotate(player.rotation)
                tail = player.position - forward * (player.radius * 0.9)
                pulse = 0.65 + 0.35 * math.sin(elapsed_time * 18.0)

                for idx in range(4):
                    t = idx / 3 if idx > 0 else 0.0
                    segment_pos = tail - forward * (14 + idx * 18)
                    width = max(1, int(7 - idx * 1.6))
                    color = (
                        int(120 + 80 * pulse),
                        int(160 + 70 * (1.0 - t)),
                        min(255, int(220 + 25 * pulse)),
                    )
                    alpha_surface = pygame.Surface((24, 24), pygame.SRCALPHA)
                    pygame.draw.circle(
                        alpha_surface,
                        (color[0], color[1], color[2], max(60, 190 - idx * 36)),
                        (12, 12),
                        width,
                    )
                    screen.blit(alpha_surface, (int(segment_pos.x) - 12, int(segment_pos.y) - 12))

            if player and player.targeting_beam_level > 0:
                forward = pygame.Vector2(0, 1).rotate(player.rotation)
                beam_start = player.position + forward * (player.radius * 0.9)
                max_range = player.get_targeting_beam_range()
                locked = False
                if targeting_mode_timer > 0 and targeting_locked_targets:
                    primary_target = targeting_locked_targets[0]
                    beam_end = primary_target.position
                    hit_found = True
                    locked = True
                else:
                    beam_end, hit_found = beam_first_hit(
                        beam_start,
                        forward,
                        max_range,
                        asteroids,
                        enemies,
                    )

                beam_pulse = 0.65 + 0.35 * math.sin(elapsed_time * 8.0)
                beam_color = (
                    int(90 + 110 * beam_pulse),
                    int(150 + 90 * beam_pulse),
                    255,
                )
                pygame.draw.line(
                    screen,
                    (40, 90, 150),
                    (int(beam_start.x), int(beam_start.y)),
                    (int(beam_end.x), int(beam_end.y)),
                    5,
                )
                pygame.draw.line(
                    screen,
                    beam_color,
                    (int(beam_start.x), int(beam_start.y)),
                    (int(beam_end.x), int(beam_end.y)),
                    2,
                )
                if hit_found:
                    pygame.draw.circle(
                        screen,
                        (190, 225, 255),
                        (int(beam_end.x), int(beam_end.y)),
                        6 if locked else 5,
                    )
                if player.targeting_computer_level > 0:
                    if locked:
                        lock_text = hud_font.render("LOCK", True, "#93c5fd")
                        screen.blit(lock_text, (int(beam_end.x) + 8, int(beam_end.y) - 10))
                    if targeting_mode_timer > 0:
                        tcomp_status = hud_font.render(
                            f"TCOMP ON: {len(targeting_locked_targets)} lock(s) {targeting_mode_timer:.1f}s",
                            True,
                            "#93c5fd",
                        )
                        screen.blit(tcomp_status, (10, 100))

            if player and player.shield_layers > 0:
                for layer in range(player.shield_layers):
                    pulse = 0.6 + 0.4 * math.sin(elapsed_time * 4.0 + layer * 0.8)
                    radius = player.radius + 8 + layer * 7
                    shield_color = (
                        int(55 + 80 * pulse),
                        int(145 + 80 * pulse),
                        255,
                    )
                    pygame.draw.circle(
                        screen,
                        shield_color,
                        (int(player.position.x), int(player.position.y)),
                        radius,
                        2,
                    )

            draw_ship_explosion_fx(screen, ship_explosion_fx)
            step_and_draw_metal_pickup_fx(screen, metal_pickup_fx, dt)

            draw_hud_chip(f"Cargo {player.total_metal_units()} metal", 10, SCREEN_HEIGHT - 34)
            draw_hud_chip(f"Gold {player.credits}", SCREEN_WIDTH - 194, SCREEN_HEIGHT - 34, UI_COLORS["accent"])

            draw_hud_chip(f"Shields {player.shield_layers}/{player.shield_level}", 10, 34, (125, 211, 252))
            draw_hud_chip(
                f"Multishot L{player.multishot_level} ({len(player.multishot_pattern())} shots)",
                10,
                58,
                (196, 181, 253),
            )
            draw_hud_chip(f"Targeting Beam L{player.targeting_beam_level}", 10, 82, UI_COLORS["accent_alt"])
            draw_hud_chip(
                f"Targeting Computer L{player.targeting_computer_level} ({player.targeting_computer_level} locks)",
                10,
                106,
                UI_COLORS["accent_alt"],
            )
            draw_hud_chip(
                (
                    f"Sublight Warp L{player.warp_drive_level} "
                    f"{player.warp_energy:.1f}/{player.get_warp_capacity_seconds():.1f}s"
                ),
                10,
                130,
                (249, 168, 212) if player.warp_boosting else (251, 207, 232),
            )
            draw_hud_chip(
                f"Sector {active_sector[0]},{active_sector[1]}  Seed {world_seed}",
                10,
                154,
                UI_COLORS["muted"],
            )
            draw_hud_chip(
                f"Owner {owner_label(sector_owner(active_sector))}",
                10,
                178,
                UI_COLORS["accent_alt"],
            )
            draw_hud_chip(
                (
                    f"Combat L{player.combat_level} "
                    f"XP {player.combat_xp}/{player.xp_needed_for_next_combat_level()} "
                    f"DMG x{player.get_combat_damage_multiplier():.2f}"
                ),
                10,
                202,
                (253, 230, 138),
            )
            draw_hud_chip(
                f"Missiles L{player.missile_level} CD {player.missile_timer:.1f}s (F)",
                10,
                226,
                (167, 243, 208) if player.missile_timer <= 0 else (209, 213, 219),
            )
            draw_hud_chip(
                (
                    f"Cloak L{player.cloak_level} "
                    f"{player.cloak_timer:.1f}/{player.get_cloak_capacity_seconds():.1f}s (V)"
                ),
                10,
                250,
                (125, 211, 252) if player.cloak_active else (148, 163, 184),
            )

            if raid_events:
                draw_hud_chip(
                    f"Raid Alerts {len(raid_events)}",
                    10,
                    274,
                    UI_COLORS["warn"],
                )

            if active_sector in raid_events:
                raid = raid_events[active_sector]
                draw_hud_chip(
                    (
                        f"UNDER ATTACK: {owner_label(raid['faction'])} "
                        f"Waves {raid.get('waves_remaining', 0)}"
                    ),
                    10,
                    298,
                    UI_COLORS["danger"],
                )

            if scanner_cooldown_timer > 0:
                draw_hud_chip(
                    f"Scanner Cooldown {scanner_cooldown_timer:.1f}s",
                    10,
                    322,
                    UI_COLORS["warn"],
                )

            if not is_docked and game_state == "playing":
                near_station = nearest_station_in_range()
                near_planet = nearest_planet_in_range()
                station_dist = (
                    player.position.distance_to(near_station.position)
                    if near_station is not None
                    else 999999.0
                )
                planet_dist = (
                    player.position.distance_to(near_planet.position)
                    if near_planet is not None
                    else 999999.0
                )

                if near_station is not None and station_dist <= planet_dist:
                    station_claim_owner = station_owner(near_station.station_id)
                    if station_claim_owner == "player":
                        draw_hud_chip("Press E at Station: Upgrade", 10, SCREEN_HEIGHT - 60, UI_COLORS["accent"])
                    else:
                        draw_hud_chip(
                            f"Press C to Claim Station ({owner_label(station_claim_owner)})",
                            10,
                            SCREEN_HEIGHT - 60,
                            UI_COLORS["warn"],
                        )
                elif near_planet is not None:
                    planet_claim_owner = planet_owner(near_planet.planet_id)
                    if planet_claim_owner == "player":
                        draw_hud_chip(
                            f"Press E at Planet: Land ({near_planet.accepted_metal} market)",
                            10,
                            SCREEN_HEIGHT - 60,
                            UI_COLORS["accent"],
                        )
                    else:
                        draw_hud_chip(
                            f"Press C to Claim Planet ({owner_label(planet_claim_owner)})",
                            10,
                            SCREEN_HEIGHT - 60,
                            UI_COLORS["warn"],
                        )

            if active_contract is not None:
                risk_rating = int(active_contract.get("risk_rating", 1))
                contract_text = hud_font.render(
                    (
                        f"Contract: {active_contract['mission']} "
                        f"({active_contract['amount']} {active_contract['unit']}, "
                        f"{active_contract.get('tile_distance', 0)} tiles, R{risk_rating}/5) -> "
                        f"{active_contract['target_type']} {active_contract['target_sector'][0]},"
                        f"{active_contract['target_sector'][1]}"
                    ),
                    True,
                    UI_COLORS["accent"],
                )
                contract_bg = pygame.Rect(8, SCREEN_HEIGHT - 132, contract_text.get_width() + 20, 48)
                pygame.draw.rect(screen, (9, 16, 29, 188), contract_bg, border_radius=8)
                pygame.draw.rect(screen, (58, 76, 106), contract_bg, 1, border_radius=8)
                screen.blit(contract_text, (18, SCREEN_HEIGHT - 128))

                threat_text = hud_font.render(
                    (
                        f"Threat: R{risk_rating}/5  Spawn {current_enemy_spawn_interval:.2f}s"
                        f"  Cap {current_enemy_max_alive}"
                    ),
                    True,
                    UI_COLORS["warn"],
                )
                screen.blit(threat_text, (18, SCREEN_HEIGHT - 106))

                target_obj = get_active_contract_target_object()
                if target_obj is not None:
                    draw_dotted_line(
                        player.position,
                        target_obj.position,
                        (246, 211, 101),
                        dash=9,
                        gap=7,
                        width=2,
                    )

                target_hint = contract_target_hint_point(target_obj)
                if target_hint is not None:
                    inset_view = pygame.Rect(26, 26, SCREEN_WIDTH - 52, SCREEN_HEIGHT - 52)
                    if not inset_view.collidepoint((target_hint.x, target_hint.y)):
                        sector_dx = active_contract["target_sector"][0] - active_sector[0]
                        sector_dy = active_contract["target_sector"][1] - active_sector[1]
                        draw_offscreen_arrow(
                            player.position,
                            target_hint,
                            (246, 211, 101),
                            label="DELIVER",
                            offset_text=f"{sector_dx:+d},{sector_dy:+d}",
                        )

            if station_message_timer > 0 and station_message:
                draw_hud_chip(station_message, 10, SCREEN_HEIGHT - 88, UI_COLORS["accent"])

            if claim_operation["active"]:
                claim_ratio = 0.0
                if claim_operation["duration"] > 0:
                    claim_ratio = max(0.0, min(1.0, claim_operation["progress"] / claim_operation["duration"]))

                bar_w = 340
                bar_h = 16
                bar_x = SCREEN_WIDTH // 2 - bar_w // 2
                bar_y = 18
                label = hud_font.render(
                    (
                        f"CLAIMING {claim_operation.get('target_kind', 'site').upper()} "
                        f"{int(claim_ratio * 100)}%  Waves:{claim_operation.get('waves_remaining', 0)}"
                    ),
                    True,
                    "#fef08a",
                )
                screen.blit(label, (bar_x, bar_y - 18))
                pygame.draw.rect(screen, (20, 24, 38), pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=6)
                pygame.draw.rect(screen, (120, 132, 162), pygame.Rect(bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)
                fill_w = int((bar_w - 4) * claim_ratio)
                if fill_w > 0:
                    pygame.draw.rect(
                        screen,
                        (250, 204, 21),
                        pygame.Rect(bar_x + 2, bar_y + 2, fill_w, bar_h - 4),
                        border_radius=4,
                    )

            if game_state == "playing":
                control_surface = hud_font.render("Esc: Pause", True, "white")
                screen.blit(control_surface, (SCREEN_WIDTH - 170, 10))

                if god_mode:
                    draw_hud_chip("GODMODE ACTIVE", 10, 10, UI_COLORS["danger"])

            if audio.music_loaded:
                music_state = "Muted" if audio.all_audio_muted or audio.music_muted else "On"
                draw_hud_chip(f"Music {music_state}", SCREEN_WIDTH - 180, SCREEN_HEIGHT - 58, UI_COLORS["muted"])
                draw_hud_chip(f"Track {audio.music_source}", SCREEN_WIDTH - 300, SCREEN_HEIGHT - 82, UI_COLORS["muted"])

        if game_state == "playing" and is_docked and has_active_game:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            panel_rect = pygame.Rect(180, 90, SCREEN_WIDTH - 360, SCREEN_HEIGHT - 180)
            if docked_context == "station":
                _sid = docked_station.station_id if docked_station is not None else ""
                _st = get_station_upgrade_state(_sid) if _sid else {"level": 1, "laser": 0, "missile": 0}
                draw_station_panel(
                    screen,
                    panel_rect,
                    player,
                    station_tab,
                    station_ui,
                    metal_prices,
                    available_jobs,
                    active_contract,
                    active_sector,
                    docked_context,
                    panel_font,
                    hud_font,
                    owner_label=owner_label(station_owner(docked_station.station_id)) if docked_station else "Unknown",
                    player_controls=(
                        docked_station is not None and station_owner(docked_station.station_id) == "player"
                    ),
                    station_level=int(_st.get("level", 1)),
                    station_laser=int(_st.get("laser", 0)),
                    station_missile=int(_st.get("missile", 0)),
                    station_level_cost_text=(
                        "MAXED"
                        if _st.get("level", 1) >= STATION_LEVEL_MAX
                        else f"{station_level_upgrade_cost(_sid)}g"
                    ),
                    station_laser_cost_text=(
                        "MAXED"
                        if _st.get("laser", 0) >= STATION_LASER_MAX
                        else f"{station_laser_upgrade_cost(_sid)}g"
                    ),
                    station_missile_cost_text=(
                        "MAXED"
                        if _st.get("missile", 0) >= STATION_MISSILE_MAX
                        else f"{station_missile_upgrade_cost(_sid)}g"
                    ),
                )
            elif docked_context == "planet" and docked_planet is not None:
                draw_planet_panel(
                    screen,
                    panel_rect,
                    player,
                    docked_planet,
                    metal_prices,
                    available_jobs,
                    active_contract,
                    active_sector,
                    docked_context,
                    panel_font,
                    hud_font,
                    planet_ui,
                    owner_label=owner_label(planet_owner(docked_planet.planet_id)),
                    player_controls=(planet_owner(docked_planet.planet_id) == "player"),
                )
        else:
            station_ui["sell_tab"] = None
            station_ui["upgrade_tab"] = None
            station_ui["sell_all"] = None
            for key in UPGRADE_BUTTON_KEYS:
                station_ui[key] = None
            station_ui["upgrade_station_level"] = None
            station_ui["upgrade_station_laser"] = None
            station_ui["upgrade_station_missile"] = None
            station_ui["undock"] = None
            planet_ui["trade"] = None
            planet_ui["undock"] = None
            for idx in range(3):
                planet_ui[f"job_{idx}"] = None

        if game_state in ("menu", "paused"):
            draw_menu_panel(
                screen,
                game_state,
                has_active_game,
                selected_difficulty,
                menu_ui,
                DIFFICULTY_SETTINGS,
                title_font,
                panel_font,
                hud_font,
                audio.music_loaded,
                audio.music_driver,
                audio.music_error,
                show_controls_overlay,
                show_audio_overlay,
                show_map_overlay,
                audio.music_muted,
                audio.music_volume,
                audio.sfx_muted,
                audio.sfx_volume,
            )

        map_overlay_active = game_state in ("menu", "paused") and has_active_game and (
            show_map_overlay or (show_ship_overlay and ship_tab == "map")
        )
        if map_overlay_active:
            draw_map_panel(
                screen,
                map_panel_rect,
                active_sector,
                explored_sectors,
                player.scanner_level if player else 0,
                active_contract,
                live_sector_intel,
                scanner_cooldown_timer,
                title_font,
                panel_font,
                hud_font,
                sector_owner_fn=sector_owner,
                owner_label_fn=owner_label,
                build_status_fn=build_status_for_sector,
                raided_sectors=set(raid_events.keys()),
            )

        if game_state in ("menu", "paused") and has_active_game and show_ship_overlay:
            ship_panel_rect = pygame.Rect(120, 78, SCREEN_WIDTH - 240, SCREEN_HEIGHT - 156)
            draw_ship_panel(
                screen,
                ship_panel_rect,
                player,
                active_contract,
                ship_tab,
                ship_ui,
                hud_font,
                panel_font,
            )

        audio.draw_toggle_icon(screen, audio_toggle_button)

        pygame.display.flip()
        dt = clock.tick(60) / 1000


if __name__ == "__main__":
    main()
