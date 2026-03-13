import math

import pygame


def _vec(value):
    return pygame.Vector2(value)


def draw_support_drones(screen, drone_specs=None, anchor_position=None):
    anchor = _vec(anchor_position) if anchor_position is not None else None
    for spec in drone_specs or []:
        drone_pos = _vec(spec.get("position", anchor if anchor is not None else (0, 0)))
        target_pos = spec.get("target")
        drone_color = spec.get("color", (125, 211, 252))
        if target_pos is not None:
            target_vec = _vec(target_pos)
            if anchor is not None:
                pygame.draw.line(
                    screen,
                    (70, 96, 124),
                    (int(anchor.x), int(anchor.y)),
                    (int(target_vec.x), int(target_vec.y)),
                    1,
                )
            pygame.draw.line(
                screen,
                drone_color,
                (int(drone_pos.x), int(drone_pos.y)),
                (int(target_vec.x), int(target_vec.y)),
                1,
            )
        pygame.draw.circle(screen, (16, 24, 38), (int(drone_pos.x), int(drone_pos.y)), 5)
        pygame.draw.circle(screen, drone_color, (int(drone_pos.x), int(drone_pos.y)), 4)
        pygame.draw.line(screen, (233, 239, 248), (int(drone_pos.x) - 4, int(drone_pos.y)), (int(drone_pos.x) + 4, int(drone_pos.y)), 1)
        pygame.draw.line(screen, (233, 239, 248), (int(drone_pos.x), int(drone_pos.y) - 4), (int(drone_pos.x), int(drone_pos.y) + 4), 1)


def draw_mining_platform(screen, position, hp_ratio, linked, buffered_credits, buffered_parts, elapsed_time, drone_specs=None):
    center = _vec(position)
    cx = int(center.x)
    cy = int(center.y)
    hp_ratio = max(0.0, min(1.0, float(hp_ratio)))
    pulse = 0.66 + 0.34 * (math.sin(elapsed_time * 3.8) * 0.5 + 0.5)
    ring_color = (226, 197, 92) if linked else (198, 108, 116)
    core_color = (99, 207, 255) if linked else (126, 144, 168)

    pygame.draw.circle(screen, (16, 24, 38), (cx, cy), 22)
    pygame.draw.circle(screen, ring_color, (cx, cy), 22, 2)
    pygame.draw.circle(screen, core_color, (cx, cy), 8 + int(2 * pulse))

    for angle in (20, 140, 260):
        arm = pygame.Vector2(1, 0).rotate(angle)
        arm_end = center + arm * 28
        pygame.draw.line(screen, (110, 136, 168), (cx, cy), (int(arm_end.x), int(arm_end.y)), 3)
        drill_tip = arm_end + arm.rotate(22) * 7
        pygame.draw.line(screen, ring_color, (int(arm_end.x), int(arm_end.y)), (int(drill_tip.x), int(drill_tip.y)), 2)
        pygame.draw.circle(screen, (237, 230, 179), (int(arm_end.x), int(arm_end.y)), 3)

    hp_w = 34
    hp_x = cx - hp_w // 2
    hp_y = cy + 30
    pygame.draw.rect(screen, (18, 24, 34), pygame.Rect(hp_x, hp_y, hp_w, 5), border_radius=3)
    pygame.draw.rect(screen, (120, 132, 148), pygame.Rect(hp_x, hp_y, hp_w, 5), 1, border_radius=3)
    fill_w = max(0, int((hp_w - 2) * hp_ratio))
    if fill_w > 0:
        pygame.draw.rect(screen, (106, 219, 163), pygame.Rect(hp_x + 1, hp_y + 1, fill_w, 3), border_radius=2)

    if buffered_credits > 0 or buffered_parts > 0:
        cargo_y = cy - 33
        cargo_color = (250, 216, 122) if linked else (216, 134, 144)
        pygame.draw.circle(screen, cargo_color, (cx - 12, cargo_y), 3)
        pygame.draw.circle(screen, (125, 211, 252), (cx, cargo_y), 3)
        pygame.draw.circle(screen, cargo_color, (cx + 12, cargo_y), 3)

    draw_support_drones(screen, drone_specs, anchor_position=center)


def draw_station_infrastructure(
    screen,
    station_position,
    mining_level,
    drone_level,
    turret_level,
    shield_level,
    elapsed_time,
):
    center = _vec(station_position)
    cx = int(center.x)
    cy = int(center.y)

    if mining_level > 0:
        for idx in range(mining_level):
            angle = -135 + idx * 22
            arm = pygame.Vector2(1, 0).rotate(angle)
            start = center + arm * 28
            end = center + arm * (44 + idx * 4)
            pygame.draw.line(screen, (134, 159, 186), (int(start.x), int(start.y)), (int(end.x), int(end.y)), 2)
            pygame.draw.circle(screen, (240, 208, 110), (int(end.x), int(end.y)), 4)

    if drone_level > 0:
        drone_count = max(1, min(4, drone_level + 1))
        orbit_radius = 44 + drone_level * 5
        for idx in range(drone_count):
            angle = elapsed_time * (52 + idx * 8) + idx * (360 / drone_count)
            offset = pygame.Vector2(orbit_radius, 0).rotate(angle)
            drone_pos = center + offset
            dx = int(drone_pos.x)
            dy = int(drone_pos.y)
            pygame.draw.circle(screen, (20, 28, 42), (dx, dy), 5)
            pygame.draw.circle(screen, (99, 220, 255), (dx, dy), 4)
            pygame.draw.line(screen, (223, 232, 244), (dx - 4, dy), (dx + 4, dy), 1)
            pygame.draw.line(screen, (223, 232, 244), (dx, dy - 4), (dx, dy + 4), 1)

    if turret_level > 0:
        turret_count = max(1, min(3, turret_level))
        for idx in range(turret_count):
            angle = 120 + idx * 88
            offset = pygame.Vector2(42 + idx * 4, 0).rotate(angle)
            turret_pos = center + offset
            tx = int(turret_pos.x)
            ty = int(turret_pos.y)
            pygame.draw.circle(screen, (22, 30, 46), (tx, ty), 7)
            pygame.draw.circle(screen, (224, 226, 234), (tx, ty), 7, 1)
            barrel = turret_pos + pygame.Vector2(9, 0).rotate(angle - 90)
            pygame.draw.line(screen, (233, 94, 105), (tx, ty), (int(barrel.x), int(barrel.y)), 2)

    if shield_level > 0:
        for idx in range(min(3, shield_level + 1)):
            radius = 30 + idx * 10
            alpha_color = 80 + idx * 30
            pygame.draw.circle(screen, (72, 170, min(255, alpha_color + 120)), (cx, cy), radius, 1)


def draw_defense_turret(screen, position, hp_ratio, level, elapsed_time, variant="onslaught_alpha"):
    center = _vec(position)
    cx = int(center.x)
    cy = int(center.y)
    hp_ratio = max(0.0, min(1.0, float(hp_ratio)))
    sweep = elapsed_time * 45.0

    if variant == "onslaught_barrage":
        pygame.draw.circle(screen, (18, 24, 38), (cx, cy), 17)
        pygame.draw.circle(screen, (246, 224, 164), (cx, cy), 17, 2)
        pygame.draw.circle(screen, (214, 132, 66), (cx, cy), 9)
        for fin_angle in (35, 155, 275):
            fin_tip = center + pygame.Vector2(22, 0).rotate(fin_angle)
            fin_left = center + pygame.Vector2(10, 0).rotate(fin_angle + 18)
            fin_right = center + pygame.Vector2(10, 0).rotate(fin_angle - 18)
            pygame.draw.polygon(
                screen,
                (102, 84, 62),
                ((int(fin_tip.x), int(fin_tip.y)), (int(fin_left.x), int(fin_left.y)), (int(fin_right.x), int(fin_right.y))),
            )
        for idx, offset in enumerate((-12, 0, 12)):
            barrel_angle = sweep + offset - 90
            barrel_end = center + pygame.Vector2(20 + idx, 0).rotate(barrel_angle)
            pygame.draw.line(screen, (248, 146, 60), (cx, cy), (int(barrel_end.x), int(barrel_end.y)), 2)
    else:
        pygame.draw.circle(screen, (18, 24, 38), (cx, cy), 15)
        pygame.draw.circle(screen, (232, 236, 244), (cx, cy), 15, 2)
        pygame.draw.circle(screen, (96, 168, 228), (cx, cy), 8)
        for fin_angle in (45, 135, 225, 315):
            fin_tip = center + pygame.Vector2(19, 0).rotate(fin_angle)
            fin_base = center + pygame.Vector2(12, 0).rotate(fin_angle)
            pygame.draw.line(screen, (84, 138, 194), (int(fin_base.x), int(fin_base.y)), (int(fin_tip.x), int(fin_tip.y)), 2)
        for idx, offset in enumerate((-6, 6)):
            barrel_angle = sweep + offset - 90
            barrel_end = center + pygame.Vector2(20 + idx * 2, 0).rotate(barrel_angle)
            pygame.draw.line(screen, (99, 220, 255), (cx, cy), (int(barrel_end.x), int(barrel_end.y)), 3 - min(idx, 1))

    hp_w = 26
    hp_x = cx - hp_w // 2
    hp_y = cy + 19
    pygame.draw.rect(screen, (14, 20, 30), pygame.Rect(hp_x, hp_y, hp_w, 4), border_radius=2)
    fill_w = max(0, int((hp_w - 2) * hp_ratio))
    if fill_w > 0:
        pygame.draw.rect(screen, (114, 226, 170), pygame.Rect(hp_x + 1, hp_y + 1, fill_w, 2), border_radius=2)


def draw_build_placement_preview(screen, kind, position, valid, elapsed_time):
    center = _vec(position)
    cx = int(center.x)
    cy = int(center.y)
    pulse = 0.58 + 0.42 * (math.sin(elapsed_time * 5.0) * 0.5 + 0.5)
    color = (126, 231, 135) if valid else (239, 104, 116)
    radius = {
        "station": 46,
        "platform": 28,
        "turret": 20,
    }.get(kind, 26)

    pygame.draw.circle(screen, color, (cx, cy), radius, 2)
    pygame.draw.circle(screen, color, (cx, cy), max(4, int(6 * pulse)))
    pygame.draw.line(screen, color, (cx - radius - 8, cy), (cx + radius + 8, cy), 1)
    pygame.draw.line(screen, color, (cx, cy - radius - 8), (cx, cy + radius + 8), 1)

    if kind == "station":
        pygame.draw.circle(screen, color, (cx, cy), radius - 14, 1)
    elif kind == "platform":
        for angle in (30, 150, 270):
            arm = pygame.Vector2(radius - 6, 0).rotate(angle)
            pygame.draw.line(screen, color, (cx, cy), (int(center.x + arm.x), int(center.y + arm.y)), 1)
    elif kind == "turret":
        barrel = center + pygame.Vector2(radius + 6, 0).rotate(-90)
        pygame.draw.line(screen, color, (cx, cy), (int(barrel.x), int(barrel.y)), 2)