import pygame

from resources import get_metal_color
from ui_theme import UI_COLORS, draw_button, draw_close_button, draw_panel


def _draw_metal_row(screen, x, y, metal_type, amount, font):
    metal_color = get_metal_color(metal_type)
    pygame.draw.circle(screen, (16, 24, 38), (x + 8, y + 10), 8)
    pygame.draw.circle(screen, metal_color, (x + 8, y + 10), 6)
    pygame.draw.circle(screen, (232, 238, 247), (x + 8, y + 10), 8, 1)

    label = font.render(f"{metal_type}: {amount}", True, metal_color)
    screen.blit(label, (x + 20, y + 1))


def resolve_ship_click(mouse_pos, ship_ui):
    close_rect = ship_ui.get("close")
    if close_rect and close_rect.collidepoint(mouse_pos):
        return "close"

    for key, rect in ship_ui.items():
        if not key.startswith("drop_"):
            continue
        if rect and rect.collidepoint(mouse_pos):
            return key
    return None


def draw_ship_panel(screen, panel_rect, player, active_contract, ship_ui, hud_font, panel_font):
    draw_panel(screen, panel_rect, border_color=UI_COLORS["accent_alt"])

    title = panel_font.render("Cargo", True, UI_COLORS["text"])
    screen.blit(title, (panel_rect.x + 20, panel_rect.y + 16))
    ship_ui["close"] = pygame.Rect(panel_rect.right - 54, panel_rect.y + 16, 34, 34)
    draw_close_button(screen, ship_ui["close"])
    ship_ui["drop_contract"] = None

    for key in list(ship_ui.keys()):
        if key.startswith("drop_"):
            ship_ui[key] = None

    content_rect = pygame.Rect(panel_rect.x + 24, panel_rect.y + 72, panel_rect.width - 48, panel_rect.height - 102)
    column_gap = 28
    left_col_width = max(300, min(430, (content_rect.width - column_gap) // 2))
    right_col_x = content_rect.x + left_col_width + column_gap

    carrying_passengers = 0
    carrying_cargo = 0
    if active_contract is not None:
        if active_contract.get("unit") in ("passenger", "team"):
            carrying_passengers = int(active_contract.get("amount", 0))
        else:
            carrying_cargo = int(active_contract.get("amount", 0))

    metal_units = player.total_metal_units()
    cargo_used = metal_units + carrying_cargo
    cargo_cap = player.get_cargo_capacity_units()

    summary_lines = [
        f"Cargo Capacity: {cargo_used}/{cargo_cap} units used",
        f"Metals in Hold: {metal_units}",
        f"Passengers On Board: {carrying_passengers}/{player.get_accommodations_capacity()}",
        f"Contract Cargo: {carrying_cargo}",
    ]
    for idx, line in enumerate(summary_lines):
        text = hud_font.render(line, True, UI_COLORS["text"])
        screen.blit(text, (content_rect.x, content_rect.y + idx * 24))

    hold_title = panel_font.render("Hold Contents", True, UI_COLORS["accent_alt"])
    screen.blit(hold_title, (content_rect.x, content_rect.y + 116))

    metals = [(metal_type, amount) for metal_type, amount in player.metals.items() if amount > 0]
    metals.sort(key=lambda pair: pair[1], reverse=True)
    if not metals:
        empty = hud_font.render("No metals in hold", True, UI_COLORS["muted"])
        screen.blit(empty, (content_rect.x, content_rect.y + 148))
    else:
        for idx, (metal_type, amount) in enumerate(metals):
            row_y = content_rect.y + 148 + idx * 38
            _draw_metal_row(screen, content_rect.x, row_y, metal_type, amount, hud_font)
            key = f"drop_metal:{metal_type}"
            ship_ui[key] = pygame.Rect(right_col_x, row_y - 4, 180, 30)
            draw_button(screen, ship_ui[key], f"Jettison {metal_type}", hud_font, active=True, tone="alt")

    manifest_title = panel_font.render("Manifest Actions", True, UI_COLORS["accent_alt"])
    screen.blit(manifest_title, (right_col_x, content_rect.y + 116))

    if active_contract is None:
        no_manifest = hud_font.render("No contract cargo or passengers aboard", True, UI_COLORS["muted"])
        screen.blit(no_manifest, (right_col_x, content_rect.y + 148))
        return

    unit = active_contract.get("unit", "cargo")
    amount = int(active_contract.get("amount", 0))
    mission = active_contract.get("mission", "Contract")
    manifest_lines = [
        f"Active Contract: {mission}",
        f"On Board: {amount} {unit}",
        f"Destination: {active_contract['target_type']} {active_contract['target_sector'][0]},{active_contract['target_sector'][1]}",
    ]
    for idx, line in enumerate(manifest_lines):
        text = hud_font.render(line, True, UI_COLORS["muted"])
        screen.blit(text, (right_col_x, content_rect.y + 148 + idx * 24))

    action_label = "Space Passengers" if unit in ("passenger", "team") else "Dump Contract Cargo"
    ship_ui["drop_contract"] = pygame.Rect(right_col_x, content_rect.y + 234, 220, 34)
    draw_button(screen, ship_ui["drop_contract"], action_label, hud_font, active=True, tone="accent")
