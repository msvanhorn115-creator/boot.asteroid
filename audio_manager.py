import os
from pathlib import Path

import pygame


class AudioManager:
    def __init__(self, source_file_path):
        self._base_dir = Path(source_file_path).resolve().parent

        self.music_loaded = False
        self.music_muted = False
        self.sfx_muted = False
        self.all_audio_muted = False
        self.music_volume = 0.35
        self.sfx_volume = 0.5
        self.music_error = ""
        self.music_source = ""
        self.music_driver = ""
        self._sfx_sounds = {}

        self._init_audio_stack()
        self._load_sfx_bank()

    def _init_audio_stack(self):
        music_candidates = [
            self._base_dir / "assets/audio/arcade_loop.ogg",
            self._base_dir / "assets/audio/arcade_loop.mp3",
            self._base_dir / "assets/audio/arcade_loop.wav",
        ]

        mixer_init_error = None
        # Driver fallback order for Linux/WSL audio stacks.
        for driver in ("pipewire", "pulseaudio", "pulse", "alsa", "dsp", "dummy"):
            try:
                if pygame.mixer.get_init() is not None:
                    pygame.mixer.quit()
                self._set_audio_driver(driver)
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                self.music_driver = driver
                mixer_init_error = None
                break
            except pygame.error as exc:
                mixer_init_error = str(exc)

        if mixer_init_error is None:
            for candidate in music_candidates:
                if candidate.exists():
                    try:
                        pygame.mixer.music.load(str(candidate))
                        pygame.mixer.music.set_volume(self.music_volume)
                        pygame.mixer.music.play(-1)
                        self.music_loaded = True
                        self.music_source = candidate.name
                    except pygame.error as exc:
                        self.music_error = f"Music load failed: {exc}"
                    break
            if not self.music_loaded and not self.music_error:
                self.music_error = "No music file found in assets/audio"
            if self.music_driver == "dummy" and self.music_loaded:
                # Dummy driver means decode succeeds, but there is no audible output.
                self.music_error = "No audio device found (using dummy driver)"
                self.music_loaded = False
        else:
            self.music_loaded = False
            self.music_error = f"Audio init failed: {mixer_init_error}"

        if "libpulse-simple.so.0" in self.music_error or "libasound.so.2" in self.music_error:
            self.music_error = "Install audio libs: libpulse0 libasound2"

    def _set_audio_driver(self, driver):
        os.environ["SDL_AUDIODRIVER"] = driver

    def _load_sfx(self, name):
        sfx_path = self._base_dir / f"assets/audio/sfx/{name}.wav"
        if not sfx_path.exists() or pygame.mixer.get_init() is None:
            return
        try:
            sound = pygame.mixer.Sound(str(sfx_path))
            sound.set_volume(self._effective_sfx_volume())
            self._sfx_sounds[name] = sound
        except pygame.error:
            return

    def _load_sfx_bank(self):
        for sfx_name in [
            "player_shoot",
            "enemy_shoot",
            "asteroid_hit",
            "enemy_hit",
            "enemy_destroyed",
            "pickup",
            "dock",
            "sell",
            "upgrade",
            "pause",
            "ui_click",
            "player_hit",
        ]:
            self._load_sfx(sfx_name)

    def _effective_music_volume(self):
        if self.all_audio_muted or self.music_muted or self.music_volume <= 0.0:
            return 0.0
        return self.music_volume

    def _effective_sfx_volume(self):
        if self.all_audio_muted or self.sfx_muted or self.sfx_volume <= 0.0:
            return 0.0
        return self.sfx_volume

    def apply_music_volume(self):
        if pygame.mixer.get_init() is None:
            return
        pygame.mixer.music.set_volume(self._effective_music_volume())

    def apply_sfx_volume(self):
        effective = self._effective_sfx_volume()
        for sound in self._sfx_sounds.values():
            sound.set_volume(effective)

    def set_music_volume(self, value):
        self.music_volume = max(0.0, min(1.0, float(value)))
        self.music_muted = self.music_volume <= 0.001
        self.apply_music_volume()

    def set_sfx_volume(self, value):
        self.sfx_volume = max(0.0, min(1.0, float(value)))
        self.sfx_muted = self.sfx_volume <= 0.001
        self.apply_sfx_volume()

    def toggle_all_mute(self):
        self.all_audio_muted = not self.all_audio_muted
        self.apply_music_volume()
        self.apply_sfx_volume()

    def play_sfx(self, name):
        sound = self._sfx_sounds.get(name)
        if sound is not None:
            sound.play()

    def draw_toggle_icon(self, screen, button_rect):
        panel_color = (24, 30, 46, 220)
        border_color = (132, 146, 176)
        icon_color = (220, 230, 255)
        mute_slash_color = (235, 70, 70)

        icon_surface = pygame.Surface((button_rect.width, button_rect.height), pygame.SRCALPHA)
        pygame.draw.circle(
            icon_surface,
            panel_color,
            (button_rect.width // 2, button_rect.height // 2),
            button_rect.width // 2,
        )
        pygame.draw.circle(
            icon_surface,
            border_color,
            (button_rect.width // 2, button_rect.height // 2),
            button_rect.width // 2,
            2,
        )

        # Speaker silhouette.
        pygame.draw.polygon(
            icon_surface,
            icon_color,
            [(14, 24), (20, 24), (27, 18), (27, 42), (20, 36), (14, 36)],
        )

        if self.all_audio_muted:
            pygame.draw.line(icon_surface, mute_slash_color, (12, 44), (44, 12), 4)
        else:
            pygame.draw.arc(icon_surface, icon_color, pygame.Rect(25, 18, 14, 24), -0.8, 0.8, 2)
            pygame.draw.arc(icon_surface, icon_color, pygame.Rect(24, 14, 20, 32), -0.8, 0.8, 2)

        screen.blit(icon_surface, button_rect.topleft)

    def shutdown(self):
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except pygame.error:
            return
