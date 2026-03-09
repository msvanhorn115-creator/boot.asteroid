from dataclasses import dataclass

import pygame


@dataclass
class BeamLockState:
    target: object = None
    candidate: object = None
    progress: float = 0.0

    def clear(self):
        self.target = None
        self.candidate = None
        self.progress = 0.0


def beam_first_hit(
    start,
    direction,
    max_distance,
    asteroids,
    enemies,
    include_asteroids=True,
    include_enemies=True,
):
    closest_hit_distance = max_distance
    hit_point = start + direction * max_distance
    hit_found = False

    beam_end = start + direction * max_distance
    beam_vector = beam_end - start
    beam_len_sq = beam_vector.length_squared()
    if beam_len_sq <= 0:
        return hit_point, hit_found

    groups = []
    if include_asteroids:
        groups.append(asteroids)
    if include_enemies:
        groups.append(enemies)

    for group in groups:
        if not group:
            continue
        for obj in group:
            to_center = obj.position - start
            t = to_center.dot(beam_vector) / beam_len_sq
            t = max(0.0, min(1.0, t))
            closest = start + beam_vector * t
            if closest.distance_to(obj.position) <= obj.radius:
                hit_distance = start.distance_to(closest)
                if hit_distance < closest_hit_distance:
                    closest_hit_distance = hit_distance
                    hit_point = start + direction * hit_distance
                    hit_found = True

    return hit_point, hit_found


def best_enemy_lock_candidate(start, direction, max_distance, cone_degrees, enemies):
    if not enemies:
        return None

    best_enemy = None
    best_angle = 999.0
    best_distance = 999999.0

    for enemy in enemies:
        offset = enemy.position - start
        distance = offset.length()
        if distance <= 0 or distance > max_distance:
            continue

        angle = abs(direction.angle_to(offset.normalize()))
        if angle > cone_degrees * 0.5:
            continue

        if angle < best_angle or (abs(angle - best_angle) < 0.01 and distance < best_distance):
            best_angle = angle
            best_distance = distance
            best_enemy = enemy

    return best_enemy


def compute_beam_endpoint(
    start,
    direction,
    max_range,
    asteroids,
    enemies,
    computer_level,
    lock_cone,
    lock_time,
    dt,
    lock_state,
):
    if computer_level <= 0:
        lock_state.clear()
        beam_end, hit_found = beam_first_hit(start, direction, max_range, asteroids, enemies)
        return beam_end, hit_found, False, None, 0.0

    lock_candidate = best_enemy_lock_candidate(start, direction, max_range, lock_cone, enemies)

    if lock_candidate is lock_state.candidate and lock_candidate is not None:
        lock_state.progress += dt
    else:
        lock_state.candidate = lock_candidate
        lock_state.progress = 0.0

    if lock_candidate is None:
        lock_state.candidate = None
        lock_state.progress = 0.0

    if lock_candidate is not None and lock_state.progress >= lock_time:
        lock_state.target = lock_candidate

    if lock_state.target is not None:
        if not lock_state.target.alive():
            lock_state.target = None
        else:
            target_offset = lock_state.target.position - start
            if target_offset.length() > max_range:
                lock_state.target = None

    if lock_state.target is not None:
        beam_end = lock_state.target.position
        return beam_end, True, True, lock_candidate, 1.0

    beam_end = start + direction * max_range
    ratio = 0.0
    if lock_candidate is not None:
        ratio = min(1.0, lock_state.progress / max(0.01, lock_time))
    return beam_end, False, False, lock_candidate, ratio
