import pygame
from constants import LINE_WIDTH, SHOT_RADIUS, SCREEN_WIDTH, SCREEN_HEIGHT
from circleshape import CircleShape


class Shot(CircleShape):
    def __init__(self, x, y, radius, owner="player"):
        super().__init__(x, y, radius)
        self.owner = owner
        self.life = 2.0  # seconds before the shot expires

    def draw(self, screen):
        pos = (int(self.position.x), int(self.position.y))

        if self.owner == "player_missile":
            pygame.draw.circle(screen, (251, 191, 36), pos, self.radius + 1)
            pygame.draw.circle(screen, (255, 245, 220), pos, max(1, self.radius - 1))
            if self.velocity.length_squared() > 0:
                trail = self.velocity.normalize() * -10
                tail = (int(self.position.x + trail.x), int(self.position.y + trail.y))
                pygame.draw.line(screen, (253, 230, 138), tail, pos, 2)
            return

        if self.owner == "station_missile":
            pygame.draw.circle(screen, (125, 211, 252), pos, self.radius + 1)
            pygame.draw.circle(screen, (224, 242, 254), pos, max(1, self.radius - 1))
            return

        if self.owner == "enemy_station_missile":
            pygame.draw.circle(screen, (251, 146, 60), pos, self.radius + 1)
            pygame.draw.circle(screen, (255, 237, 213), pos, max(1, self.radius - 1))
            return

        color = {
            "enemy": (248, 113, 113),
            "station_laser": (56, 189, 248),
            "enemy_station_laser": (251, 191, 36),
        }.get(self.owner, (255, 255, 255))
        pygame.draw.circle(screen, color, pos, self.radius, LINE_WIDTH)

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
