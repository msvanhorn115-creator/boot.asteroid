import pygame

class VirtualJoystick:
    def __init__(self, center, radius):
        self.center = pygame.Vector2(center)
        self.radius = radius
        self.active = False
        self.pointer_id = None
        self.value = pygame.Vector2(0, 0)

    def handle_event(self, event):
        if event.type == pygame.FINGERDOWN:
            pos = self._finger_pos(event)
            if self._in_bounds(pos):
                self.active = True
                self.pointer_id = event.finger_id
                self.value = self._compute_value(pos)
        elif event.type == pygame.FINGERMOTION and self.active and event.finger_id == self.pointer_id:
            pos = self._finger_pos(event)
            self.value = self._compute_value(pos)
        elif event.type == pygame.FINGERUP and self.active and event.finger_id == self.pointer_id:
            self.active = False
            self.pointer_id = None
            self.value = pygame.Vector2(0, 0)

    def _finger_pos(self, event):
        surface = pygame.display.get_surface()
        width, height = surface.get_size() if surface else (0, 0)
        return pygame.Vector2(int(event.x * width), int(event.y * height))

    def _in_bounds(self, pos):
        return (pos - self.center).length() <= self.radius

    def _compute_value(self, pos):
        delta = pos - self.center
        if delta.length() > self.radius:
            delta = delta.normalize() * self.radius
        return delta / self.radius

    def draw(self, screen):
        pygame.draw.circle(screen, (40, 40, 60), self.center, self.radius, 2)
        knob_pos = self.center + self.value * self.radius
        pygame.draw.circle(screen, (120, 180, 240), knob_pos, self.radius // 3)

    def get_turn_thrust(self):
        # X axis: turn (-1 left, +1 right), Y axis: thrust (+1 forward, -1 back)
        return self.value.x, -self.value.y
