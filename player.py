import math
import pygame
from constants import (
    PLAYER_RADIUS,
    LINE_WIDTH,
    PLAYER_TURN_SPEED,
    PLAYER_SPEED,
    PLAYER_SHOOT_SPEED,
    PLAYER_SHOOT_COOLDOWN_SECONDS,
    PLAYER_SHIELD_REGEN_INTERVAL_SECONDS,
    SHOT_RADIUS,
    UPGRADE_FIRE_RATE_BASE_COST,
    UPGRADE_FIRE_RATE_STEP_COST,
    UPGRADE_FIRE_RATE_COOLDOWN_STEP,
    UPGRADE_FIRE_RATE_MIN_COOLDOWN,
    UPGRADE_SHIELD_BASE_COST,
    UPGRADE_SHIELD_STEP_COST,
    UPGRADE_SHIELD_MAX_LEVEL,
    UPGRADE_MULTISHOT_BASE_COST,
    UPGRADE_MULTISHOT_STEP_COST,
    UPGRADE_MULTISHOT_MAX_LEVEL,
    UPGRADE_TARGETING_BEAM_BASE_COST,
    UPGRADE_TARGETING_BEAM_STEP_COST,
    UPGRADE_TARGETING_BEAM_MAX_LEVEL,
    UPGRADE_TARGETING_COMPUTER_BASE_COST,
    UPGRADE_TARGETING_COMPUTER_STEP_COST,
    UPGRADE_TARGETING_COMPUTER_MAX_LEVEL,
    UPGRADE_WARP_DRIVE_BASE_COST,
    UPGRADE_WARP_DRIVE_STEP_COST,
    UPGRADE_WARP_DRIVE_MAX_LEVEL,
    UPGRADE_SCANNER_BASE_COST,
    UPGRADE_SCANNER_STEP_COST,
    UPGRADE_SCANNER_MAX_LEVEL,
)
from circleshape import CircleShape
from shot import Shot
from resources import METAL_ECONOMY


class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.rotation = 0
        self.shoot_timer = 0
        self.on_shoot = None
        self.metals = {metal: 0 for metal in METAL_ECONOMY}
        self.credits = 0
        self.shoot_cooldown = PLAYER_SHOOT_COOLDOWN_SECONDS
        self.fire_rate_level = 0
        self.shield_level = 0
        self.shield_layers = 0
        self.shield_regen_timer = 0.0
        self.multishot_level = 0
        self.targeting_beam_level = 0
        self.targeting_computer_level = 0
        self.warp_drive_level = 0
        self.warp_energy = 0.0
        self.warp_boosting = False
        self.scanner_level = 0
        self.upgrade_cost_multiplier = 1.0

    def configure_difficulty(
        self,
        shoot_cooldown_multiplier=1.0,
        upgrade_cost_multiplier=1.0,
    ):
        self.shoot_cooldown = PLAYER_SHOOT_COOLDOWN_SECONDS * max(
            0.4, float(shoot_cooldown_multiplier)
        )
        self.upgrade_cost_multiplier = max(0.25, float(upgrade_cost_multiplier))

    def add_metal(self, metal_type, amount):
        if metal_type not in self.metals:
            return
        self.metals[metal_type] += max(0, int(amount))

    def add_metal_batch(self, metal_batch):
        for metal_type, amount in metal_batch.items():
            self.add_metal(metal_type, amount)

    def total_metal_units(self):
        return sum(self.metals.values())

    def projected_sell_value(self, prices):
        total = 0
        for metal_type, amount in self.metals.items():
            total += amount * prices.get(metal_type, 0)
        return total

    def sell_all_metals(self, prices):
        sold = {metal: qty for metal, qty in self.metals.items() if qty > 0}
        gained = self.projected_sell_value(prices)
        for metal in self.metals:
            self.metals[metal] = 0
        self.credits += gained
        return sold, gained

    def sell_metal_type(self, metal_type, price_per_unit):
        if metal_type not in self.metals:
            return 0, 0

        quantity = self.metals[metal_type]
        if quantity <= 0:
            return 0, 0

        gained = int(quantity * max(0, int(price_per_unit)))
        self.metals[metal_type] = 0
        self.credits += gained
        return quantity, gained

    def get_fire_rate_upgrade_cost(self):
        base_cost = UPGRADE_FIRE_RATE_BASE_COST + (
            self.fire_rate_level * UPGRADE_FIRE_RATE_STEP_COST
        )
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_fire_rate_upgrade(self):
        if self.shoot_cooldown <= UPGRADE_FIRE_RATE_MIN_COOLDOWN:
            return False, "Fire rate already maxed"

        cost = self.get_fire_rate_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.fire_rate_level += 1
        self.shoot_cooldown = max(
            UPGRADE_FIRE_RATE_MIN_COOLDOWN,
            self.shoot_cooldown - UPGRADE_FIRE_RATE_COOLDOWN_STEP,
        )
        return True, f"Fire rate upgraded to L{self.fire_rate_level}"

    def get_shield_upgrade_cost(self):
        base_cost = UPGRADE_SHIELD_BASE_COST + (
            self.shield_level * UPGRADE_SHIELD_STEP_COST
        )
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_shield_upgrade(self):
        if self.shield_level >= UPGRADE_SHIELD_MAX_LEVEL:
            return False, "Shield already maxed"

        cost = self.get_shield_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.shield_level += 1
        self.shield_layers = self.shield_level
        self.shield_regen_timer = 0.0
        return True, f"Shield upgraded to L{self.shield_level}"

    def get_multishot_upgrade_cost(self):
        base_cost = UPGRADE_MULTISHOT_BASE_COST + (
            self.multishot_level * UPGRADE_MULTISHOT_STEP_COST
        )
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_multishot_upgrade(self):
        if self.multishot_level >= UPGRADE_MULTISHOT_MAX_LEVEL:
            return False, "Multishot already maxed"

        cost = self.get_multishot_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.multishot_level += 1
        return True, f"Multishot upgraded to L{self.multishot_level}"

    def get_targeting_beam_upgrade_cost(self):
        base_cost = UPGRADE_TARGETING_BEAM_BASE_COST + (
            self.targeting_beam_level * UPGRADE_TARGETING_BEAM_STEP_COST
        )
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_targeting_beam_upgrade(self):
        if self.targeting_beam_level >= UPGRADE_TARGETING_BEAM_MAX_LEVEL:
            return False, "Targeting beam already maxed"

        cost = self.get_targeting_beam_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.targeting_beam_level += 1
        return True, f"Targeting beam upgraded to L{self.targeting_beam_level}"

    def get_targeting_beam_range(self):
        staged_ranges = [0, 220, 340, 470]
        level = max(0, min(self.targeting_beam_level, len(staged_ranges) - 1))
        return staged_ranges[level]

    def get_targeting_computer_upgrade_cost(self):
        base_cost = UPGRADE_TARGETING_COMPUTER_BASE_COST + (
            self.targeting_computer_level * UPGRADE_TARGETING_COMPUTER_STEP_COST
        )
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_targeting_computer_upgrade(self):
        if self.targeting_computer_level >= UPGRADE_TARGETING_COMPUTER_MAX_LEVEL:
            return False, "Targeting computer already maxed"

        cost = self.get_targeting_computer_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.targeting_computer_level += 1
        return True, f"Targeting computer upgraded to L{self.targeting_computer_level}"

    def get_warp_drive_upgrade_cost(self):
        base_cost = UPGRADE_WARP_DRIVE_BASE_COST + (
            self.warp_drive_level * UPGRADE_WARP_DRIVE_STEP_COST
        )
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_warp_drive_upgrade(self):
        if self.warp_drive_level >= UPGRADE_WARP_DRIVE_MAX_LEVEL:
            return False, "Sublight warp drive already maxed"

        cost = self.get_warp_drive_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.warp_drive_level += 1
        self.warp_energy = self.get_warp_capacity_seconds()
        return True, f"Sublight warp drive upgraded to L{self.warp_drive_level}"

    def get_warp_speed_multiplier(self):
        return [1.0, 1.45, 1.8, 2.2, 2.65][self.warp_drive_level]

    def get_warp_capacity_seconds(self):
        return [0.0, 1.0, 1.4, 1.9, 2.5][self.warp_drive_level]

    def get_scanner_upgrade_cost(self):
        base_cost = UPGRADE_SCANNER_BASE_COST + (self.scanner_level * UPGRADE_SCANNER_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_scanner_upgrade(self):
        if self.scanner_level >= UPGRADE_SCANNER_MAX_LEVEL:
            return False, "Scanner array already maxed"

        cost = self.get_scanner_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.scanner_level += 1
        return True, f"Scanner array upgraded to L{self.scanner_level}"

    def get_lock_cone_degrees(self):
        if self.targeting_computer_level <= 0:
            return 0.0
        return [0.0, 10.0, 16.0, 24.0][self.targeting_computer_level]

    def get_lock_time_seconds(self):
        if self.targeting_computer_level <= 0:
            return 999.0
        return [999.0, 0.45, 0.28, 0.15][self.targeting_computer_level]

    def credits_needed_for_full_upgrades(self):
        needed = 0
        cost_multiplier = self.upgrade_cost_multiplier

        # Fire rate maxing depends on cooldown steps, so simulate without mutating state.
        temp_level = self.fire_rate_level
        temp_cooldown = self.shoot_cooldown
        while temp_cooldown > UPGRADE_FIRE_RATE_MIN_COOLDOWN + 1e-9:
            base_cost = UPGRADE_FIRE_RATE_BASE_COST + (temp_level * UPGRADE_FIRE_RATE_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))
            temp_level += 1
            temp_cooldown = max(
                UPGRADE_FIRE_RATE_MIN_COOLDOWN,
                temp_cooldown - UPGRADE_FIRE_RATE_COOLDOWN_STEP,
            )

        for lvl in range(self.shield_level, UPGRADE_SHIELD_MAX_LEVEL):
            base_cost = UPGRADE_SHIELD_BASE_COST + (lvl * UPGRADE_SHIELD_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.multishot_level, UPGRADE_MULTISHOT_MAX_LEVEL):
            base_cost = UPGRADE_MULTISHOT_BASE_COST + (lvl * UPGRADE_MULTISHOT_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.targeting_beam_level, UPGRADE_TARGETING_BEAM_MAX_LEVEL):
            base_cost = UPGRADE_TARGETING_BEAM_BASE_COST + (lvl * UPGRADE_TARGETING_BEAM_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.targeting_computer_level, UPGRADE_TARGETING_COMPUTER_MAX_LEVEL):
            base_cost = UPGRADE_TARGETING_COMPUTER_BASE_COST + (lvl * UPGRADE_TARGETING_COMPUTER_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.warp_drive_level, UPGRADE_WARP_DRIVE_MAX_LEVEL):
            base_cost = UPGRADE_WARP_DRIVE_BASE_COST + (lvl * UPGRADE_WARP_DRIVE_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.scanner_level, UPGRADE_SCANNER_MAX_LEVEL):
            base_cost = UPGRADE_SCANNER_BASE_COST + (lvl * UPGRADE_SCANNER_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        return needed

    def refill_shields(self):
        self.shield_layers = self.shield_level
        self.shield_regen_timer = 0.0

    def absorb_hit(self):
        if self.shield_layers > 0:
            self.shield_layers -= 1
            self.shield_regen_timer = 0.0
            return True
        return False

    def multishot_pattern(self):
        if self.multishot_level <= 0:
            return [0.0]
        if self.multishot_level == 1:
            return [-7.0, 0.0, 7.0]
        if self.multishot_level == 2:
            return [-14.0, -7.0, 0.0, 7.0, 14.0]
        if self.multishot_level == 3:
            return [-20.0, -12.0, -6.0, 0.0, 6.0, 12.0, 20.0]
        return [-26.0, -18.0, -12.0, -6.0, 0.0, 6.0, 12.0, 18.0, 26.0]

    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        center = self.position
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90)

        nose = center + forward * (self.radius * 1.06)
        shoulder_left = center + forward * (self.radius * 0.2) - right * (self.radius * 0.68)
        shoulder_right = center + forward * (self.radius * 0.2) + right * (self.radius * 0.68)
        wing_left = center - forward * (self.radius * 0.16) - right * (self.radius * 0.98)
        wing_right = center - forward * (self.radius * 0.16) + right * (self.radius * 0.98)
        tail_left = center - forward * (self.radius * 0.92) - right * (self.radius * 0.35)
        tail_right = center - forward * (self.radius * 0.92) + right * (self.radius * 0.35)

        hull_points = [
            nose,
            shoulder_left,
            wing_left,
            tail_left,
            tail_right,
            wing_right,
            shoulder_right,
        ]

        hull_fill = (152, 168, 194)
        hull_edge = (242, 247, 255)
        wing_fill = (112, 130, 158)
        cockpit_fill = (214, 235, 255)
        panel_color = (96, 112, 142)

        pygame.draw.polygon(
            screen,
            hull_fill,
            [(int(p.x), int(p.y)) for p in hull_points],
        )
        pygame.draw.polygon(
            screen,
            hull_edge,
            [(int(p.x), int(p.y)) for p in hull_points],
            LINE_WIDTH,
        )

        wing_plate_left = [
            shoulder_left,
            wing_left,
            center - right * (self.radius * 0.38),
        ]
        wing_plate_right = [
            shoulder_right,
            wing_right,
            center + right * (self.radius * 0.38),
        ]
        pygame.draw.polygon(screen, wing_fill, [(int(p.x), int(p.y)) for p in wing_plate_left])
        pygame.draw.polygon(screen, wing_fill, [(int(p.x), int(p.y)) for p in wing_plate_right])

        cockpit_tip = center + forward * (self.radius * 0.62)
        cockpit_left = center - right * (self.radius * 0.25)
        cockpit_right = center + right * (self.radius * 0.25)
        cockpit = [cockpit_tip, cockpit_left, cockpit_right]
        pygame.draw.polygon(screen, cockpit_fill, [(int(p.x), int(p.y)) for p in cockpit])
        pygame.draw.polygon(screen, (244, 249, 255), [(int(p.x), int(p.y)) for p in cockpit], 1)

        tail_mid = (tail_left + tail_right) * 0.5
        spine_mid = center + forward * (self.radius * 0.28)
        pygame.draw.line(
            screen,
            panel_color,
            (int(tail_mid.x), int(tail_mid.y)),
            (int(spine_mid.x), int(spine_mid.y)),
            2,
        )

        thrust_pulse = 0.5 + 0.5 * (math.sin(pygame.time.get_ticks() * 0.013) * 0.5 + 0.5)
        thruster_outer = center - forward * (self.radius * 1.02)
        thruster_left = thruster_outer - right * (self.radius * 0.2)
        thruster_right = thruster_outer + right * (self.radius * 0.2)

        engine_color = (110, 194, 255) if not self.warp_boosting else (186, 140, 255)
        for thruster in (thruster_left, thruster_right):
            pygame.draw.circle(screen, (28, 38, 56), (int(thruster.x), int(thruster.y)), 4)
            pygame.draw.circle(
                screen,
                engine_color,
                (int(thruster.x), int(thruster.y)),
                2 + int(2 * thrust_pulse),
            )

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def move(self, dt):
        unit_vector = pygame.Vector2(0, 1)
        rotated_vector = unit_vector.rotate(self.rotation)
        rotated_with_speed_vector = rotated_vector * PLAYER_SPEED * dt
        self.position += rotated_with_speed_vector

    def shoot(self):
        if self.shoot_timer > 0:
            return

        self.shoot_timer = self.shoot_cooldown
        for spread in self.multishot_pattern():
            shot = Shot(self.position.x, self.position.y, SHOT_RADIUS, owner="player")
            shot.velocity = (
                pygame.Vector2(0, 1).rotate(self.rotation + spread) * PLAYER_SHOOT_SPEED
            )
        if self.on_shoot is not None:
            self.on_shoot()

    def update(self, dt, *args):
        self.shoot_timer -= dt

        if self.shield_level > 0 and self.shield_layers < self.shield_level:
            self.shield_regen_timer += dt
            while self.shield_regen_timer >= PLAYER_SHIELD_REGEN_INTERVAL_SECONDS:
                self.shield_layers += 1
                self.shield_regen_timer -= PLAYER_SHIELD_REGEN_INTERVAL_SECONDS
                if self.shield_layers >= self.shield_level:
                    self.shield_layers = self.shield_level
                    self.shield_regen_timer = 0.0
                    break

        keys = pygame.key.get_pressed()

        if self.warp_drive_level > 0:
            warp_capacity = self.get_warp_capacity_seconds()
            if keys[pygame.K_w] and self.warp_energy > 0.0:
                self.warp_boosting = True
                self.warp_energy = max(0.0, self.warp_energy - dt)
            else:
                self.warp_boosting = False
                self.warp_energy = min(warp_capacity, self.warp_energy + dt * 0.62)
        else:
            self.warp_boosting = False
            self.warp_energy = 0.0

        if keys[pygame.K_LEFT]:
            self.rotate(-dt)
        if keys[pygame.K_RIGHT]:
            self.rotate(dt)
        if self.warp_boosting:
            self.move(dt * self.get_warp_speed_multiplier())
        elif keys[pygame.K_UP]:
            self.move(dt)
        if keys[pygame.K_DOWN]:
            self.move(-dt)
        if keys[pygame.K_SPACE]:
            self.shoot()

        self.wrap_around_screen()
