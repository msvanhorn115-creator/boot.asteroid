import pygame

UI_COLORS = {
    "panel": (11, 18, 32, 235),
    "panel_soft": (16, 25, 40, 225),
    "panel_border": (129, 147, 183),
    "panel_border_hot": (244, 210, 125),
    "text": (232, 238, 247),
    "muted": (154, 171, 196),
    "accent": (244, 210, 125),
    "accent_alt": (94, 173, 255),
    "ok": (134, 239, 172),
    "warn": (253, 164, 175),
    "danger": (248, 113, 113),
    "button": (24, 37, 58),
    "button_hover": (34, 53, 80),
}


def draw_panel(surface, rect, border_color=None, radius=16, fill_key="panel"):
    panel_color = UI_COLORS.get(fill_key, UI_COLORS["panel"])
    border = border_color or UI_COLORS["panel_border"]

    shadow = pygame.Surface((rect.width + 12, rect.height + 12), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 80), shadow.get_rect(), border_radius=radius + 3)
    surface.blit(shadow, (rect.x + 4, rect.y + 6))

    body = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(body, panel_color, body.get_rect(), border_radius=radius)
    pygame.draw.rect(body, border, body.get_rect(), 2, border_radius=radius)
    surface.blit(body, rect.topleft)


def draw_button(surface, rect, text, font, active=False, tone="accent"):
    border = UI_COLORS["accent"] if tone == "accent" else UI_COLORS["accent_alt"]
    if active:
        fill = UI_COLORS["button_hover"]
    else:
        fill = UI_COLORS["button"]

    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, border, rect, 2, border_radius=10)
    label = font.render(text, True, border)
    surface.blit(
        label,
        (
            rect.centerx - label.get_width() // 2,
            rect.centery - label.get_height() // 2,
        ),
    )


def draw_tag(surface, x, y, text, font, tone="muted"):
    if tone == "ok":
        fg = UI_COLORS["ok"]
    elif tone == "warn":
        fg = UI_COLORS["warn"]
    elif tone == "accent":
        fg = UI_COLORS["accent"]
    else:
        fg = UI_COLORS["muted"]

    text_surface = font.render(text, True, fg)
    rect = text_surface.get_rect(topleft=(x + 8, y + 4))
    tag_rect = pygame.Rect(x, y, rect.width + 16, rect.height + 8)
    pygame.draw.rect(surface, (19, 29, 47), tag_rect, border_radius=8)
    pygame.draw.rect(surface, fg, tag_rect, 1, border_radius=8)
    surface.blit(text_surface, rect.topleft)
    return tag_rect
