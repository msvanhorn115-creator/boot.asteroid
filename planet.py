import pygame

from circleshape import CircleShape
from constants import LINE_WIDTH


class Planet(CircleShape):
    def __init__(self, x, y, accepted_metal, base_color):
        super().__init__(x, y, 56)
        self.accepted_metal = accepted_metal
        self.base_color = base_color

    def draw(self, screen):
        cx = int(self.position.x)
        cy = int(self.position.y)

        surface = self.base_color
        rim = (
            min(255, int(surface[0] * 1.15) + 20),
            min(255, int(surface[1] * 1.15) + 20),
            min(255, int(surface[2] * 1.15) + 20),
        )
        dark = (
            max(18, int(surface[0] * 0.45)),
            max(18, int(surface[1] * 0.45)),
            max(18, int(surface[2] * 0.45)),
        )

        pygame.draw.circle(screen, dark, (cx + 7, cy + 8), self.radius)
        pygame.draw.circle(screen, surface, (cx, cy), self.radius)
        pygame.draw.circle(screen, rim, (cx, cy), self.radius, 2)

        # Ring and marker for trade readability.
        pygame.draw.circle(screen, (220, 230, 245), (cx, cy), self.radius + 8, 1)
        pygame.draw.circle(screen, (245, 215, 90), (cx, cy - 6), 6)
        pygame.draw.circle(screen, (26, 32, 48), (cx, cy - 6), 3)

    def update(self, dt, *args):
        return
