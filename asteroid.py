import pygame
import random
import math
from constants import LINE_WIDTH, ASTEROID_MIN_RADIUS
from logger import log_event
from circleshape import CircleShape
from resources import (
    choose_metal_type,
    get_terminal_drop_chance,
    get_split_drop_chance,
    get_metal_color,
)


class Asteroid(CircleShape):
    def __init__(self, x, y, radius, metal_type=None):
        super().__init__(x, y, radius)
        self.wrap_enabled = False
        self.metal_type = metal_type or choose_metal_type()
        self.rotation = random.uniform(0, 360)
        self.spin = random.uniform(-45, 45)
        self.local_points = self._build_silhouette()
        self.craters = self._build_craters()

        ore_tint = get_metal_color(self.metal_type)
        self.core_color = (
            max(45, int(ore_tint[0] * 0.42)),
            max(45, int(ore_tint[1] * 0.42)),
            max(45, int(ore_tint[2] * 0.42)),
        )
        self.rim_color = (
            min(255, self.core_color[0] + 55),
            min(255, self.core_color[1] + 55),
            min(255, self.core_color[2] + 55),
        )
        self.shadow_color = (
            max(18, self.core_color[0] - 26),
            max(18, self.core_color[1] - 26),
            max(18, self.core_color[2] - 26),
        )

    def _build_silhouette(self):
        points = []
        point_count = max(8, int(self.radius * 0.38))
        for index in range(point_count):
            theta = (index / point_count) * math.tau
            # Keep the shape readable but jagged enough to feel rocky.
            jitter = random.uniform(0.74, 1.18)
            r = self.radius * jitter
            points.append(pygame.Vector2(math.cos(theta) * r, math.sin(theta) * r))
        return points

    def _build_craters(self):
        craters = []
        crater_count = max(2, int(self.radius / 8))
        for _ in range(crater_count):
            distance = random.uniform(0.12, 0.62) * self.radius
            angle = random.uniform(0, math.tau)
            size = random.uniform(0.12, 0.24) * self.radius
            craters.append(
                {
                    "offset": pygame.Vector2(math.cos(angle), math.sin(angle)) * distance,
                    "radius": max(2, int(size)),
                }
            )
        return craters

    def draw(self, screen):
        rotated_points = []
        for point in self.local_points:
            world = self.position + point.rotate(self.rotation)
            rotated_points.append((int(world.x), int(world.y)))

        pygame.draw.polygon(screen, self.shadow_color, rotated_points)
        pygame.draw.polygon(screen, self.rim_color, rotated_points, LINE_WIDTH)

        for crater in self.craters:
            crater_pos = self.position + crater["offset"].rotate(self.rotation)
            pygame.draw.circle(
                screen,
                self.core_color,
                (int(crater_pos.x), int(crater_pos.y)),
                crater["radius"],
            )
            pygame.draw.circle(
                screen,
                self.rim_color,
                (int(crater_pos.x), int(crater_pos.y)),
                max(1, crater["radius"] // 3),
                1,
            )

        # Soft highlight to avoid flat-looking rocks.
        highlight = self.position + pygame.Vector2(-self.radius * 0.28, -self.radius * 0.34)
        pygame.draw.circle(
            screen,
            self.rim_color,
            (int(highlight.x), int(highlight.y)),
            max(2, int(self.radius * 0.16)),
        )

    def update(self, dt, *args):
        self.position += self.velocity * dt
        self.rotation += self.spin * dt
        if self.wrap_enabled:
            self.wrap_around_screen()

    def split(self):
        self.kill()

        drops = {}

        if self.radius <= ASTEROID_MIN_RADIUS:
            if random.random() <= get_terminal_drop_chance():
                drops[self.metal_type] = 1
            return drops

        if random.random() <= get_split_drop_chance():
            drops[self.metal_type] = drops.get(self.metal_type, 0) + 1

        log_event("asteroid_split")
        angle = random.uniform(20, 50)

        velocity_1 = self.velocity.rotate(angle) * 1.2
        velocity_2 = self.velocity.rotate(-angle) * 1.2
        new_radius = self.radius - ASTEROID_MIN_RADIUS

        asteroid_1 = Asteroid(
            self.position.x,
            self.position.y,
            new_radius,
            metal_type=self.metal_type,
        )
        asteroid_1.velocity = velocity_1
        asteroid_1.wrap_enabled = self.wrap_enabled

        asteroid_2 = Asteroid(
            self.position.x,
            self.position.y,
            new_radius,
            metal_type=self.metal_type,
        )
        asteroid_2.velocity = velocity_2
        asteroid_2.wrap_enabled = self.wrap_enabled

        return drops
