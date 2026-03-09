import pygame

from circleshape import CircleShape
from constants import LINE_WIDTH, STATION_RADIUS


class Station(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, STATION_RADIUS)

    def draw(self, screen):
        cx = int(self.position.x)
        cy = int(self.position.y)
        pulse = 0.7 + 0.3 * ((pygame.time.get_ticks() % 1200) / 1200.0)

        rim_color = (244, 210, 88)
        inner_rim = (198, 155, 52)
        hub_color = (88, 132, 190)
        spoke_color = (122, 140, 168)
        dock_light = (120, int(185 + 70 * pulse), 255)

        # Outer frame and inner ring.
        pygame.draw.circle(screen, rim_color, (cx, cy), self.radius, 3)
        pygame.draw.circle(screen, inner_rim, (cx, cy), int(self.radius * 0.72), 2)

        # Station spokes.
        for angle in (0, 45, 90, 135):
            arm = pygame.Vector2(1, 0).rotate(angle)
            a = (int(cx + arm.x * self.radius * 0.32), int(cy + arm.y * self.radius * 0.32))
            b = (int(cx + arm.x * self.radius * 0.88), int(cy + arm.y * self.radius * 0.88))
            pygame.draw.line(screen, spoke_color, a, b, LINE_WIDTH)

        # Hub and core.
        pygame.draw.circle(screen, (24, 32, 52), (cx, cy), int(self.radius * 0.34))
        pygame.draw.circle(screen, hub_color, (cx, cy), int(self.radius * 0.24))

        # Docking lights around the ring.
        for angle in (20, 70, 160, 250, 315):
            p = pygame.Vector2(1, 0).rotate(angle) * (self.radius * 0.82)
            pygame.draw.circle(screen, dock_light, (int(cx + p.x), int(cy + p.y)), 3)

    def update(self, dt, *args):
        # Station is static for now.
        return
