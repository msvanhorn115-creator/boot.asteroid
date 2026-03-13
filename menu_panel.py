import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from ui_theme import UI_COLORS, draw_button, draw_close_button, draw_panel, draw_tag


def draw_menu_panel(
    screen,
    game_state,
    has_active_game,
    selected_difficulty,
    menu_ui,
    difficulty_settings,
    title_font,
    panel_font,
    hud_font,
    music_loaded,
    music_driver,
    music_error,
    show_controls_overlay,
    show_audio_overlay,
    music_muted,
    music_volume,
    sfx_muted,
    sfx_volume,
):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((2, 6, 14, 198))
    screen.blit(overlay, (0, 0))

    menu_panel = pygame.Rect(SCREEN_WIDTH // 2 - 350, SCREEN_HEIGHT // 2 - 280, 700, 560)
    draw_panel(screen, menu_panel, border_color=UI_COLORS["panel_border_hot"])
    menu_ui["close"] = pygame.Rect(menu_panel.right - 54, menu_panel.y + 16, 34, 34)
    draw_close_button(screen, menu_ui["close"])

    accent_bar = pygame.Rect(menu_panel.x + 20, menu_panel.y + 20, menu_panel.width - 40, 6)
    pygame.draw.rect(screen, UI_COLORS["accent_alt"], accent_bar, border_radius=3)

    title_text = "Paused" if game_state == "paused" else "Asteroid Miner"
    subtitle_text = "" if game_state == "paused" else "Select difficulty and start"

    title_surface = title_font.render(title_text, True, UI_COLORS["text"])
    screen.blit(title_surface, (menu_panel.centerx - title_surface.get_width() // 2, menu_panel.y + 40))

    if subtitle_text:
        subtitle_surface = hud_font.render(subtitle_text, True, UI_COLORS["muted"])
        screen.blit(subtitle_surface, (menu_panel.centerx - subtitle_surface.get_width() // 2, menu_panel.y + 108))

    if music_loaded:
        menu_music_hint = hud_font.render("BGM active", True, UI_COLORS["ok"])
        screen.blit(menu_music_hint, (menu_panel.centerx - menu_music_hint.get_width() // 2, menu_panel.y + 132))
        if music_driver:
            menu_music_drv = hud_font.render(f"Driver: {music_driver}", True, UI_COLORS["muted"])
            screen.blit(menu_music_drv, (menu_panel.centerx - menu_music_drv.get_width() // 2, menu_panel.y + 152))
    else:
        menu_music_hint = hud_font.render("Drop assets/audio/arcade_loop.* for BGM", True, UI_COLORS["muted"])
        screen.blit(menu_music_hint, (menu_panel.centerx - menu_music_hint.get_width() // 2, menu_panel.y + 120))
        if music_error:
            menu_music_err = hud_font.render(music_error, True, UI_COLORS["warn"])
            screen.blit(menu_music_err, (menu_panel.centerx - menu_music_err.get_width() // 2, menu_panel.y + 142))

    for key in ("easy", "normal", "hard"):
        rect = menu_ui[key]
        active = selected_difficulty == key
        draw_button(
            screen,
            rect,
            difficulty_settings[key]["label"],
            panel_font,
            active=active,
            tone="accent" if active else "alt",
        )

    preview = difficulty_settings[selected_difficulty]
    summary_lines = [
        f"Asteroids {preview['asteroid_speed']:.2f}x speed | spawn {preview['asteroid_spawn']:.2f}s",
        f"Enemies {preview['enemy_speed']:.2f}x speed, HP {preview['enemy_health']:.2f}x",
        f"Metal value {preview['sell_multiplier']:.2f}x | drops {preview['drop_rate']:.2f}x",
        (
            f"AI agg {preview.get('ai_aggression', 1.0):.2f} | acc {preview.get('ai_accuracy', 1.0):.2f} | "
            f"fire {preview.get('ai_fire_intent', 1.0):.2f}"
        ),
    ]
    summary_y = menu_panel.y + 276
    for idx, line in enumerate(summary_lines):
        text = hud_font.render(line, True, UI_COLORS["muted"])
        screen.blit(text, (menu_panel.x + 112, summary_y + idx * 20))

    draw_tag(screen, menu_panel.x + 112, menu_panel.y + 248, "Difficulty Profile", hud_font, tone="accent")

    action_label = "Resume" if has_active_game else "New Game"
    draw_button(screen, menu_ui["action"], action_label, panel_font, active=True, tone="accent")
    draw_button(screen, menu_ui["quit"], "Quit", panel_font, active=False, tone="accent")

    controls_label = "Hide Controls" if show_controls_overlay else "Controls"
    draw_button(screen, menu_ui["controls"], controls_label, hud_font, active=show_controls_overlay, tone="alt")

    audio_label = "Hide Audio" if show_audio_overlay else "Audio"
    draw_button(screen, menu_ui["audio"], audio_label, hud_font, active=show_audio_overlay, tone="alt")

    helper_text = hud_font.render("Use the top tabs or Tab / Shift+Tab to switch panels", True, UI_COLORS["muted"])
    screen.blit(helper_text, (menu_panel.centerx - helper_text.get_width() // 2, menu_panel.y + 488))

    if has_active_game and game_state == "menu":
        hint = hud_font.render("You already have a run in memory.", True, UI_COLORS["muted"])
        screen.blit(hint, (menu_panel.x + 182, menu_panel.y + 360))

    if show_controls_overlay:
        controls_panel = pygame.Rect(menu_panel.x - 320, menu_panel.y + 20, 290, 520)
        draw_panel(screen, controls_panel, border_color=UI_COLORS["accent_alt"], fill_key="panel_soft")
        controls_title = panel_font.render("Controls", True, UI_COLORS["accent_alt"])
        screen.blit(controls_title, (controls_panel.x + 84, controls_panel.y + 14))

        grouped_controls = [
            (
                "Flight",
                [
                    "Left/Right: Rotate",
                    "Up/Down: Thrust / Reverse",
                    "W: Sublight boost",
                    "V: Toggle cloak",
                ],
            ),
            (
                "Combat",
                [
                    "Space: Shoot",
                    "F: Fire missile",
                    "T: Targeting computer",
                    "C: Claim nearby site",
                ],
            ),
            (
                "Menus and Tabs",
                [
                    "Esc: Pause / Resume",
                    "M: Map tab",
                    "I: Cargo tab",
                    "S: Status tab",
                    "B: Build tab",
                    "E: Station dock / Planet trade",
                ],
            ),
            (
                "Touch and Parity",
                [
                    "Touch MAP/PAUSE mirror M/Esc",
                    "Build and interact buttons mirror B/E",
                    "Mouse/touch can activate station and planet buttons",
                    "Tab / Shift+Tab cycle Pause, Map, Cargo, Status, Build",
                ],
            ),
            (
                "Dev",
                [
                    "D: Dev god mode",
                ],
            ),
        ]

        y = controls_panel.y + 52
        for section_title, lines in grouped_controls:
            header_surface = hud_font.render(section_title, True, UI_COLORS["accent"])
            screen.blit(header_surface, (controls_panel.x + 12, y))
            y += 22
            for line in lines:
                line_surface = hud_font.render(line, True, UI_COLORS["muted"])
                screen.blit(line_surface, (controls_panel.x + 20, y))
                y += 20
            y += 8

    if show_audio_overlay:
        audio_panel = pygame.Rect(menu_panel.right + 16, menu_panel.y + 56, 280, 230)
        draw_panel(screen, audio_panel, border_color=UI_COLORS["accent_alt"], fill_key="panel_soft")
        audio_title = panel_font.render("Audio", True, UI_COLORS["accent_alt"])
        screen.blit(audio_title, (audio_panel.x + 96, audio_panel.y + 16))

        music_text = hud_font.render(
            f"Music: {'Muted' if music_muted else str(int(music_volume * 100)) + '%'}",
            True,
            UI_COLORS["muted"],
        )
        screen.blit(music_text, (audio_panel.x + 14, audio_panel.y + 38))
        sfx_text = hud_font.render(
            f"SFX: {'Muted' if sfx_muted else str(int(sfx_volume * 100)) + '%'}",
            True,
            UI_COLORS["muted"],
        )
        screen.blit(sfx_text, (audio_panel.x + 14, audio_panel.y + 132))

        for key, value in (("music_slider", music_volume), ("sfx_slider", sfx_volume)):
            rect = menu_ui[key]
            pygame.draw.rect(screen, UI_COLORS["button"], rect, border_radius=8)
            pygame.draw.rect(screen, UI_COLORS["accent_alt"], rect, 2, border_radius=8)

            fill_width = int(rect.width * max(0.0, min(1.0, value)))
            if fill_width > 0:
                fill_rect = pygame.Rect(rect.x, rect.y, fill_width, rect.height)
                pygame.draw.rect(screen, UI_COLORS["accent_alt"], fill_rect, border_radius=8)

            knob_x = rect.x + fill_width
            knob_x = max(rect.x, min(rect.right, knob_x))
            pygame.draw.circle(screen, UI_COLORS["accent"], (knob_x, rect.y + rect.height // 2), 8)
