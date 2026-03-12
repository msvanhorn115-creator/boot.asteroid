import pygame

UI_COLORS = {
    "panel": (10, 10, 12, 238),
    "panel_soft": (18, 18, 22, 228),
    "panel_border": (112, 112, 124),
    "panel_border_hot": (210, 56, 68),
    "text": (236, 236, 240),
    "muted": (158, 158, 170),
    "accent": (222, 68, 78),
    "accent_alt": (224, 224, 232),
    "ok": (198, 198, 208),
    "warn": (212, 110, 118),
    "danger": (228, 66, 72),
    "button": (28, 28, 34),
    "button_hover": (44, 44, 52),
}


def draw_panel(surface, rect, border_color=None, radius=16, fill_key="panel"):
    panel_color = UI_COLORS.get(fill_key, UI_COLORS["panel"])
    border = border_color or UI_COLORS["panel_border"]

    shadow = pygame.Surface((rect.width + 12, rect.height + 12), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect(), border_radius=radius + 3)
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


def draw_close_button(surface, rect):
    pygame.draw.rect(surface, UI_COLORS["button"], rect, border_radius=10)
    pygame.draw.rect(surface, UI_COLORS["accent"], rect, 2, border_radius=10)
    font = pygame.font.Font(None, 28)
    label = font.render("X", True, UI_COLORS["accent"])
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
    pygame.draw.rect(surface, (24, 24, 30), tag_rect, border_radius=8)
    pygame.draw.rect(surface, fg, tag_rect, 1, border_radius=8)
    surface.blit(text_surface, rect.topleft)
    return tag_rect
