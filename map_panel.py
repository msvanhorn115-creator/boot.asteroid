import pygame

from ui_theme import UI_COLORS, draw_close_button, draw_panel, draw_tag


GRID_COLS = 9
GRID_ROWS = 6
GRID_GAP = 0
THUMBNAIL_CACHE = {}


def _sector_seed(sector):
    sx, sy = sector
    return ((sx * 73856093) ^ (sy * 19349663)) & 0xFFFFFFFF


def _rand01(seed, idx):
    value = (seed ^ (idx * 2654435761)) & 0xFFFFFFFF
    value = (1103515245 * value + 12345) & 0x7FFFFFFF
    return value / float(0x7FFFFFFF)


def _compute_map_layout(panel_rect):
    margin = 24
    content_top = panel_rect.y + 116
    content_bottom = panel_rect.bottom - 24
    content_h = max(180, content_bottom - content_top)

    info_w = min(360, max(250, int(panel_rect.width * 0.31)))
    grid_area_w = max(280, panel_rect.width - (margin * 3) - info_w)

    cell = max(42, min(grid_area_w // GRID_COLS, content_h // GRID_ROWS))
    grid_w = cell * GRID_COLS
    grid_h = cell * GRID_ROWS

    grid_x = panel_rect.x + margin + max(0, (grid_area_w - grid_w) // 2)
    grid_y = content_top + max(0, (content_h - grid_h) // 2)

    info_x = grid_x + grid_w + margin
    info_y = content_top + 4
    return {
        "grid_x": grid_x,
        "grid_y": grid_y,
        "cell": cell,
        "grid_w": grid_w,
        "grid_h": grid_h,
        "info_x": info_x,
        "info_y": info_y,
    }


def _thumbnail_key(rect, sector, snapshot, intel):
    charted = bool(snapshot and snapshot.get("charted", False))
    visited = bool(snapshot and snapshot.get("visited", False))
    stations = tuple(
        (round(s.get("x", 0.0), 4), round(s.get("y", 0.0), 4))
        for s in (snapshot.get("stations", []) if snapshot else [])
    )
    planets = tuple(
        (
            round(p.get("x", 0.0), 4),
            round(p.get("y", 0.0), 4),
            tuple(p.get("color", (96, 165, 250))),
        )
        for p in (snapshot.get("planets", []) if snapshot else [])
    )
    platforms = tuple(
        (round(p.get("x", 0.0), 4), round(p.get("y", 0.0), 4))
        for p in (snapshot.get("platforms", []) if snapshot else [])
    )
    enemy_points = tuple(
        (round(p.get("x", 0.0), 4), round(p.get("y", 0.0), 4))
        for p in (intel.get("enemy_points", []) if intel is not None else [])
    )
    asteroid_points = tuple(
        (round(p.get("x", 0.0), 4), round(p.get("y", 0.0), 4), int(p.get("r", 20)))
        for p in (intel.get("asteroid_points", []) if intel is not None else [])
    )
    anomalies = tuple(
        (
            str(a.get("type", "")),
            round(a.get("x", 0.0), 4),
            round(a.get("y", 0.0), 4),
            float(a.get("strength", 1.0)),
        )
        for a in (intel.get("anomalies", []) if intel is not None else [])
    )
    return (
        rect.width,
        rect.height,
        sector[0],
        sector[1],
        charted,
        visited,
        stations,
        planets,
        platforms,
        enemy_points,
        asteroid_points,
        anomalies,
    )


def _render_sector_thumbnail(rect, sector, snapshot, intel):
    thumb = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    seed = _sector_seed(sector)
    charted = bool(snapshot and snapshot.get("charted", False))
    visited = bool(snapshot and snapshot.get("visited", False))

    if not charted and intel is None:
        thumb.fill((7, 12, 24))
        return thumb

    bg = (19, 32, 52) if visited else (14, 26, 44)
    thumb.fill(bg)

    # Stars
    for i in range(12):
        px = 2 + int(_rand01(seed, 7 + i) * max(2, rect.width - 4))
        py = 2 + int(_rand01(seed, 31 + i) * max(2, rect.height - 4))
        c = 120 + int(_rand01(seed, 63 + i) * 120)
        thumb.set_at((px, py), (c, c, min(255, c + 20)))

    if snapshot:
        for planet in snapshot.get("planets", []):
            planet_x = max(0, min(rect.width - 1, int(planet.get("x", 0.5) * rect.width)))
            planet_y = max(0, min(rect.height - 1, int(planet.get("y", 0.5) * rect.height)))
            color = tuple(planet.get("color", (96, 165, 250)))
            pygame.draw.circle(thumb, color, (planet_x, planet_y), max(3, rect.width // 10))

        for station in snapshot.get("stations", []):
            station_x = max(0, min(rect.width - 1, int(station.get("x", 0.5) * rect.width)))
            station_y = max(0, min(rect.height - 1, int(station.get("y", 0.5) * rect.height)))
            station_rect = pygame.Rect(station_x - 4, station_y - 4, 8, 8)
            pygame.draw.rect(thumb, (244, 210, 125), station_rect)
            pygame.draw.rect(thumb, (250, 230, 180), station_rect, 1)

        for platform in snapshot.get("platforms", []):
            px = max(0, min(rect.width - 1, int(platform.get("x", 0.5) * rect.width)))
            py = max(0, min(rect.height - 1, int(platform.get("y", 0.5) * rect.height)))
            tri = ((px, py - 4), (px + 4, py + 3), (px - 4, py + 3))
            pygame.draw.polygon(thumb, (250, 204, 21), tri)
            pygame.draw.polygon(thumb, (253, 230, 138), tri, 1)

    # Tactical intel only appears when scanned/current intel exists.
    if intel is not None:
        for asteroid in intel.get("asteroid_points", []):
            ax = max(0, min(rect.width - 1, int(asteroid.get("x", 0.5) * rect.width)))
            ay = max(0, min(rect.height - 1, int(asteroid.get("y", 0.5) * rect.height)))
            r = max(1, min(4, int(asteroid.get("r", 20) / 16)))
            pygame.draw.circle(thumb, (186, 230, 253), (ax, ay), r)

        for enemy in intel.get("enemy_points", []):
            sx = max(0, min(rect.width - 1, int(enemy.get("x", 0.5) * rect.width)))
            sy = max(0, min(rect.height - 1, int(enemy.get("y", 0.5) * rect.height)))
            p1 = (sx, sy - 4)
            p2 = (sx - 4, sy + 3)
            p3 = (sx + 4, sy + 3)
            pygame.draw.polygon(thumb, (248, 113, 113), (p1, p2, p3))

        for anomaly in intel.get("anomalies", []):
            ax = max(0, min(rect.width - 1, int(anomaly.get("x", 0.5) * rect.width)))
            ay = max(0, min(rect.height - 1, int(anomaly.get("y", 0.5) * rect.height)))
            anomaly_type = str(anomaly.get("type", ""))
            if anomaly_type == "black_hole":
                pygame.draw.circle(thumb, (148, 163, 184), (ax, ay), 5, 1)
                pygame.draw.circle(thumb, (17, 24, 39), (ax, ay), 3)
            elif anomaly_type == "radiation_star":
                pygame.draw.circle(thumb, (253, 186, 116), (ax, ay), 3)
                pygame.draw.circle(thumb, (251, 146, 60), (ax, ay), 5, 1)
            else:
                pygame.draw.circle(thumb, (103, 232, 249), (ax, ay), 4, 1)
                pygame.draw.line(thumb, (103, 232, 249), (ax - 3, ay), (ax + 3, ay), 1)

    return thumb


def _draw_sector_thumbnail(screen, rect, sector, snapshot, intel):
    key = _thumbnail_key(rect, sector, snapshot, intel)
    if key not in THUMBNAIL_CACHE:
        THUMBNAIL_CACHE[key] = _render_sector_thumbnail(rect, sector, snapshot, intel)
    screen.blit(THUMBNAIL_CACHE[key], rect.topleft)


def _truncate_to_width(text, font, max_width):
    if font.size(text)[0] <= max_width:
        return text

    suffix = "..."
    trimmed = text
    while trimmed and font.size(trimmed + suffix)[0] > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + suffix) if trimmed else suffix


def _blit_info_line(screen, panel_rect, x, y, text_surface):
    bottom_limit = panel_rect.bottom - 20
    if y + text_surface.get_height() > bottom_limit:
        return y, False
    screen.blit(text_surface, (x, y))
    return y + text_surface.get_height() + 4, True


def _mission_color(mission):
    mission_colors = {
        "Freight": "#d2646c",
        "Charter": "#d0d0d8",
        "Priority": "#e2e2ea",
        "Survey": "#b8b8c6",
        "Courier": "#ccccd8",
        "Medical": "#c6c6d2",
        "Relief": "#cf6b73",
        "Engineering": "#c4c4d0",
        "Transport": "#d6d6e0",
        "Diplomatic": "#dcdce6",
        "Evacuation": "#d15862",
        "Science": "#bcbcc8",
    }
    return mission_colors.get(mission, "#c8c8d2")


def get_map_cells(panel_rect, active_sector, layout=None):
    cells = []
    if layout is None:
        layout = _compute_map_layout(panel_rect)

    grid_origin_x = layout["grid_x"]
    grid_origin_y = layout["grid_y"]
    cell_size = layout["cell"]
    current_x, current_y = active_sector

    for gy in range(GRID_ROWS):
        for gx in range(GRID_COLS):
            sx = current_x + (gx - GRID_COLS // 2)
            sy = current_y + (gy - GRID_ROWS // 2)
            x = grid_origin_x + gx * cell_size
            y = grid_origin_y + gy * cell_size
            rect = pygame.Rect(x, y, cell_size - GRID_GAP, cell_size - GRID_GAP)
            content_rect = rect.inflate(-2, -2)
            in_scan_range = abs(sx - current_x) <= 1 and abs(sy - current_y) <= 1
            cells.append(
                {
                    "sector": (sx, sy),
                    "rect": rect,
                    "content_rect": content_rect,
                    "in_scan_range": in_scan_range,
                    "is_current": (sx, sy) == active_sector,
                }
            )
    return cells


def map_sector_at_point(panel_rect, active_sector, point):
    layout = _compute_map_layout(panel_rect)
    for cell in get_map_cells(panel_rect, active_sector, layout):
        if cell["rect"].collidepoint(point):
            return cell["sector"]
    return None


def map_tile_parity_ok(panel_rect, active_sector):
    """Return True only when each map tile center resolves to its exact sector."""
    layout = _compute_map_layout(panel_rect)
    cells = get_map_cells(panel_rect, active_sector, layout)
    for cell in cells:
        center = cell["rect"].center
        resolved = map_sector_at_point(panel_rect, active_sector, center)
        if resolved != cell["sector"]:
            return False
    return True


def draw_map_panel(
    screen,
    panel_rect,
    active_sector,
    explored_sectors,
    scanner_level,
    active_contract,
    live_sector_intel,
    scanner_cooldown,
    title_font,
    panel_font,
    hud_font,
    sector_owner_fn=None,
    owner_label_fn=None,
    build_status_fn=None,
    raided_sectors=None,
    tactical_visible_sectors=None,
    show_close_button=False,
):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((2, 6, 14, 214))
    screen.blit(overlay, (0, 0))

    draw_panel(screen, panel_rect, border_color=UI_COLORS["accent_alt"])

    title = title_font.render("Sector Map", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 24, panel_rect.y + 18))
    if show_close_button:
        draw_close_button(screen, pygame.Rect(panel_rect.right - 54, panel_rect.y + 16, 34, 34))
    hint = hud_font.render("Click any highlighted sector to pulse-scan", True, UI_COLORS["muted"])
    screen.blit(hint, (panel_rect.x + 24, panel_rect.y + 66))
    draw_tag(screen, panel_rect.x + 24, panel_rect.y + 88, "Live Sector Miniatures", hud_font, tone="accent")

    layout = _compute_map_layout(panel_rect)
    cells = get_map_cells(panel_rect, active_sector, layout)
    grid_origin_x = layout["grid_x"]
    grid_origin_y = layout["grid_y"]
    grid_w = layout["grid_w"]
    grid_h = layout["grid_h"]
    cell_size = layout["cell"]
    grid_rect = pygame.Rect(grid_origin_x, grid_origin_y, grid_w, grid_h)
    pygame.draw.rect(screen, (10, 18, 30), grid_rect)

    # Dotted sector lines for a continuous board feel.
    for col in range(1, GRID_COLS):
        x = grid_origin_x + col * cell_size
        for seg in range(grid_origin_y, grid_origin_y + grid_h, 9):
            pygame.draw.line(screen, (225, 231, 242), (x, seg), (x, min(seg + 4, grid_origin_y + grid_h)), 1)
    for row in range(1, GRID_ROWS):
        y = grid_origin_y + row * cell_size
        for seg in range(grid_origin_x, grid_origin_x + grid_w, 9):
            pygame.draw.line(screen, (225, 231, 242), (seg, y), (min(seg + 4, grid_origin_x + grid_w), y), 1)

    for cell in cells:
        sector = cell["sector"]
        rect = cell["rect"]
        content_rect = cell["content_rect"]
        snapshot = explored_sectors.get(sector)
        intel = live_sector_intel.get(sector)
        if tactical_visible_sectors is not None and sector not in tactical_visible_sectors:
            intel = None
        owner_key = sector_owner_fn(sector) if sector_owner_fn is not None else "unknown"

        owner_tint = {
            "player": (96, 165, 250, 34),
            "crimson": (239, 68, 68, 30),
            "jade": (16, 185, 129, 30),
            "gold": (245, 158, 11, 30),
            "null": (148, 163, 184, 18),
        }.get(owner_key, (148, 163, 184, 20))
        owner_border = {
            "player": (147, 197, 253),
            "crimson": (252, 165, 165),
            "jade": (110, 231, 183),
            "gold": (253, 230, 138),
            "null": (203, 213, 225),
        }.get(owner_key, (203, 213, 225))

        _draw_sector_thumbnail(screen, content_rect, sector, snapshot, intel)
        tint = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
        tint.fill(owner_tint)
        screen.blit(tint, content_rect.topleft)

        # Hard tile border so sectors are visually discrete even with dense thumbnails.
        pygame.draw.rect(screen, owner_border, rect, 1)

        if cell["in_scan_range"]:
            pygame.draw.rect(screen, (79, 141, 226), rect, 1)

        if cell["is_current"]:
            pygame.draw.rect(screen, "#22d3ee", rect, 2)

            center = rect.center
            # Subtle beacon ring + center dot for immediate orientation.
            pygame.draw.circle(screen, (34, 211, 238), center, max(6, rect.width // 7), 1)
            pygame.draw.circle(screen, (186, 230, 253), center, 2)

            label = hud_font.render("YOU", True, (186, 230, 253))
            tag_rect = pygame.Rect(0, 0, label.get_width() + 10, label.get_height() + 4)
            tag_rect.midbottom = (rect.centerx, rect.y - 3)
            pygame.draw.rect(screen, (9, 16, 29), tag_rect, border_radius=6)
            pygame.draw.rect(screen, (34, 211, 238), tag_rect, 1, border_radius=6)
            screen.blit(label, (tag_rect.x + 5, tag_rect.y + 2))

        if intel is not None:
            ships = int(intel.get("ships", 0))
            ship_count = hud_font.render(str(ships), True, (248, 189, 189))
            screen.blit(ship_count, (rect.right - ship_count.get_width() - 3, rect.y + 3))

        if raided_sectors is not None and sector in raided_sectors:
            pygame.draw.rect(screen, (251, 113, 133), rect, 2)

    info_x = layout["info_x"]
    info_y = layout["info_y"]
    max_info_width = max(220, panel_rect.right - info_x - 20)
    info_cursor_y = info_y

    scanner_text = panel_font.render(f"Scanner L{scanner_level}", True, UI_COLORS["accent_alt"])
    info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, scanner_text)

    cooldown_text = hud_font.render(
        f"Cooldown: {max(0.0, scanner_cooldown):.1f}s",
        True,
        UI_COLORS["warn"] if scanner_cooldown > 0 else UI_COLORS["ok"],
    )
    info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, cooldown_text)

    range_text = _truncate_to_width("Scan Range: 3x3 around current sector", hud_font, max_info_width)
    info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, hud_font.render(range_text, True, UI_COLORS["muted"]))
    pulse_size = 1 if scanner_level <= 1 else (5 if scanner_level == 2 else 9)
    pulse_text = _truncate_to_width(f"Pulse Size: {pulse_size} sectors", hud_font, max_info_width)
    info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, hud_font.render(pulse_text, True, UI_COLORS["muted"]))

    legend_lines = [
        "Visited or scanned: exact station + planet snapshots",
        "Scanned: exact asteroids + seed-stable enemy contacts",
        "Scanned anomalies: black holes / radiation stars / nebula interference",
        "Mining platforms: yellow triangle markers",
    ]
    for line in legend_lines:
        line_text = _truncate_to_width(line, hud_font, max_info_width)
        info_cursor_y, drew = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, hud_font.render(line_text, True, UI_COLORS["muted"]))
        if not drew:
            break

    owner_legend = "Owner tint: Union/Crimson/Jade/Gold/Null"
    owner_legend_text = _truncate_to_width(owner_legend, hud_font, max_info_width)
    info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, hud_font.render(owner_legend_text, True, UI_COLORS["muted"]))

    if owner_label_fn is not None:
        current_owner = owner_label_fn(sector_owner_fn(active_sector))
        owner_line = _truncate_to_width(f"Current Owner: {current_owner}", hud_font, max_info_width)
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, hud_font.render(owner_line, True, "#bfdbfe"))

    if build_status_fn is not None:
        hovered = map_sector_at_point(panel_rect, active_sector, pygame.mouse.get_pos())
        target_sector = hovered if hovered is not None else active_sector
        status_text, status_color = build_status_fn(target_sector)
        status_line = _truncate_to_width(status_text, hud_font, max_info_width)
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, hud_font.render(status_line, True, status_color))

    if active_contract:
        target = active_contract["target_sector"]
        target_type = active_contract["target_type"]
        tile_distance = active_contract.get("tile_distance", 0)
        risk_rating = int(active_contract.get("risk_rating", 1))
        hazard_bonus = int(active_contract.get("hazard_bonus", 0))
        line1 = hud_font.render("Active Contract", True, "#f6d365")
        contract_line = _truncate_to_width(
            (
                f"{active_contract['mission']}: {active_contract['amount']} "
                f"{active_contract['unit']} -> {active_contract['reward']} gold"
            ),
            hud_font,
            max_info_width,
        )
        line2 = hud_font.render(
            contract_line,
            True,
            _mission_color(active_contract.get("mission")),
        )
        destination_line = _truncate_to_width(
            f"Destination: {target_type} {target[0]},{target[1]}",
            hud_font,
            max_info_width,
        )
        line3 = hud_font.render(destination_line, True, "#a5b4fc")
        dx = target[0] - active_sector[0]
        dy = target[1] - active_sector[1]
        line4 = hud_font.render(f"Distance: {tile_distance} tiles | Risk: R{risk_rating}/5", True, "#fda4af")
        line5 = hud_font.render(f"Hazard Pay: +{hazard_bonus} gold", True, "#fdba74")
        line6 = hud_font.render(f"Offset: {dx:+d}, {dy:+d}", True, "#94a3b8")
        anomaly_summary = active_contract.get("anomaly_tag_summary", "")
        line7 = None
        if anomaly_summary:
            text = _truncate_to_width(f"Anomalies: {anomaly_summary}", hud_font, max_info_width)
            line7 = hud_font.render(text, True, "#67e8f9")
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y + 4, line1)
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, line2)
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, line3)
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, line4)
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, line5)
        info_cursor_y, _ = _blit_info_line(screen, panel_rect, info_x, info_cursor_y, line6)
        if line7 is not None:
            _blit_info_line(screen, panel_rect, info_x, info_cursor_y, line7)
    else:
        no_contract = hud_font.render("No active contract", True, "#94a3b8")
        _blit_info_line(screen, panel_rect, info_x, info_cursor_y + 4, no_contract)
