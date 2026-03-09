import pygame
from constants import LINE_WIDTH, SHOT_RADIUS, SCREEN_WIDTH, SCREEN_HEIGHT
from circleshape import CircleShape


class Shot(CircleShape):
    def __init__(self, x, y, radius, owner="player"):
        super().__init__(x, y, radius)
        self.owner = owner
        self.life = 2.0  # seconds before the shot expires

    def draw(self, screen):
        pygame.draw.circle(screen, "white", self.position, self.radius, LINE_WIDTH)

    def update(self, dt, *args):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return

        self.position += self.velocity * dt
        if (
            self.position.x < -self.radius
            or self.position.x > SCREEN_WIDTH + self.radius
            or self.position.y < -self.radius
            or self.position.y > SCREEN_HEIGHT + self.radius
        ):
            self.kill()
