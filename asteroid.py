import pygame
import random
from constants import LINE_WIDTH, ASTEROID_MIN_RADIUS
from logger import log_event
from circleshape import CircleShape


class Asteroid(CircleShape):
    def __init__(self, x, y, radius):
        super().__init__(x, y, radius)

    def draw(self, screen):
        pygame.draw.circle(screen, "white", self.position, self.radius, LINE_WIDTH)

    def update(self, dt):
        self.position += self.velocity * dt

    def split(self):
        self.kill()

        if self.radius <= ASTEROID_MIN_RADIUS:
            return

        log_event("asteroid_split")
        angle = random.uniform(20, 50)

        velocity_1 = self.velocity.rotate(angle) * 1.2
        velocity_2 = self.velocity.rotate(-angle) * 1.2
        new_radius = self.radius - ASTEROID_MIN_RADIUS

        asteroid_1 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid_1.velocity = velocity_1

        asteroid_2 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid_2.velocity = velocity_2
