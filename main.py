import sys
import random
import math
import os
from pathlib import Path
import pygame

from constants import *
from logger import log_state, log_event
from player import Player
from asteroid import Asteroid
from shot import Shot
from enemy import EnemyField, Enemy
from station import Station
from planet import Planet
from sector_manager import SectorManager
from resources import get_metal_prices, set_drop_rate_multiplier
from targeting import beam_first_hit
from upgrade_ui import UPGRADE_BUTTON_KEYS
from station_panel import draw_station_panel, resolve_station_click
from planet_panel import draw_planet_panel, resolve_planet_click
from upgrade_actions import apply_upgrade
from menu_panel import draw_menu_panel
from map_panel import draw_map_panel, map_sector_at_point
from ui_theme import UI_COLORS
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


def main():
    print("Starting Asteroids")
    print(f"Screen width: {SCREEN_WIDTH}")
    print(f"Screen height: {SCREEN_HEIGHT}")

    pygame.init()
    screen = None
    display_errors = []
    selected_video_driver = os.environ.get("SDL_VIDEODRIVER", "")

    # Scaled+resizable keeps a fixed logical resolution while allowing desktop
    # fullscreen/maximize to fill correctly without top-left anchoring.
    window_flags = pygame.SCALED | pygame.RESIZABLE

    # Prefer SDL's default backend first so Linux window decorations (title bar,
    # close button, drag behavior) are chosen by the compositor/window manager.
    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), window_flags)
        selected_video_driver = pygame.display.get_driver()
    except pygame.error as exc:
        display_errors.append(f"default: {exc}")

    if screen is None:
        display_driver_order = ["x11", "wayland"]

        if selected_video_driver and selected_video_driver in display_driver_order:
            display_driver_order.remove(selected_video_driver)
            display_driver_order.insert(0, selected_video_driver)
        elif selected_video_driver:
            display_driver_order.insert(0, selected_video_driver)

        for driver in display_driver_order:
            try:
                os.environ["SDL_VIDEODRIVER"] = driver
                if pygame.display.get_init():
                    pygame.display.quit()
                pygame.display.init()
                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), window_flags)
                selected_video_driver = driver
                break
            except pygame.error as exc:
                display_errors.append(f"{driver}: {exc}")

    if screen is None:
        print("Display initialization failed.")
        if display_errors:
            print("Tried drivers:", " | ".join(display_errors))
        print("Try running with: SDL_VIDEODRIVER=wayland or SDL_VIDEODRIVER=x11")
        shutdown_code = 1
        pygame.quit()
        raise SystemExit(shutdown_code)

    print(f"Video driver: {selected_video_driver}")
    pygame.display.set_caption("Asteroid Miner")
    clock = pygame.time.Clock()

    world_seed = int(os.environ.get("ASTEROID_WORLD_SEED", "1337"))
    sector_manager = SectorManager(world_seed, sector_size=SCREEN_WIDTH, sector_height=SCREEN_HEIGHT)

    # Optional retro BGM loader: place a licensed track in assets/audio.
    music_loaded = False
    music_muted = False
    sfx_muted = False
    all_audio_muted = False
    music_volume = 0.35
    sfx_volume = 0.5
    music_error = ""
    music_source = ""
    music_driver = ""
    base_dir = Path(__file__).resolve().parent
    music_candidates = [
        base_dir / "assets/audio/arcade_loop.ogg",
        base_dir / "assets/audio/arcade_loop.mp3",
        base_dir / "assets/audio/arcade_loop.wav",
    ]
    mixer_init_error = None
    # Driver fallback order for Linux/WSL audio stacks.
    for driver in ("pipewire", "pulseaudio", "pulse", "alsa", "dsp", "dummy"):
        try:
            os.environ["SDL_AUDIODRIVER"] = driver
            if pygame.mixer.get_init() is not None:
                pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            music_driver = driver
            mixer_init_error = None
            break
        except pygame.error as exc:
            mixer_init_error = str(exc)

    if mixer_init_error is None:
        for candidate in music_candidates:
            if candidate.exists():
                try:
                    pygame.mixer.music.load(str(candidate))
                    pygame.mixer.music.set_volume(music_volume)
                    pygame.mixer.music.play(-1)
                    music_loaded = True
                    music_source = candidate.name
                except pygame.error as exc:
                    music_error = f"Music load failed: {exc}"
                break
        if not music_loaded and not music_error:
            music_error = "No music file found in assets/audio"
        if music_driver == "dummy" and music_loaded:
            # Dummy driver means the track is decoding, but no audible output device.
            music_error = "No audio device found (using dummy driver)"
            music_loaded = False
    else:
        music_loaded = False
        music_error = f"Audio init failed: {mixer_init_error}"

    if (
        "libpulse-simple.so.0" in music_error
        or "libasound.so.2" in music_error
    ):
        music_error = "Install audio libs: libpulse0 libasound2"

    sfx_sounds = {}

    def apply_music_volume():
        if pygame.mixer.get_init() is None:
            return
        pygame.mixer.music.set_volume(
            0.0 if all_audio_muted or music_muted or music_volume <= 0.0 else music_volume
        )

    def apply_sfx_volume():
        effective = 0.0 if all_audio_muted or sfx_muted or sfx_volume <= 0.0 else sfx_volume
        for sound in sfx_sounds.values():
            sound.set_volume(effective)

    def load_sfx(name):
        sfx_path = base_dir / f"assets/audio/sfx/{name}.wav"
        if not sfx_path.exists() or pygame.mixer.get_init() is None:
            return
        try:
            sound = pygame.mixer.Sound(str(sfx_path))
            sound.set_volume(0.0 if all_audio_muted or sfx_muted else sfx_volume)
            sfx_sounds[name] = sound
        except pygame.error:
            return

    for sfx_name in [
        "player_shoot",
        "enemy_shoot",
        "asteroid_hit",
        "enemy_hit",
        "enemy_destroyed",
        "pickup",
        "dock",
        "sell",
        "upgrade",
        "pause",
        "ui_click",
        "player_hit",
    ]:
        load_sfx(sfx_name)

    def play_sfx(name):
        sound = sfx_sounds.get(name)
        if sound is not None:
            sound.play()

    def draw_audio_toggle_icon(button_rect):
        panel_color = (24, 30, 46, 220)
        border_color = (132, 146, 176)
        icon_color = (220, 230, 255)
        mute_slash_color = (235, 70, 70)

        icon_surface = pygame.Surface((button_rect.width, button_rect.height), pygame.SRCALPHA)
        pygame.draw.circle(
            icon_surface,
            panel_color,
            (button_rect.width // 2, button_rect.height // 2),
            button_rect.width // 2,
        )
        pygame.draw.circle(
            icon_surface,
            border_color,
            (button_rect.width // 2, button_rect.height // 2),
            button_rect.width // 2,
            2,
        )

        # Speaker silhouette.
        pygame.draw.polygon(
            icon_surface,
            icon_color,
            [(14, 24), (20, 24), (27, 18), (27, 42), (20, 36), (14, 36)],
        )

        if all_audio_muted:
            pygame.draw.line(icon_surface, mute_slash_color, (12, 44), (44, 12), 4)
        else:
            pygame.draw.arc(icon_surface, icon_color, pygame.Rect(25, 18, 14, 24), -0.8, 0.8, 2)
            pygame.draw.arc(icon_surface, icon_color, pygame.Rect(24, 14, 20, 32), -0.8, 0.8, 2)

        screen.blit(icon_surface, button_rect.topleft)

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
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except pygame.error:
            pass
        pygame.quit()
        if hard:
            os._exit(exit_code)
        raise SystemExit(exit_code)

    # Background seed data
    stars = []
    for _ in range(STAR_COUNT):
        stars.append(
            {
                "x": random.uniform(0, SCREEN_WIDTH),
                "y": random.uniform(0, SCREEN_HEIGHT),
                "size": random.choice([1, 1, 1, 2]),
                "phase": random.uniform(0, 6.283),
                "depth": random.uniform(0.2, 1.0),
            }
        )

    nebula_clouds = []
    for _ in range(NEBULA_CLOUD_COUNT):
        nebula_clouds.append(
            {
                "x": random.uniform(0, SCREEN_WIDTH),
                "y": random.uniform(0, SCREEN_HEIGHT),
                "radius": random.randint(80, 220),
                "depth": random.uniform(0.08, 0.22),
                "phase": random.uniform(0, 6.283),
                "color": random.choice(
                    [
                        (48, 76, 120, 26),
                        (30, 90, 120, 24),
                        (70, 50, 115, 24),
                        (20, 110, 95, 22),
                    ]
                ),
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

    available_jobs = []
    active_contract = None
    explored_sectors = {}
    live_sector_intel = {}
    persistent_sector_enemies = {}
    scanner_cooldown_timer = 0.0
    scanner_passive_timer = 0.0

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
    audio_slider_dragging = None

    def normalize_in_sector(world_x, world_y, sector_x, sector_y):
        origin_x = sector_x * sector_manager.sector_width
        origin_y = sector_y * sector_manager.sector_height
        nx = (world_x - origin_x) / float(sector_manager.sector_width)
        ny = (world_y - origin_y) / float(sector_manager.sector_height)
        return max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))

    def capture_sector_snapshot(sector_x, sector_y, visited=False, charted=False):
        stations_data = sector_manager.get_sector_stations(sector_x, sector_y)
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
        contacts = persistent_sector_enemies.get(sector)
        if contacts is None:
            sx, sy = sector
            rng = random.Random((world_seed * 1000003) ^ (sx * 92821) ^ (sy * 68917) ^ 0xA341316C)
            count = rng.choices([0, 1, 2, 3, 4], weights=[44, 27, 17, 8, 4], k=1)[0]
            contacts = []
            for _ in range(count):
                contacts.append(
                    {
                        "x": rng.uniform(0.05, 0.95),
                        "y": rng.uniform(0.05, 0.95),
                    }
                )
            persistent_sector_enemies[sector] = contacts
        return contacts

    def update_persistent_sector_enemies(dt_seconds):
        return

    def sync_active_sector_enemies_to_persistent():
        return

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
                    contacts = get_persistent_sector_enemies(sector)
                    enemy_points = [{"x": c["x"], "y": c["y"]} for c in contacts]

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

    def generate_jobs(origin_type, origin_sector=None, job_count=3):
        if origin_sector is None:
            origin_sector = active_sector

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

            reward_base = (
                130
                + tile_distance * random.randint(85, 150)
                + amount * random.randint(16, 40)
                + hazard_bonus
            )
            reward = int(reward_base * (1.0 + risk_rating * 0.14))

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
                }
            )

        return jobs

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

        player.credits += active_contract["reward"]
        station_message = f"Delivery complete: +{active_contract['reward']} gold"
        station_message_timer = 1.8
        log_event("contract_complete", **active_contract, total_gold=player.credits)
        active_contract = None
        if docked_context in ("station", "planet"):
            available_jobs = generate_jobs(docked_context, origin_sector=active_sector)

    def handle_job_slot(job_index):
        nonlocal active_contract, station_message, station_message_timer, available_jobs
        if job_index < 0 or job_index >= len(available_jobs):
            return
        selected = available_jobs[job_index]

        if active_contract is not None:
            station_message = "One active contract at a time"
            station_message_timer = 1.5
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
        nonlocal metal_prices, active_difficulty
        nonlocal targeting_locked_targets, targeting_mode_timer
        nonlocal station_sprites_by_id, planet_sprites_by_id, world_offset, active_sector
        nonlocal destroyed_seed_asteroids
        nonlocal available_jobs, active_contract, explored_sectors, show_map_overlay
        nonlocal live_sector_intel, persistent_sector_enemies, scanner_cooldown_timer, scanner_passive_timer
        nonlocal enemy_field, base_enemy_spawn_interval, base_enemy_max_alive
        nonlocal current_enemy_spawn_interval, current_enemy_max_alive

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
        EnemyField.containers = (updatable,)
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

        enemy_field = EnemyField(
            spawn_interval=settings["enemy_spawn"],
            spawn_weights=settings["enemy_weights"],
            spawn_tuning={
                "speed_multiplier": settings["enemy_speed"],
                "health_multiplier": settings["enemy_health"],
                "view_multiplier": settings["enemy_view"],
                "shoot_cooldown_multiplier": settings["enemy_shoot_cooldown"],
                "max_alive": settings["enemy_max_alive"],
            },
        )
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
        docked_planet = None
        station_tab = "upgrade"
        metal_pickup_fx = []
        ship_explosion_fx = []
        targeting_locked_targets = []
        targeting_mode_timer = 0.0
        available_jobs = generate_jobs("station", origin_sector=active_sector)
        active_contract = None
        explored_sectors = {}
        live_sector_intel = {}
        persistent_sector_enemies = {}
        scanner_cooldown_timer = 0.0
        scanner_passive_timer = 0.0
        show_map_overlay = False
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
        stations_data = sector_manager.stations_around(center_sector[0], center_sector[1], radius=1)
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

    def undock():
        nonlocal is_docked, docked_context, docked_planet, station_message, station_message_timer
        is_docked = False
        docked_context = None
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
                            if enemy.health <= 1:
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
                            enemy.take_damage()
                            break
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
        screen.fill((4, 6, 12))

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

        for star in stars:
            twinkle = 0.65 + 0.35 * (
                (math.sin(elapsed_time * STAR_TWINKLE_SPEED + star["phase"]) + 1) * 0.5
            )
            brightness = int(110 + 125 * twinkle)
            color = (brightness, brightness, min(255, brightness + 25))
            star_x = star["x"] - camera.x * star["depth"] * 0.12
            star_y = star["y"] - camera.y * star["depth"] * 0.12
            pygame.draw.circle(
                screen,
                color,
                (int(star_x % SCREEN_WIDTH), int(star_y % SCREEN_HEIGHT)),
                star["size"],
            )

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
            nonlocal music_volume, sfx_volume, music_muted, sfx_muted
            slider_rect = menu_ui["music_slider"] if kind == "music" else menu_ui["sfx_slider"]
            ratio = (mouse_x - slider_rect.x) / max(1, slider_rect.width)
            ratio = max(0.0, min(1.0, ratio))

            if kind == "music":
                music_volume = ratio
                music_muted = ratio <= 0.001
                apply_music_volume()
            else:
                sfx_volume = ratio
                sfx_muted = ratio <= 0.001
                apply_sfx_volume()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown_game(0, hard=True)

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and audio_toggle_button.collidepoint(event.pos)
            ):
                all_audio_muted = not all_audio_muted
                apply_music_volume()
                apply_sfx_volume()
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
                    is_docked = False
                    docked_context = None
                    docked_planet = None
                    play_sfx("pause")
                elif game_state in ("menu", "paused") and has_active_game:
                    show_map_overlay = not show_map_overlay
                    if not show_map_overlay:
                        # Closing map should immediately return to live gameplay.
                        game_state = "playing"
                    play_sfx("ui_click")

            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                shutdown_game(0, hard=True)

            if event.type == pygame.KEYDOWN and game_state == "playing":
                if event.key == pygame.K_d:
                    god_mode = not god_mode
                    state_text = "ON" if god_mode else "OFF"
                    credit_boost = 0
                    upgrades_granted = 0
                    if god_mode and player is not None:
                        needed = player.credits_needed_for_full_upgrades()
                        if needed > player.credits:
                            credit_boost = needed - player.credits
                            player.credits += credit_boost

                        before_total = (
                            player.fire_rate_level
                            + player.shield_level
                            + player.multishot_level
                            + player.targeting_beam_level
                            + player.targeting_computer_level
                            + player.warp_drive_level
                            + player.scanner_level
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
                if is_docked:
                    # Keep Esc behavior dedicated to pause flow.
                    pass
                elif event.key == pygame.K_e:
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
                        is_docked = True
                        docked_context = "station"
                        docked_planet = None
                        station_tab = "upgrade"
                        available_jobs = generate_jobs("station", origin_sector=active_sector)
                        if player.shield_level > 0:
                            player.refill_shields()
                        station_message = "Docked at station. Upgrade bay online."
                        station_message_timer = 2.0
                        play_sfx("dock")
                    elif near_planet is not None:
                        is_docked = True
                        docked_context = "planet"
                        docked_planet = near_planet
                        available_jobs = generate_jobs("planet", origin_sector=active_sector)
                        station_message = f"Landed on planet ({near_planet.accepted_metal} market)."
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
                }
                mouse_pos = event.pos
                if docked_context == "station":
                    station_action = resolve_station_click(mouse_pos, station_tab, station_ui)
                    if station_action == "undock":
                        undock()
                    elif station_action == "deliver_contract":
                        try_complete_contract()
                    elif station_action and station_action.startswith("job:"):
                        handle_job_slot(int(station_action.split(":", 1)[1]))
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

                if show_map_overlay and has_active_game and map_panel_rect.collidepoint(mouse_pos):
                    scanned_sector = map_sector_at_point(map_panel_rect, active_sector, mouse_pos)
                    if scanned_sector is not None:
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
                    if not show_map_overlay:
                        # Closing map from pause/menu resumes the run immediately.
                        game_state = "playing"
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

            if scanner_cooldown_timer > 0:
                draw_hud_chip(
                    f"Scanner Cooldown {scanner_cooldown_timer:.1f}s",
                    10,
                    178,
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
                    draw_hud_chip("Press E at Station: Upgrade", 10, SCREEN_HEIGHT - 60, UI_COLORS["accent"])
                elif near_planet is not None:
                    draw_hud_chip(
                        f"Press E at Planet: Land ({near_planet.accepted_metal} market)",
                        10,
                        SCREEN_HEIGHT - 60,
                        UI_COLORS["accent"],
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

            if game_state == "playing":
                controls_lines = ["Esc: Pause"]
                for idx, label in enumerate(controls_lines):
                    control_surface = hud_font.render(label, True, "white")
                    screen.blit(control_surface, (SCREEN_WIDTH - 290, 10 + idx * 20))

                if god_mode:
                    draw_hud_chip("GODMODE ACTIVE", 10, 10, UI_COLORS["danger"])

            if music_loaded:
                music_state = "Muted" if all_audio_muted or music_muted else "On"
                draw_hud_chip(f"Music {music_state}", SCREEN_WIDTH - 180, SCREEN_HEIGHT - 58, UI_COLORS["muted"])
                draw_hud_chip(f"Track {music_source}", SCREEN_WIDTH - 300, SCREEN_HEIGHT - 82, UI_COLORS["muted"])

        if game_state == "playing" and is_docked and has_active_game:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            panel_rect = pygame.Rect(180, 90, SCREEN_WIDTH - 360, SCREEN_HEIGHT - 180)
            if docked_context == "station":
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
                )
        else:
            station_ui["sell_tab"] = None
            station_ui["upgrade_tab"] = None
            station_ui["sell_all"] = None
            for key in UPGRADE_BUTTON_KEYS:
                station_ui[key] = None
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
                music_loaded,
                music_driver,
                music_error,
                show_controls_overlay,
                show_audio_overlay,
                show_map_overlay,
                music_muted,
                music_volume,
                sfx_muted,
                sfx_volume,
            )

        if game_state in ("menu", "paused") and has_active_game and show_map_overlay:
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
            )

        draw_audio_toggle_icon(audio_toggle_button)

        pygame.display.flip()
        dt = clock.tick(60) / 1000


if __name__ == "__main__":
    main()
