import math
import random
from resources import choose_metal_type, get_metal_color


class SectorManager:
    """Deterministic procedural sector generation backed by a world seed."""

    def __init__(self, seed, sector_size=1200, sector_height=None):
        self.seed = int(seed)
        self.sector_width = int(sector_size)
        self.sector_height = int(sector_height if sector_height is not None else sector_size)
        # Backward-compatible alias used by older code paths.
        self.sector_size = self.sector_width
        self._station_cache = {}
        self._asteroid_cache = {}
        self._planet_cache = {}

    def world_to_sector(self, world_position):
        sx = math.floor(world_position.x / self.sector_width)
        sy = math.floor(world_position.y / self.sector_height)
        return sx, sy

    def _sector_rng(self, sector_x, sector_y):
        # Stable integer mixing for deterministic per-sector RNG.
        mixed = (
            self.seed * 1000003
            ^ sector_x * 73856093
            ^ sector_y * 19349663
            ^ 0x9E3779B97F4A7C15
        )
        return random.Random(mixed)

    def _generate_sector(self, sector_x, sector_y):
        rng = self._sector_rng(sector_x, sector_y)
        station_count = rng.choices([0, 1, 2], weights=[62, 31, 7], k=1)[0]

        origin_x = sector_x * self.sector_width
        origin_y = sector_y * self.sector_height
        # Keep stations clearly away from sector boundaries.
        margin_x = min(430, max(140, int(self.sector_width * 0.22)))
        margin_y = min(280, max(90, int(self.sector_height * 0.22)))
        stations = []

        for index in range(station_count):
            px = origin_x + rng.uniform(margin_x, self.sector_width - margin_x)
            py = origin_y + rng.uniform(margin_y, self.sector_height - margin_y)
            station_id = f"{sector_x}:{sector_y}:{index}"
            stations.append((station_id, px, py))

        return stations

    def get_sector_stations(self, sector_x, sector_y):
        key = (sector_x, sector_y)
        if key not in self._station_cache:
            self._station_cache[key] = self._generate_sector(sector_x, sector_y)
        return self._station_cache[key]

    def stations_around(self, center_sector_x, center_sector_y, radius=1):
        stations = []
        for sy in range(center_sector_y - radius, center_sector_y + radius + 1):
            for sx in range(center_sector_x - radius, center_sector_x + radius + 1):
                stations.extend(self.get_sector_stations(sx, sy))
        return stations

    def _generate_sector_asteroids(self, sector_x, sector_y):
        rng = self._sector_rng(sector_x, sector_y)

        # Keep fields sparse so large open sectors remain available for future
        # features (planets, missions, larger structures).
        # Ensure the spawn sector is never completely empty.
        force_home_belt = sector_x == 0 and sector_y == 0
        has_belt = force_home_belt or (rng.random() < 0.38)
        if not has_belt:
            if rng.random() >= 0.22:
                return []

            # Small junk pocket for occasional non-belt sectors.
            origin_x = sector_x * self.sector_width
            origin_y = sector_y * self.sector_height
            pocket_x = origin_x + rng.uniform(self.sector_width * 0.25, self.sector_width * 0.75)
            pocket_y = origin_y + rng.uniform(self.sector_height * 0.25, self.sector_height * 0.75)
            base_theta = rng.uniform(0.0, math.tau)
            base_speed = rng.uniform(8.0, 18.0)
            base_vx = math.cos(base_theta) * base_speed
            base_vy = math.sin(base_theta) * base_speed

            specs = []
            for item_index in range(rng.randint(3, 5)):
                jitter_dist = rng.uniform(0.0, 75.0)
                jitter_theta = rng.uniform(0.0, math.tau)
                x = pocket_x + math.cos(jitter_theta) * jitter_dist
                y = pocket_y + math.sin(jitter_theta) * jitter_dist
                radius = rng.choice((20, 20, 40))
                jitter_speed = rng.uniform(1.0, 6.0)
                jitter_vel_theta = rng.uniform(0.0, math.tau)
                vx = base_vx + math.cos(jitter_vel_theta) * jitter_speed
                vy = base_vy + math.sin(jitter_vel_theta) * jitter_speed
                asteroid_id = f"a:{sector_x}:{sector_y}:pocket:{item_index}"
                specs.append((asteroid_id, x, y, radius, vx, vy))
            return specs

        origin_x = sector_x * self.sector_width
        origin_y = sector_y * self.sector_height
        center_x = origin_x + self.sector_width * 0.5
        center_y = origin_y + self.sector_height * 0.5

        belt_angle = rng.uniform(0.0, math.tau)
        belt_dir = (math.cos(belt_angle), math.sin(belt_angle))
        belt_perp = (-belt_dir[1], belt_dir[0])
        belt_base = min(self.sector_width, self.sector_height)
        belt_length = rng.uniform(belt_base * 0.58, belt_base * 0.9)
        belt_width = rng.uniform(45.0, min(120.0, belt_base * 0.18))
        cluster_count = rng.randint(4, 7)

        # Build chain-like belts by spacing cluster anchors along the belt axis.
        if cluster_count == 1:
            t_values = [0.0]
        else:
            t_values = [(-0.5 + i / (cluster_count - 1)) for i in range(cluster_count)]

        specs = []
        for cluster_index in range(cluster_count):
            t = t_values[cluster_index] + rng.uniform(-0.08, 0.08)
            lateral = rng.uniform(-belt_width, belt_width)
            cluster_x = center_x + belt_dir[0] * (t * belt_length) + belt_perp[0] * lateral
            cluster_y = center_y + belt_dir[1] * (t * belt_length) + belt_perp[1] * lateral

            junk_count = rng.randint(5, 11)
            base_speed = rng.uniform(12.0, 28.0)
            drift_theta = belt_angle + rng.uniform(-0.32, 0.32)
            base_vx = math.cos(drift_theta) * base_speed
            base_vy = math.sin(drift_theta) * base_speed

            for item_index in range(junk_count):
                jitter_dist = rng.uniform(0.0, 95.0)
                jitter_theta = rng.uniform(0.0, math.tau)
                x = cluster_x + math.cos(jitter_theta) * jitter_dist
                y = cluster_y + math.sin(jitter_theta) * jitter_dist

                radius = rng.choice((20, 20, 20, 40, 40, 60))
                jitter_speed = rng.uniform(2.0, 12.0)
                jitter_vel_theta = rng.uniform(0.0, math.tau)
                vx = base_vx + math.cos(jitter_vel_theta) * jitter_speed
                vy = base_vy + math.sin(jitter_vel_theta) * jitter_speed

                asteroid_id = f"a:{sector_x}:{sector_y}:{cluster_index}:{item_index}"
                specs.append((asteroid_id, x, y, radius, vx, vy))

        return specs

    def get_sector_asteroids(self, sector_x, sector_y):
        key = (sector_x, sector_y)
        if key not in self._asteroid_cache:
            self._asteroid_cache[key] = self._generate_sector_asteroids(sector_x, sector_y)
        return self._asteroid_cache[key]

    def asteroids_around(self, center_sector_x, center_sector_y, radius=1):
        asteroids = []
        for sy in range(center_sector_y - radius, center_sector_y + radius + 1):
            for sx in range(center_sector_x - radius, center_sector_x + radius + 1):
                asteroids.extend(self.get_sector_asteroids(sx, sy))
        return asteroids

    def _generate_sector_planets(self, sector_x, sector_y):
        rng = self._sector_rng(sector_x, sector_y)
        force_home_planet = sector_x == 0 and sector_y == 0
        planet_count = 1 if force_home_planet else rng.choices([0, 1, 2], weights=[72, 24, 4], k=1)[0]

        if planet_count <= 0:
            return []

        origin_x = sector_x * self.sector_width
        origin_y = sector_y * self.sector_height
        # Keep planets deep in-sector and visually distinct from edge transitions.
        margin_x = min(470, max(180, int(self.sector_width * 0.26)))
        margin_y = min(250, max(110, int(self.sector_height * 0.26)))
        existing_stations = self.get_sector_stations(sector_x, sector_y)
        planets = []

        for index in range(planet_count):
            px = None
            py = None
            for _ in range(12):
                cand_x = origin_x + rng.uniform(margin_x, self.sector_width - margin_x)
                cand_y = origin_y + rng.uniform(margin_y, self.sector_height - margin_y)

                too_close_to_station = any(
                    math.dist((cand_x, cand_y), (sx, sy)) < 190
                    for _, sx, sy in existing_stations
                )
                if too_close_to_station:
                    continue

                too_close_to_planet = any(
                    math.dist((cand_x, cand_y), (ox, oy)) < 230
                    for _, ox, oy, _, _ in planets
                )
                if too_close_to_planet:
                    continue

                px = cand_x
                py = cand_y
                break

            if px is None or py is None:
                px = origin_x + rng.uniform(margin_x, self.sector_width - margin_x)
                py = origin_y + rng.uniform(margin_y, self.sector_height - margin_y)

            accepted_metal = choose_metal_type(rng)
            color = get_metal_color(accepted_metal)
            planet_id = f"p:{sector_x}:{sector_y}:{index}"
            planets.append((planet_id, px, py, accepted_metal, color))

        return planets

    def get_sector_planets(self, sector_x, sector_y):
        key = (sector_x, sector_y)
        if key not in self._planet_cache:
            self._planet_cache[key] = self._generate_sector_planets(sector_x, sector_y)
        return self._planet_cache[key]

    def planets_around(self, center_sector_x, center_sector_y, radius=1):
        planets = []
        for sy in range(center_sector_y - radius, center_sector_y + radius + 1):
            for sx in range(center_sector_x - radius, center_sector_x + radius + 1):
                planets.extend(self.get_sector_planets(sx, sy))
        return planets
