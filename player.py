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
    UPGRADE_MISSILE_BASE_COST,
    UPGRADE_MISSILE_STEP_COST,
    UPGRADE_MISSILE_MAX_LEVEL,
    UPGRADE_CLOAK_BASE_COST,
    UPGRADE_CLOAK_STEP_COST,
    UPGRADE_CLOAK_MAX_LEVEL,
    UPGRADE_CARGO_HOLD_BASE_COST,
    UPGRADE_CARGO_HOLD_STEP_COST,
    UPGRADE_CARGO_HOLD_MAX_LEVEL,
    UPGRADE_ACCOMMODATIONS_BASE_COST,
    UPGRADE_ACCOMMODATIONS_STEP_COST,
    UPGRADE_ACCOMMODATIONS_MAX_LEVEL,
    UPGRADE_ENGINE_TUNING_BASE_COST,
    UPGRADE_ENGINE_TUNING_STEP_COST,
    UPGRADE_ENGINE_TUNING_MAX_LEVEL,
    UPGRADE_WEAPON_AMP_BASE_COST,
    UPGRADE_WEAPON_AMP_STEP_COST,
    UPGRADE_WEAPON_AMP_MAX_LEVEL,
    UPGRADE_DEFLECTOR_BASE_COST,
    UPGRADE_DEFLECTOR_STEP_COST,
    UPGRADE_DEFLECTOR_MAX_LEVEL,
    UPGRADE_MISSILE_PAYLOAD_BASE_COST,
    UPGRADE_MISSILE_PAYLOAD_STEP_COST,
    UPGRADE_MISSILE_PAYLOAD_MAX_LEVEL,
    UPGRADE_AUTO_MINING_BASE_COST,
    UPGRADE_AUTO_MINING_STEP_COST,
    UPGRADE_AUTO_MINING_MAX_LEVEL,
)
from circleshape import CircleShape
from shot import Shot
from resources import METAL_ECONOMY


class Player(CircleShape):
    DEFLECTOR_REGEN_SECONDS = 12.0

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
        self.deflector_level = 1
        self.deflector_layers = 1
        self.deflector_regen_timer = 0.0
        self.multishot_level = 0
        self.targeting_beam_level = 0
        self.targeting_computer_level = 0
        self.warp_drive_level = 0
        self.warp_energy = 0.0
        self.warp_boosting = False
        self.scanner_level = 0
        self.upgrade_cost_multiplier = 1.0
        self.combat_level = 1
        self.combat_xp = 0
        self.missile_level = 0
        self.missile_timer = 0.0
        self.cloak_level = 0
        self.cloak_active = False
        self.cloak_timer = 0.0
        self.cargo_hold_level = 0
        self.accommodations_level = 0
        self.engine_tuning_level = 0
        self.weapon_amp_level = 0
        self.deflector_booster_level = 0
        self.missile_payload_level = 0
        self.auto_mining_level = 0
        self.virtual_controls = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "warp": False,
            "fire": False,
        }

    def set_virtual_controls(
        self,
        *,
        left=False,
        right=False,
        up=False,
        down=False,
        warp=False,
        fire=False,
    ):
        self.virtual_controls["left"] = bool(left)
        self.virtual_controls["right"] = bool(right)
        self.virtual_controls["up"] = bool(up)
        self.virtual_controls["down"] = bool(down)
        self.virtual_controls["warp"] = bool(warp)
        self.virtual_controls["fire"] = bool(fire)

    def clear_virtual_controls(self):
        for key in self.virtual_controls:
            self.virtual_controls[key] = False

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

    def get_missile_upgrade_cost(self):
        base_cost = UPGRADE_MISSILE_BASE_COST + (self.missile_level * UPGRADE_MISSILE_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_missile_upgrade(self):
        if self.missile_level >= UPGRADE_MISSILE_MAX_LEVEL:
            return False, "Missiles already maxed"

        cost = self.get_missile_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.missile_level += 1
        return True, f"Missiles upgraded to L{self.missile_level}"

    def missile_cooldown_seconds(self):
        # Faster reload at higher missile levels.
        return max(2.4, 6.0 - self.missile_level * 0.85)

    def get_cloak_upgrade_cost(self):
        base_cost = UPGRADE_CLOAK_BASE_COST + (self.cloak_level * UPGRADE_CLOAK_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_cloak_upgrade(self):
        if self.cloak_level >= UPGRADE_CLOAK_MAX_LEVEL:
            return False, "Cloak already maxed"

        cost = self.get_cloak_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.cloak_level += 1
        return True, f"Cloak upgraded to L{self.cloak_level}"

    def get_cloak_capacity_seconds(self):
        return [0.0, 2.8, 4.6, 6.6, 9.0][max(0, min(UPGRADE_CLOAK_MAX_LEVEL, self.cloak_level))]

    def get_cargo_capacity_units(self):
        return [80, 120, 170, 230, 300][max(0, min(UPGRADE_CARGO_HOLD_MAX_LEVEL, self.cargo_hold_level))]

    def get_accommodations_capacity(self):
        return [0, 2, 4, 7, 10][max(0, min(UPGRADE_ACCOMMODATIONS_MAX_LEVEL, self.accommodations_level))]

    def get_engine_speed_multiplier(self):
        return [1.0, 1.08, 1.17, 1.28, 1.4][max(0, min(UPGRADE_ENGINE_TUNING_MAX_LEVEL, self.engine_tuning_level))]

    def get_cargo_hold_upgrade_cost(self):
        base_cost = UPGRADE_CARGO_HOLD_BASE_COST + (self.cargo_hold_level * UPGRADE_CARGO_HOLD_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_cargo_hold_upgrade(self):
        if self.cargo_hold_level >= UPGRADE_CARGO_HOLD_MAX_LEVEL:
            return False, "Cargo hold already maxed"

        cost = self.get_cargo_hold_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.cargo_hold_level += 1
        return True, f"Cargo hold upgraded to L{self.cargo_hold_level}"

    def get_accommodations_upgrade_cost(self):
        base_cost = UPGRADE_ACCOMMODATIONS_BASE_COST + (self.accommodations_level * UPGRADE_ACCOMMODATIONS_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_accommodations_upgrade(self):
        if self.accommodations_level >= UPGRADE_ACCOMMODATIONS_MAX_LEVEL:
            return False, "Accommodations already maxed"

        cost = self.get_accommodations_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.accommodations_level += 1
        return True, f"Accommodations upgraded to L{self.accommodations_level}"

    def get_engine_tuning_upgrade_cost(self):
        base_cost = UPGRADE_ENGINE_TUNING_BASE_COST + (self.engine_tuning_level * UPGRADE_ENGINE_TUNING_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_engine_tuning_upgrade(self):
        if self.engine_tuning_level >= UPGRADE_ENGINE_TUNING_MAX_LEVEL:
            return False, "Engine tuning already maxed"

        cost = self.get_engine_tuning_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.engine_tuning_level += 1
        return True, f"Engine tuning upgraded to L{self.engine_tuning_level}"

    def get_weapon_amp_upgrade_cost(self):
        base_cost = UPGRADE_WEAPON_AMP_BASE_COST + (self.weapon_amp_level * UPGRADE_WEAPON_AMP_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_weapon_amp_upgrade(self):
        if self.weapon_amp_level >= UPGRADE_WEAPON_AMP_MAX_LEVEL:
            return False, "Weapon amplifier already maxed"

        cost = self.get_weapon_amp_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.weapon_amp_level += 1
        return True, f"Weapon amplifier upgraded to L{self.weapon_amp_level}"

    def get_deflector_upgrade_cost(self):
        base_cost = UPGRADE_DEFLECTOR_BASE_COST + (self.deflector_booster_level * UPGRADE_DEFLECTOR_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_deflector_upgrade(self):
        if self.deflector_booster_level >= UPGRADE_DEFLECTOR_MAX_LEVEL:
            return False, "Deflector array already maxed"

        cost = self.get_deflector_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.deflector_booster_level += 1
        self.refill_deflector()
        return True, f"Deflector array upgraded to L{self.deflector_booster_level}"

    def get_missile_payload_upgrade_cost(self):
        base_cost = UPGRADE_MISSILE_PAYLOAD_BASE_COST + (self.missile_payload_level * UPGRADE_MISSILE_PAYLOAD_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_missile_payload_upgrade(self):
        if self.missile_level <= 0:
            return False, "Need missile launcher upgrade first"
        if self.missile_payload_level >= UPGRADE_MISSILE_PAYLOAD_MAX_LEVEL:
            return False, "Missile payload already maxed"

        cost = self.get_missile_payload_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.missile_payload_level += 1
        return True, f"Missile payload upgraded to L{self.missile_payload_level}"

    def get_auto_mining_upgrade_cost(self):
        base_cost = UPGRADE_AUTO_MINING_BASE_COST + (self.auto_mining_level * UPGRADE_AUTO_MINING_STEP_COST)
        return int(round(base_cost * self.upgrade_cost_multiplier))

    def buy_auto_mining_upgrade(self):
        if self.auto_mining_level >= UPGRADE_AUTO_MINING_MAX_LEVEL:
            return False, "Shipboard miners already maxed"

        cost = self.get_auto_mining_upgrade_cost()
        if self.credits < cost:
            return False, f"Need {cost} gold"

        self.credits -= cost
        self.auto_mining_level += 1
        return True, f"Shipboard miners upgraded to L{self.auto_mining_level}"

    def disable_cloak(self):
        self.cloak_active = False
        self.cloak_timer = 0.0

    def toggle_cloak(self):
        if self.cloak_level <= 0:
            return False, "Need cloak upgrade"
        if self.cloak_active:
            self.disable_cloak()
            return True, "Cloak disengaged"

        self.cloak_active = True
        self.cloak_timer = self.get_cloak_capacity_seconds()
        return True, f"Cloak engaged ({self.cloak_timer:.1f}s)"

    def get_lock_cone_degrees(self):
        if self.targeting_computer_level <= 0:
            return 0.0
        return [0.0, 10.0, 16.0, 24.0][self.targeting_computer_level]

    def get_lock_time_seconds(self):
        if self.targeting_computer_level <= 0:
            return 999.0
        return [999.0, 0.45, 0.28, 0.15][self.targeting_computer_level]

    def xp_needed_for_next_combat_level(self):
        lvl = max(1, int(self.combat_level))
        # Gentle early ramp, steeper later so progression remains meaningful.
        return int(60 + (lvl - 1) * 34 + ((lvl - 1) ** 2) * 7)

    def award_combat_xp(self, amount):
        gained_levels = 0
        self.combat_xp += max(0, int(amount))

        while self.combat_xp >= self.xp_needed_for_next_combat_level():
            self.combat_xp -= self.xp_needed_for_next_combat_level()
            self.combat_level += 1
            gained_levels += 1

        return gained_levels

    def get_combat_damage_multiplier(self):
        return self.get_combat_level_damage_multiplier() * self.get_weapon_amp_multiplier()

    def get_combat_level_damage_multiplier(self):
        return 1.0 + max(0, self.combat_level - 1) * 0.07

    def get_weapon_amp_multiplier(self):
        return 1.0 + self.weapon_amp_level * 0.18

    def get_combat_damage(self):
        return self.get_combat_damage_multiplier()

    def get_deflector_capacity(self):
        return self.deflector_level + self.deflector_booster_level

    def get_deflector_regen_seconds(self):
        return max(6.0, self.DEFLECTOR_REGEN_SECONDS - self.deflector_booster_level * 1.25)

    def get_missile_payload_multiplier(self):
        return 1.0 + self.missile_payload_level * 0.14

    def get_missile_damage(self):
        base_damage = 1.7 + self.missile_level * 0.7
        return base_damage * self.get_combat_damage_multiplier() * self.get_missile_payload_multiplier()

    def get_missile_splash_radius(self):
        return 60 + self.missile_level * 12 + self.missile_payload_level * 8

    def get_auto_mining_drone_count(self):
        if self.auto_mining_level <= 0:
            return 0
        return 1 if self.auto_mining_level < 3 else 2

    def get_auto_mining_range(self):
        if self.auto_mining_level <= 0:
            return 0.0
        return 125.0 + self.auto_mining_level * 36.0

    def get_auto_mining_harvest_rate(self):
        if self.auto_mining_level <= 0:
            return 0.0
        return 0.34 + self.auto_mining_level * 0.10

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

        for lvl in range(self.missile_level, UPGRADE_MISSILE_MAX_LEVEL):
            base_cost = UPGRADE_MISSILE_BASE_COST + (lvl * UPGRADE_MISSILE_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.cloak_level, UPGRADE_CLOAK_MAX_LEVEL):
            base_cost = UPGRADE_CLOAK_BASE_COST + (lvl * UPGRADE_CLOAK_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.cargo_hold_level, UPGRADE_CARGO_HOLD_MAX_LEVEL):
            base_cost = UPGRADE_CARGO_HOLD_BASE_COST + (lvl * UPGRADE_CARGO_HOLD_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.accommodations_level, UPGRADE_ACCOMMODATIONS_MAX_LEVEL):
            base_cost = UPGRADE_ACCOMMODATIONS_BASE_COST + (lvl * UPGRADE_ACCOMMODATIONS_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.engine_tuning_level, UPGRADE_ENGINE_TUNING_MAX_LEVEL):
            base_cost = UPGRADE_ENGINE_TUNING_BASE_COST + (lvl * UPGRADE_ENGINE_TUNING_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.weapon_amp_level, UPGRADE_WEAPON_AMP_MAX_LEVEL):
            base_cost = UPGRADE_WEAPON_AMP_BASE_COST + (lvl * UPGRADE_WEAPON_AMP_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.deflector_booster_level, UPGRADE_DEFLECTOR_MAX_LEVEL):
            base_cost = UPGRADE_DEFLECTOR_BASE_COST + (lvl * UPGRADE_DEFLECTOR_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        if self.missile_level > 0:
            for lvl in range(self.missile_payload_level, UPGRADE_MISSILE_PAYLOAD_MAX_LEVEL):
                base_cost = UPGRADE_MISSILE_PAYLOAD_BASE_COST + (lvl * UPGRADE_MISSILE_PAYLOAD_STEP_COST)
                needed += int(round(base_cost * cost_multiplier))

        for lvl in range(self.auto_mining_level, UPGRADE_AUTO_MINING_MAX_LEVEL):
            base_cost = UPGRADE_AUTO_MINING_BASE_COST + (lvl * UPGRADE_AUTO_MINING_STEP_COST)
            needed += int(round(base_cost * cost_multiplier))

        return needed

    def refill_shields(self):
        self.shield_layers = self.shield_level
        self.shield_regen_timer = 0.0
        self.refill_deflector()

    def refill_deflector(self):
        self.deflector_layers = self.get_deflector_capacity()
        self.deflector_regen_timer = 0.0

    def absorb_hit(self):
        if self.shield_layers > 0:
            self.shield_layers -= 1
            self.shield_regen_timer = 0.0
            return True
        return False

    def absorb_deflector_hit(self):
        if self.deflector_layers <= 0:
            return False
        self.deflector_layers -= 1
        self.deflector_regen_timer = 0.0
        return True

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

        if self.deflector_layers > 0:
            deflector_pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.01)
            deflector_color = (
                min(255, int(220 * deflector_pulse)),
                min(255, int(208 * deflector_pulse)),
                120,
            )
            deflector_radius = int(self.radius + 5 + max(0, self.get_deflector_capacity() - 1) * 2)
            pygame.draw.circle(
                screen,
                deflector_color,
                (int(center.x), int(center.y)),
                deflector_radius,
                1,
            )
            if self.get_deflector_capacity() > 1:
                for index in range(self.deflector_layers):
                    angle = (pygame.time.get_ticks() * 0.06) + (360.0 / self.deflector_layers) * index
                    pip_pos = center + pygame.Vector2(deflector_radius + 5, 0).rotate(angle)
                    pygame.draw.circle(screen, deflector_color, (int(pip_pos.x), int(pip_pos.y)), 2)

        if self.shield_level > 0:
            shield_ratio = 0.0
            shield_ratio = self.shield_layers / float(self.shield_level)
            pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() * 0.008)
            alpha_scale = 0.35 + 0.65 * max(0.15, shield_ratio)
            shield_color = (
                min(255, int(72 + 90 * pulse)),
                min(255, int(180 + 45 * pulse)),
                255,
            )

            base_radius = self.radius + 7
            ring_gap = 4
            for layer_index in range(self.shield_level):
                ring_radius = int(base_radius + layer_index * ring_gap)
                ring_active = layer_index < self.shield_layers
                ring_pulse = 0.72 + 0.28 * math.sin((pygame.time.get_ticks() * 0.008) + layer_index * 0.55)
                if ring_active:
                    ring_color = (
                        min(255, int(shield_color[0] * ring_pulse)),
                        min(255, int(shield_color[1] * ring_pulse)),
                        shield_color[2],
                    )
                    ring_width = 2 if layer_index < self.shield_layers - 1 else 3
                else:
                    ring_color = (42, 84, 122)
                    ring_width = 1
                pygame.draw.circle(
                    screen,
                    ring_color,
                    (int(center.x), int(center.y)),
                    ring_radius,
                    ring_width,
                )

            shield_radius = int(base_radius + max(0, self.shield_level - 1) * ring_gap)

            if self.shield_layers > 0:
                orbit_radius = shield_radius + 6
                pip_count = self.shield_layers
                for index in range(pip_count):
                    angle = (pygame.time.get_ticks() * 0.08) + (360.0 / pip_count) * index
                    pip_pos = center + pygame.Vector2(orbit_radius, 0).rotate(angle)
                    pip_color = (
                        int(shield_color[0] * alpha_scale),
                        int(shield_color[1] * alpha_scale),
                        shield_color[2],
                    )
                    pygame.draw.circle(screen, pip_color, (int(pip_pos.x), int(pip_pos.y)), 3)

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def move(self, dt):
        unit_vector = pygame.Vector2(0, 1)
        rotated_vector = unit_vector.rotate(self.rotation)
        rotated_with_speed_vector = rotated_vector * PLAYER_SPEED * self.get_engine_speed_multiplier() * dt
        self.position += rotated_with_speed_vector

    def shoot(self):
        if self.shoot_timer > 0:
            return

        if self.cloak_active:
            self.disable_cloak()

        self.shoot_timer = self.shoot_cooldown
        for spread in self.multishot_pattern():
            shot = Shot(self.position.x, self.position.y, SHOT_RADIUS, owner="player")
            shot.velocity = (
                pygame.Vector2(0, 1).rotate(self.rotation + spread) * PLAYER_SHOOT_SPEED
            )
        if self.on_shoot is not None:
            self.on_shoot()

    def shoot_missile(self):
        if self.missile_level <= 0 or self.missile_timer > 0.0:
            return False

        if self.cloak_active:
            self.disable_cloak()

        self.missile_timer = self.missile_cooldown_seconds()
        shot = Shot(self.position.x, self.position.y, SHOT_RADIUS + 2, owner="player_missile")
        shot.velocity = pygame.Vector2(0, 1).rotate(self.rotation) * (PLAYER_SHOOT_SPEED * 0.8)
        return True

    def update(self, dt, *args):
        self.shoot_timer -= dt
        self.missile_timer = max(0.0, self.missile_timer - dt)
        if self.cloak_active:
            self.cloak_timer = max(0.0, self.cloak_timer - dt)
            if self.cloak_timer <= 0.0:
                self.disable_cloak()

        max_deflector_layers = self.get_deflector_capacity()
        if max_deflector_layers > 0 and self.deflector_layers < max_deflector_layers:
            self.deflector_regen_timer += dt
            if self.deflector_regen_timer >= self.get_deflector_regen_seconds():
                self.deflector_layers = max_deflector_layers
                self.deflector_regen_timer = 0.0

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
        left_pressed = keys[pygame.K_LEFT] or self.virtual_controls["left"]
        right_pressed = keys[pygame.K_RIGHT] or self.virtual_controls["right"]
        up_pressed = keys[pygame.K_UP] or self.virtual_controls["up"]
        down_pressed = keys[pygame.K_DOWN] or self.virtual_controls["down"]
        warp_pressed = keys[pygame.K_w] or self.virtual_controls["warp"]
        fire_pressed = keys[pygame.K_SPACE] or self.virtual_controls["fire"]

        touch_turn_scale = 1.45 if (self.virtual_controls["left"] or self.virtual_controls["right"]) else 1.0
        touch_thrust_scale = 1.3 if (self.virtual_controls["up"] or self.virtual_controls["down"]) else 1.0

        if self.warp_drive_level > 0:
            warp_capacity = self.get_warp_capacity_seconds()
            if warp_pressed and self.warp_energy > 0.0:
                self.warp_boosting = True
                self.warp_energy = max(0.0, self.warp_energy - dt)
            else:
                self.warp_boosting = False
                self.warp_energy = min(warp_capacity, self.warp_energy + dt * 0.62)
        else:
            self.warp_boosting = False
            self.warp_energy = 0.0

        if left_pressed:
            self.rotate(-dt * touch_turn_scale)
        if right_pressed:
            self.rotate(dt * touch_turn_scale)
        if self.warp_boosting:
            self.move(dt * self.get_warp_speed_multiplier())
        elif up_pressed:
            self.move(dt * touch_thrust_scale)
        if down_pressed:
            self.move(-dt * touch_thrust_scale)
        if fire_pressed:
            self.shoot()

        self.wrap_around_screen()
