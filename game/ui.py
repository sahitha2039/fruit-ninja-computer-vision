"""
ui.py
-----
Heads-up display, menu screens, and game-over screen.

All drawing is done on a passed *surface* so this module remains
stateless and can be called from the main loop without holding a
reference to the display.
"""
from __future__ import annotations

import pygame


# ---------------------------------------------------------------------------
# Colours & constants
# ---------------------------------------------------------------------------

_BLACK      = (  0,   0,   0)
_WHITE      = (255, 255, 255)
_YELLOW     = (255, 220,  40)
_ORANGE     = (255, 140,  20)
_RED        = (220,  50,  50)
_CYAN       = ( 80, 220, 255)
_DARK       = ( 20,  20,  40)
_SEMI       = ( 0,    0,   0, 140)   # semi-transparent panel fill

_HEART  = "♥"
_SKULL  = "💀"


# ---------------------------------------------------------------------------
# Score popup (floating +N text)
# ---------------------------------------------------------------------------

class ScorePopup:
    """Floating score text that rises and fades."""

    def __init__(self, x: float, y: float, text: str, color=(255, 220, 40)):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.age = 0.0
        self.lifespan = 0.9

    @property
    def alive(self) -> bool:
        return self.age < self.lifespan

    def update(self, dt: float):
        self.y -= 60 * dt   # float upward
        self.age += dt

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        alpha = int(255 * max(0, 1.0 - self.age / self.lifespan))
        txt_surf = font.render(self.text, True, self.color)
        txt_surf.set_alpha(alpha)
        surface.blit(txt_surf, (int(self.x), int(self.y)))


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class UI:
    """Draws all UI elements onto the given surface."""

    def __init__(self, width: int, height: int):
        self.width  = width
        self.height = height

        pygame.font.init()

        # Font sizes
        self._font_xl  = self._load_font(72)
        self._font_lg  = self._load_font(48)
        self._font_md  = self._load_font(32)
        self._font_sm  = self._load_font(22)
        self._font_xs  = self._load_font(16)
        self._font_combo = self._load_font(56, bold=True)

        # Score popups
        self.popups: list[ScorePopup] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
        candidates = ["Arial", "Helvetica", "FreeSans", "DejaVuSans"]
        for name in candidates:
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                return f
            except Exception:
                continue
        return pygame.font.Font(None, size)

    def _blit_centered(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        y: int,
        color=_WHITE,
        shadow: bool = True,
    ):
        if shadow:
            sh = font.render(text, True, _BLACK)
            sh_rect = sh.get_rect(centerx=self.width // 2, top=y + 2)
            surface.blit(sh, sh_rect)

        txt = font.render(text, True, color)
        rect = txt.get_rect(centerx=self.width // 2, top=y)
        surface.blit(txt, rect)

    def _draw_panel(
        self,
        surface: pygame.Surface,
        x: int, y: int, w: int, h: int,
        radius: int = 16,
    ):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        pygame.draw.rect(panel, (0, 0, 0, 160), (0, 0, w, h), border_radius=radius)
        pygame.draw.rect(panel, (80, 180, 255, 80), (0, 0, w, h), 2, border_radius=radius)
        surface.blit(panel, (x, y))

    # ------------------------------------------------------------------
    # Score popups
    # ------------------------------------------------------------------

    def add_popup(self, x: float, y: float, points: int, combo: int):
        if combo > 1:
            text  = f"+{points}  ×{combo} COMBO!"
            color = _ORANGE
        else:
            text  = f"+{points}"
            color = _YELLOW
        self.popups.append(ScorePopup(x - 30, y - 20, text, color))

    def update_popups(self, dt: float):
        self.popups = [p for p in self.popups if p.alive]
        for p in self.popups:
            p.update(dt)

    def draw_popups(self, surface: pygame.Surface):
        for p in self.popups:
            p.draw(surface, self._font_md)

    # ------------------------------------------------------------------
    # HUD (in-game overlay)
    # ------------------------------------------------------------------

    def draw_hud(
        self,
        surface: pygame.Surface,
        score: int,
        lives: int,
        combo: int,
    ):
        """Draw score, lives, and combo counter."""
        # --- Score panel (top-left) ---
        score_text = f"{score:,}"
        self._draw_panel(surface, 10, 10, 180, 60)
        lbl = self._font_xs.render("SCORE", True, _CYAN)
        surface.blit(lbl, (20, 15))
        val = self._font_md.render(score_text, True, _WHITE)
        surface.blit(val, (20, 32))

        # --- Lives (top-right) ---
        hearts = _HEART * max(0, lives)
        empty  = "○" * max(0, 3 - lives)
        lives_text = hearts + empty
        self._draw_panel(surface, self.width - 170, 10, 160, 60)
        lbl2 = self._font_xs.render("LIVES", True, _RED)
        surface.blit(lbl2, (self.width - 160, 15))
        val2 = self._font_md.render(lives_text, True, _RED)
        surface.blit(val2, (self.width - 160, 32))

        # --- Combo (centre-top, only when active) ---
        if combo >= 2:
            alpha = 255
            combo_text = f"×{combo}  COMBO!"
            c_surf = self._font_combo.render(combo_text, True, _ORANGE)
            c_surf.set_alpha(alpha)
            rect = c_surf.get_rect(centerx=self.width // 2, top=16)
            # shadow
            sh = self._font_combo.render(combo_text, True, _BLACK)
            sh.set_alpha(alpha)
            surface.blit(sh, (rect.x + 2, rect.y + 2))
            surface.blit(c_surf, rect)

        self.draw_popups(surface)

    # ------------------------------------------------------------------
    # Menu screen
    # ------------------------------------------------------------------

    def draw_menu(self, surface: pygame.Surface, high_score: int):
        """Full-screen main menu."""
        surface.fill(_DARK)

        # Title gradient simulation using two passes
        self._blit_centered(surface, self._font_xl, "🍉 IRL FRUIT NINJA 🍉", 120,
                            _YELLOW)
        self._blit_centered(surface, self._font_md,
                            "Slice fruits with your real hand!", 215, _WHITE)

        # Instructions panel
        pw, ph = 540, 220
        px = (self.width - pw) // 2
        py = 270
        self._draw_panel(surface, px, py, pw, ph)

        lines = [
            ("🖐  Stand in front of your webcam", _WHITE),
            ("✋  Raise your hand to the camera", _CYAN),
            ("⚡  Swipe fast to slice fruits", _YELLOW),
            ("💣  Avoid slicing the bombs!", _RED),
            ("💔  3 misses = game over", _WHITE),
        ]
        for i, (line, color) in enumerate(lines):
            txt = self._font_sm.render(line, True, color)
            surface.blit(txt, (px + 24, py + 16 + i * 40))

        # High score
        if high_score > 0:
            self._blit_centered(surface, self._font_md,
                                f"🏆  Best: {high_score:,}", 510, _ORANGE)

        # Start prompt (pulsing)
        import time
        pulse = abs(int((time.monotonic() % 1.0) * 255 * 2) - 255)
        prompt = self._font_lg.render("PRESS SPACE  or  CLICK  TO START", True,
                                      (pulse, 255, pulse))
        rect = prompt.get_rect(centerx=self.width // 2, top=560)
        surface.blit(prompt, rect)

        # Controls reminder
        self._blit_centered(surface, self._font_xs, "ESC = quit   Q = quit",
                            self.height - 28, (120, 120, 160))

    # ------------------------------------------------------------------
    # Game-over screen
    # ------------------------------------------------------------------

    def draw_game_over(
        self,
        surface: pygame.Surface,
        score: int,
        high_score: int,
    ):
        """Full-screen game-over overlay."""
        surface.fill(_DARK)

        self._blit_centered(surface, self._font_xl, "GAME OVER", 100, _RED)

        # Score summary
        pw, ph = 400, 180
        px = (self.width - pw) // 2
        py = 220
        self._draw_panel(surface, px, py, pw, ph)

        score_lines = [
            (f"Your score:  {score:,}", _WHITE, self._font_lg),
            (f"Best score:  {high_score:,}", _YELLOW, self._font_md),
        ]
        y_off = py + 24
        for text, color, font in score_lines:
            txt = font.render(text, True, color)
            rect = txt.get_rect(centerx=self.width // 2, top=y_off)
            surface.blit(txt, rect)
            y_off += font.get_height() + 16

        if score >= high_score and score > 0:
            self._blit_centered(surface, self._font_md,
                                "🏆  NEW HIGH SCORE!", y_off + 10, _ORANGE)

        import time
        pulse = abs(int((time.monotonic() % 1.0) * 255 * 2) - 255)
        prompt = self._font_lg.render("SPACE / CLICK — play again", True,
                                      (pulse, 255, pulse))
        rect = prompt.get_rect(centerx=self.width // 2, top=460)
        surface.blit(prompt, rect)

        self._blit_centered(surface, self._font_sm, "ESC — main menu",
                            530, (160, 160, 200))
