import sys
import random
import math
import os
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

from constants import *
from logger import log_state, log_event
from player import Player
from asteroid import Asteroid
from shot import Shot
from enemy import Enemy, SuicideBomber, Harasser, Tank
from station import Station
from planet import Planet
from sector_manager import SectorManager
from resources import get_metal_color, get_metal_prices, set_drop_rate_multiplier
from targeting import beam_first_hit, best_enemy_lock_candidate
from upgrade_ui import UPGRADE_BUTTON_KEYS
from station_panel import draw_station_panel, resolve_station_click
from planet_panel import draw_planet_panel, resolve_planet_click
from ship_panel import draw_ship_panel, resolve_ship_click
from status_panel import draw_status_panel
from upgrade_actions import apply_upgrade
from menu_panel import draw_menu_panel
from map_panel import draw_map_panel, map_sector_at_point, map_tile_parity_ok
from ui_theme import UI_COLORS, draw_button, draw_close_button, draw_panel
from audio_manager import AudioManager
from display_setup import init_display, DisplayInitError
from buildables import (
    draw_build_placement_preview,
    draw_defense_turret,
    draw_mining_platform,
    draw_support_drones,
    draw_station_infrastructure,
)
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
    default_planet_settlement_state as compute_default_planet_settlement_state,
    settlement_requirements as compute_settlement_requirements,
    settlement_happiness as compute_settlement_happiness,
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
from joystick import VirtualJoystick


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
        "ai_aggression": 0.82,
        "ai_accuracy": 0.7,
        "ai_strafe": 0.78,
        "ai_fire_intent": 0.72,
        "ai_memory": 0.82,
        "progression_scale": 0.88,
        "command_threat_step": 0.011,
        "command_threat_max": 0.18,
        "pressure_cap": 1.22,
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
        "ai_aggression": 1.0,
        "ai_accuracy": 1.0,
        "ai_strafe": 1.0,
        "ai_fire_intent": 1.0,
        "ai_memory": 1.0,
        "progression_scale": 1.0,
        "command_threat_step": 0.019,
        "command_threat_max": 0.34,
        "pressure_cap": 1.55,
    },
    "hard": {
        "label": "Hard",
        "asteroid_spawn": 0.62,
        "enemy_spawn": 3.1,
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
        "ai_aggression": 1.25,
        "ai_accuracy": 1.2,
        "ai_strafe": 1.22,
        "ai_fire_intent": 1.28,
        "ai_memory": 1.24,
        "progression_scale": 1.14,
        "command_threat_step": 0.024,
        "command_threat_max": 0.5,
        "pressure_cap": 1.95,
    },
}

BUILD_STATION_COST = 900
BUILD_MINING_PLATFORM_COST = 780
MINING_PLATFORM_MAX_PER_SECTOR = 2
BUILD_DEFENSE_TURRET_COST = 420
DEFENSE_TURRET_MAX_PER_SECTOR = 4
INFRA_UPGRADE_MAX = 4
INFRA_MINING_BASE_COST = 240
INFRA_MINING_STEP_COST = 170
INFRA_DRONE_BASE_COST = 260
INFRA_DRONE_STEP_COST = 190
INFRA_TURRET_BASE_COST = 280
INFRA_TURRET_STEP_COST = 210
INFRA_SHIELD_BASE_COST = 300
INFRA_SHIELD_STEP_COST = 230
DEV_MODE_GOLD_BONUS = 50000


def main():
    print("Starting Asteroids")
    print(f"Screen width: {SCREEN_WIDTH}")
    print(f"Screen height: {SCREEN_HEIGHT}")

    pygame.init()
    try:
        window_surface, selected_video_driver = init_display(SCREEN_WIDTH, SCREEN_HEIGHT)
    except DisplayInitError as exc:
        print("Display initialization failed.")
        if exc.errors:
            print("Tried drivers:", " | ".join(exc.errors))
        print("Try running with: SDL_VIDEODRIVER=wayland or SDL_VIDEODRIVER=x11")
        pygame.quit()
        raise SystemExit(1)

    print(f"Video driver: {selected_video_driver}")
    pygame.display.set_caption("Asteroid Miner")
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()
    clock = pygame.time.Clock()

    world_seed = int(os.environ.get("ASTEROID_WORLD_SEED", "1337"))
    sector_manager = SectorManager(world_seed, sector_size=SCREEN_WIDTH, sector_height=SCREEN_HEIGHT)
    audio = AudioManager(__file__)

    def play_sfx(name):
        audio.play_sfx(name)

    hud_font = pygame.font.SysFont("dejavusansmono", 18)
    panel_font = pygame.font.SysFont("dejavusans", 23)
    title_font = pygame.font.SysFont("freesansbold", 40)

    def current_window_surface():
        surface = pygame.display.get_surface()
        return surface if surface is not None else window_surface

    def map_window_to_logical(pos):
        if pos is None:
            return None

        surface = current_window_surface()
        if surface is None:
            return (int(pos[0]), int(pos[1]))

        window_width, window_height = surface.get_size()
        if window_width <= 0 or window_height <= 0:
            return None

        scale = min(window_width / float(SCREEN_WIDTH), window_height / float(SCREEN_HEIGHT))
        if scale <= 0:
            return None

        render_width = SCREEN_WIDTH * scale
        render_height = SCREEN_HEIGHT * scale
        offset_x = (window_width - render_width) * 0.5
        offset_y = (window_height - render_height) * 0.5

        local_x = (float(pos[0]) - offset_x) / scale
        local_y = (float(pos[1]) - offset_y) / scale
        if local_x < 0 or local_x > SCREEN_WIDTH or local_y < 0 or local_y > SCREEN_HEIGHT:
            return None

        return (int(local_x), int(local_y))

    def present_frame():
        surface = current_window_surface()
        if surface is None:
            return

        window_width, window_height = surface.get_size()
        if window_width == SCREEN_WIDTH and window_height == SCREEN_HEIGHT:
            surface.blit(screen, (0, 0))
        else:
            scale = min(window_width / float(SCREEN_WIDTH), window_height / float(SCREEN_HEIGHT))
            scaled_size = (
                max(1, int(round(SCREEN_WIDTH * scale))),
                max(1, int(round(SCREEN_HEIGHT * scale))),
            )
            scaled_frame = pygame.transform.smoothscale(screen, scaled_size)
            blit_pos = (
                (window_width - scaled_size[0]) // 2,
                (window_height - scaled_size[1]) // 2,
            )
            surface.fill((0, 0, 0))
            surface.blit(scaled_frame, blit_pos)

        pygame.display.flip()

    def draw_hud_chip(text, x, y, color=None):
        fg = UI_COLORS["text"] if color is None else color
        label = hud_font.render(text, True, fg)
        bg_rect = pygame.Rect(x, y, label.get_width() + 16, label.get_height() + 8)
        pygame.draw.rect(screen, (9, 16, 29, 188), bg_rect, border_radius=8)
        pygame.draw.rect(screen, (58, 76, 106), bg_rect, 1, border_radius=8)
        screen.blit(label, (x + 8, y + 4))
        return bg_rect

    def hud_chip_size(text):
        width, height = hud_font.size(text)
        return width + 16, height + 8

    def truncate_hud_text(text, max_width):
        if max_width is None:
            return text
        if hud_chip_size(text)[0] <= max_width:
            return text

        suffix = "..."
        trimmed = str(text)
        while trimmed and hud_chip_size(trimmed + suffix)[0] > max_width:
            trimmed = trimmed[:-1]
        return (trimmed + suffix) if trimmed else suffix

    def draw_hud_chip_right(text, right_x, y, color=None):
        width, _ = hud_chip_size(text)
        return draw_hud_chip(text, right_x - width, y, color)

    def draw_hud_stack(items, x, y, align="left", gap=6, max_width=None):
        cursor_y = y
        rects = []
        for text, color in items:
            if not text:
                continue
            clipped = truncate_hud_text(text, max_width)
            if align == "right":
                rect = draw_hud_chip_right(clipped, x, cursor_y, color)
            else:
                rect = draw_hud_chip(clipped, x, cursor_y, color)
            rects.append(rect)
            cursor_y = rect.bottom + gap
        return rects

    def draw_hud_stack_up(items, x, bottom_y, align="left", gap=6, max_width=None):
        cursor_bottom = bottom_y
        rects = []
        for text, color in items:
            if not text:
                continue
            clipped = truncate_hud_text(text, max_width)
            _, height = hud_chip_size(clipped)
            chip_y = cursor_bottom - height
            if align == "right":
                rect = draw_hud_chip_right(clipped, x, chip_y, color)
            else:
                rect = draw_hud_chip(clipped, x, chip_y, color)
            rects.append(rect)
            cursor_bottom = rect.y - gap
        return rects

    def wrap_text_to_width(text, font, max_width, max_lines=None):
        words = str(text).split()
        if not words:
            return [""]

        lines = []
        current = words[0]
        for word in words[1:]:
            proposal = f"{current} {word}"
            if font.size(proposal)[0] <= max_width:
                current = proposal
            else:
                lines.append(current)
                current = word

        lines.append(current)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = truncate_hud_text(lines[-1], max_width)
        return lines

    def draw_wrapped_lines(text, x, y, font, color, max_width, line_gap=4, max_lines=None):
        lines = wrap_text_to_width(text, font, max_width, max_lines=max_lines)
        cursor_y = y
        for line in lines:
            surface = font.render(line, True, color)
            screen.blit(surface, (x, cursor_y))
            cursor_y += surface.get_height() + line_gap
        return cursor_y

    dt = 0.0
    elapsed_time = 0.0

    def shutdown_game(exit_code=0, hard=False):
        audio.shutdown()
        pygame.quit()
        if hard:
            os._exit(exit_code)
        raise SystemExit(exit_code)

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
                "hue": bg_rng.choice([(225, 235, 255), (210, 230, 255), (255, 232, 208), (208, 245, 255)]),
            }
        )
    stardust = [{
        "x": bg_rng.uniform(0, SCREEN_WIDTH),
        "y": bg_rng.uniform(0, SCREEN_HEIGHT),
        "depth": bg_rng.uniform(0.4, 1.0),
        "phase": bg_rng.uniform(0, 6.283),
        "alpha": bg_rng.randint(40, 110),
    } for _ in range(80)]
    nebula_clouds = [{
        "x": bg_rng.uniform(0, SCREEN_WIDTH),
        "y": bg_rng.uniform(0, SCREEN_HEIGHT),
        "radius": bg_rng.randint(140, 260),
        "depth": bg_rng.uniform(0.08, 0.22),
        "phase": bg_rng.uniform(0, 6.283),
        "color": bg_rng.choice([(22, 44, 74, 26), (32, 24, 64, 22), (18, 58, 62, 20)]),
    } for _ in range(6)]
    backdrop_gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        t = y / max(1, SCREEN_HEIGHT - 1)
        color = (
            int(6 + 8 * t),
            int(10 + 10 * t),
            int(18 + 18 * t),
        )
        pygame.draw.line(backdrop_gradient, color, (0, y), (SCREEN_WIDTH, y))
    shooting_stars = []
    shooting_star_timer = bg_rng.uniform(7.0, 16.0)

    def draw_wrapped_circle(target, color, center_x, center_y, radius):
        positions_x = [center_x]
        positions_y = [center_y]
        if center_x - radius < 0:
            positions_x.append(center_x + SCREEN_WIDTH)
        if center_x + radius > SCREEN_WIDTH:
            positions_x.append(center_x - SCREEN_WIDTH)
        if center_y - radius < 0:
            positions_y.append(center_y + SCREEN_HEIGHT)
        if center_y + radius > SCREEN_HEIGHT:
            positions_y.append(center_y - SCREEN_HEIGHT)
        for draw_x in positions_x:
            for draw_y in positions_y:
                pygame.draw.circle(target, color, (int(draw_x), int(draw_y)), int(radius))

    def spawn_shooting_star():
        start_x = bg_rng.uniform(SCREEN_WIDTH * 0.25, SCREEN_WIDTH * 1.05)
        start_y = bg_rng.uniform(-40, SCREEN_HEIGHT * 0.35)
        angle = bg_rng.uniform(math.radians(200), math.radians(230))
        speed = bg_rng.uniform(580.0, 880.0)
        velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
        shooting_stars.append(
            {
                "pos": pygame.Vector2(start_x, start_y),
                "vel": velocity,
                "life": bg_rng.uniform(0.45, 0.9),
                "max_life": 0.9,
                "trail": bg_rng.uniform(90.0, 160.0),
            }
        )

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
    has_active_game = False
    game_state = "menu"

    station_message = ""
    station_message_timer = 0.0
    is_docked = False
    docked_context = None
    docked_station = None
    docked_planet = None
    station_tab = "ship_core"
    metal_pickup_fx = []
    ship_explosion_fx = []
    god_mode = False
    player_spawn_grace_timer = 0.0
    selected_difficulty = "normal"
    metal_prices = get_metal_prices()
    active_difficulty = DIFFICULTY_SETTINGS[selected_difficulty]
    enemy_field = None
    base_enemy_spawn_interval = active_difficulty["enemy_spawn"]
    base_enemy_max_alive = active_difficulty["enemy_max_alive"]
    current_enemy_spawn_interval = base_enemy_spawn_interval
    current_enemy_max_alive = base_enemy_max_alive
    targeting_locked_targets = []
    targeting_mode_timer = 0.0
    targeting_mode_duration = 4.0

    station_ui = {
        "sell_tab": None,
        "upgrade_tab": None,
        "sell_all": None,
        "undock": None,
        "upgrade_infra_mining": None,
        "upgrade_infra_drone": None,
        "upgrade_infra_turret": None,
        "upgrade_infra_shield": None,
    }
    for key in UPGRADE_BUTTON_KEYS:
        station_ui[key] = None

    planet_ui = {"trade": None, "undock": None}
    for idx in range(3):
        planet_ui[f"job_{idx}"] = None
    ship_ui = {"close": None}
    status_ui = {"close": None}
    pause_nav_ui = {"home": None, "map": None, "ship": None, "status": None, "build": None}
    menu_ui = {
        "action": None,
        "quit": None,
        "controls": None,
        "audio": None,
        "music_slider": None,
        "sfx_slider": None,
        "easy": None,
        "normal": None,
        "hard": None,
        "close": None,
    }
    build_ui = {
        "tab_construct": None,
        "tab_infra": None,
        "tab_logistics": None,
        "subtab_primary": None,
        "subtab_secondary": None,
        "build_station": None,
        "build_platform": None,
        "place_turret": None,
        "build_mining": None,
        "build_drone": None,
        "build_turret": None,
        "build_shield": None,
        "placement_cancel": None,
        "close": None,
    }
    pause_tab = "home"
    build_tab = "build_construct_core"
    build_placement_mode = None

    available_jobs = []
    active_contract = None
    explored_sectors = {}
    live_sector_intel = {}
    persistent_sector_enemies = {}
    scanner_cooldown_timer = 0.0
    scanner_passive_timer = 0.0
    scanner_live_window = set()
    scanner_live_timer = 0.0
    sector_wrap_transition_timer = 0.0
    anomaly_tick_timer = 0.0
    anomaly_pressure_hint = ""
    sector_enemy_entry_grace_timer = 0.0
    sector_owner_overrides = {(0, 0): "player"}
    station_owner_overrides = {}
    planet_owner_overrides = {}
    built_stations_by_sector = {}
    mining_platforms_by_sector = {}
    defense_turrets_by_sector = {}
    platform_convoy_states = {}
    platform_harvest_progress = {}
    ship_auto_mining_progress = {}
    station_upgrades = {}
    station_health = {}
    station_disabled_timers = {}
    infrastructure_health = {}
    sector_economy_states = {}
    economy_state_cache = {"version": 1, "sectors": {}}
    station_defense_fire_timer = 0.0
    enemy_station_fire_timer = 0.0
    infrastructure_defense_fire_timer = 0.0
    passive_drone_income_timer = 0.0
    drone_intercept_cooldown = 0.0
    platform_logistics_hint_timer = 0.0
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
        "telegraph_sent": False,
    }
    claim_initiated_targets = set()
    audio_slider_dragging = None
    show_touch_action_controls = True
    active_touch_actions = {}
    touch_action_specs = {
        "build": {"label": "BUILD", "color": (74, 222, 128)},
        "interact": {"label": "INTERACT", "color": (56, 189, 248)},
        "map": {"label": "MAP", "color": (250, 204, 21)},
        "pause": {"label": "||", "color": (196, 181, 253)},
    }

    def close_panel_rect(panel_rect):
        return pygame.Rect(panel_rect.right - 54, panel_rect.y + 16, 34, 34)

    def build_touch_action_buttons():
        button_w = 98
        button_h = 52
        gap = 10
        right = SCREEN_WIDTH - 16
        bottom = SCREEN_HEIGHT - 16
        order = ("interact", "build", "map", "pause")
        return {
            key: pygame.Rect(right - button_w, bottom - (idx + 1) * button_h - idx * gap, button_w, button_h)
            for idx, key in enumerate(order)
        }

    def refresh_touch_action_buttons():
        nonlocal touch_action_buttons
        touch_action_buttons = build_touch_action_buttons()

    def spawn_enemy_wave(sector, faction, count=2, entry_mode="offscreen"):
        pack = get_persistent_sector_enemies(sector)
        contacts = pack.get("contacts", [])
        for _ in range(max(1, int(count))):
            new_contact = reinforcement_contact(world_seed, sector, contacts, allow_tank=True)
            new_contact = tune_contact_for_difficulty(new_contact)
            new_contact["faction"] = faction
            new_contact["entry_mode"] = entry_mode
            contacts.append(new_contact)
            if sector == active_sector:
                spawn_contact_enemy(new_contact)

    touch_action_buttons = build_touch_action_buttons()
    pause_button_rect = pygame.Rect(10, 10, 120, 40)
    map_panel_rect = pygame.Rect(70, 78, SCREEN_WIDTH - 140, SCREEN_HEIGHT - 156)
    audio_toggle_button = pygame.Rect(SCREEN_WIDTH - 54, 10, 44, 44)

    def event_pointer_pos(evt):
        if hasattr(evt, "pos"):
            return map_window_to_logical(evt.pos)
        if evt.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            surface = pygame.display.get_surface()
            width, height = surface.get_size() if surface is not None else (SCREEN_WIDTH, SCREEN_HEIGHT)
            return map_window_to_logical((int(evt.x * width), int(evt.y * height)))
        return None

    def event_pointer_id(evt):
        if evt.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            return "mouse-left"
        if evt.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            return f"finger:{getattr(evt, 'finger_id', 0)}"
        return None

    def touch_action_at_pos(pos, buttons):
        if pos is None:
            return None
        for key, rect in buttons.items():
            if rect.collidepoint(pos):
                return key
        return None

    def draw_touch_action_buttons(target, buttons):
        active_actions = {action for action in active_touch_actions.values() if action is not None}
        for key, rect in buttons.items():
            spec = touch_action_specs[key]
            tone = spec["color"]
            fill = (26, 46, 72, 220) if key in active_actions else (12, 18, 32, 185)
            pygame.draw.rect(target, fill, rect, border_radius=12)
            pygame.draw.rect(target, tone, rect, 2, border_radius=12)
            label = hud_font.render(spec["label"], True, tone)
            target.blit(label, label.get_rect(center=rect.center))

    def draw_infrastructure_sprite(target, infra, clock_seconds):
        pos = infra["position"]
        pygame.draw.circle(target, (148, 163, 184), (int(pos.x), int(pos.y)), int(infra["radius"]), 2)

    def cancel_build_placement(message=None, play_click=True):
        nonlocal build_placement_mode, station_message, station_message_timer
        if build_placement_mode is None:
            return False
        build_placement_mode = None
        if message:
            station_message = message
            station_message_timer = 1.3
        if play_click:
            play_sfx("ui_click")
        return True

    def open_pause_tab(tab_name):
        nonlocal game_state, is_docked, docked_context, docked_planet, pause_tab, build_tab, build_placement_mode
        if not has_active_game:
            return
        pause_tab = tab_name
        if tab_name == "build":
            build_tab = "build_construct_core"
        else:
            build_placement_mode = None
        game_state = "paused"
        is_docked = False
        docked_context = None
        docked_planet = None

    def build_menu_ui_layout():
        menu_panel = pygame.Rect(SCREEN_WIDTH // 2 - 350, SCREEN_HEIGHT // 2 - 280, 700, 560)
        diff_y = menu_panel.y + 196
        diff_w = 148
        diff_h = 42
        diff_gap = 18
        diff_left = menu_panel.centerx - ((diff_w * 3 + diff_gap * 2) // 2)
        menu_ui["easy"] = pygame.Rect(diff_left, diff_y, diff_w, diff_h)
        menu_ui["normal"] = pygame.Rect(diff_left + diff_w + diff_gap, diff_y, diff_w, diff_h)
        menu_ui["hard"] = pygame.Rect(diff_left + (diff_w + diff_gap) * 2, diff_y, diff_w, diff_h)
        menu_ui["action"] = pygame.Rect(menu_panel.x + 110, menu_panel.y + 388, 220, 44)
        menu_ui["quit"] = pygame.Rect(menu_panel.right - 330, menu_panel.y + 388, 220, 44)
        small_w = 108
        small_h = 34
        small_gap = 10
        row_y = menu_panel.y + 446
        row_left = menu_panel.x + 56
        menu_ui["controls"] = pygame.Rect(row_left, row_y, small_w, small_h)
        menu_ui["audio"] = pygame.Rect(row_left + (small_w + small_gap), row_y, small_w, small_h)
        audio_panel = pygame.Rect(menu_panel.right + 16, menu_panel.y + 56, 280, 230)
        menu_ui["music_slider"] = pygame.Rect(audio_panel.x + 16, audio_panel.y + 72, audio_panel.width - 32, 16)
        menu_ui["sfx_slider"] = pygame.Rect(audio_panel.x + 16, audio_panel.y + 166, audio_panel.width - 32, 16)
        menu_ui["close"] = pygame.Rect(menu_panel.right - 54, menu_panel.y + 16, 34, 34)

    def build_pause_nav_layout():
        tab_w = 132
        tab_h = 36
        tab_gap = 10
        total_w = tab_w * 5 + tab_gap * 4
        left = SCREEN_WIDTH // 2 - total_w // 2
        top = 18
        for idx, key in enumerate(("home", "map", "ship", "status", "build")):
            pause_nav_ui[key] = pygame.Rect(left + idx * (tab_w + tab_gap), top, tab_w, tab_h)

    def pause_nav_active_tab():
        return pause_tab if pause_tab in ("home", "map", "ship", "status", "build") else "home"

    def cycle_pause_tab(step):
        nonlocal pause_tab
        if not has_active_game:
            return False
        ordered = ["home", "map", "ship", "status", "build"]
        current = pause_nav_active_tab()
        idx = ordered.index(current)
        open_pause_tab(ordered[(idx + step) % len(ordered)])
        play_sfx("ui_click")
        return True

    def draw_pause_navigation():
        if not has_active_game or game_state not in ("menu", "paused"):
            return
        build_pause_nav_layout()
        nav_rect = pygame.Rect(pause_nav_ui["home"].x - 16, 10, (pause_nav_ui["build"].right - pause_nav_ui["home"].x) + 32, 52)
        pygame.draw.rect(screen, (8, 14, 26, 212), nav_rect, border_radius=14)
        pygame.draw.rect(screen, (88, 102, 134), nav_rect, 1, border_radius=14)
        labels = {
            "home": "Pause",
            "map": "Map",
            "ship": "Inventory",
            "status": "Status",
            "build": "Build",
        }
        active_key = pause_nav_active_tab()
        for key, label in labels.items():
            draw_button(screen, pause_nav_ui[key], label, hud_font, active=(active_key == key), tone="alt" if key != active_key else "accent")

    def menu_panel_active():
        return game_state == "menu" or (game_state == "paused" and pause_tab in ("home", "controls", "audio"))

    def build_panel_rect():
        build_margin_x = max(140, SCREEN_WIDTH // 10)
        build_margin_y = max(72, SCREEN_HEIGHT // 10)
        return pygame.Rect(build_margin_x, build_margin_y, SCREEN_WIDTH - build_margin_x * 2, SCREEN_HEIGHT - build_margin_y * 2)

    def close_pause_overlay():
        nonlocal game_state, pause_tab
        if build_placement_mode is not None:
            return cancel_build_placement("Placement canceled")
        if pause_tab in ("controls", "audio", "map", "ship", "status", "build"):
            pause_tab = "home"
            play_sfx("ui_click")
            return True
        if game_state == "paused":
            start_or_resume_game()
            play_sfx("pause")
            return True
        if has_active_game:
            start_or_resume_game()
            play_sfx("pause")
            return True
        shutdown_game(0)

    def set_audio_slider_value(slider_key, pointer_x):
        rect = menu_ui.get(slider_key)
        if rect is None:
            return
        value = max(0.0, min(1.0, (pointer_x - rect.x) / max(1, rect.width)))
        if slider_key == "music_slider":
            audio.set_music_volume(value)
        elif slider_key == "sfx_slider":
            audio.set_sfx_volume(value)

    def start_or_resume_game():
        nonlocal game_state, has_active_game, pause_tab, build_placement_mode
        if not has_active_game:
            init_new_game(selected_difficulty)
            has_active_game = True
        game_state = "playing"
        pause_tab = "home"
        build_placement_mode = None

    def handle_menu_click(pos):
        nonlocal selected_difficulty, game_state, pause_tab, audio_slider_dragging
        if not menu_panel_active():
            return False
        build_menu_ui_layout()
        if menu_ui.get("close") and menu_ui["close"].collidepoint(pos):
            return close_pause_overlay()
        for key in ("easy", "normal", "hard"):
            rect = menu_ui.get(key)
            if rect is not None and rect.collidepoint(pos):
                selected_difficulty = key
                play_sfx("ui_click")
                return True
        for key in ("music_slider", "sfx_slider"):
            rect = menu_ui.get(key)
            if rect is not None and rect.collidepoint(pos):
                audio_slider_dragging = key
                set_audio_slider_value(key, pos[0])
                return True
        if menu_ui["action"] and menu_ui["action"].collidepoint(pos):
            start_or_resume_game()
            play_sfx("pause")
            return True
        if menu_ui["quit"] and menu_ui["quit"].collidepoint(pos):
            shutdown_game(0)
        for key, target_tab in {"controls": "controls", "audio": "audio"}.items():
            rect = menu_ui.get(key)
            if rect is not None and rect.collidepoint(pos):
                pause_tab = "home" if pause_tab == target_tab else target_tab
                if game_state == "playing":
                    game_state = "paused"
                play_sfx("ui_click")
                return True
        return False

    def dock_at_station(station_obj):
        nonlocal is_docked, docked_context, docked_station, docked_planet, available_jobs, station_tab
        is_docked = True
        docked_context = "station"
        docked_station = station_obj
        docked_planet = None
        station_tab = "ship_core"
        available_jobs = generate_context_jobs("station", active_sector)
        play_sfx("dock")

    def dock_at_planet(planet_obj):
        nonlocal is_docked, docked_context, docked_station, docked_planet, available_jobs
        is_docked = True
        docked_context = "planet"
        docked_station = None
        docked_planet = planet_obj
        available_jobs = generate_context_jobs("planet", active_sector, planet_id=planet_obj.planet_id)
        play_sfx("dock")

    def handle_interact_action():
        nonlocal station_message, station_message_timer
        if not has_active_game or player is None:
            return
        if game_state in ("menu", "paused"):
            start_or_resume_game()
            return
        if is_docked:
            undock()
            return
        near_station = nearest_station_in_range()
        near_planet = nearest_planet_in_range()
        station_dist = player.position.distance_to(near_station.position) if near_station is not None else float("inf")
        planet_dist = player.position.distance_to(near_planet.position) if near_planet is not None else float("inf")
        disrupt_cloak_on_interaction()
        if near_station is not None and station_dist <= planet_dist:
            if station_owner(near_station.station_id) != "player":
                station_message = "Claim this station first (press C nearby)"
                station_message_timer = 1.4
                play_sfx("ui_click")
                return
            dock_at_station(near_station)
            return
        if near_planet is not None:
            if planet_owner(near_planet.planet_id) != "player":
                station_message = "Claim this planet first (press C nearby)"
                station_message_timer = 1.4
                play_sfx("ui_click")
                return
            dock_at_planet(near_planet)
            return
        station_message = "Nothing nearby to interact with"
        station_message_timer = 1.2
        play_sfx("ui_click")

    def handle_claim_action():
        nonlocal station_message, station_message_timer
        if not has_active_game or player is None or game_state != "playing":
            return
        if is_docked:
            if docked_context == "station" and docked_station is not None:
                owner = station_owner(docked_station.station_id)
                if owner != "player":
                    start_claim_operation("station", docked_station.station_id, owner)
                    return
            if docked_context == "planet" and docked_planet is not None:
                owner = planet_owner(docked_planet.planet_id)
                if owner != "player":
                    start_claim_operation("planet", docked_planet.planet_id, owner)
                    return
        near_station = nearest_station_in_range()
        if near_station is not None:
            owner = station_owner(near_station.station_id)
            if owner != "player":
                start_claim_operation("station", near_station.station_id, owner)
                return
        near_planet = nearest_planet_in_range()
        if near_planet is not None:
            owner = planet_owner(near_planet.planet_id)
            if owner != "player":
                start_claim_operation("planet", near_planet.planet_id, owner)
                return
        station_message = "Nothing nearby to claim"
        station_message_timer = 1.2
        play_sfx("ui_click")

    def handle_station_panel_action(action):
        nonlocal station_tab
        if action is None:
            return False
        if action == "close" or action == "undock":
            undock()
            return True
        if action == "deliver_contract":
            try_complete_contract()
            return True
        if action.startswith("job:"):
            handle_job_slot(int(action.split(":", 1)[1]))
            return True
        if action.startswith("tab:"):
            station_tab = action.split(":", 1)[1]
            play_sfx("ui_click")
            return True
        if action in UPGRADE_BUTTON_KEYS:
            upgrade_key = action[4:] if action.startswith("buy_") else action
            buy_upgrade(upgrade_key)
            return True
        if action == "upgrade_station_level":
            buy_station_upgrade("level")
            return True
        if action == "upgrade_station_laser":
            buy_station_upgrade("laser")
            return True
        if action == "upgrade_station_missile":
            buy_station_upgrade("missile")
            return True
        if action == "upgrade_infra_mining":
            buy_station_upgrade("infra_mining")
            return True
        if action == "upgrade_infra_drone":
            buy_station_upgrade("infra_drone")
            return True
        if action == "upgrade_infra_turret":
            buy_station_upgrade("infra_turret")
            return True
        if action == "upgrade_infra_shield":
            buy_station_upgrade("infra_shield")
            return True
        return False

    def handle_planet_panel_action(action):
        if action is None:
            return False
        if action == "close" or action == "undock":
            undock()
            return True
        if action == "trade":
            if docked_planet is not None:
                sell_to_planet(docked_planet)
            return True
        if action == "deliver_contract":
            try_complete_contract()
            return True
        if action.startswith("job:"):
            handle_job_slot(int(action.split(":", 1)[1]))
            return True
        return False

    def handle_ship_panel_action(action):
        nonlocal active_contract, station_message, station_message_timer
        if action is None:
            return False
        if action == "close":
            return close_pause_overlay()
        if action == "drop_contract":
            if active_contract is None:
                return False
            unit = active_contract.get("unit", "cargo")
            amount = int(active_contract.get("amount", 0))
            active_contract = None
            station_message = (
                f"Spaced {amount} {unit}" if unit in ("passenger", "team") else f"Dumped contract cargo ({amount} {unit})"
            )
            station_message_timer = 1.6
            play_sfx("ui_click")
            log_event("contract_abandoned", unit=unit, amount=amount)
            return True
        if action.startswith("drop_metal:"):
            metal_type = action.split(":", 1)[1]
            amount = int(player.metals.get(metal_type, 0)) if player is not None else 0
            if player is None or amount <= 0:
                return False
            player.metals[metal_type] = 0
            station_message = f"Jettisoned {amount} {metal_type}"
            station_message_timer = 1.4
            play_sfx("ui_click")
            log_event("cargo_jettisoned", metal=metal_type, amount=amount)
            return True
        return False

    def sync_virtual_controls():
        if player is None:
            return
        player.set_virtual_controls(
            left=False,
            right=False,
            up=False,
            down=False,
            fire=False,
        )

    def lower_left_hud_anchor():
        return 10

    def lower_left_message_y():
        return SCREEN_HEIGHT - 88

    def handle_scanner_action(target_sector=None):
        nonlocal station_message, station_message_timer, game_state, pause_tab
        if not has_active_game or player is None:
            return False
        if target_sector is None:
            target_sector = active_sector
        if player.scanner_level <= 0:
            station_message = "Need scanner upgrade"
            station_message_timer = 1.4
            play_sfx("ui_click")
            return True
        dx = target_sector[0] - active_sector[0]
        dy = target_sector[1] - active_sector[1]
        if (dx, dy) not in scanner_pulse_offsets(player.scanner_level):
            station_message = "Select a highlighted map sector"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return True
        scanned = perform_scanner_pulse(target_sector, force=False)
        if scanned > 0:
            station_message = f"Remote scan: {target_sector[0]},{target_sector[1]}" if target_sector != active_sector else f"Scanner pulse: {scanned} sector(s) refreshed"
            station_message_timer = 1.5
            play_sfx("upgrade")
            game_state = "paused"
            pause_tab = "map"
        elif scanner_cooldown_timer > 0.0:
            station_message = f"Scanner cooling down {scanner_cooldown_timer:.1f}s"
            station_message_timer = 1.4
            play_sfx("ui_click")
        else:
            station_message = "Scanner found nothing new"
            station_message_timer = 1.4
            play_sfx("ui_click")
        return True

    def toggle_dev_mode():
        nonlocal god_mode, station_message, station_message_timer
        if player is None:
            return False
        god_mode = not god_mode
        state_text = "ON" if god_mode else "OFF"
        credit_boost = 0
        upgrades_granted = 0
        if god_mode:
            needed = player.credits_needed_for_full_upgrades()
            target_credits = needed + DEV_MODE_GOLD_BONUS
            if target_credits > player.credits:
                credit_boost = target_credits - player.credits
                player.credits += credit_boost
            before_total = sum((
                player.fire_rate_level,
                player.shield_level,
                player.multishot_level,
                player.targeting_beam_level,
                player.targeting_computer_level,
                player.warp_drive_level,
                player.scanner_level,
                player.missile_level,
                player.cloak_level,
                player.cargo_hold_level,
                player.accommodations_level,
                player.engine_tuning_level,
                player.weapon_amp_level,
                player.deflector_booster_level,
                player.missile_payload_level,
                player.auto_mining_level,
            ))
            for buy_upgrade_fn in (
                player.buy_fire_rate_upgrade,
                player.buy_shield_upgrade,
                player.buy_multishot_upgrade,
                player.buy_targeting_beam_upgrade,
                player.buy_targeting_computer_upgrade,
                player.buy_warp_drive_upgrade,
                player.buy_scanner_upgrade,
                player.buy_missile_upgrade,
                player.buy_cloak_upgrade,
                player.buy_cargo_hold_upgrade,
                player.buy_accommodations_upgrade,
                player.buy_engine_tuning_upgrade,
                player.buy_weapon_amp_upgrade,
                player.buy_deflector_upgrade,
                player.buy_missile_payload_upgrade,
                player.buy_auto_mining_upgrade,
            ):
                while buy_upgrade_fn()[0]:
                    pass
            after_total = sum((
                player.fire_rate_level,
                player.shield_level,
                player.multishot_level,
                player.targeting_beam_level,
                player.targeting_computer_level,
                player.warp_drive_level,
                player.scanner_level,
                player.missile_level,
                player.cloak_level,
                player.cargo_hold_level,
                player.accommodations_level,
                player.engine_tuning_level,
                player.weapon_amp_level,
                player.deflector_booster_level,
                player.missile_payload_level,
                player.auto_mining_level,
            ))
            upgrades_granted = max(0, after_total - before_total)
            player.refill_shields()
            player.warp_energy = player.get_warp_capacity_seconds()
            player.missile_timer = 0.0
            if player.cloak_active:
                player.cloak_timer = player.get_cloak_capacity_seconds()
            apply_scanner_reveal()
        station_message = (
            f"DEV GOD MODE: {state_text} (+{credit_boost} cr, +{upgrades_granted} upgrades)"
            if god_mode
            else f"DEV GOD MODE: {state_text}"
        )
        station_message_timer = 1.8
        log_event("dev_god_mode", enabled=god_mode, credit_boost=credit_boost, upgrades_granted=upgrades_granted)
        play_sfx("ui_click")
        return True

    def handle_keydown(event):
        nonlocal game_state, pause_tab, god_mode, station_message, station_message_timer, selected_difficulty
        nonlocal targeting_mode_timer
        if event.key == pygame.K_q and game_state in ("menu", "paused"):
            shutdown_game(0)
        if event.key == pygame.K_ESCAPE:
            if build_placement_mode is not None:
                return cancel_build_placement("Placement canceled")
            if has_active_game and game_state == "playing":
                open_pause_tab("home")
                play_sfx("pause")
            elif has_active_game and game_state == "paused":
                start_or_resume_game()
                play_sfx("pause")
            return True
        if event.key == pygame.K_TAB and has_active_game and game_state in ("menu", "paused"):
            backwards = bool(event.mod & pygame.KMOD_SHIFT)
            return cycle_pause_tab(-1 if backwards else 1)
        if event.key == pygame.K_d:
            return toggle_dev_mode()
        if game_state in ("menu", "paused"):
            if event.key == pygame.K_1:
                selected_difficulty = "easy"
                return True
            if event.key == pygame.K_2:
                selected_difficulty = "normal"
                return True
            if event.key == pygame.K_3:
                selected_difficulty = "hard"
                return True
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                start_or_resume_game()
                return True
            if event.key == pygame.K_m and has_active_game:
                open_pause_tab("map")
                return True
            if event.key == pygame.K_i and has_active_game:
                open_pause_tab("ship")
                return True
            if event.key == pygame.K_s and has_active_game:
                open_pause_tab("status")
                return True
            if event.key == pygame.K_b and has_active_game:
                open_pause_tab("build")
                return True
            return False
        if event.key == pygame.K_e:
            handle_interact_action()
            return True
        if event.key == pygame.K_c:
            handle_claim_action()
            return True
        if event.key == pygame.K_f and player is not None:
            if player.shoot_missile():
                play_sfx("player_shoot")
            else:
                play_sfx("ui_click")
            return True
        if event.key == pygame.K_v and player is not None:
            success, message = player.toggle_cloak()
            station_message = message
            station_message_timer = 1.4
            play_sfx("upgrade" if success else "ui_click")
            return True
        if event.key == pygame.K_t and player is not None:
            if player.targeting_computer_level > 0:
                targeting_mode_timer = targeting_mode_duration
                play_sfx("ui_click")
            else:
                station_message = "Need targeting computer upgrade"
                station_message_timer = 1.2
                play_sfx("ui_click")
            return True
        if event.key == pygame.K_m:
            open_pause_tab("map")
            play_sfx("pause")
            return True
        if event.key == pygame.K_i:
            open_pause_tab("ship")
            play_sfx("pause")
            return True
        if event.key == pygame.K_s:
            open_pause_tab("status")
            play_sfx("pause")
            return True
        if event.key == pygame.K_b:
            open_pause_tab("build")
            play_sfx("pause")
            return True
        return False

    def handle_pointer_down(event):
        nonlocal audio_slider_dragging, game_state, pause_tab, build_tab
        refresh_touch_action_buttons()
        pos = event_pointer_pos(event)
        pointer_id = event_pointer_id(event)
        if pos is None:
            return False
        is_secondary_click = bool(hasattr(event, "button") and event.button == 3)
        if audio_toggle_button.collidepoint(pos):
            audio.toggle_all_mute()
            play_sfx("ui_click")
            return True
        if game_state in ("menu", "paused") and has_active_game:
            build_pause_nav_layout()
            for key in ("home", "map", "ship", "status", "build"):
                rect = pause_nav_ui.get(key)
                if rect is not None and rect.collidepoint(pos):
                    open_pause_tab(key)
                    play_sfx("ui_click")
                    return True
            if pause_tab == "build":
                if build_placement_mode is not None:
                    cancel_rect = build_ui.get("placement_cancel")
                    if is_secondary_click or (cancel_rect is not None and cancel_rect.collidepoint(pos)):
                        return cancel_build_placement("Placement canceled")
                    if not try_place_buildable_at_cursor(pos):
                        play_sfx("ui_click")
                    return True
                if build_ui.get("close") and build_ui["close"].collidepoint(pos):
                    return close_pause_overlay()
                for key, target in {
                    "tab_construct": "build_construct_core",
                    "tab_infra": "build_infra_economy",
                    "tab_logistics": "build_logistics_links",
                }.items():
                    rect = build_ui.get(key)
                    if rect is not None and rect.collidepoint(pos):
                        build_tab = target
                        play_sfx("ui_click")
                        return True
                if build_ui.get("subtab_primary") and build_ui["subtab_primary"].collidepoint(pos):
                    build_tab = (
                        "build_construct_core" if build_tab.startswith("build_construct_")
                        else "build_infra_economy" if build_tab.startswith("build_infra_")
                        else "build_logistics_links"
                    )
                    play_sfx("ui_click")
                    return True
                if build_ui.get("subtab_secondary") and build_ui["subtab_secondary"].collidepoint(pos):
                    build_tab = (
                        "build_construct_sites" if build_tab.startswith("build_construct_")
                        else "build_infra_defense" if build_tab.startswith("build_infra_")
                        else "build_logistics_convoy"
                    )
                    play_sfx("ui_click")
                    return True
                for key in ("build_station", "build_platform", "place_turret", "build_mining", "build_drone", "build_turret", "build_shield"):
                    rect = build_ui.get(key)
                    if rect is not None and rect.collidepoint(pos):
                        if not build_tab_action(key):
                            play_sfx("ui_click")
                        return True
            if pause_tab == "ship":
                return handle_ship_panel_action(resolve_ship_click(pos, ship_ui))
            if pause_tab == "status":
                if status_ui.get("close") and status_ui["close"].collidepoint(pos):
                    return close_pause_overlay()
            if pause_tab == "map" and close_panel_rect(map_panel_rect).collidepoint(pos):
                return close_pause_overlay()
        if menu_panel_active() and handle_menu_click(pos):
            return True
        if game_state in ("menu", "paused") and has_active_game and pause_tab == "map":
            if map_tile_parity_ok(map_panel_rect, active_sector):
                sector = map_sector_at_point(map_panel_rect, active_sector, pos)
                if sector is not None:
                    ftl_targets = owned_ftl_target_sectors(active_sector, player.warp_drive_level if player else 0)
                    if sector in ftl_targets:
                        return handle_ftl_jump_action(sector)
                    if sector in scanner_target_sectors(active_sector, player.scanner_level if player else 0):
                        return handle_scanner_action(sector)
        if game_state == "playing" and is_docked:
            if docked_context == "station":
                return handle_station_panel_action(resolve_station_click(pos, station_tab, station_ui))
            if docked_context == "planet":
                return handle_planet_panel_action(resolve_planet_click(pos, planet_ui))
        if game_state == "playing" and pause_button_rect.collidepoint(pos):
            open_pause_tab("home")
            play_sfx("pause")
            return True
        if game_state == "playing" and show_touch_action_controls and not is_docked:
            action = touch_action_at_pos(pos, touch_action_buttons)
            if action is not None:
                active_touch_actions[pointer_id] = action
                if action == "map":
                    open_pause_tab("map")
                elif action == "build":
                    open_pause_tab("build")
                elif action == "pause":
                    open_pause_tab("home")
                elif action == "interact":
                    handle_interact_action()
                sync_virtual_controls()
                return True
        return False

    def handle_pointer_motion(event):
        pos = event_pointer_pos(event)
        pointer_id = event_pointer_id(event)
        if pos is None:
            return False
        refresh_touch_action_buttons()
        if audio_slider_dragging is not None:
            set_audio_slider_value(audio_slider_dragging, pos[0])
            return True
        if pointer_id in active_touch_actions:
            if active_touch_actions.get(pointer_id) is not None:
                return True
        return False

    def handle_pointer_up(event):
        nonlocal audio_slider_dragging
        refresh_touch_action_buttons()
        pointer_id = event_pointer_id(event)
        audio_slider_dragging = None
        active_touch_actions.pop(pointer_id, None)
        sync_virtual_controls()
        return False

    def handle_event(event):
        nonlocal window_surface
        if event.type == pygame.VIDEORESIZE:
            window_surface = pygame.display.set_mode((max(640, event.w), max(360, event.h)), pygame.RESIZABLE)
            return True
        if event.type == pygame.WINDOWSIZECHANGED:
            surface = pygame.display.get_surface()
            if surface is not None:
                window_surface = surface
            return False
        if event.type == pygame.KEYDOWN:
            return handle_keydown(event)
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            return handle_pointer_down(event)
        if event.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            return handle_pointer_motion(event)
        if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            return handle_pointer_up(event)
        return False

    def normalize_in_sector(world_x, world_y, sector_x, sector_y):
        origin_x = sector_x * sector_manager.sector_width
        origin_y = sector_y * sector_manager.sector_height
        nx = (world_x - origin_x) / float(sector_manager.sector_width)
        ny = (world_y - origin_y) / float(sector_manager.sector_height)
        return max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))

    def world_to_local_position(world_x, world_y):
        return pygame.Vector2(float(world_x) - world_offset.x, float(world_y) - world_offset.y)

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

    def ensure_sector_planet_settlements(sector, state=None):
        if sector_owner(sector) != "player":
            return None

        current = state if state is not None else sector_economy_states.get(sector)
        if current is None:
            current = default_sector_economy_state(sector)
            sector_economy_states[sector] = current

        settlements = current.setdefault("settlements", {})
        for planet_id, _, _, accepted_metal, _ in sector_manager.get_sector_planets(sector[0], sector[1]):
            if planet_id in settlements:
                continue
            settlements[planet_id] = compute_default_planet_settlement_state(
                world_seed,
                sector,
                planet_id,
                accepted_metal,
            )
        return settlements

    def ensure_planet_settlement_state(planet_id):
        if planet_id is None:
            return None

        sector = parse_planet_sector(planet_id)
        state = ensure_player_sector_economy(sector)
        if state is None:
            return None

        settlements = ensure_sector_planet_settlements(sector, state=state)
        if settlements is None:
            return None

        if planet_id not in settlements:
            accepted_metal = "iron"
            for pid, _, _, metal, _ in sector_manager.get_sector_planets(sector[0], sector[1]):
                if pid == planet_id:
                    accepted_metal = metal
                    break
            settlements[planet_id] = compute_default_planet_settlement_state(
                world_seed,
                sector,
                planet_id,
                accepted_metal,
            )
        return settlements.get(planet_id)

    def planet_happiness(planet_id):
        settlement = ensure_planet_settlement_state(planet_id)
        if settlement is None:
            return 1.0
        return compute_settlement_happiness(settlement)

    def jobs_with_planet_happiness(jobs, planet_id):
        happiness = planet_happiness(planet_id)
        # Keep payout impact noticeable but bounded for early-game readability.
        payout_multiplier = max(0.8, min(1.3, 0.76 + happiness * 0.36))

        modified = []
        for job in jobs:
            item = dict(job)
            base_reward = int(item.get("reward", 0))
            item["reward"] = max(1, int(round(base_reward * payout_multiplier)))
            item["settlement_happiness"] = round(happiness, 2)
            modified.append(item)
        return modified

    def average_sector_settlement_happiness(sector):
        state = ensure_player_sector_economy(sector)
        if state is None:
            return 1.0
        settlements = ensure_sector_planet_settlements(sector, state=state)
        if not settlements:
            return 1.0

        values = [compute_settlement_happiness(s) for s in settlements.values()]
        if not values:
            return 1.0
        return sum(values) / float(len(values))

    def command_progression_profile():
        if player is None:
            return {
                "level": 1,
                "threat_scale": 1.0,
                "territory": 1,
                "infra": 0,
                "defense": 0,
                "population": 0,
            }

        owned = {home_sector}
        for sector, owner in sector_owner_overrides.items():
            if owner == "player":
                owned.add(sector)

        infra_score = 0.0
        defense_score = 0.0
        for station_id, _x, _y in stations_around_with_built(active_sector[0], active_sector[1], radius=8):
            if station_owner(station_id) != "player":
                continue
            st = get_station_upgrade_state(station_id)
            infra_score += float(st.get("level", 1))
            defense_score += float(st.get("laser", 0)) + float(st.get("missile", 0))

        total_population = 0
        for sector in owned:
            state = ensure_player_sector_economy(sector)
            if state is not None:
                total_population += int(state.get("population", 0))

        upgrade_depth = (
            player.shield_level
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
            + player.weapon_amp_level
            + player.deflector_booster_level
            + player.missile_payload_level
            + player.auto_mining_level
        )

        economic_band = min(18.0, float(player.credits) / 1200.0)
        raw_score = (
            player.combat_level * 2.4
            + len(owned) * 2.3
            + infra_score * 0.95
            + defense_score * 1.35
            + (total_population / 150.0)
            + (upgrade_depth * 0.7)
            + economic_band
        )
        difficulty_scale = float(DIFFICULTY_SETTINGS[selected_difficulty].get("progression_scale", 1.0))
        scaled_score = raw_score * difficulty_scale
        command_level = max(1, int(1 + scaled_score / 7.0))

        diff_cfg = DIFFICULTY_SETTINGS[selected_difficulty]
        threat_step = float(diff_cfg.get("command_threat_step", 0.02))
        threat_max = float(diff_cfg.get("command_threat_max", 0.38))
        threat_scale = 1.0 + min(threat_max, (command_level - 1) * threat_step)

        return {
            "level": command_level,
            "threat_scale": threat_scale,
            "territory": len(owned),
            "infra": int(round(infra_score)),
            "defense": int(round(defense_score)),
            "population": total_population,
        }

    def jobs_with_anomaly_incentives(jobs):
        boosted = []
        for job in jobs:
            item = dict(job)
            target_sector = item.get("target_sector")
            anomalies = scanner_anomalies_for_sector(target_sector) if target_sector is not None else []
            if not anomalies:
                item["anomaly_bonus"] = 0
                item["anomaly_tags"] = []
                item["anomaly_tag_summary"] = ""
                boosted.append(item)
                continue

            tags = []
            bonus = 0
            pressure_boost = 0.0
            for anomaly in anomalies:
                t = str(anomaly.get("type", ""))
                strength = max(0.5, float(anomaly.get("strength", 1.0)))
                if t == "black_hole":
                    tags.append("black hole")
                    bonus += int(round(80 * strength))
                    pressure_boost += 0.16 * strength
                elif t == "radiation_star":
                    tags.append("radiation")
                    bonus += int(round(70 * strength))
                    pressure_boost += 0.14 * strength
                elif t == "nebula_interference":
                    tags.append("nebula")
                    bonus += int(round(60 * strength))
                    pressure_boost += 0.12 * strength

            item["anomaly_bonus"] = max(0, int(bonus))
            item["reward"] = int(item.get("reward", 0)) + item["anomaly_bonus"]
            item["hazard_bonus"] = int(item.get("hazard_bonus", 0)) + item["anomaly_bonus"]
            item["attack_pressure"] = float(item.get("attack_pressure", 1.0)) + pressure_boost
            item["risk_rating"] = max(1, min(5, int(item.get("risk_rating", 1)) + 1))
            item["anomaly_tags"] = sorted(set(tags))
            item["anomaly_tag_summary"] = ", ".join(item["anomaly_tags"])
            boosted.append(item)

        return boosted

    def generate_context_jobs(context, origin_sector, planet_id=None):
        jobs = generate_jobs(context, sector_manager, origin_sector=origin_sector)
        jobs = jobs_with_anomaly_incentives(jobs)
        if context == "planet" and planet_id:
            jobs = jobs_with_planet_happiness(jobs, planet_id)
        return jobs

    def build_owned_sector_resource_networks():
        owned = {home_sector}
        for sector, owner in sector_owner_overrides.items():
            if owner == "player":
                owned.add(sector)

        visited = set()
        sector_network = {}
        resource_keys = ("food", "water", "power", "medical", "parts")

        for seed_sector in list(owned):
            if seed_sector in visited:
                continue

            stack = [seed_sector]
            component = []
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                if current not in owned:
                    continue
                visited.add(current)
                component.append(current)

                cx, cy = current
                for neighbor in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if neighbor in owned and neighbor not in visited:
                        stack.append(neighbor)

            pooled = {key: 0 for key in resource_keys}
            for sector in component:
                state = ensure_player_sector_economy(sector)
                resources = state.get("resources", {}) if state is not None else {}
                for key in resource_keys:
                    pooled[key] += int(resources.get(key, 0))

            for sector in component:
                sector_network[sector] = dict(pooled)

        return sector_network

    def update_settlement_economies(dt_seconds):
        dirty = False
        network_supply_by_sector = build_owned_sector_resource_networks()
        for sector, state in list(sector_economy_states.items()):
            if sector_owner(sector) != "player":
                continue

            settlements = ensure_sector_planet_settlements(sector, state=state)
            if not settlements:
                continue

            state["last_tick"] = float(state.get("last_tick", 0.0)) + dt_seconds
            tick_seconds = 8.0
            if state["last_tick"] < tick_seconds:
                continue

            ticks = int(state["last_tick"] // tick_seconds)
            state["last_tick"] -= tick_seconds * ticks
            ticks = min(4, max(1, ticks))
            resources = network_supply_by_sector.get(sector, state.get("resources", {}))
            state["shared_resources"] = dict(resources)

            for _ in range(ticks):
                for settlement in settlements.values():
                    req = compute_settlement_requirements(settlement)

                    for key in ("food", "water", "power"):
                        network_supply = max(0.0, float(resources.get(key, 0.0)))
                        local_gain = 2 + int(network_supply * 0.03)
                        current = int(settlement.get(key, 0))
                        settlement[key] = max(0, min(260, current + local_gain - int(req.get(key, 0))))

                    sec_need = int(req.get("security", 0))
                    sec_current = int(settlement.get("security", 0))
                    sec_delta = 1 if sec_current >= sec_need else -1
                    settlement["security"] = max(5, min(220, sec_current + sec_delta))

                    happiness = compute_settlement_happiness(settlement)
                    pop = int(settlement.get("population", 0))
                    if happiness >= 1.12:
                        pop += 1
                    elif happiness < 0.72 and pop > 20:
                        pop -= 1
                    settlement["population"] = max(20, min(1800, pop))

            if settlements:
                total_population = sum(int(s.get("population", 0)) for s in settlements.values())
                state["population"] = total_population
                state["workers"] = max(8, int(total_population * 0.48))

            dirty = True

        if dirty:
            snapshot_economy_state_cache()

    def ensure_player_sector_economy(sector):
        if sector_owner(sector) != "player":
            return None

        state = sector_economy_states.get(sector)
        if state is None:
            state = default_sector_economy_state(sector)
            sector_economy_states[sector] = state
        ensure_sector_planet_settlements(sector, state=state)
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

        state.setdefault("infra_mining", 0)
        state.setdefault("infra_drone", 0)
        state.setdefault("infra_turret", 0)
        state.setdefault("infra_shield", 0)
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

    def station_infra_level(station_id, kind):
        state = get_station_upgrade_state(station_id)
        return int(state.get(kind, 0))

    def station_infra_upgrade_cost(station_id, kind):
        lvl = station_infra_level(station_id, kind)
        if kind == "infra_mining":
            return INFRA_MINING_BASE_COST + lvl * INFRA_MINING_STEP_COST
        if kind == "infra_drone":
            return INFRA_DRONE_BASE_COST + lvl * INFRA_DRONE_STEP_COST
        if kind == "infra_turret":
            return INFRA_TURRET_BASE_COST + lvl * INFRA_TURRET_STEP_COST
        return INFRA_SHIELD_BASE_COST + lvl * INFRA_SHIELD_STEP_COST

    def infrastructure_max_health(station_id, kind):
        st = get_station_upgrade_state(station_id)
        level = int(st.get("level", 1))
        shield = int(st.get("infra_shield", 0))
        infra_level = int(st.get(kind, 0))
        return 35.0 + level * 10.0 + shield * 16.0 + infra_level * 12.0

    def ensure_infrastructure_health(station_id, kind):
        key = f"{station_id}:{kind}"
        max_hp = infrastructure_max_health(station_id, kind)
        hp = infrastructure_health.get(key)
        if hp is None:
            infrastructure_health[key] = max_hp
            return max_hp
        infrastructure_health[key] = min(max_hp, float(hp))
        return infrastructure_health[key]

    def infrastructure_offset(kind):
        return {
            "infra_mining": pygame.Vector2(-52, -20),
            "infra_drone": pygame.Vector2(52, -20),
            "infra_turret": pygame.Vector2(-44, 36),
            "infra_shield": pygame.Vector2(44, 36),
        }.get(kind, pygame.Vector2(0, 0))

    def station_max_health(station_id):
        st = get_station_upgrade_state(station_id)
        level = int(st.get("level", 1))
        shield = int(st.get("infra_shield", 0))
        return 120.0 + level * 42.0 + shield * 26.0

    def ensure_station_health(station_id):
        max_hp = station_max_health(station_id)
        hp = station_health.get(station_id)
        if hp is None:
            station_health[station_id] = max_hp
            return max_hp
        station_health[station_id] = min(max_hp, float(hp))
        return station_health[station_id]

    def station_disabled_timer(station_id):
        return max(0.0, float(station_disabled_timers.get(station_id, 0.0)))

    def station_is_disabled(station_id):
        return station_disabled_timer(station_id) > 0.0

    def active_sector_station_targets():
        targets = []
        for station in list(stations) if stations is not None else []:
            sid = getattr(station, "station_id", "")
            if parse_station_sector(sid) != active_sector:
                continue
            if station_owner(sid) != "player":
                continue
            if station_is_disabled(sid):
                continue
            hp = ensure_station_health(sid)
            if hp <= 0.0:
                continue
            targets.append(
                {
                    "station_id": sid,
                    "position": pygame.Vector2(station.position),
                    "radius": float(getattr(station, "radius", STATION_RADIUS)),
                    "hp": hp,
                    "max_hp": station_max_health(sid),
                    "level": station_level(sid),
                }
            )
        return targets

    def active_sector_station_statuses():
        statuses = []
        for station in list(stations) if stations is not None else []:
            sid = getattr(station, "station_id", "")
            if parse_station_sector(sid) != active_sector:
                continue
            if station_owner(sid) != "player":
                continue
            max_hp = station_max_health(sid)
            hp = ensure_station_health(sid)
            disabled_timer = station_disabled_timer(sid)
            statuses.append(
                {
                    "station_id": sid,
                    "position": pygame.Vector2(station.position),
                    "radius": float(getattr(station, "radius", STATION_RADIUS)),
                    "hp": hp,
                    "max_hp": max_hp,
                    "hp_ratio": 0.0 if max_hp <= 0 else max(0.0, min(1.0, hp / max_hp)),
                    "disabled_timer": disabled_timer,
                    "disabled": disabled_timer > 0.0,
                }
            )
        return statuses

    def draw_station_status_overlays(target, station_statuses):
        if not station_statuses:
            return

        for status in station_statuses:
            hp_ratio = float(status.get("hp_ratio", 1.0))
            disabled = bool(status.get("disabled", False))
            if not disabled and hp_ratio >= 0.995 and active_sector not in raid_events:
                continue

            pos = pygame.Vector2(status["position"])
            radius = float(status.get("radius", STATION_RADIUS))
            bar_w = 80
            bar_h = 8
            bar_x = int(pos.x - bar_w * 0.5)
            bar_y = int(pos.y - radius - 24)
            label_y = bar_y - 18

            if disabled:
                label_text = f"DISABLED {status['disabled_timer']:.0f}s"
                label_color = UI_COLORS["danger"]
                fill_color = (239, 68, 68)
            else:
                label_text = f"HULL {int(round(hp_ratio * 100))}%"
                label_color = UI_COLORS["warn"] if hp_ratio < 0.55 else UI_COLORS["muted"]
                fill_color = (250, 204, 21) if hp_ratio < 0.55 else (96, 165, 250)

            label_surface = hud_font.render(label_text, True, label_color)
            label_rect = label_surface.get_rect(center=(int(pos.x), label_y + label_surface.get_height() // 2))
            label_bg = label_rect.inflate(10, 4)
            pygame.draw.rect(target, (9, 16, 29, 208), label_bg, border_radius=6)
            pygame.draw.rect(target, label_color, label_bg, 1, border_radius=6)
            target.blit(label_surface, label_rect)

            bar_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
            pygame.draw.rect(target, (9, 16, 29), bar_rect, border_radius=4)
            pygame.draw.rect(target, (88, 102, 134), bar_rect, 1, border_radius=4)
            fill_w = int((bar_w - 2) * hp_ratio)
            if fill_w > 0:
                pygame.draw.rect(target, fill_color, pygame.Rect(bar_x + 1, bar_y + 1, fill_w, bar_h - 2), border_radius=3)

    def active_sector_infrastructure_targets():
        targets = []
        for station in list(stations) if stations is not None else []:
            sid = getattr(station, "station_id", "")
            if parse_station_sector(sid) != active_sector:
                continue
            if station_owner(sid) != "player":
                continue
            st = get_station_upgrade_state(sid)
            for kind in ("infra_mining", "infra_drone", "infra_turret", "infra_shield"):
                lvl = int(st.get(kind, 0))
                if lvl <= 0:
                    continue
                hp = ensure_infrastructure_health(sid, kind)
                if hp <= 0:
                    continue
                pos = station.position + infrastructure_offset(kind)
                targets.append({
                    "station_id": sid,
                    "kind": kind,
                    "position": pygame.Vector2(pos),
                    "station_position": pygame.Vector2(station.position),
                    "radius": 12 + lvl,
                    "hp": hp,
                    "max_hp": infrastructure_max_health(sid, kind),
                    "level": lvl,
                })
        return targets

    def infrastructure_damage_multiplier(station_id):
        shield_level = station_infra_level(station_id, "infra_shield")
        # Shield nets reduce module damage so infrastructure remains defendable.
        return max(0.42, 1.0 - shield_level * 0.14)

    def apply_infrastructure_damage(target, base_damage):
        key = f"{target['station_id']}:{target['kind']}"
        current_hp = float(infrastructure_health.get(key, target["max_hp"]))
        effective = max(0.2, float(base_damage) * infrastructure_damage_multiplier(target["station_id"]))
        infrastructure_health[key] = max(0.0, current_hp - effective)
        return infrastructure_health[key] <= 0.0

    def apply_station_damage(target, base_damage):
        sid = target.get("station_id", "")
        if not sid:
            return False
        current_hp = ensure_station_health(sid)
        shield_level = station_infra_level(sid, "infra_shield")
        effective = max(0.25, float(base_damage) * max(0.45, 1.0 - shield_level * 0.1))
        remaining = max(0.0, current_hp - effective)
        station_health[sid] = remaining
        if remaining > 0.0:
            return False
        station_disabled_timers[sid] = max(station_disabled_timer(sid), 18.0)
        station_health[sid] = max(18.0, station_max_health(sid) * 0.22)
        return True

    def repair_infrastructure_from_shields(dt_seconds):
        for station in list(stations) if stations is not None else []:
            sid = getattr(station, "station_id", "")
            if parse_station_sector(sid) != active_sector or station_owner(sid) != "player":
                continue
            shield_lvl = station_infra_level(sid, "infra_shield")
            if shield_lvl <= 0:
                continue
            for kind in ("infra_mining", "infra_drone", "infra_turret", "infra_shield"):
                infra_lvl = station_infra_level(sid, kind)
                if infra_lvl <= 0:
                    continue
                key = f"{sid}:{kind}"
                max_hp = infrastructure_max_health(sid, kind)
                current_hp = ensure_infrastructure_health(sid, kind)
                regen_rate = (0.22 + shield_lvl * 0.18 + infra_lvl * 0.05) * dt_seconds
                infrastructure_health[key] = min(max_hp, float(current_hp) + regen_rate)

    def repair_station_combat_state(dt_seconds):
        for station in list(stations) if stations is not None else []:
            sid = getattr(station, "station_id", "")
            if parse_station_sector(sid) != active_sector or station_owner(sid) != "player":
                continue
            max_hp = station_max_health(sid)
            current_hp = ensure_station_health(sid)
            shield_lvl = station_infra_level(sid, "infra_shield")
            regen_rate = (0.32 + station_level(sid) * 0.1 + shield_lvl * 0.22) * dt_seconds
            disable_timer = station_disabled_timer(sid)
            if disable_timer > 0.0:
                station_disabled_timers[sid] = max(0.0, disable_timer - dt_seconds)
                regen_cap = max_hp * (0.42 if station_disabled_timer(sid) > 0.0 else 0.68)
                station_health[sid] = min(regen_cap, current_hp + regen_rate * 0.75)
            else:
                station_health[sid] = min(max_hp, current_hp + regen_rate)

    def try_drone_intercept_hostile_shot(shot):
        nonlocal drone_intercept_cooldown
        if drone_intercept_cooldown > 0.0:
            return None
        if shot is None:
            return None

        owner = getattr(shot, "owner", None)
        if owner not in ("enemy", "enemy_station_laser", "enemy_station_missile"):
            return None

        for station in list(stations) if stations is not None else []:
            sid = getattr(station, "station_id", "")
            if parse_station_sector(sid) != active_sector or station_owner(sid) != "player":
                continue
            drone_lvl = station_infra_level(sid, "infra_drone")
            if drone_lvl <= 0:
                continue
            intercept_radius = 56 + drone_lvl * 24
            if station.position.distance_to(shot.position) > intercept_radius:
                continue
            intercept_chance = min(0.9, 0.33 + drone_lvl * 0.14)
            if random.random() <= intercept_chance:
                shot.kill()
                drone_intercept_cooldown = max(0.08, 0.34 - drone_lvl * 0.04)
                return station.position
        return None

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

    def get_sector_defense_turrets(sector):
        return defense_turrets_by_sector.get(sector, [])

    def placement_margin_for(kind):
        if kind == "station":
            return 150
        if kind == "platform":
            return 106
        return 78

    def placement_clearance_for(kind):
        if kind == "station":
            return 180.0
        if kind == "platform":
            return 112.0
        return 92.0

    def validate_build_placement(kind, screen_pos):
        x = float(screen_pos[0])
        y = float(screen_pos[1])
        margin = placement_margin_for(kind)
        if x < margin or x > SCREEN_WIDTH - margin or y < margin or y > SCREEN_HEIGHT - margin:
            return False, "Cannot place on the sector edge", None

        world_pos = pygame.Vector2(x, y) + world_offset
        clearance = placement_clearance_for(kind)

        for _station_id, world_x, world_y in get_sector_stations_with_built(active_sector[0], active_sector[1]):
            if world_pos.distance_to((world_x, world_y)) < clearance:
                return False, "Too close to another station", None

        for platform in get_sector_mining_platforms(active_sector):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue
            if world_pos.distance_to((float(platform.get("x", 0.0)), float(platform.get("y", 0.0)))) < clearance:
                return False, "Too close to another buildable", None

        for turret in get_sector_defense_turrets(active_sector):
            if float(turret.get("hp", 0.0)) <= 0.0:
                continue
            if world_pos.distance_to((float(turret.get("x", 0.0)), float(turret.get("y", 0.0)))) < clearance:
                return False, "Too close to another buildable", None

        for _planet_id, world_x, world_y, _accepted_metal, _color in sector_manager.get_sector_planets(active_sector[0], active_sector[1]):
            if world_pos.distance_to((world_x, world_y)) < clearance + 70.0:
                return False, "Too close to a planet", None

        return True, "", world_pos

    def stations_around_with_built(center_sector_x, center_sector_y, radius=1):
        stations_data = []
        for sy in range(center_sector_y - radius, center_sector_y + radius + 1):
            for sx in range(center_sector_x - radius, center_sector_x + radius + 1):
                stations_data.extend(get_sector_stations_with_built(sx, sy))
        return stations_data

    def build_status_for_sector(sector):
        player_station_id = player_station_in_sector(sector)
        if player_station_id is not None:
            return ("Build: you already have a station in this sector", "#94a3b8")
        if player is None or player.credits < BUILD_STATION_COST:
            return (f"Build: need {BUILD_STATION_COST} gold (press B)", "#fca5a5")
        return (f"Build Station: press B ({BUILD_STATION_COST}g)", "#86efac")

    def ftl_jump_range(level):
        staged = [0, 2, 3, 4, 6]
        idx = max(0, min(len(staged) - 1, int(level or 0)))
        return staged[idx]

    def owned_ftl_target_sectors(center_sector, warp_level):
        jump_range = ftl_jump_range(warp_level)
        if jump_range <= 0:
            return set()

        reachable = set()
        cx, cy = center_sector
        for sy in range(cy - jump_range, cy + jump_range + 1):
            for sx in range(cx - jump_range, cx + jump_range + 1):
                sector = (sx, sy)
                if sector == center_sector:
                    continue
                if max(abs(sx - cx), abs(sy - cy)) > jump_range:
                    continue
                if sector_owner(sector) == "player":
                    reachable.add(sector)
        return reachable

    def map_action_status_for_sector(sector):
        if sector == active_sector:
            return ("Current sector", UI_COLORS["muted"])

        ftl_targets = owned_ftl_target_sectors(active_sector, player.warp_drive_level if player else 0)
        if sector in ftl_targets:
            return (f"FTL jump ready: click to warp to {sector[0]},{sector[1]}", "#fcd34d")

        if sector_owner(sector) == "player" and player is not None and player.warp_drive_level > 0:
            return (
                f"Owned sector out of FTL range ({ftl_jump_range(player.warp_drive_level)} tiles)",
                UI_COLORS["warn"],
            )

        if sector in scanner_target_sectors(active_sector, player.scanner_level if player else 0):
            return (f"Scanner: click to pulse sector {sector[0]},{sector[1]}", "#93c5fd")

        return build_status_for_sector(sector)

    def sector_security_rating(sector):
        # Security infrastructure is intentionally simple: station defenses and
        # level upgrades raise regional security and suppress raid intensity.
        score = 0.0
        stations_data = get_sector_stations_with_built(sector[0], sector[1])
        for station_id, _, _ in stations_data:
            if station_owner(station_id) != "player":
                continue
            st = get_station_upgrade_state(station_id)
            level = int(st.get("level", 1))
            laser = int(st.get("laser", 0))
            missile = int(st.get("missile", 0))
            infra_mining = int(st.get("infra_mining", 0))
            infra_drone = int(st.get("infra_drone", 0))
            infra_turret = int(st.get("infra_turret", 0))
            infra_shield = int(st.get("infra_shield", 0))
            score += max(
                0.0,
                (level - 1) * 1.2
                + laser * 1.6
                + missile * 1.8
                + infra_mining * 0.5
                + infra_drone * 1.1
                + infra_turret * 1.3
                + infra_shield * 1.25,
            )

        for platform in get_sector_mining_platforms(sector):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue
            hp_ratio = float(platform.get("hp", 0.0)) / max(1.0, float(platform.get("max_hp", 1.0)))
            score += 0.65 * max(0.2, min(1.0, hp_ratio))

        for turret in get_sector_defense_turrets(sector):
            if float(turret.get("hp", 0.0)) <= 0.0:
                continue
            hp_ratio = float(turret.get("hp", 0.0)) / max(1.0, float(turret.get("max_hp", 1.0)))
            score += 1.0 * max(0.2, min(1.0, hp_ratio)) * max(1, int(turret.get("level", 1)))

        return max(0.0, min(12.0, score))

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
            new_contact = tune_contact_for_difficulty(new_contact)
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

        weighted = []
        for sector in candidates:
            happiness = average_sector_settlement_happiness(sector)
            # Lower happiness increases pressure and raid likelihood.
            base_weight = max(1, int(round((2.1 - max(0.5, min(1.6, happiness))) * 4)))
            convoy_focus = 1.0 + platform_raid_focus_bonus(sector)
            weight = max(1, int(round(base_weight * convoy_focus)))
            weighted.append(weight)

        target_sector = random.choices(candidates, weights=weighted, k=1)[0]
        raider = random.choice(["crimson", "jade", "gold"])
        cfg = raid_settings()
        security = sector_security_rating(target_sector)
        strain = max(0, min(3, int(ensure_platform_convoy_state(target_sector).get("strain", 0))))
        strain_wave_bonus = strain
        strain_wave_count_bonus = 1 if strain >= 2 else 0
        strain_interval_scale = max(0.62, 1.0 - strain * 0.12)
        wave_cut = int(security // 4.0)
        size_cut = int(security // 3.0)
        raid_events[target_sector] = {
            "faction": raider,
            "waves_remaining": max(1, int(cfg["waves"]) - wave_cut + strain_wave_count_bonus),
            "wave_size": max(1, int(cfg["wave_size"]) - size_cut + strain_wave_bonus),
            "wave_timer": 0.0,
            "wave_interval": max(2.6, float(cfg["wave_interval"]) * strain_interval_scale),
            "age": 0.0,
            "timeout": cfg["timeout"] + security * 6.0,
            "security": round(security, 2),
            "convoy_strain": strain,
        }

        station_message = (
            f"Raid alert: {owner_label(raider)} attacking sector "
            f"{target_sector[0]},{target_sector[1]}"
        )
        if security > 0.0:
            station_message += f" (security {security:.1f} dampening)"
        if strain > 0:
            station_message += f" | convoy strain {convoy_warning_label(strain)}"
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
                    spawn_enemy_wave(
                    sector,
                    raid["faction"],
                    count=raid.get("wave_size", 2),
                    entry_mode="offscreen"
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
        claim_operation["telegraph_sent"] = False
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
        claim_faction = owner_key if owner_key not in ("player", "null") else sector_hostile_faction(active_sector)
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
        claim_operation["telegraph_sent"] = False
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
            available_jobs = generate_context_jobs("station", claim_sector)
        elif target_kind == "planet" and target_id:
            planet_owner_overrides[target_id] = "player"
            available_jobs = generate_context_jobs("planet", claim_sector, planet_id=target_id)

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

        platforms = []
        for platform in get_sector_mining_platforms((sector_x, sector_y)):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue
            nx, ny = normalize_in_sector(float(platform.get("x", 0.0)), float(platform.get("y", 0.0)), sector_x, sector_y)
            platforms.append({"x": nx, "y": ny})

        asteroid_count = 0
        for asteroid_id, *_ in asteroid_data:
            if asteroid_id in destroyed_seed_asteroids:
                continue
            asteroid_count += 1

        previous = explored_sectors.get((sector_x, sector_y), {})
        explored_sectors[(sector_x, sector_y)] = {
            "has_station": len(stations) > 0,
            "has_platform": len(platforms) > 0,
            "has_planet": len(planets) > 0,
            "asteroid_density": asteroid_count,
            "stations": stations,
            "platforms": platforms,
            "planets": planets,
            "visited": bool(visited or previous.get("visited", False)),
            "charted": bool(charted or visited or previous.get("charted", False)),
        }

    def scanner_cooldown_for_level(level):
        # L0 unavailable, L1-L4 progressively faster scan cadence.
        return [999.0, 10.0, 7.0, 5.0, 3.5][max(0, min(4, int(level)))]

    def _stable_text_seed(text):
        seed = 2166136261
        for ch in str(text):
            seed ^= ord(ch)
            seed = (seed * 16777619) & 0xFFFFFFFF
        return seed

    def tune_contact_for_difficulty(contact):
        tuned = dict(contact)
        role = tuned.get("type", "harasser")
        cid = tuned.get("id", "")
        rng = random.Random((world_seed * 1315423911) ^ _stable_text_seed(cid) ^ 0x9E3779B9)
        roll = rng.random()

        if selected_difficulty == "easy":
            if role == "tank":
                tuned["type"] = "bomber" if roll < 0.22 else "harasser"
        elif selected_difficulty == "hard":
            if role == "harasser" and roll < 0.16:
                tuned["type"] = "tank"
            elif role == "bomber" and roll < 0.05:
                tuned["type"] = "tank"

        return tuned

    def get_persistent_sector_enemies(sector):
        pack = persistent_sector_enemies.get(sector)
        if pack is None:
            owner = sector_owner(sector)
            hostile_faction = sector_hostile_faction(sector)
            opening_size = max(2, min(5, int(base_enemy_max_alive) - 1))
            contacts = []
            if owner != "player":
                contacts = opening_contacts(world_seed, sector, allow_tank=True)[:opening_size]
                contacts = [tune_contact_for_difficulty(contact) for contact in contacts]
                for contact in contacts:
                    contact["faction"] = hostile_faction

            pack = {
                "contacts": contacts,
                "reinforce_timer": 10.0,
                "faction": hostile_faction,
            }
            persistent_sector_enemies[sector] = pack
        else:
            fallback_faction = pack.get("faction", sector_hostile_faction(sector))
            if fallback_faction not in ("crimson", "jade", "gold"):
                fallback_faction = sector_hostile_faction(sector)
            pack["faction"] = fallback_faction

            # Keep migrated/legacy contacts visually and behaviorally consistent.
            for contact in pack.get("contacts", []):
                contact_faction = contact.get("faction", fallback_faction)
                if contact_faction not in ("crimson", "jade", "gold"):
                    contact_faction = fallback_faction
                contact["faction"] = contact_faction
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
            ai_aggression=active_difficulty.get("ai_aggression", 1.0),
            ai_accuracy=active_difficulty.get("ai_accuracy", 1.0),
            ai_strafe=active_difficulty.get("ai_strafe", 1.0),
            ai_fire_intent=active_difficulty.get("ai_fire_intent", 1.0),
            ai_memory=active_difficulty.get("ai_memory", 1.0),
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
        new_contact = tune_contact_for_difficulty(new_contact)
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
                fallback_faction = pack.get("faction", sector_hostile_faction(active_sector))
                contact = {
                    "id": contact_id,
                    "type": "harasser",
                    "x": 0.5,
                    "y": 0.5,
                    "faction": fallback_faction,
                    "alive": True,
                    "opening": False,
                }
                contacts.append(contact)
                by_id[contact_id] = contact

            contact_faction = contact.get("faction", pack.get("faction", sector_hostile_faction(active_sector)))
            if contact_faction not in ("crimson", "jade", "gold"):
                contact_faction = pack.get("faction", sector_hostile_faction(active_sector))
            contact["faction"] = contact_faction

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

    def scanner_target_sectors(center_sector, level):
        return {
            (center_sector[0] + dx, center_sector[1] + dy)
            for dx, dy in scanner_pulse_offsets(level)
        }

    def scanner_anomalies_for_sector(sector):
        sx, sy = sector
        rng = random.Random(
            (world_seed * 1000003)
            ^ (sx * 73856093)
            ^ (sy * 19349663)
            ^ 0xA53C9E11
        )

        # Keep anomalies sparse and seed-stable for low-memory exploration pressure.
        roll = rng.random()
        if roll < 0.66:
            count = 0
        elif roll < 0.9:
            count = 1
        else:
            count = 2

        anomalies = []
        kinds = ["black_hole", "radiation_star", "nebula_interference"]
        for _ in range(count):
            anomaly_type = rng.choice(kinds)
            anomalies.append(
                {
                    "type": anomaly_type,
                    "x": rng.uniform(0.08, 0.92),
                    "y": rng.uniform(0.08, 0.92),
                    "strength": round(rng.uniform(0.8, 1.5), 2),
                }
            )
        return anomalies

    def anomaly_effect_profile(sector):
        if player is None:
            return {"pressure": 0.0, "entries": [], "hint": ""}

        entries = []
        total_pressure = 0.0
        for anomaly in scanner_anomalies_for_sector(sector):
            anomaly_type = str(anomaly.get("type", ""))
            strength = max(0.5, float(anomaly.get("strength", 1.0)))

            if anomaly_type == "black_hole":
                required = 3
                have = int(player.engine_tuning_level)
                deficit = max(0, required - have)
                if deficit > 0:
                    total_pressure += deficit * strength * 0.55
                entries.append({
                    "type": anomaly_type,
                    "required": required,
                    "have": have,
                    "deficit": deficit,
                    "strength": strength,
                    "x": float(anomaly.get("x", 0.5)),
                    "y": float(anomaly.get("y", 0.5)),
                })
            elif anomaly_type == "radiation_star":
                required = 2
                have = int(player.shield_level)
                deficit = max(0, required - have)
                if deficit > 0:
                    total_pressure += deficit * strength * 0.6
                entries.append({
                    "type": anomaly_type,
                    "required": required,
                    "have": have,
                    "deficit": deficit,
                    "strength": strength,
                    "x": float(anomaly.get("x", 0.5)),
                    "y": float(anomaly.get("y", 0.5)),
                })
            elif anomaly_type == "nebula_interference":
                required = 2
                have = int(player.scanner_level)
                deficit = max(0, required - have)
                if deficit > 0:
                    total_pressure += deficit * strength * 0.45
                entries.append({
                    "type": anomaly_type,
                    "required": required,
                    "have": have,
                    "deficit": deficit,
                    "strength": strength,
                    "x": float(anomaly.get("x", 0.5)),
                    "y": float(anomaly.get("y", 0.5)),
                })

        unmet = [entry for entry in entries if entry.get("deficit", 0) > 0]
        if not unmet:
            hint = "Anomaly pressure stable"
        else:
            labels = {
                "black_hole": "Engine",
                "radiation_star": "Shield",
                "nebula_interference": "Scanner",
            }
            needs = []
            for entry in unmet:
                needs.append(labels.get(entry["type"], "Upgrade"))
            hint = "Need " + "/".join(sorted(set(needs)))

        return {"pressure": total_pressure, "entries": entries, "hint": hint}

    def apply_active_sector_anomaly_effects(dt_seconds):
        nonlocal anomaly_tick_timer, scanner_cooldown_timer, station_message, station_message_timer, anomaly_pressure_hint
        if player is None:
            return

        profile = anomaly_effect_profile(active_sector)
        anomaly_pressure_hint = profile.get("hint", "")
        entries = profile.get("entries", [])
        if not entries:
            anomaly_tick_timer = 0.0
            return

        anomaly_tick_timer += dt_seconds
        radiation_load = 0.0
        for entry in entries:
            deficit = int(entry.get("deficit", 0))
            strength = float(entry.get("strength", 1.0))
            if deficit <= 0:
                continue

            if entry.get("type") == "black_hole":
                center = pygame.Vector2(
                    float(entry.get("x", 0.5)) * SCREEN_WIDTH,
                    float(entry.get("y", 0.5)) * SCREEN_HEIGHT,
                )
                delta = center - player.position
                if delta.length_squared() > 1e-6:
                    pull = delta.normalize() * (18.0 * deficit * strength * dt_seconds)
                    player.position += pull
                player.warp_energy = max(0.0, player.warp_energy - dt_seconds * 0.42 * deficit * strength)
            elif entry.get("type") == "nebula_interference":
                scanner_cooldown_timer = min(
                    8.0,
                    scanner_cooldown_timer + dt_seconds * 0.95 * deficit * strength,
                )
            elif entry.get("type") == "radiation_star":
                radiation_load += deficit * strength

        if radiation_load > 0.0 and anomaly_tick_timer >= 2.25:
            anomaly_tick_timer = 0.0
            if player.shield_layers > 0:
                player.shield_layers = max(0, player.shield_layers - 1)
                station_message = f"Radiation pulse drained shields ({player.shield_layers} layers left)"
                station_message_timer = 1.2
                play_sfx("player_hit")
            elif radiation_load >= 1.3:
                apply_player_hit("radiation_pulse")

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

        anomalies = scanner_anomalies_for_sector(sector)

        live_sector_intel[sector] = {
            "ships": len(enemy_points),
            "asteroids_current": asteroid_count,
            "enemy_points": enemy_points,
            "asteroid_points": asteroid_points,
            "anomalies": anomalies,
        }

        if not visited:
            capture_sector_snapshot(sx, sy, visited=False, charted=True)

        return True

    def perform_scanner_pulse(center_sector, force=False):
        nonlocal scanner_cooldown_timer, scanner_passive_timer, scanner_live_window, scanner_live_timer
        if player is None or player.scanner_level <= 0:
            return 0

        if not force and scanner_cooldown_timer > 0:
            return 0

        scanned = 0
        if center_sector == active_sector:
            sectors_to_scan = [
                (center_sector[0] + dx, center_sector[1] + dy)
                for dx, dy in scanner_pulse_offsets(player.scanner_level)
            ]
        else:
            dx = center_sector[0] - active_sector[0]
            dy = center_sector[1] - active_sector[1]
            if abs(dx) > 1 or abs(dy) > 1:
                return 0
            # Remote scan only reveals the exact selected sector.
            sectors_to_scan = [center_sector]

        scanned_sectors = set()
        for sector in sectors_to_scan:
            if scan_sector(sector):
                scanned += 1
                scanned_sectors.add(sector)

        if scanned_sectors:
            scanner_live_window = set(scanned_sectors)
            scanner_live_timer = 2.8 if force else max(3.0, scanner_cooldown_for_level(player.scanner_level))

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
            available_jobs = generate_context_jobs(
                docked_context,
                active_sector,
                planet_id=(docked_planet.planet_id if docked_planet is not None else None),
            )

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
        nonlocal is_docked, docked_context, docked_station, docked_planet, station_tab, metal_pickup_fx, ship_explosion_fx
        nonlocal player_spawn_grace_timer
        nonlocal docked_station
        nonlocal metal_prices, active_difficulty
        nonlocal targeting_locked_targets, targeting_mode_timer
        nonlocal station_sprites_by_id, planet_sprites_by_id, world_offset, active_sector
        nonlocal destroyed_seed_asteroids
        nonlocal available_jobs, active_contract, explored_sectors, build_tab
        nonlocal live_sector_intel, persistent_sector_enemies, scanner_cooldown_timer, scanner_passive_timer
        nonlocal scanner_live_window, scanner_live_timer
        nonlocal anomaly_tick_timer, anomaly_pressure_hint
        nonlocal enemy_field, base_enemy_spawn_interval, base_enemy_max_alive
        nonlocal current_enemy_spawn_interval, current_enemy_max_alive
        nonlocal sector_enemy_entry_grace_timer
        nonlocal sector_owner_overrides, station_owner_overrides, planet_owner_overrides
        nonlocal built_stations_by_sector, mining_platforms_by_sector, defense_turrets_by_sector, platform_convoy_states, platform_harvest_progress, ship_auto_mining_progress
        nonlocal raid_events, raid_spawn_timer
        nonlocal home_station_id, home_planet_id
        nonlocal station_upgrades, station_health, station_disabled_timers, station_defense_fire_timer, enemy_station_fire_timer
        nonlocal infrastructure_health, infrastructure_defense_fire_timer, passive_drone_income_timer, drone_intercept_cooldown
        nonlocal platform_logistics_hint_timer
        nonlocal sector_economy_states, economy_state_cache
        nonlocal claim_initiated_targets, build_placement_mode

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
        ship_auto_mining_progress = {}
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
        station_tab = "ship_core"
        metal_pickup_fx = []
        ship_explosion_fx = []
        player_spawn_grace_timer = 2.5
        targeting_locked_targets = []
        targeting_mode_timer = 0.0
        available_jobs = generate_context_jobs("station", active_sector)
        active_contract = None
        explored_sectors = {}
        live_sector_intel = {}
        persistent_sector_enemies = {}
        scanner_cooldown_timer = 0.0
        scanner_passive_timer = 0.0
        scanner_live_window = set()
        scanner_live_timer = 0.0
        anomaly_tick_timer = 0.0
        anomaly_pressure_hint = ""
        sector_enemy_entry_grace_timer = 0.0
        sector_owner_overrides = {home_sector: "player"}
        station_owner_overrides = {}
        planet_owner_overrides = {}
        built_stations_by_sector = {}
        mining_platforms_by_sector = {}
        defense_turrets_by_sector = {}
        platform_convoy_states = {}
        platform_harvest_progress = {}
        station_upgrades = {}
        station_health = {}
        station_disabled_timers = {}
        infrastructure_health = {}
        sector_economy_states = {}
        economy_state_cache = {"version": 1, "sectors": {}}
        station_defense_fire_timer = 0.0
        enemy_station_fire_timer = 0.0
        infrastructure_defense_fire_timer = 0.0
        passive_drone_income_timer = 0.0
        drone_intercept_cooldown = 0.0
        platform_logistics_hint_timer = 0.0
        build_placement_mode = None

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
            station_upgrades[home_station_id] = {
                "level": 1,
                "laser": 0,
                "missile": 0,
                "infra_mining": 0,
                "infra_drone": 0,
                "infra_turret": 0,
                "infra_shield": 0,
            }
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
        build_tab = "build_construct_core"
        load_active_sector_enemies(reset_grace=True)
        capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
        apply_scanner_reveal()

    def nearest_enemies_for_lock(max_locks):
        if not player or not enemies or max_locks <= 0:
            return []

        live_enemies = [enemy for enemy in list(enemies) if enemy.alive()]
        live_enemies.sort(key=lambda enemy: player.position.distance_to(enemy.position))
        return live_enemies[:max_locks]

    def acquire_player_missile_target(shot):
        if shot is None or enemies is None:
            return None

        existing_target = getattr(shot, "guided_target", None)
        if existing_target is not None and existing_target.alive():
            return existing_target

        live_enemies = [enemy for enemy in list(enemies) if enemy.alive()]
        if not live_enemies:
            shot.guided_target = None
            return None

        locked_target = None
        for candidate in targeting_locked_targets:
            if candidate is not None and candidate.alive():
                locked_target = candidate
                break
        if locked_target is not None:
            shot.guided_target = locked_target
            return locked_target

        if shot.velocity.length_squared() > 1e-6:
            travel_direction = shot.velocity.normalize()
        elif player is not None:
            travel_direction = pygame.Vector2(0, 1).rotate(player.rotation)
        else:
            travel_direction = pygame.Vector2(0, 1)

        search_range = 280 + max(0, int(getattr(player, "missile_level", 0))) * 120
        target = best_enemy_lock_candidate(
            shot.position,
            travel_direction,
            search_range,
            140.0,
            live_enemies,
        )
        if target is None:
            live_enemies.sort(key=lambda enemy: shot.position.distance_to(enemy.position))
            target = live_enemies[0]

        shot.guided_target = target
        return target

    def update_player_guided_missiles(dt_seconds):
        if shots is None or player is None:
            return

        for shot in list(shots):
            if getattr(shot, "owner", None) != "player_missile":
                continue

            target = acquire_player_missile_target(shot)
            if target is None:
                continue

            offset = target.position - shot.position
            if offset.length_squared() <= 1e-6:
                continue

            desired_direction = offset.normalize()
            speed = max(220.0, shot.velocity.length())
            if shot.velocity.length_squared() > 1e-6:
                current_direction = shot.velocity.normalize()
            else:
                current_direction = desired_direction

            turn_rate = 210.0 + player.missile_level * 55.0
            angle_delta = current_direction.angle_to(desired_direction)
            max_turn = turn_rate * dt_seconds
            clamped_turn = max(-max_turn, min(max_turn, angle_delta))
            new_direction = current_direction.rotate(clamped_turn)
            shot.velocity = new_direction * speed

    def sector_from_world_offset():
        return (
            int(round(world_offset.x / float(sector_manager.sector_width))),
            int(round(world_offset.y / float(sector_manager.sector_height))),
        )

    def sync_station_sectors(force=False):
        nonlocal active_sector, station_sprites_by_id, scanner_live_window, scanner_live_timer
        if player is None:
            return False

        center_sector = sector_from_world_offset()
        if not force and center_sector == active_sector:
            return False

        previous_sector = active_sector
        active_sector = center_sector
        if previous_sector != active_sector:
            scanner_live_window.clear()
            scanner_live_timer = 0.0
        desired_ids = set()
        stations_data = stations_around_with_built(center_sector[0], center_sector[1], radius=0)
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

        center_sector = sector_from_world_offset()
        if not force and center_sector == active_sector:
            return

        desired_ids = set()
        planets_data = sector_manager.planets_around(center_sector[0], center_sector[1], radius=0)
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

        asteroid_specs = sector_manager.asteroids_around(active_sector[0], active_sector[1], radius=0)
        safe_spawn_radius = 180
        asteroid_edge_buffer = 96
        for asteroid_id, world_x, world_y, radius, vx, vy in asteroid_specs:
            if asteroid_id in destroyed_seed_asteroids:
                continue

            local_x = world_x - world_offset.x
            local_y = world_y - world_offset.y
            if local_x < asteroid_edge_buffer or local_x > SCREEN_WIDTH - asteroid_edge_buffer:
                continue
            if local_y < asteroid_edge_buffer or local_y > SCREEN_HEIGHT - asteroid_edge_buffer:
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
        nonlocal station_message, station_message_timer, sector_wrap_transition_timer
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
            sector_wrap_transition_timer = 0.18
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

        happiness = planet_happiness(planet.planet_id)
        market_multiplier = max(0.8, min(1.35, 0.78 + happiness * 0.37))
        tuned_total = max(1, int(round(gained * market_multiplier)))
        adjusted = tuned_total - gained
        if adjusted != 0:
            player.credits += adjusted
            gained = tuned_total

        station_message = f"Sold {sold_units} {metal_type} for {gained} gold (happiness x{market_multiplier:.2f})"
        station_message_timer = 1.8
        log_event(
            "planet_trade",
            metal=metal_type,
            quantity=sold_units,
            gold=gained,
            market_multiplier=round(market_multiplier, 3),
            settlement_happiness=round(happiness, 3),
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

    def player_station_in_sector(sector):
        sx, sy = sector
        for station_id, _x, _y in get_sector_stations_with_built(sx, sy):
            if station_owner(station_id) == "player":
                return station_id
        return None

    def get_sector_mining_platforms(sector):
        return mining_platforms_by_sector.get(sector, [])

    def _convoy_seed_sector_state(sector):
        sx, sy = sector
        seed = (world_seed * 1103515245) ^ (sx * 73856093) ^ (sy * 19349663) ^ 0x6B84221D
        rng = random.Random(seed & 0xFFFFFFFF)
        return {
            "cooldown": 20.0 + rng.uniform(6.0, 18.0),
            "active": False,
            "time_left": 0.0,
            "stabilize_progress": 0.0,
            "efficiency": 1.0,
            "failures": 0,
            "strain": 0,
        }

    def ensure_platform_convoy_state(sector):
        state = platform_convoy_states.get(sector)
        if state is None:
            state = _convoy_seed_sector_state(sector)
            platform_convoy_states[sector] = state
        return state

    def platform_convoy_snapshot(sector):
        state = ensure_platform_convoy_state(sector)
        return {
            "active": bool(state.get("active", False)),
            "time_left": float(state.get("time_left", 0.0)),
            "cooldown": float(state.get("cooldown", 0.0)),
            "stabilize_progress": float(state.get("stabilize_progress", 0.0)),
            "efficiency": float(state.get("efficiency", 1.0)),
            "failures": int(state.get("failures", 0)),
            "strain": int(state.get("strain", 0)),
        }

    def platform_recovery_efficiency(sector):
        return max(0.45, min(1.0, float(ensure_platform_convoy_state(sector).get("efficiency", 1.0))))

    def platform_output_multiplier(sector):
        strain = int(ensure_platform_convoy_state(sector).get("strain", 0))
        return max(0.46, 1.0 - 0.18 * max(0, min(3, strain)))

    def platform_raid_focus_bonus(sector):
        strain = int(ensure_platform_convoy_state(sector).get("strain", 0))
        return max(0.0, min(0.9, 0.24 * max(0, min(3, strain))))

    def convoy_warning_label(strain):
        level = max(0, min(3, int(strain)))
        if level <= 0:
            return "STABLE"
        if level == 1:
            return "ELEVATED"
        if level == 2:
            return "HIGH"
        return "CRITICAL"

    def update_platform_convoy_events(dt_seconds):
        nonlocal station_message, station_message_timer, platform_logistics_hint_timer
        if player is None:
            return

        sector = active_sector
        live_platforms = [
            p
            for p in get_sector_mining_platforms(sector)
            if float(p.get("hp", 0.0)) > 0.0
        ]
        if sector_owner(sector) != "player" or not live_platforms:
            return

        state = ensure_platform_convoy_state(sector)
        raid_active = sector in raid_events
        state["cooldown"] = max(0.0, float(state.get("cooldown", 0.0)) - dt_seconds)

        # Route health slowly recovers when convoy pressure is absent.
        if not bool(state.get("active", False)) and not raid_active:
            state["efficiency"] = min(1.0, float(state.get("efficiency", 1.0)) + dt_seconds * 0.012)

        if not bool(state.get("active", False)) and state["cooldown"] <= 0.0:
            state["active"] = True
            state["time_left"] = 15.0
            state["stabilize_progress"] = 0.0
            state["cooldown"] = 0.0
            if platform_logistics_hint_timer <= 0.0:
                station_message = "Convoy retrieval window opened: escort route to a mining platform"
                station_message_timer = 1.9
                platform_logistics_hint_timer = 1.0

        if not bool(state.get("active", False)):
            return

        state["time_left"] = max(0.0, float(state.get("time_left", 0.0)) - dt_seconds)

        near_any_platform = False
        for platform in live_platforms:
            pos = world_to_local_position(platform.get("x", 0.0), platform.get("y", 0.0))
            if player.position.distance_to(pos) <= 170.0:
                near_any_platform = True
                break

        if near_any_platform and not raid_active:
            state["stabilize_progress"] = min(
                4.0,
                float(state.get("stabilize_progress", 0.0)) + dt_seconds,
            )

        if float(state.get("stabilize_progress", 0.0)) >= 4.0:
            state["active"] = False
            state["time_left"] = 0.0
            state["stabilize_progress"] = 0.0
            state["cooldown"] = 28.0
            state["efficiency"] = min(1.0, float(state.get("efficiency", 1.0)) + 0.12)
            had_strain = int(state.get("strain", 0)) > 0
            state["strain"] = 0
            if platform_logistics_hint_timer <= 0.0:
                station_message = (
                    "Convoy route stabilized: failure chain cleared"
                    if had_strain
                    else "Convoy route stabilized: recovery efficiency improved"
                )
                station_message_timer = 1.8
                platform_logistics_hint_timer = 1.0
            return

        if float(state.get("time_left", 0.0)) <= 0.0:
            state["active"] = False
            state["stabilize_progress"] = 0.0
            state["cooldown"] = 16.0
            state["failures"] = int(state.get("failures", 0)) + 1
            state["strain"] = min(3, int(state.get("strain", 0)) + 1)
            penalty = 0.09 if raid_active else 0.05
            state["efficiency"] = max(0.45, float(state.get("efficiency", 1.0)) - penalty)
            if platform_logistics_hint_timer <= 0.0:
                station_message = (
                    "Convoy retrieval failed under pressure: buffered cargo recovery reduced"
                    if raid_active
                    else "Convoy retrieval missed: buffered cargo recovery reduced"
                )
                station_message_timer = 1.9
                platform_logistics_hint_timer = 1.0

    def active_sector_mining_platform_targets():
        targets = []
        for platform in get_sector_mining_platforms(active_sector):
            hp = float(platform.get("hp", 0.0))
            if hp <= 0.0:
                continue
            targets.append(
                {
                    "platform_id": str(platform.get("id", "")),
                    "position": world_to_local_position(platform.get("x", 0.0), platform.get("y", 0.0)),
                    "radius": 15,
                    "hp": hp,
                    "max_hp": float(platform.get("max_hp", 140.0)),
                }
            )
        return targets

    def active_sector_defense_turret_targets():
        targets = []
        for turret in get_sector_defense_turrets(active_sector):
            hp = float(turret.get("hp", 0.0))
            if hp <= 0.0:
                continue
            targets.append(
                {
                    "turret_id": str(turret.get("id", "")),
                    "position": world_to_local_position(turret.get("x", 0.0), turret.get("y", 0.0)),
                    "radius": 16,
                    "hp": hp,
                    "max_hp": float(turret.get("max_hp", 90.0)),
                    "level": int(turret.get("level", 1)),
                }
            )
        return targets

    def platform_logistics_summary(sector):
        live = 0
        linked = 0
        buffered_credits = 0
        buffered_parts = 0
        for platform in get_sector_mining_platforms(sector):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue
            live += 1
            if bool(platform.get("linked", True)):
                linked += 1
            buffered_credits += int(platform.get("buffer_credits", 0))
            buffered_parts += int(platform.get("buffer_parts", 0))
        return {
            "live": live,
            "linked": linked,
            "offline": max(0, live - linked),
            "buffer_credits": buffered_credits,
            "buffer_parts": buffered_parts,
        }

    def update_platform_logistics(dt_seconds):
        nonlocal station_message, station_message_timer, platform_logistics_hint_timer
        if player is None:
            return

        raid_active = active_sector in raid_events
        recovery_efficiency = platform_recovery_efficiency(active_sector)
        transfer_credits = 0
        transfer_parts = 0
        lost_credits = 0
        lost_parts = 0
        relinked = 0

        for platform in get_sector_mining_platforms(active_sector):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue

            platform.setdefault("linked", True)
            platform.setdefault("buffer_credits", 0)
            platform.setdefault("buffer_parts", 0)
            platform.setdefault("max_hp", max(1.0, float(platform.get("hp", 1.0))))

            pos = world_to_local_position(platform.get("x", 0.0), platform.get("y", 0.0))
            near_player = player.position.distance_to(pos) <= 156.0

            if raid_active:
                platform["linked"] = False
            elif near_player and not bool(platform.get("linked", False)):
                platform["linked"] = True
                relinked += 1

            if near_player:
                buffered_credits = int(platform.get("buffer_credits", 0))
                buffered_parts = int(platform.get("buffer_parts", 0))
                recovered_credits = int(round(buffered_credits * recovery_efficiency))
                recovered_parts = int(round(buffered_parts * recovery_efficiency))
                transfer_credits += recovered_credits
                transfer_parts += recovered_parts
                lost_credits += max(0, buffered_credits - recovered_credits)
                lost_parts += max(0, buffered_parts - recovered_parts)
                platform["buffer_credits"] = 0
                platform["buffer_parts"] = 0

        if transfer_credits > 0:
            player.credits += transfer_credits
        if transfer_parts > 0:
            eco_state = ensure_player_sector_economy(active_sector)
            if eco_state is not None:
                resources = eco_state.setdefault("resources", {})
                resources["parts"] = int(resources.get("parts", 0)) + transfer_parts
                snapshot_economy_state_cache()

        platform_logistics_hint_timer = max(0.0, platform_logistics_hint_timer - dt_seconds)
        if relinked > 0 and platform_logistics_hint_timer <= 0.0:
            station_message = f"Route link restored for {relinked} mining platform(s)"
            station_message_timer = 1.6
            platform_logistics_hint_timer = 1.1
        elif (transfer_credits > 0 or transfer_parts > 0) and platform_logistics_hint_timer <= 0.0:
            if lost_credits > 0 or lost_parts > 0:
                station_message = (
                    f"Recovered +{transfer_credits}g, +{transfer_parts} parts "
                    f"(route loss {lost_credits}g/{lost_parts} parts)"
                )
            else:
                station_message = f"Recovered platform cargo +{transfer_credits}g, +{transfer_parts} parts"
            station_message_timer = 1.7
            platform_logistics_hint_timer = 1.1

    def apply_mining_platform_damage(target, base_damage):
        platforms = get_sector_mining_platforms(active_sector)
        for platform in platforms:
            if str(platform.get("id", "")) != target.get("platform_id", ""):
                continue
            platform["hp"] = max(0.0, float(platform.get("hp", 0.0)) - max(0.2, float(base_damage)))
            capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
            return platform["hp"] <= 0.0
        return False

    def apply_defense_turret_damage(target, base_damage):
        turrets = get_sector_defense_turrets(active_sector)
        for turret in turrets:
            if str(turret.get("id", "")) != target.get("turret_id", ""):
                continue
            turret["hp"] = max(0.0, float(turret.get("hp", 0.0)) - max(0.2, float(base_damage)))
            return turret["hp"] <= 0.0
        return False

    def start_build_placement(kind):
        nonlocal build_placement_mode, station_message, station_message_timer
        if kind == "station":
            if player_station_in_sector(active_sector) is not None:
                station_message = "You already have a station in this sector"
                station_message_timer = 1.5
                return False
            if player.credits < BUILD_STATION_COST:
                station_message = f"Need {BUILD_STATION_COST} gold to build station"
                station_message_timer = 1.5
                return False
            build_placement_mode = {"kind": "station", "label": "Station", "cost": BUILD_STATION_COST}
        elif kind == "platform":
            if sector_owner(active_sector) != "player":
                station_message = "Claim this sector before deploying a mining platform"
                station_message_timer = 1.7
                return False
            if player_station_in_sector(active_sector) is None:
                station_message = "Need a Union station in sector first"
                station_message_timer = 1.6
                return False
            live_count = sum(1 for p in get_sector_mining_platforms(active_sector) if float(p.get("hp", 0.0)) > 0.0)
            if live_count >= MINING_PLATFORM_MAX_PER_SECTOR:
                station_message = "Mining platform cap reached in this sector"
                station_message_timer = 1.6
                return False
            if player.credits < BUILD_MINING_PLATFORM_COST:
                station_message = f"Need {BUILD_MINING_PLATFORM_COST} gold"
                station_message_timer = 1.4
                return False
            build_placement_mode = {"kind": "platform", "label": "Mining Platform", "cost": BUILD_MINING_PLATFORM_COST}
        elif kind == "turret":
            if sector_owner(active_sector) != "player":
                station_message = "Claim this sector before placing a defense turret"
                station_message_timer = 1.6
                return False
            if player_station_in_sector(active_sector) is None:
                station_message = "Need a Union station in sector first"
                station_message_timer = 1.6
                return False
            live_count = sum(1 for turret in get_sector_defense_turrets(active_sector) if float(turret.get("hp", 0.0)) > 0.0)
            if live_count >= DEFENSE_TURRET_MAX_PER_SECTOR:
                station_message = "Defense turret cap reached in this sector"
                station_message_timer = 1.5
                return False
            if player.credits < BUILD_DEFENSE_TURRET_COST:
                station_message = f"Need {BUILD_DEFENSE_TURRET_COST} gold"
                station_message_timer = 1.4
                return False
            build_placement_mode = {"kind": "turret", "label": "Defense Turret", "cost": BUILD_DEFENSE_TURRET_COST}
        else:
            return False

        station_message = f"Placement mode: click sector to place {build_placement_mode['label']}"
        station_message_timer = 1.6
        play_sfx("upgrade")
        return True

    def place_station_at(world_pos):
        nonlocal station_message, station_message_timer, build_placement_mode
        sx, sy = active_sector
        station_id = f"{sx}:{sy}:player"
        built_stations_by_sector[(sx, sy)] = (station_id, float(world_pos.x), float(world_pos.y))
        station_owner_overrides[station_id] = "player"
        station_upgrades[station_id] = {
            "level": 1,
            "laser": 0,
            "missile": 0,
            "infra_mining": 0,
            "infra_drone": 0,
            "infra_turret": 0,
            "infra_shield": 0,
        }
        sector_owner_overrides[(sx, sy)] = "player"
        ensure_player_sector_economy((sx, sy))
        snapshot_economy_state_cache()
        player.credits -= BUILD_STATION_COST
        build_placement_mode = None
        sync_station_sectors(force=True)
        capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
        station_message = "Station built. Sector is now under your control"
        station_message_timer = 2.0
        play_sfx("upgrade")
        return True

    def place_mining_platform_at(world_pos):
        nonlocal station_message, station_message_timer, build_placement_mode
        sector_platforms = get_sector_mining_platforms(active_sector)
        idx = len(sector_platforms)
        max_hp = 120.0 + idx * 18.0
        platform_id = f"{active_sector[0]}:{active_sector[1]}:platform:{idx + 1}"
        sector_platforms.append(
            {
                "id": platform_id,
                "x": float(world_pos.x),
                "y": float(world_pos.y),
                "hp": max_hp,
                "max_hp": max_hp,
                "linked": True,
                "buffer_credits": 0,
                "buffer_parts": 0,
            }
        )
        mining_platforms_by_sector[active_sector] = sector_platforms
        player.credits -= BUILD_MINING_PLATFORM_COST
        build_placement_mode = None
        capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
        station_message = "Mining platform deployed"
        station_message_timer = 1.7
        play_sfx("upgrade")
        return True

    def place_defense_turret_at(world_pos):
        nonlocal station_message, station_message_timer, build_placement_mode
        sector_turrets = get_sector_defense_turrets(active_sector)
        idx = len(sector_turrets)
        turret_id = f"{active_sector[0]}:{active_sector[1]}:turret:{idx + 1}"
        max_hp = 90.0
        sector_turrets.append(
            {
                "id": turret_id,
                "x": float(world_pos.x),
                "y": float(world_pos.y),
                "variant": "onslaught_alpha" if idx % 2 == 0 else "onslaught_barrage",
                "level": 1,
                "hp": max_hp,
                "max_hp": max_hp,
                "cooldown": 0.0,
            }
        )
        defense_turrets_by_sector[active_sector] = sector_turrets
        player.credits -= BUILD_DEFENSE_TURRET_COST
        build_placement_mode = None
        station_message = "Defense turret emplaced"
        station_message_timer = 1.7
        play_sfx("upgrade")
        return True

    def asteroid_tracking_id(asteroid):
        seeded_id = getattr(asteroid, "seeded_id", None)
        if seeded_id is not None:
            return f"seed:{seeded_id}"
        return f"runtime:{id(asteroid)}"

    def mining_platform_drone_count(platform):
        hp_ratio = float(platform.get("hp", 0.0)) / max(1.0, float(platform.get("max_hp", 1.0)))
        return 3 if hp_ratio >= 0.75 else 2

    def mining_platform_target_asteroids(platform, limit=None):
        if asteroids is None:
            return []

        local_pos = world_to_local_position(platform.get("x", 0.0), platform.get("y", 0.0))
        max_targets = mining_platform_drone_count(platform) if limit is None else int(limit)
        candidates = []
        for asteroid in list(asteroids):
            if not asteroid.alive():
                continue
            distance = local_pos.distance_to(asteroid.position)
            candidates.append((distance, asteroid))
        candidates.sort(key=lambda item: item[0])
        return [asteroid for _, asteroid in candidates[:max_targets]]

    def mining_platform_drone_specs(platform):
        local_pos = world_to_local_position(platform.get("x", 0.0), platform.get("y", 0.0))
        targets = mining_platform_target_asteroids(platform)
        specs = []

        if targets:
            for idx, asteroid in enumerate(targets):
                harvest_key = f"{platform.get('id', '')}:{asteroid_tracking_id(asteroid)}"
                threshold = max(1.0, asteroid.radius / 18.0)
                progress = min(1.0, float(platform_harvest_progress.get(harvest_key, 0.0)) / threshold)
                travel = 0.26 + 0.56 * (0.5 + 0.5 * math.sin(elapsed_time * 3.6 + idx * 1.3 + progress * 3.2))
                drone_pos = local_pos.lerp(asteroid.position, min(0.92, travel))
                specs.append(
                    {
                        "position": drone_pos,
                        "target": asteroid.position,
                        "color": get_metal_color(getattr(asteroid, "metal_type", "iron")),
                    }
                )
            return specs

        idle_count = mining_platform_drone_count(platform)
        for idx in range(idle_count):
            angle = elapsed_time * (58 + idx * 7) + idx * (360.0 / idle_count)
            orbit = pygame.Vector2(28 + idx * 3, 0).rotate(angle)
            specs.append(
                {
                    "position": local_pos + orbit,
                    "target": None,
                    "color": (125, 211, 252),
                }
            )
        return specs

    def ship_auto_mining_target_asteroids(limit=None):
        if asteroids is None or player is None or player.auto_mining_level <= 0:
            return []

        max_targets = player.get_auto_mining_drone_count() if limit is None else int(limit)
        if max_targets <= 0:
            return []

        max_range = player.get_auto_mining_range()
        candidates = []
        for asteroid in list(asteroids):
            if not asteroid.alive():
                continue
            distance = player.position.distance_to(asteroid.position)
            if distance > max_range:
                continue
            candidates.append((distance, asteroid))
        candidates.sort(key=lambda item: item[0])
        return [asteroid for _, asteroid in candidates[:max_targets]]

    def ship_auto_mining_drone_specs():
        if player is None or player.auto_mining_level <= 0:
            return []

        targets = ship_auto_mining_target_asteroids()
        specs = []
        if targets:
            for idx, asteroid in enumerate(targets):
                harvest_key = f"ship:{asteroid_tracking_id(asteroid)}"
                threshold = max(1.1, asteroid.radius / 16.0)
                progress = min(1.0, float(ship_auto_mining_progress.get(harvest_key, 0.0)) / threshold)
                travel = 0.24 + 0.5 * (0.5 + 0.5 * math.sin(elapsed_time * 3.2 + idx * 1.1 + progress * 3.4))
                drone_anchor = player.position + pygame.Vector2(24 + idx * 6, 0).rotate(elapsed_time * (64 + idx * 8) + idx * 140)
                drone_pos = drone_anchor.lerp(asteroid.position, min(0.82, travel))
                specs.append(
                    {
                        "position": drone_pos,
                        "target": asteroid.position,
                        "color": get_metal_color(getattr(asteroid, "metal_type", "iron")),
                    }
                )
            return specs

        idle_count = player.get_auto_mining_drone_count()
        for idx in range(idle_count):
            angle = elapsed_time * (76 + idx * 7) + idx * (360.0 / max(1, idle_count))
            orbit = pygame.Vector2(24 + idx * 5, 0).rotate(angle)
            specs.append(
                {
                    "position": player.position + orbit,
                    "target": None,
                    "color": (125, 211, 252),
                }
            )
        return specs

    def platform_mining_reward(metals):
        credits = 0
        parts = 0
        for metal_type, amount in metals.items():
            amount = max(0, int(amount))
            credits += max(6, int(round(metal_prices.get(metal_type, 12) * 0.42))) * amount
            parts += amount
        return credits, parts

    def credit_platform_mining(platform, metals):
        if not metals:
            return

        credits, parts = platform_mining_reward(metals)
        eco_state = ensure_player_sector_economy(active_sector)
        raid_active = active_sector in raid_events
        if raid_active or not bool(platform.get("linked", True)):
            platform["linked"] = False
            platform["buffer_credits"] = min(220, int(platform.get("buffer_credits", 0)) + credits)
            platform["buffer_parts"] = min(180, int(platform.get("buffer_parts", 0)) + parts)
            return

        if credits > 0:
            player.credits += credits
        if parts > 0 and eco_state is not None:
            resources = eco_state.setdefault("resources", {})
            resources["parts"] = int(resources.get("parts", 0)) + parts
            snapshot_economy_state_cache()

    def update_mining_platform_drone_behavior(dt_seconds):
        nonlocal platform_harvest_progress
        if asteroids is None or player is None:
            return

        active_keys = set()
        for platform in get_sector_mining_platforms(active_sector):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue

            targets = mining_platform_target_asteroids(platform)
            mined_asteroid = False
            for asteroid in targets:
                harvest_key = f"{platform.get('id', '')}:{asteroid_tracking_id(asteroid)}"
                active_keys.add(harvest_key)
                threshold = max(1.0, asteroid.radius / 18.0)
                platform_harvest_progress[harvest_key] = float(platform_harvest_progress.get(harvest_key, 0.0)) + dt_seconds * 0.85
                if platform_harvest_progress[harvest_key] < threshold:
                    continue

                platform_harvest_progress.pop(harvest_key, None)
                seeded_id = getattr(asteroid, "seeded_id", None)
                if seeded_id is not None:
                    destroyed_seed_asteroids.add(seeded_id)
                impact_position = asteroid.position.copy()
                play_sfx("asteroid_hit")
                mined_metals = asteroid.split()
                if mined_metals:
                    spawn_metal_pickup_fx(metal_pickup_fx, impact_position, mined_metals)
                    credit_platform_mining(platform, mined_metals)
                mined_asteroid = True
                break

            if mined_asteroid:
                continue

        for harvest_key in list(platform_harvest_progress.keys()):
            if harvest_key not in active_keys:
                platform_harvest_progress.pop(harvest_key, None)

    def update_ship_auto_mining_behavior(dt_seconds):
        nonlocal ship_auto_mining_progress
        if asteroids is None or player is None or player.auto_mining_level <= 0 or is_docked:
            ship_auto_mining_progress = {}
            return

        active_keys = set()
        targets = ship_auto_mining_target_asteroids()
        for asteroid in targets:
            harvest_key = f"ship:{asteroid_tracking_id(asteroid)}"
            active_keys.add(harvest_key)
            threshold = max(1.1, asteroid.radius / 16.0)
            ship_auto_mining_progress[harvest_key] = float(ship_auto_mining_progress.get(harvest_key, 0.0)) + dt_seconds * player.get_auto_mining_harvest_rate()
            if ship_auto_mining_progress[harvest_key] < threshold:
                continue

            ship_auto_mining_progress.pop(harvest_key, None)
            seeded_id = getattr(asteroid, "seeded_id", None)
            if seeded_id is not None:
                destroyed_seed_asteroids.add(seeded_id)
            impact_position = asteroid.position.copy()
            play_sfx("asteroid_hit")
            mined_metals = asteroid.split()
            if mined_metals:
                player.add_metal_batch(mined_metals)
                spawn_metal_pickup_fx(metal_pickup_fx, impact_position, mined_metals)
                log_event(
                    "resource_mined_auto_drone",
                    metals=mined_metals,
                    total_units=player.total_metal_units(),
                    level=player.auto_mining_level,
                )
            break

        for harvest_key in list(ship_auto_mining_progress.keys()):
            if harvest_key not in active_keys:
                ship_auto_mining_progress.pop(harvest_key, None)

    def fire_defense_turret_variant(turret, turret_pos, target_enemy):
        variant = str(turret.get("variant", "onslaught_alpha"))
        level = max(1, int(turret.get("level", 1)))
        delta = pygame.Vector2(target_enemy.position) - turret_pos
        if delta.length_squared() <= 1e-6:
            return False

        base_direction = delta.normalize()
        if variant == "onslaught_barrage":
            spreads = (-12, 0, 12)
            speed = PLAYER_SHOOT_SPEED * 1.02
            life = 1.15
            damage = 0.6 + level * 0.34
            cooldown = max(0.78, 1.18 - level * 0.04)
        else:
            spreads = (-5, 5)
            speed = PLAYER_SHOOT_SPEED * 1.18
            life = 0.9
            damage = 0.72 + level * 0.4
            cooldown = max(0.42, 0.72 - level * 0.03)

        for spread in spreads:
            direction = base_direction.rotate(spread)
            shot = Shot(turret_pos.x, turret_pos.y, max(2, SHOT_RADIUS), owner="defense_turret")
            shot.velocity = direction * speed
            shot.life = life
            shot.damage = damage
        turret["cooldown"] = cooldown
        return True

    def try_place_buildable_at_cursor(screen_pos):
        nonlocal station_message, station_message_timer
        if build_placement_mode is None:
            return False
        valid, reason, world_pos = validate_build_placement(build_placement_mode["kind"], screen_pos)
        if not valid:
            station_message = reason
            station_message_timer = 1.2
            return False
        if build_placement_mode["kind"] == "station":
            return place_station_at(world_pos)
        if build_placement_mode["kind"] == "platform":
            return place_mining_platform_at(world_pos)
        if build_placement_mode["kind"] == "turret":
            return place_defense_turret_at(world_pos)
        return False

    def try_build_mining_platform_in_active_sector():
        nonlocal station_message, station_message_timer
        if sector_owner(active_sector) != "player":
            station_message = "Claim this sector before deploying a mining platform"
            station_message_timer = 1.7
            play_sfx("ui_click")
            return False
        if player_station_in_sector(active_sector) is None:
            station_message = "Need a Union station in sector first"
            station_message_timer = 1.6
            play_sfx("ui_click")
            return False

        sector_platforms = get_sector_mining_platforms(active_sector)
        live_count = sum(1 for p in sector_platforms if float(p.get("hp", 0.0)) > 0.0)
        if live_count >= MINING_PLATFORM_MAX_PER_SECTOR:
            station_message = "Mining platform cap reached in this sector"
            station_message_timer = 1.6
            play_sfx("ui_click")
            return False

        if player.credits < BUILD_MINING_PLATFORM_COST:
            station_message = f"Need {BUILD_MINING_PLATFORM_COST} gold"
            station_message_timer = 1.4
            play_sfx("ui_click")
            return False
        return start_build_placement("platform")

    def try_upgrade_station_kind(station_id, kind):
        nonlocal station_message, station_message_timer
        if station_id is None:
            station_message = "No Union station in sector"
            station_message_timer = 1.4
            play_sfx("ui_click")
            return False

        state = get_station_upgrade_state(station_id)
        limits = {
            "level": STATION_LEVEL_MAX,
            "laser": STATION_LASER_MAX,
            "missile": STATION_MISSILE_MAX,
            "infra_mining": INFRA_UPGRADE_MAX,
            "infra_drone": INFRA_UPGRADE_MAX,
            "infra_turret": INFRA_UPGRADE_MAX,
            "infra_shield": INFRA_UPGRADE_MAX,
        }
        labels = {
            "level": "Station Hull",
            "laser": "Station Laser",
            "missile": "Station Missile",
            "infra_mining": "Mining Drones",
            "infra_drone": "Interceptor Drones",
            "infra_turret": "Turret Grid",
            "infra_shield": "Shield Net",
        }
        if kind not in limits:
            return False

        current = int(state.get(kind, 0))
        if current >= int(limits[kind]):
            station_message = f"{labels[kind]} maxed"
            station_message_timer = 1.3
            play_sfx("ui_click")
            return False

        if kind == "level":
            cost = station_level_upgrade_cost(station_id)
        elif kind == "laser":
            cost = station_laser_upgrade_cost(station_id)
        elif kind == "missile":
            cost = station_missile_upgrade_cost(station_id)
        else:
            cost = station_infra_upgrade_cost(station_id, kind)

        if player.credits < cost:
            station_message = f"Need {cost} gold"
            station_message_timer = 1.3
            play_sfx("ui_click")
            return False

        player.credits -= cost
        state[kind] = current + 1
        if kind.startswith("infra_"):
            ensure_infrastructure_health(station_id, kind)
        station_message = f"{labels[kind]} upgraded to L{state[kind]}"
        station_message_timer = 1.6
        play_sfx("upgrade")
        return True

    def try_build_station_in_active_sector():
        nonlocal station_message, station_message_timer
        existing_player_station = player_station_in_sector(active_sector)
        if existing_player_station is not None:
            station_message = "You already have a station in this sector"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return False
        if player.credits < BUILD_STATION_COST:
            station_message = f"Need {BUILD_STATION_COST} gold to build station"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return False
        return start_build_placement("station")

    def build_tab_action(action_key):
        sid = player_station_in_sector(active_sector)
        if action_key == "build_station":
            return try_build_station_in_active_sector()
        if action_key == "build_platform":
            return try_build_mining_platform_in_active_sector()
        if action_key == "place_turret":
            return start_build_placement("turret")
        if action_key == "build_mining":
            return try_upgrade_station_kind(sid, "infra_mining")
        if action_key == "build_drone":
            return try_upgrade_station_kind(sid, "infra_drone")
        if action_key == "build_turret":
            return try_upgrade_station_kind(sid, "infra_turret")
        if action_key == "build_shield":
            return try_upgrade_station_kind(sid, "infra_shield")
        return False

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

        try_upgrade_station_kind(sid, kind)

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
        if player_spawn_grace_timer > 0.0:
            return
        if god_mode:
            return
        if hit_source == "asteroid_collision" and player.absorb_deflector_hit():
            play_sfx("player_hit")
            station_message = "Deflector shield absorbed asteroid impact"
            station_message_timer = 1.2
            log_event(
                "deflector_hit",
                source=hit_source,
                deflector_layers=player.deflector_layers,
            )
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

    def handle_ftl_jump_action(target_sector):
        nonlocal station_message, station_message_timer, world_offset, player_spawn_grace_timer
        if not has_active_game or player is None:
            return False
        if is_docked:
            station_message = "Undock before initiating FTL"
            station_message_timer = 1.4
            play_sfx("ui_click")
            return True
        if target_sector == active_sector:
            station_message = "Already in that sector"
            station_message_timer = 1.2
            play_sfx("ui_click")
            return True

        reachable = owned_ftl_target_sectors(active_sector, player.warp_drive_level)
        if target_sector not in reachable:
            station_message = "Target sector is outside owned FTL range"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return True

        sync_active_sector_enemies_to_persistent()
        world_offset.update(
            float(target_sector[0] * sector_manager.sector_width),
            float(target_sector[1] * sector_manager.sector_height),
        )
        player.position.update(SCREEN_WIDTH * 0.5, SCREEN_HEIGHT * 0.5)
        player_spawn_grace_timer = max(player_spawn_grace_timer, 1.6)
        sector_changed = sync_station_sectors(force=True)
        sync_planet_sectors(force=True)
        sync_asteroid_sectors(force=True)
        if sector_changed:
            load_active_sector_enemies(reset_grace=True)
        capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
        apply_scanner_reveal()
        station_message = f"FTL jump complete: {active_sector[0]},{active_sector[1]}"
        station_message_timer = 1.5
        play_sfx("upgrade")
        return True

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
            present_frame()

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
        nonlocal scanner_cooldown_timer, scanner_passive_timer, scanner_live_window, scanner_live_timer
        nonlocal anomaly_tick_timer, anomaly_pressure_hint, sector_wrap_transition_timer
        nonlocal station_defense_fire_timer, enemy_station_fire_timer, station_health, station_disabled_timers
        nonlocal infrastructure_defense_fire_timer, passive_drone_income_timer, ship_auto_mining_progress, drone_intercept_cooldown
        nonlocal platform_logistics_hint_timer
        nonlocal player_spawn_grace_timer

        player_spawn_grace_timer = max(0.0, player_spawn_grace_timer - dt)
        previous_wrap_transition_timer = sector_wrap_transition_timer
        sector_wrap_transition_timer = max(0.0, sector_wrap_transition_timer - dt)
        if previous_wrap_transition_timer > 0.0 and sector_wrap_transition_timer <= 0.0:
            sync_station_sectors(force=True)
            sync_planet_sectors(force=True)
            sync_asteroid_sectors(force=True)

        command_profile = command_progression_profile()
        pressure = contract_attack_pressure() * float(command_profile.get("threat_scale", 1.0))
        pressure = min(float(active_difficulty.get("pressure_cap", 1.6)), pressure)

        current_enemy_spawn_interval = max(0.55, base_enemy_spawn_interval / pressure)
        current_enemy_max_alive = max(
            1,
            int(round(base_enemy_max_alive * (0.85 + 0.45 * max(0.0, pressure - 1.0)))),
        )
        if enemy_field is not None:
            enemy_field.spawn_interval = current_enemy_spawn_interval
            enemy_field.spawn_tuning["max_alive"] = current_enemy_max_alive

        if player is not None:
            scanner_cooldown_timer = max(0.0, scanner_cooldown_timer - dt)
            scanner_live_timer = max(0.0, scanner_live_timer - dt)
            if scanner_live_timer <= 0.0:
                scanner_live_window.clear()
            apply_active_sector_anomaly_effects(dt)
            update_settlement_economies(dt)
            update_persistent_sector_enemies(dt)
            sync_active_sector_enemies_to_persistent()
            update_raid_events(dt)
            update_platform_convoy_events(dt)
            repair_infrastructure_from_shields(dt)
            repair_station_combat_state(dt)
            update_platform_logistics(dt)
            update_ship_auto_mining_behavior(dt)

            drone_intercept_cooldown = max(0.0, drone_intercept_cooldown - dt)

            passive_drone_income_timer = max(0.0, passive_drone_income_timer - dt)
            if passive_drone_income_timer <= 0.0:
                mined_total = 0
                mined_parts = 0
                for station in list(stations) if stations is not None else []:
                    sid = getattr(station, "station_id", "")
                    if parse_station_sector(sid) != active_sector:
                        continue
                    if station_owner(sid) != "player":
                        continue
                    mining_lvl = station_infra_level(sid, "infra_mining")
                    if mining_lvl <= 0:
                        continue
                    mined_total += max(1, int(round(1.4 + mining_lvl * 1.55 + station_level(sid) * 0.5)))
                    mined_parts += max(1, int(round(0.8 + mining_lvl * 0.6)))
                if mined_total > 0:
                    player.credits += mined_total
                if mined_parts > 0:
                    eco_state = ensure_player_sector_economy(active_sector)
                    if eco_state is not None:
                        resources = eco_state.setdefault("resources", {})
                        resources["parts"] = int(resources.get("parts", 0)) + mined_parts
                        snapshot_economy_state_cache()

                platform_credit = 0
                platform_parts = 0
                raid_active = active_sector in raid_events
                platform_output_scale = platform_output_multiplier(active_sector)
                for platform in get_sector_mining_platforms(active_sector):
                    if float(platform.get("hp", 0.0)) <= 0.0:
                        continue
                    platform.setdefault("linked", True)
                    platform.setdefault("buffer_credits", 0)
                    platform.setdefault("buffer_parts", 0)
                    hp_ratio = float(platform.get("hp", 0.0)) / max(1.0, float(platform.get("max_hp", 1.0)))
                    mined_credit = max(1, int(round(4.5 * hp_ratio * platform_output_scale)))
                    mined_parts = max(1, int(round(2.1 * hp_ratio * platform_output_scale)))
                    if raid_active or not bool(platform.get("linked", True)):
                        platform["linked"] = False
                        platform["buffer_credits"] = min(220, int(platform.get("buffer_credits", 0)) + mined_credit)
                        platform["buffer_parts"] = min(180, int(platform.get("buffer_parts", 0)) + mined_parts)
                    else:
                        platform_credit += mined_credit
                        platform_parts += mined_parts
                if platform_credit > 0:
                    player.credits += platform_credit
                if platform_parts > 0:
                    eco_state = ensure_player_sector_economy(active_sector)
                    if eco_state is not None:
                        resources = eco_state.setdefault("resources", {})
                        resources["parts"] = int(resources.get("parts", 0)) + platform_parts
                        snapshot_economy_state_cache()
                passive_drone_income_timer = 8.0

            station_defense_fire_timer = max(0.0, station_defense_fire_timer - dt)
            enemy_station_fire_timer = max(0.0, enemy_station_fire_timer - dt)
            if station_defense_fire_timer <= 0.0 and enemies is not None:
                for station in list(stations) if stations is not None else []:
                    sid = getattr(station, "station_id", "")
                    if parse_station_sector(sid) != active_sector:
                        continue
                    if station_owner(sid) != "player":
                        continue
                    if station_is_disabled(sid):
                        continue
                    st = get_station_upgrade_state(sid)
                    live_targets = [enemy for enemy in list(enemies) if enemy.alive()]
                    if not live_targets:
                        continue

                    laser_level = max(1, int(st.get("laser", 0)))
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
                station_defense_fire_timer = 1.05

            if enemies is not None:
                live_targets = [enemy for enemy in list(enemies) if enemy.alive()]
                if live_targets:
                    for turret in get_sector_defense_turrets(active_sector):
                        if float(turret.get("hp", 0.0)) <= 0.0:
                            continue
                        turret["cooldown"] = max(0.0, float(turret.get("cooldown", 0.0)) - dt)
                        if float(turret.get("cooldown", 0.0)) > 0.0:
                            continue
                        turret_pos = world_to_local_position(turret.get("x", 0.0), turret.get("y", 0.0))
                        variant = str(turret.get("variant", "onslaught_alpha"))
                        target = min(live_targets, key=lambda enemy: turret_pos.distance_to(enemy.position))
                        turret_range = 250 + int(turret.get("level", 1)) * 30
                        if variant == "onslaught_barrage":
                            turret_range += 36
                        if turret_pos.distance_to(target.position) > turret_range:
                            continue
                        if fire_defense_turret_variant(turret, turret_pos, target):
                            play_sfx("enemy_shoot")

            infrastructure_defense_fire_timer = max(0.0, infrastructure_defense_fire_timer - dt)
            if infrastructure_defense_fire_timer <= 0.0 and enemies is not None:
                for station in list(stations) if stations is not None else []:
                    sid = getattr(station, "station_id", "")
                    if parse_station_sector(sid) != active_sector:
                        continue
                    if station_owner(sid) != "player":
                        continue
                    if station_is_disabled(sid):
                        continue

                    st = get_station_upgrade_state(sid)
                    drone_lvl = int(st.get("infra_drone", 0))
                    turret_lvl = int(st.get("infra_turret", 0))
                    if drone_lvl <= 0 and turret_lvl <= 0:
                        continue
                    live_targets = [enemy for enemy in list(enemies) if enemy.alive()]
                    if not live_targets:
                        continue
                    target = min(live_targets, key=lambda e: station.position.distance_to(e.position))
                    fired = False
                    if turret_lvl > 0 and station.position.distance_to(target.position) <= 300 + turret_lvl * 34:
                        fired = fire_station_projectile(
                            station,
                            target.position,
                            "infra_turret",
                            "laser",
                            turret_lvl,
                        )
                    if not fired and drone_lvl > 0 and station.position.distance_to(target.position) <= 260 + drone_lvl * 38:
                        fired = fire_station_projectile(
                            station,
                            target.position,
                            "infra_drone",
                            "missile",
                            drone_lvl,
                        )
                infrastructure_defense_fire_timer = 1.25

            if enemy_station_fire_timer <= 0.0 and player is not None:
                station_targets = active_sector_station_targets()
                infra_targets = active_sector_infrastructure_targets()
                platform_targets = active_sector_mining_platform_targets()
                turret_targets = active_sector_defense_turret_targets()
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
                    if station_targets and active_sector in raid_events:
                        target_pos = min(
                            station_targets,
                            key=lambda item: station.position.distance_to(item["position"]),
                        )["position"]
                    elif platform_targets and active_sector in raid_events:
                        target_pos = min(
                            platform_targets,
                            key=lambda item: station.position.distance_to(item["position"]),
                        )["position"]
                    elif station_targets:
                        target_pos = min(
                            station_targets,
                            key=lambda item: station.position.distance_to(item["position"]),
                        )["position"]
                    elif infra_targets:
                        target_pos = min(
                            infra_targets,
                            key=lambda item: station.position.distance_to(item["position"]),
                        )["position"]
                    elif turret_targets:
                        target_pos = min(
                            turret_targets,
                            key=lambda item: station.position.distance_to(item["position"]),
                        )["position"]
                    else:
                        target_pos = player.position

                    distance_to_player = station.position.distance_to(target_pos)

                    if player.cloak_active and not station_targets and not infra_targets and not platform_targets and not turret_targets:
                        continue

                    laser_range = 210 + level * 20 + laser_level * 28
                    missile_range = 300 + level * 30 + missile_level * 36

                    fired = False
                    if missile_level > 0 and distance_to_player <= missile_range:
                        fired = fire_station_projectile(
                            station,
                            target_pos,
                            "enemy_station_missile",
                            "missile",
                            missile_level,
                        )
                    if not fired and laser_level > 0 and distance_to_player <= laser_range:
                        fired = fire_station_projectile(
                            station,
                            target_pos,
                            "enemy_station_laser",
                            "laser",
                            laser_level,
                        )
                enemy_station_fire_timer = 1.95

            station_targets = active_sector_station_targets()
            infra_targets = active_sector_infrastructure_targets()
            platform_targets = active_sector_mining_platform_targets()
            turret_targets = active_sector_defense_turret_targets()
            prioritized_targets = (
                station_targets + platform_targets + infra_targets + turret_targets
                if active_sector in raid_events
                else station_targets + infra_targets + turret_targets + platform_targets
            )
            if prioritized_targets and enemies is not None:
                sec = sector_security_rating(active_sector)
                if sec < 5.0 or active_sector in raid_events:
                    ordered_enemies = [enemy for enemy in list(enemies) if enemy.alive()]
                    ordered_enemies.sort(key=lambda e: e.position.distance_to(player.position))
                    hostile_focus = min(
                        len(ordered_enemies),
                        max(2, min(6, len(prioritized_targets) + max(0, int(round(4.5 - sec))))),
                    )
                    for enemy in ordered_enemies:
                        enemy.forced_target_timer = 0.0
                    for enemy in ordered_enemies[:hostile_focus]:
                        target = min(prioritized_targets, key=lambda t: enemy.position.distance_to(t["position"]))
                        enemy.forced_target_position = pygame.Vector2(target["position"])
                        enemy.forced_target_velocity = pygame.Vector2(0, 0)
                        enemy.forced_target_radius = float(target.get("radius", 18.0))
                        enemy.forced_target_timer = 0.9
                        if enemy.shoot_timer > 0:
                            continue
                        if enemy.position.distance_to(target["position"]) > enemy.view_range * 1.08:
                            continue
                        enemy.aim_at_target(target["position"], None)
                        enemy.shoot()

            if claim_operation["active"]:
                if active_sector != claim_operation["sector"]:
                    station_message = cancel_claim("Claim failed: left target sector")
                    station_message_timer = 1.8
                    play_sfx("ui_click")
                else:
                    claim_operation["progress"] += dt
                    if claim_operation["waves_remaining"] > 0:
                        claim_operation["wave_timer"] = max(0.0, claim_operation["wave_timer"] - dt)
                        if claim_operation["wave_timer"] <= 2.2 and not claim_operation.get("telegraph_sent", False):
                            claim_operation["telegraph_sent"] = True
                            station_message = (
                                "Reinforcements inbound from sector edge. "
                                f"{claim_operation['waves_remaining']} wave(s) remaining"
                            )
                            station_message_timer = 1.5
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
                            claim_operation["telegraph_sent"] = False
                            station_message = (
                                f"Wave engaged from edge. "
                                f"{claim_operation['waves_remaining']} wave(s) remaining"
                            )
                            station_message_timer = 1.5
                            play_sfx("enemy_shoot")

                    if claim_operation["progress"] >= claim_operation["duration"]:
                        complete_claim_operation()

            # Passive ping at scanner capstone level.
            if player.scanner_level >= 4:
                scanner_passive_timer += dt
                if scanner_passive_timer >= 9.0:
                    # Capstone scanner now refreshes only current-sector tactical intel.
                    # Nearby sectors still require explicit pulse scans.
                    scan_sector(active_sector)
                    scanner_live_window = {active_sector}
                    scanner_live_timer = max(scanner_live_timer, 2.8)
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
            if updatable is not None:
                updatable.update(dt, player)
            if player is not None and prev_player_position is not None:
                update_world_offset_from_wrap(prev_player_position, player.position)
                if sync_station_sectors():
                    sync_planet_sectors(force=True)
                    sync_asteroid_sectors(force=True)
                    load_active_sector_enemies(reset_grace=True)

            update_mining_platform_drone_behavior(dt)
            update_player_guided_missiles(dt)

            if enemies is not None:
                for enemy in list(enemies):
                    if enemy.collides_with(player):
                        apply_player_hit("enemy_collision")

            if asteroids is not None:
                for asteroid in list(asteroids):
                    if asteroid.collides_with(player):
                        apply_player_hit("asteroid_collision")

            if shots is not None:
                for shot in list(shots):
                    if getattr(shot, "owner", None) == "player":
                        if enemies is not None:
                            for enemy in list(enemies):
                                if enemy.collides_with(shot):
                                    shot.kill()
                                    damage = player.get_combat_damage() if player is not None else 1.0
                                    will_destroy = enemy.health <= damage
                                    if will_destroy:
                                        play_sfx("enemy_destroyed")
                                    else:
                                        play_sfx("enemy_hit")
                                    enemy.take_damage(damage)
                                    if will_destroy:
                                        award_player_xp(enemy_xp_reward(enemy))
                                    break
                    elif getattr(shot, "owner", None) == "player_missile":
                        if enemies is not None:
                            for enemy in list(enemies):
                                if enemy.collides_with(shot):
                                    shot.kill()
                                    missile_damage = player.get_missile_damage()
                                    impact_position = enemy.position.copy()
                                    will_destroy = enemy.health <= missile_damage
                                    if will_destroy:
                                        play_sfx("enemy_destroyed")
                                    else:
                                        play_sfx("enemy_hit")
                                    enemy.take_damage(missile_damage)
                                    if will_destroy:
                                        award_player_xp(enemy_xp_reward(enemy) + 4)

                                    splash_radius = player.get_missile_splash_radius()
                                    for splash_target in list(enemies):
                                        if not splash_target.alive() or splash_target is enemy:
                                            continue
                                        distance = splash_target.position.distance_to(impact_position)
                                        if distance > splash_radius:
                                            continue
                                        splash_ratio = 1.0 - min(1.0, distance / splash_radius)
                                        splash_damage = max(0.1, missile_damage * 0.42 * splash_ratio)
                                        splash_kill = splash_target.health <= splash_damage
                                        splash_target.take_damage(splash_damage)
                                        if splash_kill:
                                            award_player_xp(enemy_xp_reward(splash_target))

                                    spawn_ship_explosion_fx(
                                        ship_explosion_fx,
                                        impact_position,
                                        8 + player.missile_level * 1.2,
                                        "#f97316",
                                        burst_scale=1.0,
                                        fragments=False,
                                        sparks=False,
                                        spark_life_scale=0.65,
                                    )
                                    break
                    elif getattr(shot, "owner", None) in ("station_laser", "station_missile"):
                        if enemies is not None:
                            for enemy in list(enemies):
                                if enemy.collides_with(shot):
                                    shot.kill()
                                    damage = float(getattr(shot, "damage", 1.0))
                                    will_destroy = enemy.health <= damage
                                    enemy.take_damage(damage)
                                    if will_destroy:
                                        award_player_xp(enemy_xp_reward(enemy))
                                        play_sfx("enemy_destroyed")
                                    else:
                                        play_sfx("enemy_hit")
                                    break
                    elif getattr(shot, "owner", None) in ("infra_turret", "infra_drone", "defense_turret"):
                        if enemies is not None:
                            for enemy in list(enemies):
                                if enemy.collides_with(shot):
                                    shot.kill()
                                    damage = float(getattr(shot, "damage", 1.0)) * 0.9
                                    will_destroy = enemy.health <= damage
                                    enemy.take_damage(damage)
                                    if will_destroy:
                                        award_player_xp(enemy_xp_reward(enemy))
                                    break
                    elif getattr(shot, "owner", None) in ("enemy_station_laser", "enemy_station_missile"):
                        intercept_pos = try_drone_intercept_hostile_shot(shot)
                        if intercept_pos is not None:
                            spawn_ship_explosion_fx(ship_explosion_fx, intercept_pos, 5, "#67e8f9", burst_scale=0.65)
                            continue
                        hit_station = False
                        for target in active_sector_station_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                disabled = apply_station_damage(target, float(getattr(shot, "damage", 1.0)))
                                hit_station = True
                                if disabled:
                                    station_message = "Station disabled"
                                    station_message_timer = 1.4
                                break
                        if hit_station:
                            continue
                        hit_infra = False
                        for target in active_sector_infrastructure_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                destroyed = apply_infrastructure_damage(target, float(getattr(shot, "damage", 1.0)))
                                hit_infra = True
                                if destroyed:
                                    station_message = f"{target['kind'].replace('infra_', '').title()} destroyed"
                                    station_message_timer = 1.3
                                break
                        if hit_infra:
                            continue
                        hit_platform = False
                        for target in active_sector_mining_platform_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                destroyed = apply_mining_platform_damage(target, float(getattr(shot, "damage", 1.0)))
                                hit_platform = True
                                if destroyed:
                                    station_message = "Mining platform destroyed"
                                    station_message_timer = 1.3
                                break
                        if hit_platform:
                            continue
                        hit_turret = False
                        for target in active_sector_defense_turret_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                destroyed = apply_defense_turret_damage(target, float(getattr(shot, "damage", 1.0)))
                                hit_turret = True
                                if destroyed:
                                    station_message = "Defense turret destroyed"
                                    station_message_timer = 1.3
                                break
                        if hit_turret:
                            continue
                        if shot.collides_with(player):
                            shot.kill()
                            apply_player_hit("enemy_station_shot")
                    elif getattr(shot, "owner", None) == "enemy":
                        intercept_pos = try_drone_intercept_hostile_shot(shot)
                        if intercept_pos is not None:
                            spawn_ship_explosion_fx(ship_explosion_fx, intercept_pos, 5, "#67e8f9", burst_scale=0.65)
                            continue
                        hit_station = False
                        for target in active_sector_station_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                disabled = apply_station_damage(target, 1.0)
                                hit_station = True
                                if disabled:
                                    station_message = "Station disabled"
                                    station_message_timer = 1.4
                                break
                        if hit_station:
                            continue
                        hit_infra = False
                        for target in active_sector_infrastructure_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                destroyed = apply_infrastructure_damage(target, 1.0)
                                hit_infra = True
                                if destroyed:
                                    station_message = f"{target['kind'].replace('infra_', '').title()} destroyed"
                                    station_message_timer = 1.3
                                break
                        if hit_infra:
                            continue
                        hit_platform = False
                        for target in active_sector_mining_platform_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                destroyed = apply_mining_platform_damage(target, 1.0)
                                hit_platform = True
                                if destroyed:
                                    station_message = "Mining platform destroyed"
                                    station_message_timer = 1.3
                                break
                        if hit_platform:
                            continue
                        hit_turret = False
                        for target in active_sector_defense_turret_targets():
                            if shot.position.distance_to(target["position"]) <= target["radius"] + shot.radius:
                                shot.kill()
                                destroyed = apply_defense_turret_damage(target, 1.0)
                                hit_turret = True
                                if destroyed:
                                    station_message = "Defense turret destroyed"
                                    station_message_timer = 1.3
                                break
                        if hit_turret:
                            continue
                        if shot.collides_with(player):
                            shot.kill()
                            apply_player_hit("enemy_shot")

            if asteroids is not None and shots is not None:
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
                                "station_laser",
                                "station_missile",
                            ):
                                award_player_xp(asteroid_xp_reward(asteroid))
                            if getattr(shot, "owner", None) != "player_missile":
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

    def render_frame():
        camera = player.position if player else pygame.Vector2(0, 0)
        draw_background(camera)

        station_statuses = active_sector_station_statuses() if has_active_game else []

        if drawable:
            for obj in drawable:
                obj.draw(screen)

        for platform in get_sector_mining_platforms(active_sector):
            hp = float(platform.get("hp", 0.0))
            if hp <= 0.0:
                continue
            draw_mining_platform(
                screen,
                world_to_local_position(platform.get("x", 0.0), platform.get("y", 0.0)),
                hp / max(1.0, float(platform.get("max_hp", 1.0))),
                bool(platform.get("linked", True)),
                int(platform.get("buffer_credits", 0)),
                int(platform.get("buffer_parts", 0)),
                elapsed_time,
                drone_specs=mining_platform_drone_specs(platform),
            )

        for turret in get_sector_defense_turrets(active_sector):
            hp = float(turret.get("hp", 0.0))
            if hp <= 0.0:
                continue
            draw_defense_turret(
                screen,
                world_to_local_position(turret.get("x", 0.0), turret.get("y", 0.0)),
                hp / max(1.0, float(turret.get("max_hp", 1.0))),
                int(turret.get("level", 1)),
                elapsed_time,
                variant=str(turret.get("variant", "onslaught_alpha")),
            )

        for station in list(stations) if stations is not None else []:
            sid = getattr(station, "station_id", "")
            if parse_station_sector(sid) != active_sector:
                continue
            station_state = get_station_upgrade_state(sid)
            draw_station_infrastructure(
                screen,
                station.position,
                int(station_state.get("infra_mining", 0)),
                int(station_state.get("infra_drone", 0)),
                int(station_state.get("infra_turret", 0)),
                int(station_state.get("infra_shield", 0)),
                elapsed_time,
            )

            draw_station_status_overlays(screen, station_statuses)

        if game_state == "playing" and player is not None and player.auto_mining_level > 0 and not is_docked:
            draw_support_drones(screen, ship_auto_mining_drone_specs(), anchor_position=player.position)

        draw_ship_explosion_fx(screen, ship_explosion_fx)
        step_and_draw_metal_pickup_fx(screen, metal_pickup_fx, dt)

        left_hud_x = lower_left_hud_anchor()

        if game_state == "playing" and player is not None and has_active_game:
            if player.targeting_beam_level > 0 and not is_docked:
                forward = pygame.Vector2(0, 1).rotate(player.rotation)
                beam_start = player.position + forward * (player.radius * 0.9)
                max_range = player.get_targeting_beam_range()
                locked = False
                if targeting_mode_timer > 0 and targeting_locked_targets:
                    beam_end = targeting_locked_targets[0].position
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
                if locked:
                    lock_text = hud_font.render("LOCK", True, "#93c5fd")
                    screen.blit(lock_text, (int(beam_end.x) + 8, int(beam_end.y) - 10))
            cmd_profile = command_progression_profile()
            top_left_items = [
                (f"Shields {player.shield_layers}/{player.shield_level}", (125, 211, 252)),
                (
                    (
                        f"Sublight Warp L{player.warp_drive_level} "
                        f"{player.warp_energy:.1f}/{player.get_warp_capacity_seconds():.1f}s"
                    ),
                    (249, 168, 212) if player.warp_boosting else (251, 207, 232),
                ),
            ]
            top_right_items = [
                (f"Command L{int(cmd_profile.get('level', 1))}", UI_COLORS["accent_alt"]),
            ]
            bottom_left_items = [
                (f"Cargo {player.total_metal_units()} metal", UI_COLORS["text"]),
            ]
            bottom_right_items = [
                (f"Gold {player.credits}", UI_COLORS["accent"]),
            ]

            if god_mode:
                top_right_items.insert(0, ("GODMODE ACTIVE", UI_COLORS["danger"]))

            if sector_owner(active_sector) == "player":
                sec = sector_security_rating(active_sector)
                top_right_items.append(
                    (f"Sector Security {sec:.1f}", UI_COLORS["ok"] if sec >= 4.0 else UI_COLORS["muted"])
                )
                disabled_station_count = sum(1 for status in station_statuses if status["disabled"])
                damaged_station_statuses = [status for status in station_statuses if not status["disabled"] and status["hp_ratio"] < 0.995]
                if disabled_station_count > 0:
                    top_right_items.append((f"Stations Disabled {disabled_station_count}", UI_COLORS["danger"]))
                elif damaged_station_statuses:
                    weakest = min(damaged_station_statuses, key=lambda status: status["hp_ratio"])
                    top_right_items.append((f"Station Hull {int(round(weakest['hp_ratio'] * 100))}%", UI_COLORS["warn"]))
                logistics = platform_logistics_summary(active_sector)
                if int(logistics.get("live", 0)) > 0:
                    convoy = platform_convoy_snapshot(active_sector)
                    convoy_warning = convoy_warning_label(int(convoy.get("strain", 0)))
                    top_right_items.append(
                        (
                        (
                            f"Platform Links {int(logistics.get('linked', 0))}/{int(logistics.get('live', 0))} | "
                            f"Buffer {int(logistics.get('buffer_credits', 0))}g/{int(logistics.get('buffer_parts', 0))}p"
                        ),
                            UI_COLORS["warn"] if int(logistics.get("offline", 0)) > 0 else UI_COLORS["muted"],
                        )
                    )
                    convoy_text = (
                        (
                            f"Convoy Active {float(convoy.get('time_left', 0.0)):.1f}s "
                            f"Escort {float(convoy.get('stabilize_progress', 0.0)):.1f}/4.0 "
                            f"Eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% "
                            f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                        )
                        if bool(convoy.get("active", False))
                        else (
                            f"Convoy Next {float(convoy.get('cooldown', 0.0)):.1f}s "
                            f"Eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% "
                            f"Misses {int(convoy.get('failures', 0))} "
                            f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                        )
                    )
                    top_right_items.append(
                        (convoy_text, UI_COLORS["warn"] if bool(convoy.get("active", False)) else UI_COLORS["muted"])
                    )

            if raid_events:
                top_right_items.append((f"Raid Alerts {len(raid_events)}", UI_COLORS["warn"]))

            if active_sector in raid_events:
                raid = raid_events[active_sector]
                top_right_items.append(
                    (
                        f"UNDER ATTACK: {owner_label(raid['faction'])} "
                        f"Waves {raid.get('waves_remaining', 0)}",
                        UI_COLORS["danger"],
                    )
                )
                if float(raid.get("security", 0.0)) > 0.0:
                    top_right_items.append(
                        (f"Defense Dampening x{float(raid.get('security', 0.0)):.1f}", UI_COLORS["ok"])
                    )

            if scanner_cooldown_timer > 0:
                top_right_items.append((f"Scanner Cooldown {scanner_cooldown_timer:.1f}s", UI_COLORS["warn"]))

            anomaly_profile = anomaly_effect_profile(active_sector)
            anomaly_pressure = float(anomaly_profile.get("pressure", 0.0))
            if anomaly_pressure > 0.0:
                top_right_items.append((f"Anomaly Pressure {anomaly_pressure:.2f} ({anomaly_pressure_hint})", UI_COLORS["warn"]))

            context_prompt = None
            context_prompt_color = UI_COLORS["accent"]
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
                        context_prompt = "Press E at Station: Upgrade"
                        context_prompt_color = UI_COLORS["accent"]
                    else:
                        context_prompt = f"Press C to Claim Station ({owner_label(station_claim_owner)})"
                        context_prompt_color = UI_COLORS["warn"]
                elif near_planet is not None:
                    planet_claim_owner = planet_owner(near_planet.planet_id)
                    if planet_claim_owner == "player":
                        context_prompt = f"Press E at Planet: Land ({near_planet.accepted_metal} market)"
                        context_prompt_color = UI_COLORS["accent"]
                    else:
                        context_prompt = f"Press C to Claim Planet ({owner_label(planet_claim_owner)})"
                        context_prompt_color = UI_COLORS["warn"]

            if context_prompt:
                bottom_left_items.append((context_prompt, context_prompt_color))

            if active_contract is not None:
                risk_rating = int(active_contract.get("risk_rating", 1))
                bottom_right_items.append(
                    (
                        f"Threat: R{risk_rating}/5  Spawn {current_enemy_spawn_interval:.2f}s"
                        f"  Cap {current_enemy_max_alive}",
                        UI_COLORS["warn"],
                    ),
                )
                bottom_right_items.append(
                    (
                        (
                            f"Contract: {active_contract['mission']} "
                            f"({active_contract['amount']} {active_contract['unit']}, "
                            f"{active_contract.get('tile_distance', 0)} tiles, R{risk_rating}/5) -> "
                            f"{active_contract['target_type']} {active_contract['target_sector'][0]},"
                            f"{active_contract['target_sector'][1]}"
                        ),
                        UI_COLORS["accent"],
                    )
                )

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
                bottom_left_items.append((station_message, UI_COLORS["accent"]))

            if audio.music_loaded:
                music_state = "Muted" if audio.all_audio_muted or audio.music_muted else "On"
                bottom_right_items.append((f"Music {music_state}", UI_COLORS["muted"]))
                if audio.music_source:
                    bottom_right_items.append((f"Track {audio.music_source}", UI_COLORS["muted"]))

            top_left_x = 10
            top_left_y = pause_button_rect.bottom + 10
            top_right_y = audio_toggle_button.bottom + 10
            bottom_left_base = SCREEN_HEIGHT - 10
            bottom_right_base = (
                min(rect.top for rect in touch_action_buttons.values()) - 10
                if show_touch_action_controls and not is_docked
                else SCREEN_HEIGHT - 10
            )
            lane_width = max(240, SCREEN_WIDTH // 2 - 32)

            draw_hud_stack(top_left_items, top_left_x, top_left_y, max_width=lane_width)
            draw_hud_stack(top_right_items, SCREEN_WIDTH - 10, top_right_y, align="right", max_width=lane_width)
            draw_hud_stack_up(bottom_left_items, left_hud_x, bottom_left_base, max_width=lane_width)
            draw_hud_stack_up(bottom_right_items, SCREEN_WIDTH - 10, bottom_right_base, align="right", max_width=lane_width)

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
                if claim_operation.get("waves_remaining", 0) > 0:
                    eta = max(0.0, float(claim_operation.get("wave_timer", 0.0)))
                    eta_text = hud_font.render(
                        f"Next wave in {eta:.1f}s (edge entry)",
                        True,
                        UI_COLORS["warn"] if eta <= 2.5 else UI_COLORS["muted"],
                    )
                    screen.blit(eta_text, (bar_x, bar_y + 20))
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
            draw_button(screen, pause_button_rect, "Esc: Pause", hud_font, active=False, tone="alt")
            if show_touch_action_controls and not is_docked:
                draw_touch_action_buttons(screen, touch_action_buttons)

        if game_state == "playing" and is_docked and has_active_game:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            dock_margin_x = max(96, SCREEN_WIDTH // 12)
            dock_margin_y = max(56, SCREEN_HEIGHT // 12)
            panel_rect = pygame.Rect(dock_margin_x, dock_margin_y, SCREEN_WIDTH - dock_margin_x * 2, SCREEN_HEIGHT - dock_margin_y * 2)
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
                    player_controls=(docked_station is not None and station_owner(docked_station.station_id) == "player"),
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
                    infra_mining=int(_st.get("infra_mining", 0)),
                    infra_drone=int(_st.get("infra_drone", 0)),
                    infra_turret=int(_st.get("infra_turret", 0)),
                    infra_shield=int(_st.get("infra_shield", 0)),
                    infra_mining_cost_text=(
                        "MAXED"
                        if _st.get("infra_mining", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_mining')}g"
                    ),
                    infra_drone_cost_text=(
                        "MAXED"
                        if _st.get("infra_drone", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_drone')}g"
                    ),
                    infra_turret_cost_text=(
                        "MAXED"
                        if _st.get("infra_turret", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_turret')}g"
                    ),
                    infra_shield_cost_text=(
                        "MAXED"
                        if _st.get("infra_shield", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_shield')}g"
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
                    settlement_happiness=planet_happiness(docked_planet.planet_id),
                )

        show_pause_home = game_state == "menu" or (game_state == "paused" and pause_tab in ("home", "controls", "audio"))

        if show_pause_home:
            build_menu_ui_layout()
            show_controls = (pause_tab == "controls")
            show_audio = (pause_tab == "audio")
            show_map = (pause_tab == "map")
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
                show_controls,
                show_audio,
                audio.music_muted,
                audio.music_volume,
                audio.sfx_muted,
                audio.sfx_volume,
            )

        draw_pause_navigation()

        map_overlay_active = game_state in ("menu", "paused") and has_active_game and pause_tab == "map"
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
                build_status_fn=map_action_status_for_sector,
                raided_sectors=set(raid_events.keys()),
                tactical_visible_sectors=scanner_live_window,
                scanner_target_sectors=scanner_target_sectors(active_sector, player.scanner_level if player else 0),
                ftl_target_sectors=owned_ftl_target_sectors(active_sector, player.warp_drive_level if player else 0),
                show_close_button=True,
            )

        if game_state in ("menu", "paused") and has_active_game and pause_tab == "ship":
            ship_margin_x = max(88, SCREEN_WIDTH // 14)
            ship_margin_y = max(52, SCREEN_HEIGHT // 13)
            ship_panel_rect = pygame.Rect(ship_margin_x, ship_margin_y, SCREEN_WIDTH - ship_margin_x * 2, SCREEN_HEIGHT - ship_margin_y * 2)
            draw_ship_panel(
                screen,
                ship_panel_rect,
                player,
                active_contract,
                ship_ui,
                hud_font,
                panel_font,
            )

        if game_state in ("menu", "paused") and has_active_game and pause_tab == "status":
            ship_margin_x = max(88, SCREEN_WIDTH // 14)
            ship_margin_y = max(52, SCREEN_HEIGHT // 13)
            status_panel_rect = pygame.Rect(ship_margin_x, ship_margin_y, SCREEN_WIDTH - ship_margin_x * 2, SCREEN_HEIGHT - ship_margin_y * 2)
            draw_status_panel(
                screen,
                status_panel_rect,
                player,
                active_contract,
                status_ui,
                hud_font,
                panel_font,
                command_profile=command_progression_profile(),
                active_sector=active_sector,
                sector_owner_label=owner_label(sector_owner(active_sector)),
                world_seed=world_seed,
            )

        if game_state in ("menu", "paused") and has_active_game and pause_tab == "build":
            for key in build_ui:
                build_ui[key] = None

            if build_placement_mode is not None:
                banner = pygame.Rect(64, 34, SCREEN_WIDTH - 128, 82)
                draw_panel(screen, banner, border_color=UI_COLORS["accent_alt"], fill_key="panel_soft")
                placement_title = panel_font.render(f"Place {build_placement_mode['label']}", True, UI_COLORS["text"])
                placement_hint = hud_font.render(
                    "Click a clear spot in the sector. Edge placements are blocked. Esc or right-click cancels.",
                    True,
                    UI_COLORS["muted"],
                )
                cost_hint = hud_font.render(f"Cost {int(build_placement_mode['cost'])}g", True, UI_COLORS["accent"])
                gold_hint = hud_font.render(f"Current gold {int(player.credits)}g", True, UI_COLORS["accent_alt"])
                cost_x = banner.right - cost_hint.get_width() - 72
                gold_x = max(banner.x + 18, cost_x - gold_hint.get_width() - 18)
                screen.blit(placement_title, (banner.x + 18, banner.y + 14))
                screen.blit(placement_hint, (banner.x + 18, banner.y + 44))
                screen.blit(cost_hint, (cost_x, banner.y + 17))
                screen.blit(gold_hint, (gold_x, banner.y + 17))
                build_ui["placement_cancel"] = pygame.Rect(banner.right - 52, banner.y + 14, 34, 34)
                draw_close_button(screen, build_ui["placement_cancel"])

                margin = placement_margin_for(build_placement_mode["kind"])
                sector_rect = pygame.Rect(margin, margin, SCREEN_WIDTH - margin * 2, SCREEN_HEIGHT - margin * 2)
                pygame.draw.rect(screen, (88, 102, 134), sector_rect, 1, border_radius=16)

                cursor_pos = map_window_to_logical(pygame.mouse.get_pos())
                if cursor_pos is None:
                    preview_text = hud_font.render("Move cursor into the sector view", True, UI_COLORS["warn"])
                else:
                    valid_preview, reason, _preview_world = validate_build_placement(build_placement_mode["kind"], cursor_pos)
                    draw_build_placement_preview(screen, build_placement_mode["kind"], cursor_pos, valid_preview, elapsed_time)
                    preview_text = hud_font.render(reason if not valid_preview else "Valid placement", True, UI_COLORS["ok"] if valid_preview else UI_COLORS["warn"])
                screen.blit(preview_text, (banner.x + 18, banner.bottom - 24))
                audio.draw_toggle_icon(screen, audio_toggle_button)
                present_frame()
                return

            build_margin_x = max(96, SCREEN_WIDTH // 12)
            build_margin_y = max(64, SCREEN_HEIGHT // 11)
            build_panel = pygame.Rect(
                build_margin_x,
                build_margin_y,
                SCREEN_WIDTH - build_margin_x * 2,
                SCREEN_HEIGHT - build_margin_y * 2,
            )
            draw_panel(screen, build_panel, border_color=UI_COLORS["accent_alt"])
            title = panel_font.render("Sector Buildables", True, UI_COLORS["text"])
            screen.blit(title, (build_panel.x + 20, build_panel.y + 18))
            build_ui["close"] = close_panel_rect(build_panel)
            draw_close_button(screen, build_ui["close"])

            top_group = "logistics"
            if build_tab.startswith("build_construct_"):
                top_group = "construct"
            elif build_tab.startswith("build_infra_"):
                top_group = "infra"

            tab_y = build_panel.y + 52
            tab_w = max(118, min(150, (build_panel.width - 80) // 6))
            tab_gap = 8
            tabs_left = build_panel.x + 20
            build_ui["tab_construct"] = pygame.Rect(tabs_left, tab_y, tab_w, 32)
            build_ui["tab_infra"] = pygame.Rect(tabs_left + tab_w + tab_gap, tab_y, tab_w, 32)
            build_ui["tab_logistics"] = pygame.Rect(tabs_left + (tab_w + tab_gap) * 2, tab_y, tab_w, 32)
            draw_button(screen, build_ui["tab_construct"], "Construction", hud_font, active=(top_group == "construct"), tone="alt")
            draw_button(screen, build_ui["tab_infra"], "Infrastructure", hud_font, active=(top_group == "infra"), tone="alt")
            draw_button(screen, build_ui["tab_logistics"], "Logistics", hud_font, active=(top_group == "logistics"), tone="alt")

            subtab_primary_label = "Overview"
            subtab_secondary_label = "Details"
            if top_group == "construct":
                subtab_primary_label = "Core"
                subtab_secondary_label = "Sites"
            elif top_group == "infra":
                subtab_primary_label = "Economy"
                subtab_secondary_label = "Defense"
            elif top_group == "logistics":
                subtab_primary_label = "Links"
                subtab_secondary_label = "Convoys"

            subtab_w = tab_w
            subtabs_right = build_panel.right - 20 - (subtab_w * 2 + tab_gap)
            build_ui["subtab_primary"] = pygame.Rect(subtabs_right, tab_y, subtab_w, 32)
            build_ui["subtab_secondary"] = pygame.Rect(subtabs_right + subtab_w + tab_gap, tab_y, subtab_w, 32)
            subtab_primary_active = (
                (top_group == "construct" and build_tab == "build_construct_core")
                or (top_group == "infra" and build_tab == "build_infra_economy")
                or (top_group == "logistics" and build_tab == "build_logistics_links")
            )
            draw_button(screen, build_ui["subtab_primary"], subtab_primary_label, hud_font, active=subtab_primary_active)
            draw_button(screen, build_ui["subtab_secondary"], subtab_secondary_label, hud_font, active=(not subtab_primary_active))

            pager_hint = hud_font.render("Tabs 1/2 and 2/2 keep each panel focused", True, UI_COLORS["muted"])
            pager_x = max(build_panel.x + 20, build_panel.right - pager_hint.get_width() - 72)
            screen.blit(pager_hint, (pager_x, build_panel.y + 24))

            content_y = build_panel.y + 96

            status = hud_font.render(
                f"Sector {active_sector[0]},{active_sector[1]} | Security {sector_security_rating(active_sector):.1f}",
                True,
                UI_COLORS["muted"],
            )
            screen.blit(status, (build_panel.x + 20, content_y))
            build_gold = hud_font.render(f"Current gold: {int(player.credits)}", True, UI_COLORS["accent"])
            screen.blit(build_gold, (build_panel.right - build_gold.get_width() - 20, content_y))

            sid = player_station_in_sector(active_sector)
            has_station = sid is not None
            foreign_station_present = len(get_sector_stations_with_built(active_sector[0], active_sector[1])) > (1 if has_station else 0)
            logistics = platform_logistics_summary(active_sector)
            convoy = platform_convoy_snapshot(active_sector)
            convoy_warning = convoy_warning_label(int(convoy.get("strain", 0)))
            live_platforms = int(logistics.get("live", 0))
            st = get_station_upgrade_state(sid) if sid is not None else {
                "infra_mining": 0,
                "infra_drone": 0,
                "infra_turret": 0,
                "infra_shield": 0,
            }

            if top_group == "construct":
                construct_gap = 14
                construct_w = max(220, (build_panel.width - 40 - construct_gap * 2) // 3)
                status_w = construct_w - 8
                station_x = build_panel.x + 20
                platform_x = station_x + construct_w + construct_gap
                turret_x = platform_x + construct_w + construct_gap

                build_ui["build_station"] = pygame.Rect(station_x, content_y + 38, construct_w, 36)
                draw_button(
                    screen,
                    build_ui["build_station"],
                    ("Build Station (MAX)" if has_station else f"Place Station ({BUILD_STATION_COST}g)"),
                    hud_font,
                    active=(not has_station and player.credits >= BUILD_STATION_COST),
                )

                station_status_text = "Click button, then click sector to place"
                station_status_color = UI_COLORS["muted"]
                if has_station:
                    station_status_text = "You already have a station in this sector"
                elif player.credits < BUILD_STATION_COST:
                    station_status_text = f"Need {BUILD_STATION_COST} gold to build a station"
                    station_status_color = UI_COLORS["warn"]
                else:
                    station_status_text = f"Ready to build station in sector {active_sector[0]},{active_sector[1]}"
                    station_status_color = UI_COLORS["ok"]
                next_station_y = draw_wrapped_lines(
                    station_status_text,
                    station_x,
                    content_y + 78,
                    hud_font,
                    station_status_color,
                    status_w,
                    max_lines=3,
                )
                if foreign_station_present and not has_station:
                    draw_wrapped_lines(
                        "Non-player station detected here; your station can still be built.",
                        station_x,
                        next_station_y + 2,
                        hud_font,
                        UI_COLORS["muted"],
                        status_w,
                        max_lines=3,
                    )

                build_ui["build_platform"] = pygame.Rect(platform_x, content_y + 38, construct_w, 36)
                platform_active = (
                    has_station
                    and sector_owner(active_sector) == "player"
                    and live_platforms < MINING_PLATFORM_MAX_PER_SECTOR
                    and player.credits >= BUILD_MINING_PLATFORM_COST
                )
                draw_button(
                    screen,
                    build_ui["build_platform"],
                    (
                        f"Place Platform ({BUILD_MINING_PLATFORM_COST}g)"
                        if live_platforms < MINING_PLATFORM_MAX_PER_SECTOR
                        else "Place Platform (MAX)"
                    ),
                    hud_font,
                    active=platform_active,
                )

                platform_status_text = "Pick a slot away from the edge"
                platform_status_color = UI_COLORS["muted"]
                if not has_station:
                    platform_status_text = "Need a station in this sector before deploying a platform"
                    platform_status_color = UI_COLORS["warn"]
                elif sector_owner(active_sector) != "player":
                    platform_status_text = "Claim the sector before deploying mining platforms"
                    platform_status_color = UI_COLORS["warn"]
                elif live_platforms >= MINING_PLATFORM_MAX_PER_SECTOR:
                    platform_status_text = f"Platform cap reached ({MINING_PLATFORM_MAX_PER_SECTOR} max)"
                elif player.credits < BUILD_MINING_PLATFORM_COST:
                    platform_status_text = f"Need {BUILD_MINING_PLATFORM_COST} gold to deploy a platform"
                    platform_status_color = UI_COLORS["warn"]
                else:
                    platform_status_text = f"Ready to deploy mining platform {live_platforms + 1}/{MINING_PLATFORM_MAX_PER_SECTOR}"
                    platform_status_color = UI_COLORS["ok"]
                draw_wrapped_lines(
                    platform_status_text,
                    platform_x,
                    content_y + 78,
                    hud_font,
                    platform_status_color,
                    status_w,
                    max_lines=3,
                )

                live_turrets = sum(1 for turret in get_sector_defense_turrets(active_sector) if float(turret.get("hp", 0.0)) > 0.0)
                build_ui["place_turret"] = pygame.Rect(turret_x, content_y + 38, construct_w, 36)
                turret_active = (
                    has_station
                    and sector_owner(active_sector) == "player"
                    and live_turrets < DEFENSE_TURRET_MAX_PER_SECTOR
                    and player.credits >= BUILD_DEFENSE_TURRET_COST
                )
                draw_button(
                    screen,
                    build_ui["place_turret"],
                    (
                        f"Place Defense Turret ({BUILD_DEFENSE_TURRET_COST}g)"
                        if live_turrets < DEFENSE_TURRET_MAX_PER_SECTOR
                        else "Place Defense Turret (MAX)"
                    ),
                    hud_font,
                    active=turret_active,
                )

                turret_status_text = "Select a clear defense position"
                turret_status_color = UI_COLORS["muted"]
                if not has_station:
                    turret_status_text = "Need a station in this sector before placing a turret"
                    turret_status_color = UI_COLORS["warn"]
                elif sector_owner(active_sector) != "player":
                    turret_status_text = "Claim the sector before placing defense turrets"
                    turret_status_color = UI_COLORS["warn"]
                elif live_turrets >= DEFENSE_TURRET_MAX_PER_SECTOR:
                    turret_status_text = f"Turret cap reached ({DEFENSE_TURRET_MAX_PER_SECTOR} max)"
                elif player.credits < BUILD_DEFENSE_TURRET_COST:
                    turret_status_text = f"Need {BUILD_DEFENSE_TURRET_COST} gold to place a turret"
                    turret_status_color = UI_COLORS["warn"]
                else:
                    turret_status_text = f"Ready to place turret {live_turrets + 1}/{DEFENSE_TURRET_MAX_PER_SECTOR}"
                    turret_status_color = UI_COLORS["ok"]
                draw_wrapped_lines(
                    turret_status_text,
                    turret_x,
                    content_y + 78,
                    hud_font,
                    turret_status_color,
                    status_w,
                    max_lines=3,
                )

                turret_status_text = "Standalone turret buildable"
                turret_status_color = UI_COLORS["muted"]
                if not has_station:
                    turret_status_text = "Need a station in this sector first"
                    turret_status_color = UI_COLORS["warn"]
                elif sector_owner(active_sector) != "player":
                    turret_status_text = "Claim the sector before placing turrets"
                    turret_status_color = UI_COLORS["warn"]
                elif live_turrets >= DEFENSE_TURRET_MAX_PER_SECTOR:
                    turret_status_text = f"Turret cap reached ({DEFENSE_TURRET_MAX_PER_SECTOR} max)"
                elif player.credits < BUILD_DEFENSE_TURRET_COST:
                    turret_status_text = f"Need {BUILD_DEFENSE_TURRET_COST} gold to place a turret"
                    turret_status_color = UI_COLORS["warn"]
                else:
                    turret_status_text = f"Ready to place turret {live_turrets + 1}/{DEFENSE_TURRET_MAX_PER_SECTOR}"
                    turret_status_color = UI_COLORS["ok"]
                screen.blit(hud_font.render(turret_status_text, True, turret_status_color), (turret_x, content_y + 78))

                if build_tab == "build_construct_sites":
                    site_hint1 = hud_font.render("Stations, platforms, and turrets now place where you click in-sector.", True, UI_COLORS["muted"])
                    site_hint2 = hud_font.render("Placement is blocked near sector edges and major structures.", True, UI_COLORS["muted"])
                    screen.blit(site_hint1, (build_panel.x + 20, content_y + 124))
                    screen.blit(site_hint2, (build_panel.x + 20, content_y + 146))
                else:
                    platform_hint = hud_font.render(
                        (
                            f"Mining Platforms {live_platforms}/{MINING_PLATFORM_MAX_PER_SECTOR} | "
                            f"Turrets {live_turrets}/{DEFENSE_TURRET_MAX_PER_SECTOR}"
                        ),
                        True,
                        UI_COLORS["muted"],
                    )
                    screen.blit(platform_hint, (build_panel.x + 20, content_y + 124))

            elif top_group == "infra":
                labels = [
                    (
                        "build_mining",
                        "Mining Drones",
                        int(st.get("infra_mining", 0)),
                        station_infra_upgrade_cost(sid, "infra_mining") if sid is not None else None,
                    ),
                    (
                        "build_drone",
                        "Interceptor Drones",
                        int(st.get("infra_drone", 0)),
                        station_infra_upgrade_cost(sid, "infra_drone") if sid is not None else None,
                    ),
                    (
                        "build_turret",
                        "Turret Grid",
                        int(st.get("infra_turret", 0)),
                        station_infra_upgrade_cost(sid, "infra_turret") if sid is not None else None,
                    ),
                    (
                        "build_shield",
                        "Shield Net",
                        int(st.get("infra_shield", 0)),
                        station_infra_upgrade_cost(sid, "infra_shield") if sid is not None else None,
                    ),
                ]
                active_keys = {"build_mining", "build_drone"} if build_tab == "build_infra_economy" else {"build_drone", "build_turret", "build_shield"}
                for idx, (key, name, level, cost) in enumerate(labels):
                    if key not in active_keys:
                        continue
                    y = content_y + 40 + idx * 50
                    build_ui[key] = pygame.Rect(build_panel.x + 20, y, 420, 38)
                    if not has_station:
                        label = f"{name} (need station first)"
                        active = False
                    elif level >= INFRA_UPGRADE_MAX:
                        label = f"{name} L{level} (MAX)"
                        active = False
                    else:
                        label = f"{name} L{level} -> L{level+1} ({cost}g)"
                        active = player.credits >= int(cost)
                    draw_button(screen, build_ui[key], label, hud_font, active=active)

            else:
                logistics_hint = hud_font.render(
                    (
                        f"Links online {int(logistics.get('linked', 0))}/{live_platforms} | "
                        f"Buffered {int(logistics.get('buffer_credits', 0))}g, {int(logistics.get('buffer_parts', 0))} parts"
                    ),
                    True,
                    UI_COLORS["warn"] if int(logistics.get("offline", 0)) > 0 else UI_COLORS["muted"],
                )
                screen.blit(logistics_hint, (build_panel.x + 20, content_y + 40))

                if build_tab == "build_logistics_convoy":
                    convoy_hint = hud_font.render(
                        (
                            (
                                f"Convoy ACTIVE {float(convoy.get('time_left', 0.0)):.1f}s | "
                                f"Escort {float(convoy.get('stabilize_progress', 0.0)):.1f}/4.0 | "
                                f"Recovery eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% | "
                                f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                            )
                            if bool(convoy.get("active", False))
                            else (
                                f"Convoy next {float(convoy.get('cooldown', 0.0)):.1f}s | "
                                f"Recovery eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% | "
                                f"Missed runs {int(convoy.get('failures', 0))} | "
                                f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                            )
                        ),
                        True,
                        UI_COLORS["warn"] if bool(convoy.get("active", False)) else UI_COLORS["muted"],
                    )
                    screen.blit(convoy_hint, (build_panel.x + 20, content_y + 72))

                    output_penalty = int(round((1.0 - platform_output_multiplier(active_sector)) * 100))
                    if output_penalty > 0:
                        penalty_hint = hud_font.render(
                            f"Route strain reduces passive output by {output_penalty}% until stabilization.",
                            True,
                            UI_COLORS["warn"],
                        )
                        screen.blit(penalty_hint, (build_panel.x + 20, content_y + 96))
                else:
                    relink_hint = hud_font.render(
                        "Fly near offline platforms to restore links and recover buffered cargo",
                        True,
                        UI_COLORS["muted"],
                    )
                    screen.blit(relink_hint, (build_panel.x + 20, content_y + 72))

        else:
            for key in build_ui:
                build_ui[key] = None

        audio.draw_toggle_icon(screen, audio_toggle_button)
        present_frame()

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

    def draw_button(screen, rect, label, font, active=False, tone="alt"):
        if isinstance(tone, str):
            tone = UI_COLORS.get(tone, UI_COLORS["accent_alt"])
        pygame.draw.rect(screen, (12, 18, 32, 185), rect, border_radius=12)
        pygame.draw.rect(screen, tone, rect, 2, border_radius=12)
        label = font.render(label, True, tone)
        screen.blit(label, label.get_rect(center=rect.center))

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

        happiness = planet_happiness(planet.planet_id)
        market_multiplier = max(0.8, min(1.35, 0.78 + happiness * 0.37))
        tuned_total = max(1, int(round(gained * market_multiplier)))
        adjusted = tuned_total - gained
        if adjusted != 0:
            player.credits += adjusted
            gained = tuned_total

        station_message = f"Sold {sold_units} {metal_type} for {gained} gold (happiness x{market_multiplier:.2f})"
        station_message_timer = 1.8
        log_event(
            "planet_trade",
            metal=metal_type,
            quantity=sold_units,
            gold=gained,
            market_multiplier=round(market_multiplier, 3),
            settlement_happiness=round(happiness, 3),
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

    def player_station_in_sector(sector):
        sx, sy = sector
        for station_id, _x, _y in get_sector_stations_with_built(sx, sy):
            if station_owner(station_id) == "player":
                return station_id
        return None

    def get_sector_mining_platforms(sector):
        return mining_platforms_by_sector.get(sector, [])

    def _convoy_seed_sector_state(sector):
        sx, sy = sector
        seed = (world_seed * 1103515245) ^ (sx * 73856093) ^ (sy * 19349663) ^ 0x6B84221D
        rng = random.Random(seed & 0xFFFFFFFF)
        return {
            "cooldown": 20.0 + rng.uniform(6.0, 18.0),
            "active": False,
            "time_left": 0.0,
            "stabilize_progress": 0.0,
            "efficiency": 1.0,
            "failures": 0,
            "strain": 0,
        }

    def ensure_platform_convoy_state(sector):
        state = platform_convoy_states.get(sector)
        if state is None:
            state = _convoy_seed_sector_state(sector)
            platform_convoy_states[sector] = state
        return state

    def platform_convoy_snapshot(sector):
        state = ensure_platform_convoy_state(sector)
        return {
            "active": bool(state.get("active", False)),
            "time_left": float(state.get("time_left", 0.0)),
            "cooldown": float(state.get("cooldown", 0.0)),
            "stabilize_progress": float(state.get("stabilize_progress", 0.0)),
            "efficiency": float(state.get("efficiency", 1.0)),
            "failures": int(state.get("failures", 0)),
            "strain": int(state.get("strain", 0)),
        }

    def platform_recovery_efficiency(sector):
        return max(0.45, min(1.0, float(ensure_platform_convoy_state(sector).get("efficiency", 1.0))))

    def platform_output_multiplier(sector):
        strain = int(ensure_platform_convoy_state(sector).get("strain", 0))
        return max(0.46, 1.0 - 0.18 * max(0, min(3, strain)))

    def platform_raid_focus_bonus(sector):
        strain = int(ensure_platform_convoy_state(sector).get("strain", 0))
        return max(0.0, min(0.9, 0.24 * max(0, min(3, strain))))

    def convoy_warning_label(strain):
        level = max(0, min(3, int(strain)))
        if level <= 0:
            return "STABLE"
        if level == 1:
            return "ELEVATED"
        if level == 2:
            return "HIGH"
        return "CRITICAL"

    def update_platform_convoy_events(dt_seconds):
        nonlocal station_message, station_message_timer, platform_logistics_hint_timer
        if player is None:
            return

        sector = active_sector
        live_platforms = [
            p
            for p in get_sector_mining_platforms(sector)
            if float(p.get("hp", 0.0)) > 0.0
        ]
        if sector_owner(sector) != "player" or not live_platforms:
            return

        state = ensure_platform_convoy_state(sector)
        raid_active = sector in raid_events
        state["cooldown"] = max(0.0, float(state.get("cooldown", 0.0)) - dt_seconds)

        # Route health slowly recovers when convoy pressure is absent.
        if not bool(state.get("active", False)) and not raid_active:
            state["efficiency"] = min(1.0, float(state.get("efficiency", 1.0)) + dt_seconds * 0.012)

        if not bool(state.get("active", False)) and state["cooldown"] <= 0.0:
            state["active"] = True
            state["time_left"] = 15.0
            state["stabilize_progress"] = 0.0
            state["cooldown"] = 0.0
            if platform_logistics_hint_timer <= 0.0:
                station_message = "Convoy retrieval window opened: escort route to a mining platform"
                station_message_timer = 1.9
                platform_logistics_hint_timer = 1.0

        if not bool(state.get("active", False)):
            return

        state["time_left"] = max(0.0, float(state.get("time_left", 0.0)) - dt_seconds)

        near_any_platform = False
        for platform in live_platforms:
            pos = world_to_local_position(platform.get("x", 0.0), platform.get("y", 0.0))
            if player.position.distance_to(pos) <= 170.0:
                near_any_platform = True
                break

        if near_any_platform and not raid_active:
            state["stabilize_progress"] = min(
                4.0,
                float(state.get("stabilize_progress", 0.0)) + dt_seconds,
            )

        if float(state.get("stabilize_progress", 0.0)) >= 4.0:
            state["active"] = False
            state["time_left"] = 0.0
            state["stabilize_progress"] = 0.0
            state["cooldown"] = 28.0
            state["efficiency"] = min(1.0, float(state.get("efficiency", 1.0)) + 0.12)
            had_strain = int(state.get("strain", 0)) > 0
            state["strain"] = 0
            if platform_logistics_hint_timer <= 0.0:
                station_message = (
                    "Convoy route stabilized: failure chain cleared"
                    if had_strain
                    else "Convoy route stabilized: recovery efficiency improved"
                )
                station_message_timer = 1.8
                platform_logistics_hint_timer = 1.0
            return

        if float(state.get("time_left", 0.0)) <= 0.0:
            state["active"] = False
            state["stabilize_progress"] = 0.0
            state["cooldown"] = 16.0
            state["failures"] = int(state.get("failures", 0)) + 1
            state["strain"] = min(3, int(state.get("strain", 0)) + 1)
            penalty = 0.09 if raid_active else 0.05
            state["efficiency"] = max(0.45, float(state.get("efficiency", 1.0)) - penalty)
            if platform_logistics_hint_timer <= 0.0:
                station_message = (
                    "Convoy retrieval failed under pressure: buffered cargo recovery reduced"
                    if raid_active
                    else "Convoy retrieval missed: buffered cargo recovery reduced"
                )
                station_message_timer = 1.9
                platform_logistics_hint_timer = 1.0

    def active_sector_mining_platform_targets():
        targets = []
        for platform in get_sector_mining_platforms(active_sector):
            hp = float(platform.get("hp", 0.0))
            if hp <= 0.0:
                continue
            targets.append(
                {
                    "platform_id": str(platform.get("id", "")),
                    "position": pygame.Vector2(float(platform.get("x", 0.0)), float(platform.get("y", 0.0))),
                    "radius": 15,
                    "hp": hp,
                    "max_hp": float(platform.get("max_hp", 140.0)),
                }
            )
        return targets

    def platform_logistics_summary(sector):
        live = 0
        linked = 0
        buffered_credits = 0
        buffered_parts = 0
        for platform in get_sector_mining_platforms(sector):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue
            live += 1
            if bool(platform.get("linked", True)):
                linked += 1
            buffered_credits += int(platform.get("buffer_credits", 0))
            buffered_parts += int(platform.get("buffer_parts", 0))
        return {
            "live": live,
            "linked": linked,
            "offline": max(0, live - linked),
            "buffer_credits": buffered_credits,
            "buffer_parts": buffered_parts,
        }

    def update_platform_logistics(dt_seconds):
        nonlocal station_message, station_message_timer, platform_logistics_hint_timer
        if player is None:
            return

        raid_active = active_sector in raid_events
        recovery_efficiency = platform_recovery_efficiency(active_sector)
        transfer_credits = 0
        transfer_parts = 0
        lost_credits = 0
        lost_parts = 0
        relinked = 0

        for platform in get_sector_mining_platforms(active_sector):
            if float(platform.get("hp", 0.0)) <= 0.0:
                continue

            platform.setdefault("linked", True)
            platform.setdefault("buffer_credits", 0)
            platform.setdefault("buffer_parts", 0)
            platform.setdefault("max_hp", max(1.0, float(platform.get("hp", 1.0))))

            pos = pygame.Vector2(float(platform.get("x", 0.0)), float(platform.get("y", 0.0)))
            near_player = player.position.distance_to(pos) <= 156.0

            if raid_active:
                platform["linked"] = False
            elif near_player and not bool(platform.get("linked", False)):
                platform["linked"] = True
                relinked += 1

            if near_player:
                buffered_credits = int(platform.get("buffer_credits", 0))
                buffered_parts = int(platform.get("buffer_parts", 0))
                recovered_credits = int(round(buffered_credits * recovery_efficiency))
                recovered_parts = int(round(buffered_parts * recovery_efficiency))
                transfer_credits += recovered_credits
                transfer_parts += recovered_parts
                lost_credits += max(0, buffered_credits - recovered_credits)
                lost_parts += max(0, buffered_parts - recovered_parts)
                platform["buffer_credits"] = 0
                platform["buffer_parts"] = 0

        if transfer_credits > 0:
            player.credits += transfer_credits
        if transfer_parts > 0:
            eco_state = ensure_player_sector_economy(active_sector)
            if eco_state is not None:
                resources = eco_state.setdefault("resources", {})
                resources["parts"] = int(resources.get("parts", 0)) + transfer_parts
                snapshot_economy_state_cache()

        platform_logistics_hint_timer = max(0.0, platform_logistics_hint_timer - dt_seconds)
        if relinked > 0 and platform_logistics_hint_timer <= 0.0:
            station_message = f"Route link restored for {relinked} mining platform(s)"
            station_message_timer = 1.6
            platform_logistics_hint_timer = 1.1
        elif (transfer_credits > 0 or transfer_parts > 0) and platform_logistics_hint_timer <= 0.0:
            if lost_credits > 0 or lost_parts > 0:
                station_message = (
                    f"Recovered +{transfer_credits}g, +{transfer_parts} parts "
                    f"(route loss {lost_credits}g/{lost_parts} parts)"
                )
            else:
                station_message = f"Recovered platform cargo +{transfer_credits}g, +{transfer_parts} parts"
            station_message_timer = 1.7
            platform_logistics_hint_timer = 1.1

    def apply_mining_platform_damage(target, base_damage):
        platforms = get_sector_mining_platforms(active_sector)
        for platform in platforms:
            if str(platform.get("id", "")) != target.get("platform_id", ""):
                continue
            platform["hp"] = max(0.0, float(platform.get("hp", 0.0)) - max(0.2, float(base_damage)))
            capture_sector_snapshot(active_sector[0], active_sector[1], visited=True, charted=True)
            return platform["hp"] <= 0.0
        return False

    def try_build_mining_platform_in_active_sector():
        nonlocal station_message, station_message_timer
        if sector_owner(active_sector) != "player":
            station_message = "Claim this sector before deploying a mining platform"
            station_message_timer = 1.7
            play_sfx("ui_click")
            return False
        if player_station_in_sector(active_sector) is None:
            station_message = "Need a Union station in sector first"
            station_message_timer = 1.6
            play_sfx("ui_click")
            return False

        sector_platforms = get_sector_mining_platforms(active_sector)
        live_count = sum(1 for p in sector_platforms if float(p.get("hp", 0.0)) > 0.0)
        if live_count >= MINING_PLATFORM_MAX_PER_SECTOR:
            station_message = "Mining platform cap reached in this sector"
            station_message_timer = 1.6
            play_sfx("ui_click")
            return False

        if player.credits < BUILD_MINING_PLATFORM_COST:
            station_message = f"Need {BUILD_MINING_PLATFORM_COST} gold"
            station_message_timer = 1.4
            play_sfx("ui_click")
            return False
        return start_build_placement("platform")

    def try_upgrade_station_kind(station_id, kind):
        nonlocal station_message, station_message_timer
        if station_id is None:
            station_message = "No Union station in sector"
            station_message_timer = 1.4
            play_sfx("ui_click")
            return False

        state = get_station_upgrade_state(station_id)
        limits = {
            "level": STATION_LEVEL_MAX,
            "laser": STATION_LASER_MAX,
            "missile": STATION_MISSILE_MAX,
            "infra_mining": INFRA_UPGRADE_MAX,
            "infra_drone": INFRA_UPGRADE_MAX,
            "infra_turret": INFRA_UPGRADE_MAX,
            "infra_shield": INFRA_UPGRADE_MAX,
        }
        labels = {
            "level": "Station Hull",
            "laser": "Station Laser",
            "missile": "Station Missile",
            "infra_mining": "Mining Drones",
            "infra_drone": "Interceptor Drones",
            "infra_turret": "Turret Grid",
            "infra_shield": "Shield Net",
        }
        if kind not in limits:
            return False

        current = int(state.get(kind, 0))
        if current >= int(limits[kind]):
            station_message = f"{labels[kind]} maxed"
            station_message_timer = 1.3
            play_sfx("ui_click")
            return False

        if kind == "level":
            cost = station_level_upgrade_cost(station_id)
        elif kind == "laser":
            cost = station_laser_upgrade_cost(station_id)
        elif kind == "missile":
            cost = station_missile_upgrade_cost(station_id)
        else:
            cost = station_infra_upgrade_cost(station_id, kind)

        if player.credits < cost:
            station_message = f"Need {cost} gold"
            station_message_timer = 1.3
            play_sfx("ui_click")
            return False

        player.credits -= cost
        state[kind] = current + 1
        if kind.startswith("infra_"):
            ensure_infrastructure_health(station_id, kind)
        station_message = f"{labels[kind]} upgraded to L{state[kind]}"
        station_message_timer = 1.6
        play_sfx("upgrade")
        return True

    def try_build_station_in_active_sector():
        nonlocal station_message, station_message_timer
        existing_player_station = player_station_in_sector(active_sector)
        if existing_player_station is not None:
            station_message = "You already have a station in this sector"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return False
        if player.credits < BUILD_STATION_COST:
            station_message = f"Need {BUILD_STATION_COST} gold to build station"
            station_message_timer = 1.5
            play_sfx("ui_click")
            return False
        return start_build_placement("station")

    def build_tab_action(action_key):
        sid = player_station_in_sector(active_sector)
        if action_key == "build_station":
            return try_build_station_in_active_sector()
        if action_key == "build_platform":
            return try_build_mining_platform_in_active_sector()
        if action_key == "place_turret":
            return start_build_placement("turret")
        if action_key == "build_mining":
            return try_upgrade_station_kind(sid, "infra_mining")
        if action_key == "build_drone":
            return try_upgrade_station_kind(sid, "infra_drone")
        if action_key == "build_turret":
            return try_upgrade_station_kind(sid, "infra_turret")
        if action_key == "build_shield":
            return try_upgrade_station_kind(sid, "infra_shield")
        return False

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

        try_upgrade_station_kind(sid, kind)

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
        if player_spawn_grace_timer > 0.0:
            return
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
            step_and_draw_metal_pickup_fx(screen, metal_pickup_fx, frame_dt)

            draw_hud_chip(f"Cargo {player.total_metal_units()} metal", 10, SCREEN_HEIGHT - 34)
            draw_hud_chip(f"Gold {player.credits}", SCREEN_WIDTH - 194, SCREEN_HEIGHT - 34, UI_COLORS["accent"])

            draw_hud_chip(f"Shields {player.shield_layers}/{player.shield_level}", 10, 34, (125, 211, 252))
            draw_hud_chip(
                (
                    f"Sublight Warp L{player.warp_drive_level} "
                    f"{player.warp_energy:.1f}/{player.get_warp_capacity_seconds():.1f}s"
                ),
                10,
                    58,
                (249, 168, 212) if player.warp_boosting else (251, 207, 232),
            )
            cmd_profile = command_progression_profile()
            draw_hud_chip(
                f"Command L{int(cmd_profile.get('level', 1))}",
                SCREEN_WIDTH - 220,
                34,
                UI_COLORS["accent_alt"],
            )
            if sector_owner(active_sector) == "player":
                sec = sector_security_rating(active_sector)
                draw_hud_chip(
                    f"Sector Security {sec:.1f}",
                    10,
                    202,
                    UI_COLORS["ok"] if sec >= 4.0 else UI_COLORS["muted"],
                )
                logistics = platform_logistics_summary(active_sector)
                if int(logistics.get("live", 0)) > 0:
                    convoy = platform_convoy_snapshot(active_sector)
                    convoy_warning = convoy_warning_label(int(convoy.get("strain", 0)))
                    draw_hud_chip(
                        (
                            f"Platform Links {int(logistics.get('linked', 0))}/{int(logistics.get('live', 0))} | "
                            f"Buffer {int(logistics.get('buffer_credits', 0))}g/{int(logistics.get('buffer_parts', 0))}p"
                        ),
                        10,
                        226,
                        UI_COLORS["warn"] if int(logistics.get("offline", 0)) > 0 else UI_COLORS["muted"],
                    )
                    convoy_text = (
                        (
                            f"Convoy Active {float(convoy.get('time_left', 0.0)):.1f}s "
                            f"Escort {float(convoy.get('stabilize_progress', 0.0)):.1f}/4.0 "
                            f"Eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% "
                            f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                        )
                        if bool(convoy.get("active", False))
                        else (
                            f"Convoy Next {float(convoy.get('cooldown', 0.0)):.1f}s "
                            f"Eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% "
                            f"Misses {int(convoy.get('failures', 0))} "
                            f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                        )
                    )
                    draw_hud_chip(
                        convoy_text,
                        10,
                        250,
                        UI_COLORS["warn"] if bool(convoy.get("active", False)) else UI_COLORS["muted"],
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
                if float(raid.get("security", 0.0)) > 0.0:
                    draw_hud_chip(
                        f"Defense Dampening x{float(raid.get('security', 0.0)):.1f}",
                        10,
                        322,
                        UI_COLORS["ok"],
                    )

            if scanner_cooldown_timer > 0:
                draw_hud_chip(
                    f"Scanner Cooldown {scanner_cooldown_timer:.1f}s",
                    10,
                    346,
                    UI_COLORS["warn"],
                )

            anomaly_profile = anomaly_effect_profile(active_sector)
            anomaly_pressure = float(anomaly_profile.get("pressure", 0.0))
            if anomaly_pressure > 0.0:
                draw_hud_chip(
                    f"Anomaly Pressure {anomaly_pressure:.2f} ({anomaly_pressure_hint})",
                    10,
                    370,
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
                if claim_operation.get("waves_remaining", 0) > 0:
                    eta = max(0.0, float(claim_operation.get("wave_timer", 0.0)))
                    eta_text = hud_font.render(
                        f"Next wave in {eta:.1f}s (edge entry)",
                        True,
                        UI_COLORS["warn"] if eta <= 2.5 else UI_COLORS["muted"],
                    )
                    screen.blit(eta_text, (bar_x, bar_y + 20))
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
                draw_button(screen, pause_button_rect, "Esc: Pause", hud_font, active=False, tone="alt")

                if show_touch_action_controls and not is_docked:
                    draw_touch_action_buttons(screen, touch_action_buttons)

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

            dock_margin_x = max(96, SCREEN_WIDTH // 12)
            dock_margin_y = max(56, SCREEN_HEIGHT // 12)
            panel_rect = pygame.Rect(dock_margin_x, dock_margin_y, SCREEN_WIDTH - dock_margin_x * 2, SCREEN_HEIGHT - dock_margin_y * 2)
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
                    infra_mining=int(_st.get("infra_mining", 0)),
                    infra_drone=int(_st.get("infra_drone", 0)),
                    infra_turret=int(_st.get("infra_turret", 0)),
                    infra_shield=int(_st.get("infra_shield", 0)),
                    infra_mining_cost_text=(
                        "MAXED"
                        if _st.get("infra_mining", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_mining')}g"
                    ),
                    infra_drone_cost_text=(
                        "MAXED"
                        if _st.get("infra_drone", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_drone')}g"
                    ),
                    infra_turret_cost_text=(
                        "MAXED"
                        if _st.get("infra_turret", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_turret')}g"
                    ),
                    infra_shield_cost_text=(
                        "MAXED"
                        if _st.get("infra_shield", 0) >= INFRA_UPGRADE_MAX
                        else f"{station_infra_upgrade_cost(_sid, 'infra_shield')}g"
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
                    settlement_happiness=planet_happiness(docked_planet.planet_id),
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
            station_ui["upgrade_infra_mining"] = None
            station_ui["upgrade_infra_drone"] = None
            station_ui["upgrade_infra_turret"] = None
            station_ui["upgrade_infra_shield"] = None
            station_ui["undock"] = None
            planet_ui["trade"] = None
            planet_ui["undock"] = None
            for idx in range(3):
                planet_ui[f"job_{idx}"] = None

            if has_active_game and pause_tab == "build":
                for key in build_ui:
                    build_ui[key] = None

                build_margin_x = max(96, SCREEN_WIDTH // 12)
                build_margin_y = max(64, SCREEN_HEIGHT // 11)
                build_panel = pygame.Rect(
                    build_margin_x,
                    build_margin_y,
                    SCREEN_WIDTH - build_margin_x * 2,
                    SCREEN_HEIGHT - build_margin_y * 2,
                )
                draw_panel(screen, build_panel, border_color=UI_COLORS["accent_alt"])
                title = panel_font.render("Sector Buildables", True, UI_COLORS["text"])
                screen.blit(title, (build_panel.x + 20, build_panel.y + 18))
                build_ui["close"] = close_panel_rect(build_panel)
                draw_close_button(screen, build_ui["close"])

                top_group = "logistics"
                if build_tab.startswith("build_construct_"):
                    top_group = "construct"
                elif build_tab.startswith("build_infra_"):
                    top_group = "infra"

                tab_y = build_panel.y + 52
                tab_w = max(118, min(150, (build_panel.width - 80) // 6))
                tab_gap = 8
                tabs_left = build_panel.x + 20
                build_ui["tab_construct"] = pygame.Rect(tabs_left, tab_y, tab_w, 32)
                build_ui["tab_infra"] = pygame.Rect(tabs_left + tab_w + tab_gap, tab_y, tab_w, 32)
                build_ui["tab_logistics"] = pygame.Rect(tabs_left + (tab_w + tab_gap) * 2, tab_y, tab_w, 32)
                draw_button(screen, build_ui["tab_construct"], "Construction", hud_font, active=(top_group == "construct"), tone="alt")
                draw_button(screen, build_ui["tab_infra"], "Infrastructure", hud_font, active=(top_group == "infra"), tone="alt")
                draw_button(screen, build_ui["tab_logistics"], "Logistics", hud_font, active=(top_group == "logistics"), tone="alt")

                subtab_primary_label = "Overview"
                subtab_secondary_label = "Details"
                if top_group == "construct":
                    subtab_primary_label = "Core"
                    subtab_secondary_label = "Sites"
                elif top_group == "infra":
                    subtab_primary_label = "Economy"
                    subtab_secondary_label = "Defense"
                elif top_group == "logistics":
                    subtab_primary_label = "Links"
                    subtab_secondary_label = "Convoys"

                subtab_w = tab_w
                subtabs_right = build_panel.right - 20 - (subtab_w * 2 + tab_gap)
                build_ui["subtab_primary"] = pygame.Rect(subtabs_right, tab_y, subtab_w, 32)
                build_ui["subtab_secondary"] = pygame.Rect(subtabs_right + subtab_w + tab_gap, tab_y, subtab_w, 32)
                subtab_primary_active = (
                    (top_group == "construct" and build_tab == "build_construct_core")
                    or (top_group == "infra" and build_tab == "build_infra_economy")
                    or (top_group == "logistics" and build_tab == "build_logistics_links")
                )
                draw_button(screen, build_ui["subtab_primary"], subtab_primary_label, hud_font, active=subtab_primary_active)
                draw_button(screen, build_ui["subtab_secondary"], subtab_secondary_label, hud_font, active=(not subtab_primary_active))

                pager_hint = hud_font.render("Tabs 1/2 and 2/2 keep each panel focused", True, UI_COLORS["muted"])
                screen.blit(pager_hint, (max(build_panel.x + 20, build_panel.right - pager_hint.get_width() - 20), build_panel.y + 24))

                content_y = build_panel.y + 96

                status = hud_font.render(
                    f"Sector {active_sector[0]},{active_sector[1]} | Security {sector_security_rating(active_sector):.1f}",
                    True,
                    UI_COLORS["muted"],
                )
                screen.blit(status, (build_panel.x + 20, content_y))
                build_gold = hud_font.render(f"Current gold: {int(player.credits)}", True, UI_COLORS["accent"])
                screen.blit(build_gold, (build_panel.right - build_gold.get_width() - 20, content_y))

                sid = player_station_in_sector(active_sector)
                has_station = sid is not None
                foreign_station_present = len(get_sector_stations_with_built(active_sector[0], active_sector[1])) > (1 if has_station else 0)
                logistics = platform_logistics_summary(active_sector)
                convoy = platform_convoy_snapshot(active_sector)
                convoy_warning = convoy_warning_label(int(convoy.get("strain", 0)))
                live_platforms = int(logistics.get("live", 0))
                st = get_station_upgrade_state(sid) if sid is not None else {
                    "infra_mining": 0,
                    "infra_drone": 0,
                    "infra_turret": 0,
                    "infra_shield": 0,
                }

                if top_group == "construct":
                    construct_gap = 14
                    construct_w = max(220, (build_panel.width - 40 - construct_gap * 2) // 3)
                    station_x = build_panel.x + 20
                    platform_x = station_x + construct_w + construct_gap
                    turret_x = platform_x + construct_w + construct_gap

                    build_ui["build_station"] = pygame.Rect(station_x, content_y + 38, construct_w, 36)
                    draw_button(
                        screen,
                        build_ui["build_station"],
                        ("Build Station (MAX)" if has_station else f"Place Station ({BUILD_STATION_COST}g)"),
                        hud_font,
                        active=(not has_station and player.credits >= BUILD_STATION_COST),
                    )

                    station_status_text = "Click button, then click sector to place"
                    station_status_color = UI_COLORS["muted"]
                    if has_station:
                        station_status_text = "You already have a station in this sector"
                    elif player.credits < BUILD_STATION_COST:
                        station_status_text = f"Need {BUILD_STATION_COST} gold to build a station"
                        station_status_color = UI_COLORS["warn"]
                    else:
                        station_status_text = f"Ready to build station in sector {active_sector[0]},{active_sector[1]}"
                        station_status_color = UI_COLORS["ok"]
                    screen.blit(
                        hud_font.render(station_status_text, True, station_status_color),
                        (station_x, content_y + 78),
                    )
                    if foreign_station_present and not has_station:
                        screen.blit(
                            hud_font.render("Non-player station detected here; your station can still be built.", True, UI_COLORS["muted"]),
                            (station_x, content_y + 100),
                        )

                    build_ui["build_platform"] = pygame.Rect(platform_x, content_y + 38, construct_w, 36)
                    platform_active = (
                        has_station
                        and sector_owner(active_sector) == "player"
                        and live_platforms < MINING_PLATFORM_MAX_PER_SECTOR
                        and player.credits >= BUILD_MINING_PLATFORM_COST
                    )
                    draw_button(
                        screen,
                        build_ui["build_platform"],
                        (
                            f"Place Platform ({BUILD_MINING_PLATFORM_COST}g)"
                            if live_platforms < MINING_PLATFORM_MAX_PER_SECTOR
                            else "Place Platform (MAX)"
                        ),
                        hud_font,
                        active=platform_active,
                    )

                    platform_status_text = "Pick a slot away from the edge"
                    platform_status_color = UI_COLORS["muted"]
                    if not has_station:
                        platform_status_text = "Need a station in this sector before deploying a platform"
                        platform_status_color = UI_COLORS["warn"]
                    elif sector_owner(active_sector) != "player":
                        platform_status_text = "Claim the sector before deploying mining platforms"
                        platform_status_color = UI_COLORS["warn"]
                    elif live_platforms >= MINING_PLATFORM_MAX_PER_SECTOR:
                        platform_status_text = f"Platform cap reached ({MINING_PLATFORM_MAX_PER_SECTOR} max)"
                    elif player.credits < BUILD_MINING_PLATFORM_COST:
                        platform_status_text = f"Need {BUILD_MINING_PLATFORM_COST} gold to deploy a platform"
                        platform_status_color = UI_COLORS["warn"]
                    else:
                        platform_status_text = f"Ready to deploy mining platform {live_platforms + 1}/{MINING_PLATFORM_MAX_PER_SECTOR}"
                        platform_status_color = UI_COLORS["ok"]
                    screen.blit(
                        hud_font.render(platform_status_text, True, platform_status_color),
                        (platform_x, content_y + 78),
                    )

                    live_turrets = sum(1 for turret in get_sector_defense_turrets(active_sector) if float(turret.get("hp", 0.0)) > 0.0)
                    build_ui["place_turret"] = pygame.Rect(turret_x, content_y + 38, construct_w, 36)
                    turret_active = (
                        has_station
                        and sector_owner(active_sector) == "player"
                        and live_turrets < DEFENSE_TURRET_MAX_PER_SECTOR
                        and player.credits >= BUILD_DEFENSE_TURRET_COST
                    )
                    draw_button(
                        screen,
                        build_ui["place_turret"],
                        (
                            f"Place Defense Turret ({BUILD_DEFENSE_TURRET_COST}g)"
                            if live_turrets < DEFENSE_TURRET_MAX_PER_SECTOR
                            else "Place Defense Turret (MAX)"
                        ),
                        hud_font,
                        active=turret_active,
                    )

                    turret_status_text = "Standalone turret buildable"
                    turret_status_color = UI_COLORS["muted"]
                    if not has_station:
                        turret_status_text = "Need a station in this sector first"
                        turret_status_color = UI_COLORS["warn"]
                    elif sector_owner(active_sector) != "player":
                        turret_status_text = "Claim the sector before placing turrets"
                        turret_status_color = UI_COLORS["warn"]
                    elif live_turrets >= DEFENSE_TURRET_MAX_PER_SECTOR:
                        turret_status_text = f"Turret cap reached ({DEFENSE_TURRET_MAX_PER_SECTOR} max)"
                    elif player.credits < BUILD_DEFENSE_TURRET_COST:
                        turret_status_text = f"Need {BUILD_DEFENSE_TURRET_COST} gold to place a turret"
                        turret_status_color = UI_COLORS["warn"]
                    else:
                        turret_status_text = f"Ready to place turret {live_turrets + 1}/{DEFENSE_TURRET_MAX_PER_SECTOR}"
                        turret_status_color = UI_COLORS["ok"]
                    screen.blit(hud_font.render(turret_status_text, True, turret_status_color), (turret_x, content_y + 78))

                    if build_tab == "build_construct_sites":
                        site_hint1 = hud_font.render("Stations, platforms, and turrets now place where you click in-sector.", True, UI_COLORS["muted"])
                        site_hint2 = hud_font.render("Placement is blocked near sector edges and major structures.", True, UI_COLORS["muted"])
                        screen.blit(site_hint1, (build_panel.x + 20, content_y + 124))
                        screen.blit(site_hint2, (build_panel.x + 20, content_y + 146))
                    else:
                        platform_hint = hud_font.render(
                            (
                                f"Mining Platforms {live_platforms}/{MINING_PLATFORM_MAX_PER_SECTOR} | "
                                f"Turrets {live_turrets}/{DEFENSE_TURRET_MAX_PER_SECTOR}"
                            ),
                            True,
                            UI_COLORS["muted"],
                        )
                        screen.blit(platform_hint, (build_panel.x + 20, content_y + 124))

                elif top_group == "infra":
                    labels = [
                        (
                            "build_mining",
                            "Mining Drones",
                            int(st.get("infra_mining", 0)),
                            station_infra_upgrade_cost(sid, "infra_mining") if sid is not None else None,
                        ),
                        (
                            "build_drone",
                            "Interceptor Drones",
                            int(st.get("infra_drone", 0)),
                            station_infra_upgrade_cost(sid, "infra_drone") if sid is not None else None,
                        ),
                        (
                            "build_turret",
                            "Turret Grid",
                            int(st.get("infra_turret", 0)),
                            station_infra_upgrade_cost(sid, "infra_turret") if sid is not None else None,
                        ),
                        (
                            "build_shield",
                            "Shield Net",
                            int(st.get("infra_shield", 0)),
                            station_infra_upgrade_cost(sid, "infra_shield") if sid is not None else None,
                        ),
                    ]
                    active_keys = {"build_mining", "build_drone"} if build_tab == "build_infra_economy" else {"build_drone", "build_turret", "build_shield"}
                    for idx, (key, name, level, cost) in enumerate(labels):
                        if key not in active_keys:
                            continue
                        y = content_y + 40 + idx * 50
                        build_ui[key] = pygame.Rect(build_panel.x + 20, y, 420, 38)
                        if not has_station:
                            label = f"{name} (need station first)"
                            active = False
                        elif level >= INFRA_UPGRADE_MAX:
                            label = f"{name} L{level} (MAX)"
                            active = False
                        else:
                            label = f"{name} L{level} -> L{level+1} ({cost}g)"
                            active = player.credits >= int(cost)
                        draw_button(screen, build_ui[key], label, hud_font, active=active)

                else:
                    logistics_hint = hud_font.render(
                        (
                            f"Links online {int(logistics.get('linked', 0))}/{live_platforms} | "
                            f"Buffered {int(logistics.get('buffer_credits', 0))}g, {int(logistics.get('buffer_parts', 0))} parts"
                        ),
                        True,
                        UI_COLORS["warn"] if int(logistics.get("offline", 0)) > 0 else UI_COLORS["muted"],
                    )
                    screen.blit(logistics_hint, (build_panel.x + 20, content_y + 40))

                    if build_tab == "build_logistics_convoy":
                        convoy_hint = hud_font.render(
                            (
                                (
                                    f"Convoy ACTIVE {float(convoy.get('time_left', 0.0)):.1f}s | "
                                    f"Escort {float(convoy.get('stabilize_progress', 0.0)):.1f}/4.0 | "
                                    f"Recovery eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% | "
                                    f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                                )
                                if bool(convoy.get("active", False))
                                else (
                                    f"Convoy next {float(convoy.get('cooldown', 0.0)):.1f}s | "
                                    f"Recovery eff {int(round(float(convoy.get('efficiency', 1.0)) * 100))}% | "
                                    f"Missed runs {int(convoy.get('failures', 0))} | "
                                    f"Strain {int(convoy.get('strain', 0))} {convoy_warning}"
                                )
                            ),
                            True,
                            UI_COLORS["warn"] if bool(convoy.get("active", False)) else UI_COLORS["muted"],
                        )
                        screen.blit(convoy_hint, (build_panel.x + 20, content_y + 72))

                        output_penalty = int(round((1.0 - platform_output_multiplier(active_sector)) * 100))
                        if output_penalty > 0:
                            penalty_hint = hud_font.render(
                                f"Route strain reduces passive output by {output_penalty}% until stabilization.",
                                True,
                                UI_COLORS["warn"],
                            )
                            screen.blit(penalty_hint, (build_panel.x + 20, content_y + 96))
                    else:
                        relink_hint = hud_font.render(
                            "Fly near offline platforms to restore links and recover buffered cargo",
                            True,
                            UI_COLORS["muted"],
                        )
                        screen.blit(relink_hint, (build_panel.x + 20, content_y + 72))

            else:
                for key in build_ui:
                    build_ui[key] = None

        map_overlay_active = game_state in ("menu", "paused") and has_active_game and pause_tab == "map"
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
                build_status_fn=map_action_status_for_sector,
                raided_sectors=set(raid_events.keys()),
                tactical_visible_sectors=scanner_live_window,
                scanner_target_sectors=scanner_target_sectors(active_sector, player.scanner_level if player else 0),
                ftl_target_sectors=owned_ftl_target_sectors(active_sector, player.warp_drive_level if player else 0),
            )

        if game_state in ("menu", "paused") and has_active_game and pause_tab == "ship":
            ship_margin_x = max(88, SCREEN_WIDTH // 14)
            ship_margin_y = max(52, SCREEN_HEIGHT // 13)
            ship_panel_rect = pygame.Rect(ship_margin_x, ship_margin_y, SCREEN_WIDTH - ship_margin_x * 2, SCREEN_HEIGHT - ship_margin_y * 2)
            draw_ship_panel(
                screen,
                ship_panel_rect,
                player,
                active_contract,
                ship_ui,
                hud_font,
                panel_font,
            )

        if game_state in ("menu", "paused") and has_active_game and pause_tab == "status":
            ship_margin_x = max(88, SCREEN_WIDTH // 14)
            ship_margin_y = max(52, SCREEN_HEIGHT // 13)
            status_panel_rect = pygame.Rect(ship_margin_x, ship_margin_y, SCREEN_WIDTH - ship_margin_x * 2, SCREEN_HEIGHT - ship_margin_y * 2)
            draw_status_panel(
                screen,
                status_panel_rect,
                player,
                active_contract,
                status_ui,
                hud_font,
                panel_font,
                command_profile=command_progression_profile(),
                active_sector=active_sector,
                sector_owner_label=owner_label(sector_owner(active_sector)),
                world_seed=world_seed,
            )

        audio.draw_toggle_icon(screen, audio_toggle_button)

        present_frame()
        dt = clock.tick(60) / 1000

    # Persistent main game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            handle_event(event)
        sync_virtual_controls()
        update_play_state()
        render_frame()
        dt = clock.tick(60) / 1000
    pygame.quit()


if __name__ == "__main__":
    main()
