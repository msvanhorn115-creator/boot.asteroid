import os
import sys

import pygame


class DisplayInitError(RuntimeError):
    def __init__(self, errors):
        super().__init__("Display initialization failed")
        self.errors = list(errors)


def _display_driver_order(requested_driver):
    normalized_driver = (requested_driver or "").strip().lower()

    if normalized_driver:
        ordered = [normalized_driver]
    elif sys.platform.startswith("linux"):
        # Prefer X11 first on Linux so SDL gets a decorated native window with
        # title bar controls when XWayland is available.
        ordered = ["x11", "wayland"]
    else:
        ordered = []

    for driver in ("x11", "wayland"):
        if driver not in ordered:
            ordered.append(driver)

    ordered.append("")
    return ordered


def _ensure_window_decorations():
    try:
        from pygame._sdl2.video import Window

        window = Window.from_display_module()
        window.borderless = False
    except (ImportError, pygame.error, AttributeError, TypeError):
        pass


def init_display(screen_width, screen_height):
    screen = None
    display_errors = []
    selected_video_driver = os.environ.get("SDL_VIDEODRIVER", "").strip()

    # Use a native resizable window so Linux window managers can keep standard
    # title bar controls instead of SDL's scaled renderer path.
    window_flags = pygame.RESIZABLE

    for driver in _display_driver_order(selected_video_driver):
        attempt_label = driver or "default"
        try:
            if driver:
                os.environ["SDL_VIDEODRIVER"] = driver
            else:
                os.environ.pop("SDL_VIDEODRIVER", None)

            if pygame.display.get_init():
                pygame.display.quit()
            pygame.display.init()
            screen = pygame.display.set_mode((screen_width, screen_height), window_flags)
            _ensure_window_decorations()
            selected_video_driver = pygame.display.get_driver()
            break
        except pygame.error as exc:
            display_errors.append(f"{attempt_label}: {exc}")

    if screen is None:
        raise DisplayInitError(display_errors)

    return screen, selected_video_driver
