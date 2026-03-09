import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH


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
    show_map_overlay,
    music_muted,
    music_volume,
    sfx_muted,
    sfx_volume,
):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))
    screen.blit(overlay, (0, 0))

    menu_panel = pygame.Rect(SCREEN_WIDTH // 2 - 350, SCREEN_HEIGHT // 2 - 280, 700, 560)
    pygame.draw.rect(screen, "#111827", menu_panel)
    pygame.draw.rect(screen, "#f6d365", menu_panel, 2)

    title_text = "Paused" if game_state == "paused" else "Asteroid Miner"
    subtitle_text = "Esc again quits" if game_state == "paused" else "Select difficulty and start"

    title_surface = title_font.render(title_text, True, "white")
    screen.blit(title_surface, (menu_panel.centerx - title_surface.get_width() // 2, menu_panel.y + 40))

    subtitle_surface = hud_font.render(subtitle_text, True, "#cbd5e1")
    screen.blit(subtitle_surface, (menu_panel.centerx - subtitle_surface.get_width() // 2, menu_panel.y + 108))

    if music_loaded:
        menu_music_hint = hud_font.render("BGM active", True, "#a6e3a1")
        screen.blit(menu_music_hint, (menu_panel.centerx - menu_music_hint.get_width() // 2, menu_panel.y + 132))
        if music_driver:
            menu_music_drv = hud_font.render(f"Driver: {music_driver}", True, "#94a3b8")
            screen.blit(menu_music_drv, (menu_panel.centerx - menu_music_drv.get_width() // 2, menu_panel.y + 152))
    else:
        menu_music_hint = hud_font.render("Drop assets/audio/arcade_loop.* for BGM", True, "#94a3b8")
        screen.blit(menu_music_hint, (menu_panel.centerx - menu_music_hint.get_width() // 2, menu_panel.y + 120))
        if music_error:
            menu_music_err = hud_font.render(music_error, True, "#fca5a5")
            screen.blit(menu_music_err, (menu_panel.centerx - menu_music_err.get_width() // 2, menu_panel.y + 142))

    for key in ("easy", "normal", "hard"):
        rect = menu_ui[key]
        active = selected_difficulty == key
        border = "#f6d365" if active else "#60748a"
        fill = "#1f2937" if active else "#111827"
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, border, rect, 2)
        label = panel_font.render(difficulty_settings[key]["label"], True, border)
        screen.blit(label, (rect.x + 16, rect.y + 8))

    preview = difficulty_settings[selected_difficulty]
    summary_lines = [
        f"Asteroids {preview['asteroid_speed']:.2f}x speed | spawn {preview['asteroid_spawn']:.2f}s",
        f"Enemies {preview['enemy_speed']:.2f}x speed, HP {preview['enemy_health']:.2f}x",
        f"Metal value {preview['sell_multiplier']:.2f}x | drops {preview['drop_rate']:.2f}x",
    ]
    for idx, line in enumerate(summary_lines):
        text = hud_font.render(line, True, "#cbd5e1")
        screen.blit(text, (menu_panel.x + 112, menu_panel.y + 278 + idx * 20))

    action_label = "Resume" if has_active_game else "New Game"
    pygame.draw.rect(screen, "#1f2937", menu_ui["action"])
    pygame.draw.rect(screen, "#f6d365", menu_ui["action"], 2)
    action_surface = panel_font.render(action_label, True, "#f6d365")
    screen.blit(
        action_surface,
        (
            menu_ui["action"].centerx - action_surface.get_width() // 2,
            menu_ui["action"].centery - action_surface.get_height() // 2,
        ),
    )

    pygame.draw.rect(screen, "#1f2937", menu_ui["quit"])
    pygame.draw.rect(screen, "#f6d365", menu_ui["quit"], 2)
    quit_surface = panel_font.render("Quit", True, "#f6d365")
    screen.blit(
        quit_surface,
        (
            menu_ui["quit"].centerx - quit_surface.get_width() // 2,
            menu_ui["quit"].centery - quit_surface.get_height() // 2,
        ),
    )

    pygame.draw.rect(screen, "#1f2937", menu_ui["controls"])
    pygame.draw.rect(screen, "#f6d365", menu_ui["controls"], 2)
    controls_label = "Hide Controls" if show_controls_overlay else "Controls"
    controls_surface = hud_font.render(controls_label, True, "#f6d365")
    screen.blit(
        controls_surface,
        (
            menu_ui["controls"].centerx - controls_surface.get_width() // 2,
            menu_ui["controls"].centery - controls_surface.get_height() // 2,
        ),
    )

    pygame.draw.rect(screen, "#1f2937", menu_ui["audio"])
    pygame.draw.rect(screen, "#f6d365", menu_ui["audio"], 2)
    audio_label = "Hide Audio" if show_audio_overlay else "Audio"
    audio_surface = hud_font.render(audio_label, True, "#f6d365")
    screen.blit(
        audio_surface,
        (
            menu_ui["audio"].centerx - audio_surface.get_width() // 2,
            menu_ui["audio"].centery - audio_surface.get_height() // 2,
        ),
    )

    pygame.draw.rect(screen, "#1f2937", menu_ui["map"])
    pygame.draw.rect(screen, "#f6d365", menu_ui["map"], 2)
    map_label = "Hide Map" if show_map_overlay else "Map"
    map_surface = hud_font.render(map_label, True, "#f6d365")
    screen.blit(
        map_surface,
        (
            menu_ui["map"].centerx - map_surface.get_width() // 2,
            menu_ui["map"].centery - map_surface.get_height() // 2,
        ),
    )

    if has_active_game and game_state == "menu":
        hint = hud_font.render("You already have a run in memory.", True, "#cbd5e1")
        screen.blit(hint, (menu_panel.x + 182, menu_panel.y + 306))

    if show_controls_overlay:
        controls_panel = pygame.Rect(menu_panel.x - 300, menu_panel.y + 28, 270, 360)
        pygame.draw.rect(screen, "#0b1220", controls_panel)
        pygame.draw.rect(screen, "#f6d365", controls_panel, 2)
        controls_title = panel_font.render("Controls", True, "#f6d365")
        screen.blit(controls_title, (controls_panel.x + 62, controls_panel.y + 16))

        controls_lines = [
            "Left/Right: Rotate",
            "Up/Down: Thrust / Reverse",
            "W: Sublight boost",
            "Space: Shoot",
            "E: Station dock / Planet trade",
            "T: Targeting computer",
            "M: Sector map",
            "D: Dev god mode",
            "Mouse: Station buttons",
            "Esc: Pause / Quit from pause",
        ]
        for idx, line in enumerate(controls_lines):
            line_surface = hud_font.render(line, True, "#cbd5e1")
            screen.blit(line_surface, (controls_panel.x + 14, controls_panel.y + 74 + idx * 30))

    if show_audio_overlay:
        audio_panel = pygame.Rect(menu_panel.right + 16, menu_panel.y + 56, 280, 230)
        pygame.draw.rect(screen, "#0b1220", audio_panel)
        pygame.draw.rect(screen, "#f6d365", audio_panel, 2)
        audio_title = panel_font.render("Audio", True, "#f6d365")
        screen.blit(audio_title, (audio_panel.x + 96, audio_panel.y + 16))

        music_text = hud_font.render(
            f"Music: {'Muted' if music_muted else str(int(music_volume * 100)) + '%'}",
            True,
            "#cbd5e1",
        )
        screen.blit(music_text, (audio_panel.x + 14, audio_panel.y + 38))
        sfx_text = hud_font.render(
            f"SFX: {'Muted' if sfx_muted else str(int(sfx_volume * 100)) + '%'}",
            True,
            "#cbd5e1",
        )
        screen.blit(sfx_text, (audio_panel.x + 14, audio_panel.y + 132))

        for key, value in (("music_slider", music_volume), ("sfx_slider", sfx_volume)):
            rect = menu_ui[key]
            pygame.draw.rect(screen, "#1f2937", rect)
            pygame.draw.rect(screen, "#f6d365", rect, 2)

            fill_width = int(rect.width * max(0.0, min(1.0, value)))
            if fill_width > 0:
                fill_rect = pygame.Rect(rect.x, rect.y, fill_width, rect.height)
                pygame.draw.rect(screen, "#60a5fa", fill_rect)

            knob_x = rect.x + fill_width
            knob_x = max(rect.x, min(rect.right, knob_x))
            pygame.draw.circle(screen, "#f6d365", (knob_x, rect.y + rect.height // 2), 8)
