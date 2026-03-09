import random

import pygame

from constants import SCREEN_HEIGHT
from resources import get_metal_color


def spawn_metal_pickup_fx(metal_pickup_fx, start_pos, mined_metals):
    target = pygame.Vector2(120, SCREEN_HEIGHT - 26)
    for metal_type, amount in mined_metals.items():
        color = get_metal_color(metal_type)
        for _ in range(amount):
            jitter = pygame.Vector2(random.uniform(-12, 12), random.uniform(-12, 12))
            start = pygame.Vector2(start_pos) + jitter
            midpoint = (start + target) * 0.5
            control = midpoint + pygame.Vector2(
                random.uniform(-70, 70),
                -random.uniform(110, 210),
            )
            for _particle in range(2):
                metal_pickup_fx.append(
                    {
                        "start": start,
                        "control": control,
                        "end": target,
                        "color": color,
                        "t": 0.0,
                        "duration": random.uniform(0.55, 0.9),
                        "radius": random.randint(7, 11),
                        "trail": [],
                    }
                )


def step_and_draw_metal_pickup_fx(screen, metal_pickup_fx, dt):
    for fx in list(metal_pickup_fx):
        fx["t"] += dt / fx["duration"]
        t = min(1.0, fx["t"])
        one_minus_t = 1.0 - t
        pos = (
            (one_minus_t * one_minus_t) * fx["start"]
            + (2 * one_minus_t * t) * fx["control"]
            + (t * t) * fx["end"]
        )

        fx["trail"].append(pos)
        if len(fx["trail"]) > 5:
            fx["trail"].pop(0)

        for idx, trail_pos in enumerate(fx["trail"]):
            fade = (idx + 1) / len(fx["trail"])
            trail_radius = max(2, int(fx["radius"] * 0.6 * fade))
            trail_color = (
                int(fx["color"][0] * 0.7),
                int(fx["color"][1] * 0.7),
                int(fx["color"][2] * 0.7),
            )
            pygame.draw.circle(
                screen,
                trail_color,
                (int(trail_pos.x), int(trail_pos.y)),
                trail_radius,
            )

        draw_radius = max(1, int(fx["radius"] * (1.0 - 0.35 * t)))
        glow_radius = draw_radius + 5
        glow_color = (
            min(255, fx["color"][0] + 35),
            min(255, fx["color"][1] + 35),
            min(255, fx["color"][2] + 35),
        )
        pygame.draw.circle(screen, glow_color, (int(pos.x), int(pos.y)), glow_radius)
        pygame.draw.circle(screen, fx["color"], (int(pos.x), int(pos.y)), draw_radius)

        if t >= 1.0:
            metal_pickup_fx.remove(fx)


def spawn_ship_explosion_fx(ship_explosion_fx, center, radius, base_color, burst_scale=1.0):
    color = pygame.Color(base_color)
    center_vec = pygame.Vector2(center)

    fragment_count = max(4, int(6 * burst_scale))
    for _ in range(fragment_count):
        angle = random.uniform(0, 360)
        speed = random.uniform(110, 280) * burst_scale
        velocity = pygame.Vector2(1, 0).rotate(angle) * speed
        ship_explosion_fx.append(
            {
                "kind": "fragment",
                "pos": center_vec.copy(),
                "vel": velocity,
                "life": random.uniform(0.35, 0.72),
                "max_life": random.uniform(0.35, 0.72),
                "size": random.uniform(radius * 0.25, radius * 0.55),
                "rotation": random.uniform(0, 360),
                "spin": random.uniform(-500, 500),
                "color": color,
            }
        )

    spark_count = max(10, int(18 * burst_scale))
    for _ in range(spark_count):
        angle = random.uniform(0, 360)
        speed = random.uniform(120, 420) * burst_scale
        velocity = pygame.Vector2(1, 0).rotate(angle) * speed
        spark_color = pygame.Color(
            min(255, color.r + random.randint(20, 65)),
            min(255, color.g + random.randint(20, 65)),
            min(255, color.b + random.randint(20, 65)),
        )
        ship_explosion_fx.append(
            {
                "kind": "spark",
                "pos": center_vec.copy(),
                "vel": velocity,
                "life": random.uniform(0.2, 0.5),
                "max_life": random.uniform(0.2, 0.5),
                "size": random.uniform(2.0, 4.0),
                "rotation": 0.0,
                "spin": 0.0,
                "color": spark_color,
            }
        )


def update_ship_explosion_fx(ship_explosion_fx, delta_time):
    for fx in list(ship_explosion_fx):
        fx["life"] -= delta_time
        if fx["life"] <= 0:
            ship_explosion_fx.remove(fx)
            continue

        fx["pos"] += fx["vel"] * delta_time
        fx["vel"] *= 0.985
        fx["rotation"] += fx["spin"] * delta_time


def draw_ship_explosion_fx(target, ship_explosion_fx):
    for fx in ship_explosion_fx:
        life_ratio = max(0.0, min(1.0, fx["life"] / fx["max_life"]))
        color = (
            int(fx["color"].r * life_ratio),
            int(fx["color"].g * life_ratio),
            int(fx["color"].b * life_ratio),
        )
        pos = fx["pos"]

        if fx["kind"] == "fragment":
            direction = pygame.Vector2(1, 0).rotate(fx["rotation"])
            half = direction * fx["size"]
            start = pos - half
            end = pos + half
            pygame.draw.line(
                target,
                color,
                (int(start.x), int(start.y)),
                (int(end.x), int(end.y)),
                2,
            )
        else:
            draw_radius = max(1, int(fx["size"] * life_ratio))
            pygame.draw.circle(target, color, (int(pos.x), int(pos.y)), draw_radius)
