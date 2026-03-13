import math
import random
import pygame

from constants import (
    ENEMY_SPAWN_RATE_SECONDS,
    ENEMY_SHOOT_COOLDOWN_SECONDS,
    ENEMY_SHOT_SPEED,
    ENEMY_SPEED,
    ENEMY_ALERT_LOSE_MULTIPLIER,
    ENEMY_BOMBER_VIEW_RANGE,
    ENEMY_HARASSER_VIEW_RANGE,
    ENEMY_TANK_VIEW_RANGE,
    SHOT_RADIUS,
    LINE_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from circleshape import CircleShape
from shot import Shot
from logger import log_event


class Enemy(CircleShape):
    """Base enemy type."""

    COLOR = "red"

    def __init__(
        self,
        x,
        y,
        radius,
        health=1,
        view_range=280,
        speed_multiplier=1.0,
        health_multiplier=1.0,
        view_multiplier=1.0,
        shoot_cooldown_multiplier=1.0,
        ai_aggression=1.0,
        ai_accuracy=1.0,
        ai_strafe=1.0,
        ai_fire_intent=1.0,
        ai_memory=1.0,
    ):
        super().__init__(x, y, radius)
        self.rotation = 0
        self.health = max(1, int(round(health * max(0.2, float(health_multiplier)))))
        self.shoot_timer = 0
        self.view_range = view_range * max(0.3, float(view_multiplier))
        self.alerted = False
        self.idle_timer = random.uniform(0.4, 1.6)
        self.speed_multiplier = max(0.2, float(speed_multiplier))
        self.shoot_cooldown_multiplier = max(0.2, float(shoot_cooldown_multiplier))
        self.ai_aggression = max(0.4, min(1.8, float(ai_aggression)))
        self.ai_accuracy = max(0.4, min(1.8, float(ai_accuracy)))
        self.ai_strafe = max(0.4, min(1.8, float(ai_strafe)))
        self.ai_fire_intent = max(0.3, min(2.0, float(ai_fire_intent)))
        self.ai_memory = max(0.6, min(1.7, float(ai_memory)))

    def scaled_speed(self, base_scale):
        return ENEMY_SPEED * self.speed_multiplier * base_scale

    def can_see_player(self, player):
        if player is None:
            self.alerted = False
            return False

        if getattr(player, "cloak_active", False):
            self.alerted = False
            return False

        distance = self.position.distance_to(player.position)
        lose_range = self.view_range * ENEMY_ALERT_LOSE_MULTIPLIER * self.ai_memory

        if self.alerted:
            self.alerted = distance <= lose_range
        else:
            self.alerted = distance <= self.view_range

        return self.alerted

    def idle_patrol(self, dt, speed_scale=0.3):
        self.idle_timer -= dt
        if self.idle_timer <= 0:
            self.idle_timer = random.uniform(0.8, 2.4)
            self.rotation += random.uniform(-120, 120)

        direction = pygame.Vector2(0, 1).rotate(self.rotation)
        self.velocity = direction * self.scaled_speed(speed_scale)

    def draw(self, screen):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90)
        center = self.position

        if isinstance(self, SuicideBomber):
            points = [
                center + forward * (self.radius * 1.12),
                center + right * (self.radius * 0.74),
                center - forward * (self.radius * 1.02),
                center - right * (self.radius * 0.74),
            ]
        elif isinstance(self, Harasser):
            points = [
                center + forward * (self.radius * 1.25),
                center + forward * (self.radius * 0.05) + right * (self.radius * 0.6),
                center - forward * (self.radius * 0.92),
                center + forward * (self.radius * 0.05) - right * (self.radius * 0.6),
            ]
        elif isinstance(self, Tank):
            points = [
                center + forward * (self.radius * 1.0),
                center + forward * (self.radius * 0.45) + right * (self.radius * 0.82),
                center - forward * (self.radius * 0.45) + right * (self.radius * 0.82),
                center - forward * (self.radius * 1.0),
                center - forward * (self.radius * 0.45) - right * (self.radius * 0.82),
                center + forward * (self.radius * 0.45) - right * (self.radius * 0.82),
            ]
        else:
            points = [
                center + forward * self.radius,
                center - forward * self.radius - right * (self.radius / 1.5),
                center - forward * self.radius + right * (self.radius / 1.5),
            ]

        nose = max(points, key=lambda p: forward.dot(p - center))
        rear = min(points, key=lambda p: forward.dot(p - center))

        base_color = getattr(self, "color_override", self.COLOR)
        base = pygame.Color(base_color)
        fill = (
            max(25, int(base.r * 0.48)),
            max(25, int(base.g * 0.48)),
            max(25, int(base.b * 0.48)),
        )
        edge = (base.r, base.g, base.b)
        highlight = (
            min(255, int(base.r * 0.75) + 45),
            min(255, int(base.g * 0.75) + 45),
            min(255, int(base.b * 0.75) + 45),
        )
        panel = (
            min(255, int(base.r * 0.65) + 20),
            min(255, int(base.g * 0.65) + 20),
            min(255, int(base.b * 0.65) + 20),
        )

        pygame.draw.polygon(screen, fill, [(int(p.x), int(p.y)) for p in points])
        pygame.draw.polygon(screen, edge, [(int(p.x), int(p.y)) for p in points], LINE_WIDTH)

        cockpit_tip = center + (nose - center) * 0.55
        cockpit_left = center - right * (self.radius * 0.22)
        cockpit_right = center + right * (self.radius * 0.22)
        pygame.draw.polygon(
            screen,
            highlight,
            [(int(cockpit_tip.x), int(cockpit_tip.y)), (int(cockpit_left.x), int(cockpit_left.y)), (int(cockpit_right.x), int(cockpit_right.y))],
        )

        spine = center + (nose - center) * 0.34
        pygame.draw.line(
            screen,
            panel,
            (int(rear.x), int(rear.y)),
            (int(spine.x), int(spine.y)),
            2,
        )

        if isinstance(self, SuicideBomber):
            fin_left = center - right * (self.radius * 0.9)
            fin_right = center + right * (self.radius * 0.9)
            pygame.draw.line(
                screen,
                edge,
                (int(fin_left.x), int(fin_left.y)),
                (int(rear.x), int(rear.y)),
                2,
            )
            pygame.draw.line(
                screen,
                edge,
                (int(fin_right.x), int(fin_right.y)),
                (int(rear.x), int(rear.y)),
                2,
            )
        elif isinstance(self, Harasser):
            pod_left = center - right * (self.radius * 0.58)
            pod_right = center + right * (self.radius * 0.58)
            pygame.draw.circle(screen, panel, (int(pod_left.x), int(pod_left.y)), 3)
            pygame.draw.circle(screen, panel, (int(pod_right.x), int(pod_right.y)), 3)
        elif isinstance(self, Tank):
            pygame.draw.circle(screen, edge, (int(center.x), int(center.y)), int(self.radius * 0.38), 1)

        engine_pulse = 0.5 + 0.5 * (math.sin(pygame.time.get_ticks() * 0.01 + self.radius) * 0.5 + 0.5)
        engine_color = (
            min(255, int(highlight[0] * 0.9)),
            min(255, int(highlight[1] * 0.9)),
            min(255, int(highlight[2] * 0.9)),
        )
        pygame.draw.circle(screen, (24, 28, 38), (int(rear.x), int(rear.y)), 4)
        pygame.draw.circle(
            screen,
            engine_color,
            (int(rear.x), int(rear.y)),
            2 + int(2 * engine_pulse),
        )

        faction_key = getattr(self, "faction_key", "")
        if faction_key:
            badge_center = center + right * (self.radius * 0.72) - forward * (self.radius * 0.15)
            badge_color = {
                "player": (147, 197, 253),
                "crimson": (252, 165, 165),
                "jade": (110, 231, 183),
                "gold": (253, 230, 138),
            }.get(faction_key, (203, 213, 225))

            pygame.draw.circle(screen, (9, 16, 29), (int(badge_center.x), int(badge_center.y)), 6)
            pygame.draw.circle(screen, badge_color, (int(badge_center.x), int(badge_center.y)), 5, 1)

            if faction_key == "crimson":
                pygame.draw.line(
                    screen,
                    badge_color,
                    (int(badge_center.x - 2), int(badge_center.y + 2)),
                    (int(badge_center.x), int(badge_center.y - 2)),
                    2,
                )
                pygame.draw.line(
                    screen,
                    badge_color,
                    (int(badge_center.x), int(badge_center.y - 2)),
                    (int(badge_center.x + 2), int(badge_center.y + 2)),
                    2,
                )
            elif faction_key == "jade":
                pygame.draw.polygon(
                    screen,
                    badge_color,
                    [
                        (int(badge_center.x), int(badge_center.y - 2)),
                        (int(badge_center.x + 2), int(badge_center.y)),
                        (int(badge_center.x), int(badge_center.y + 2)),
                        (int(badge_center.x - 2), int(badge_center.y)),
                    ],
                )
            elif faction_key == "gold":
                pygame.draw.circle(screen, badge_color, (int(badge_center.x), int(badge_center.y)), 2)
            elif faction_key == "player":
                pygame.draw.line(
                    screen,
                    badge_color,
                    (int(badge_center.x), int(badge_center.y - 2)),
                    (int(badge_center.x), int(badge_center.y + 2)),
                    1,
                )
                pygame.draw.line(
                    screen,
                    badge_color,
                    (int(badge_center.x - 2), int(badge_center.y)),
                    (int(badge_center.x + 2), int(badge_center.y)),
                    1,
                )

    def take_damage(self, amount=1):
        self.health -= amount
        log_event("enemy_hit", health=self.health)
        if self.health <= 0:
            self.kill()
            log_event("enemy_destroyed")

    def aim_at(self, target_pos):
        # Point toward a target position
        delta = target_pos - self.position
        if delta.length_squared() == 0:
            return
        direction = delta.normalize()
        angle = math.degrees(math.atan2(direction.y, direction.x)) - 90
        self.rotation = angle

    def aim_at_target(self, target_pos, target_velocity=None):
        target = pygame.Vector2(target_pos)
        if target_velocity is not None:
            lead_seconds = 0.06 + 0.09 * self.ai_accuracy
            target += pygame.Vector2(target_velocity) * lead_seconds

        delta = target - self.position
        if delta.length_squared() == 0:
            return

        direction = delta.normalize()
        angle = math.degrees(math.atan2(direction.y, direction.x)) - 90
        jitter_degrees = max(0.0, 8.0 - self.ai_accuracy * 4.0)
        if jitter_degrees > 0:
            angle += random.uniform(-jitter_degrees, jitter_degrees)
        self.rotation = angle

    def should_fire(self, dt):
        trigger_prob = min(1.0, dt * (2.2 * self.ai_fire_intent))
        return random.random() < trigger_prob

    def active_target(self, player):
        forced_target_timer = float(getattr(self, "forced_target_timer", 0.0) or 0.0)
        if forced_target_timer > 0.0 and hasattr(self, "forced_target_position"):
            target_pos = pygame.Vector2(self.forced_target_position)
            target_velocity = pygame.Vector2(getattr(self, "forced_target_velocity", (0.0, 0.0)))
            target_radius = float(getattr(self, "forced_target_radius", 18.0))
            return target_pos, target_velocity, target_radius, True

        if player is None:
            return None, None, 0.0, False

        return (
            pygame.Vector2(player.position),
            pygame.Vector2(getattr(player, "velocity", (0.0, 0.0))),
            float(getattr(player, "radius", 18.0)),
            False,
        )

    def shoot(self):
        if self.shoot_timer > 0:
            return

        self.shoot_timer = ENEMY_SHOOT_COOLDOWN_SECONDS * self.shoot_cooldown_multiplier
        shot = Shot(self.position.x, self.position.y, SHOT_RADIUS, owner="enemy")
        shot.velocity = pygame.Vector2(0, 1).rotate(self.rotation) * ENEMY_SHOT_SPEED

    def update(self, dt, player=None):
        # Default: do nothing
        self.shoot_timer = max(0, self.shoot_timer - dt)
        forced_target_timer = float(getattr(self, "forced_target_timer", 0.0) or 0.0)
        if forced_target_timer > 0.0:
            self.forced_target_timer = max(0.0, forced_target_timer - dt)

        entry_timer = float(getattr(self, "entry_timer", 0.0) or 0.0)
        if entry_timer > 0.0 and hasattr(self, "entry_target"):
            target = pygame.Vector2(self.entry_target)
            delta = target - self.position
            if delta.length_squared() > 1e-6:
                direction = delta.normalize()
                self.velocity = direction * self.scaled_speed(0.95)
                angle = math.degrees(math.atan2(direction.y, direction.x)) - 90
                self.rotation = angle
            self.entry_timer = max(0.0, entry_timer - dt)

        self.position += self.velocity * dt
        # Optional spawn-entry timer lets enemies fly in from off-screen first.
        no_wrap_timer = float(getattr(self, "no_wrap_timer", 0.0) or 0.0)
        if no_wrap_timer > 0.0:
            self.no_wrap_timer = max(0.0, no_wrap_timer - dt)
        else:
            self.wrap_around_screen()

    def behavior(self, dt, player):
        # override in subclasses
        pass


class SuicideBomber(Enemy):
    COLOR = "orange"

    def __init__(self, x, y, **tuning):
        super().__init__(
            x,
            y,
            radius=18,
            health=1,
            view_range=ENEMY_BOMBER_VIEW_RANGE,
            speed_multiplier=tuning.get("speed_multiplier", 1.0),
            health_multiplier=tuning.get("health_multiplier", 1.0),
            view_multiplier=tuning.get("view_multiplier", 1.0),
            shoot_cooldown_multiplier=tuning.get("shoot_cooldown_multiplier", 1.0),
        )

    def behavior(self, dt, player):
        # Charge directly at the player
        if float(getattr(self, "entry_timer", 0.0) or 0.0) > 0.0:
            return

        target_pos, target_velocity, _target_radius, force_engage = self.active_target(player)
        if target_pos is None:
            self.velocity = pygame.Vector2(0, 0)
            return

        if not force_engage and not self.can_see_player(player):
            self.idle_patrol(dt, speed_scale=0.26)
            return

        delta = target_pos - self.position
        if delta.length_squared() == 0:
            self.velocity = pygame.Vector2(0, 0)
            return

        direction = delta.normalize()
        speed_scale = 0.9 + 0.22 * self.ai_aggression
        self.velocity = direction * self.scaled_speed(speed_scale)
        self.aim_at_target(target_pos, target_velocity)

    def update(self, dt, player=None):
        super().update(dt, player)
        self.behavior(dt, player)


class Harasser(Enemy):
    COLOR = "cyan"

    def __init__(self, x, y, **tuning):
        super().__init__(
            x,
            y,
            radius=16,
            health=1,
            view_range=ENEMY_HARASSER_VIEW_RANGE,
            speed_multiplier=tuning.get("speed_multiplier", 1.0),
            health_multiplier=tuning.get("health_multiplier", 1.0),
            view_multiplier=tuning.get("view_multiplier", 1.0),
            shoot_cooldown_multiplier=tuning.get("shoot_cooldown_multiplier", 1.0),
        )

    def behavior(self, dt, player):
        if float(getattr(self, "entry_timer", 0.0) or 0.0) > 0.0:
            return

        target_pos, target_velocity, target_radius, force_engage = self.active_target(player)
        if target_pos is None:
            self.velocity = pygame.Vector2(0, 0)
            return

        if not force_engage and not self.can_see_player(player):
            self.idle_patrol(dt, speed_scale=0.3)
            return

        displacement = target_pos - self.position
        distance = displacement.length()
        desired_range = max(
            72.0 + target_radius * 2.6,
            self.view_range * max(0.55, 0.9 - 0.14 * (self.ai_aggression - 1.0)),
        )

        if distance == 0:
            self.velocity = pygame.Vector2(0, 0)
            return

        # Keep distance: evade if too close, approach if too far, strafe when in band.
        if distance < desired_range * 0.6:
            self.velocity = (-displacement).normalize() * self.scaled_speed(0.68 + 0.18 * self.ai_aggression)
        elif distance > desired_range:
            self.velocity = displacement.normalize() * self.scaled_speed(0.65 + 0.2 * self.ai_aggression)
        else:
            toward = displacement.normalize()
            strafe = pygame.Vector2(-toward.y, toward.x)
            strafe_sign = 1.0 if (int(pygame.time.get_ticks() / 900) % 2 == 0) else -1.0
            strafe_push = 0.85 * self.ai_strafe
            self.velocity = (strafe * strafe_sign * strafe_push + toward * 0.16) * self.scaled_speed(0.62 + 0.16 * self.ai_aggression)

        self.aim_at_target(target_pos, target_velocity)

        # Fire at the player when in range
        if distance < self.view_range * (0.84 + 0.14 * self.ai_accuracy) and self.should_fire(dt):
            self.shoot()

    def update(self, dt, player=None):
        super().update(dt, player)
        self.behavior(dt, player)


class Tank(Enemy):
    COLOR = "magenta"

    def __init__(self, x, y, **tuning):
        super().__init__(
            x,
            y,
            radius=22,
            health=3,
            view_range=ENEMY_TANK_VIEW_RANGE,
            speed_multiplier=tuning.get("speed_multiplier", 1.0),
            health_multiplier=tuning.get("health_multiplier", 1.0),
            view_multiplier=tuning.get("view_multiplier", 1.0),
            shoot_cooldown_multiplier=tuning.get("shoot_cooldown_multiplier", 1.0),
        )

    def behavior(self, dt, player):
        if float(getattr(self, "entry_timer", 0.0) or 0.0) > 0.0:
            return

        target_pos, target_velocity, target_radius, force_engage = self.active_target(player)
        if target_pos is None:
            self.velocity = pygame.Vector2(0, 0)
            return

        if not force_engage and not self.can_see_player(player):
            self.idle_patrol(dt, speed_scale=0.22)
            return

        displacement = target_pos - self.position
        distance = displacement.length()
        close_range = max(110.0 + target_radius * 2.4, 180 * (0.9 + 0.24 * self.ai_aggression))

        if distance == 0:
            self.velocity = pygame.Vector2(0, 0)
            return

        # Move toward player if too far, slow down when close
        if distance > close_range:
            self.velocity = displacement.normalize() * self.scaled_speed(0.52 + 0.12 * self.ai_aggression)
        else:
            toward = displacement.normalize()
            strafe = pygame.Vector2(-toward.y, toward.x)
            self.velocity = (strafe * (0.32 * self.ai_strafe) + toward * 0.12) * self.scaled_speed(0.44 + 0.1 * self.ai_aggression)

        self.aim_at_target(target_pos, target_velocity)

        # Fire occasionally at close range
        if distance < close_range and self.should_fire(dt):
            self.shoot()

    def update(self, dt, player=None):
        super().update(dt, player)
        self.behavior(dt, player)


class EnemyField(pygame.sprite.Sprite):
    """Spawns enemies along the edges of the screen."""

    def __init__(self, spawn_interval=None, spawn_weights=None, spawn_tuning=None):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.spawn_timer = 0.0
        self.spawn_interval = (
            ENEMY_SPAWN_RATE_SECONDS
            if spawn_interval is None
            else spawn_interval
        )
        self.spawn_weights = [1, 1, 1] if spawn_weights is None else spawn_weights
        self.spawn_tuning = {} if spawn_tuning is None else dict(spawn_tuning)

    def spawn(self, enemy_cls, position, velocity):
        enemy = enemy_cls(position.x, position.y, **self.spawn_tuning)
        enemy.velocity = velocity

    def update(self, dt, *args):
        self.spawn_timer += dt
        if self.spawn_timer > self.spawn_interval:
            self.spawn_timer = 0

            max_alive = int(self.spawn_tuning.get("max_alive", 0) or 0)
            enemy_group = Enemy.containers[0] if hasattr(Enemy, "containers") else None
            if max_alive > 0 and enemy_group is not None and len(enemy_group) >= max_alive:
                return

            # pick a random edge
            edge = random.choice([
                (pygame.Vector2(1, 0), lambda y: pygame.Vector2(0, y * SCREEN_HEIGHT)),
                (pygame.Vector2(-1, 0), lambda y: pygame.Vector2(SCREEN_WIDTH, y * SCREEN_HEIGHT)),
                (pygame.Vector2(0, 1), lambda x: pygame.Vector2(x * SCREEN_WIDTH, 0)),
                (pygame.Vector2(0, -1), lambda x: pygame.Vector2(x * SCREEN_WIDTH, SCREEN_HEIGHT)),
            ])

            speed = random.randint(60, 140)
            velocity = edge[0] * speed
            velocity = velocity.rotate(random.randint(-20, 20))
            position = edge[1](random.uniform(0, 1))

            enemy_type = random.choices(
                [SuicideBomber, Harasser, Tank],
                weights=self.spawn_weights,
                k=1,
            )[0]
            self.spawn(enemy_type, position, velocity)
