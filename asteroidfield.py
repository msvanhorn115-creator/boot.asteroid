import pygame
import random
from asteroid import Asteroid
from constants import *


class AsteroidField(pygame.sprite.Sprite):
    edges = [
        [
            pygame.Vector2(1, 0),
            lambda y: pygame.Vector2(0, y * SCREEN_HEIGHT),
        ],
        [
            pygame.Vector2(-1, 0),
            lambda y: pygame.Vector2(SCREEN_WIDTH, y * SCREEN_HEIGHT),
        ],
        [
            pygame.Vector2(0, 1),
            lambda x: pygame.Vector2(x * SCREEN_WIDTH, 0),
        ],
        [
            pygame.Vector2(0, -1),
            lambda x: pygame.Vector2(x * SCREEN_WIDTH, SCREEN_HEIGHT),
        ],
    ]

    def __init__(self, spawn_interval=None, speed_scale=1.0, max_kind=None):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.spawn_timer = 0.0
        self.spawn_interval = (
            ASTEROID_SPAWN_RATE_SECONDS
            if spawn_interval is None
            else spawn_interval
        )
        self.speed_scale = max(0.2, float(speed_scale))
        self.max_kind = ASTEROID_KINDS if max_kind is None else max(1, int(max_kind))

    def spawn(self, radius, position, velocity):
        asteroid = Asteroid(position.x, position.y, radius)
        asteroid.velocity = velocity

    def update(self, dt, *args):
        self.spawn_timer += dt
        if self.spawn_timer > self.spawn_interval:
            self.spawn_timer = 0

            edge = random.choice(self.edges)
            speed = int(random.randint(40, 100) * self.speed_scale)
            velocity = edge[0] * speed
            velocity = velocity.rotate(random.randint(-30, 30))
            position = edge[1](random.uniform(0, 1))
            kind = random.randint(1, self.max_kind)
            self.spawn(ASTEROID_MIN_RADIUS * kind, position, velocity)
