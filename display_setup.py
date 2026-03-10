import os

import pygame


class DisplayInitError(RuntimeError):
    def __init__(self, errors):
        super().__init__("Display initialization failed")
        self.errors = list(errors)


def init_display(screen_width, screen_height):
    screen = None
    display_errors = []
    selected_video_driver = os.environ.get("SDL_VIDEODRIVER", "")

    # Scaled+resizable keeps a fixed logical resolution while allowing desktop
    # fullscreen/maximize to fill correctly without top-left anchoring.
    window_flags = pygame.SCALED | pygame.RESIZABLE

    # Prefer SDL's default backend first so Linux window decorations (title bar,
    # close button, drag behavior) are chosen by the compositor/window manager.
    try:
        screen = pygame.display.set_mode((screen_width, screen_height), window_flags)
        selected_video_driver = pygame.display.get_driver()
    except pygame.error as exc:
        display_errors.append(f"default: {exc}")

    if screen is None:
        display_driver_order = ["x11", "wayland"]

        if selected_video_driver and selected_video_driver in display_driver_order:
            display_driver_order.remove(selected_video_driver)
            display_driver_order.insert(0, selected_video_driver)
        elif selected_video_driver:
            display_driver_order.insert(0, selected_video_driver)

        for driver in display_driver_order:
            try:
                os.environ["SDL_VIDEODRIVER"] = driver
                if pygame.display.get_init():
                    pygame.display.quit()
                pygame.display.init()
                screen = pygame.display.set_mode((screen_width, screen_height), window_flags)
                selected_video_driver = driver
                break
            except pygame.error as exc:
                display_errors.append(f"{driver}: {exc}")

    if screen is None:
        raise DisplayInitError(display_errors)

    return screen, selected_video_driver
