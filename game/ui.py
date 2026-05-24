"""
ui.py
-----
Heads-up display, menu screens, and game-over screen.

All drawing is done on a passed *surface* so this module remains
stateless and can be called from the main loop without holding a
reference to the display.
"""
from __future__ import annotations

import math
import time

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

# Menu theme — soft pastel gradient (matches HTML design)
_MENU_BG    = ( 18,  18,  35)        # fallback only
_PINK       = (244, 182, 213)        # #f4b6d5
_LAVENDER   = (199, 146, 234)        # #c792ea
_WHITE_DIM  = (200, 200, 220)

# Pastel gradient palette (pink → lavender → mint)
_GRAD_TL    = (252, 228, 242)        # top-left: soft pink
_GRAD_TR    = (232, 213, 245)        # top-right: soft lavender
_GRAD_BL    = (220, 240, 255)        # bottom-left: soft periwinkle
_GRAD_BR    = (212, 245, 235)        # bottom-right: soft mint

# Instruction line colours (matching HTML colour coding)
_INSTR_NEUTRAL  = ( 60,  50,  70)   # dark plum — webcam line
_INSTR_PURPLE   = (140,  80, 200)   # purple — raise hand
_INSTR_GREEN    = ( 50, 170, 100)   # green — swipe fast
_INSTR_ORANGE   = (220,  80,  40)   # red-orange — bombs
_INSTR_RED      = (200,  50,  50)   # red — misses

# Title / subtitle colours
_TITLE_COLOR    = (130,  60, 180)   # deep lavender-purple
_SUBTITLE_COLOR = (150, 100, 190)   # muted lavender

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

    def _get_or_create_gradient(self, w: int, h: int) -> pygame.Surface:
        """
        Build (once) a soft 4-corner pastel gradient (pink→lavender→mint).
        Uses a tiny 2×2 surface scaled to full size — instant and smooth.
        """
        if not hasattr(self, '_gradient_cache') or self._gradient_cache.get_size() != (w, h):
            # 2×2 seed: top-left=pink, top-right=lavender, bottom-left=periwinkle, bottom-right=mint
            seed = pygame.Surface((2, 2))
            seed.set_at((0, 0), _GRAD_TL)
            seed.set_at((1, 0), _GRAD_TR)
            seed.set_at((0, 1), _GRAD_BL)
            seed.set_at((1, 1), _GRAD_BR)
            self._gradient_cache = pygame.transform.smoothscale(seed, (w, h))
        return self._gradient_cache

    # ------------------------------------------------------------------
    # Decorative shape helpers (emoji-free, cross-platform)
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_4star(surface: pygame.Surface, cx: int, cy: int,
                    outer: float, inner: float, color, alpha: int):
        """Draw a 4-pointed star (sparkle) at (cx, cy)."""
        import math as _m
        pts = []
        for i in range(8):
            angle = _m.pi / 4 * i - _m.pi / 4
            r = outer if i % 2 == 0 else inner
            pts.append((cx + r * _m.cos(angle), cy + r * _m.sin(angle)))
        star_surf = pygame.Surface(
            (int(outer * 2 + 4), int(outer * 2 + 4)), pygame.SRCALPHA)
        shifted = [(x - cx + outer + 2, y - cy + outer + 2) for x, y in pts]
        pygame.draw.polygon(star_surf, (*color, alpha), shifted)
        surface.blit(star_surf, (int(cx - outer - 2), int(cy - outer - 2)))

    @staticmethod
    def _draw_flower(surface: pygame.Surface, cx: int, cy: int,
                     r: float, color, alpha: int):
        """Draw a simple 5-petal flower circle cluster."""
        import math as _m
        size = int(r * 2 + 4)
        fl = pygame.Surface((size, size), pygame.SRCALPHA)
        ox, oy = r + 2, r + 2
        petal_r = int(r * 0.55)
        for i in range(5):
            ang = 2 * _m.pi * i / 5 - _m.pi / 2
            px = int(ox + r * 0.55 * _m.cos(ang))
            py = int(oy + r * 0.55 * _m.sin(ang))
            pygame.draw.circle(fl, (*color, alpha), (px, py), petal_r)
        # centre dot
        pygame.draw.circle(fl, (255, 230, 240, alpha), (int(ox), int(oy)), int(r * 0.35))
        surface.blit(fl, (int(cx - r - 2), int(cy - r - 2)))

    @staticmethod
    def _draw_bullet(surface: pygame.Surface, cx: int, cy: int,
                     r: float, color):
        """Draw a small filled circle bullet."""
        pygame.draw.circle(surface, color, (int(cx), int(cy)), int(r))

    def draw_menu(self, surface: pygame.Surface, high_score: int):
        """Full-screen main menu — soft pastel gradient theme matching HTML design."""
        now = time.monotonic()

        # --- Pastel gradient background ---
        grad = self._get_or_create_gradient(self.width, self.height)
        surface.blit(grad, (0, 0))

        # --- Background sparkles — drawn as 4-pointed stars, twinkle anim ---
        _SPARKLE_DATA = [
            (0.10, 0.12, 0.0,  10, 4),
            (0.85, 0.20, 0.8,   8, 3),
            (0.20, 0.75, 1.5,  10, 4),
            (0.92, 0.40, 0.4,   7, 3),
            (0.75, 0.85, 2.0,   8, 3),
            (0.45, 0.08, 1.2,   9, 4),
            (0.08, 0.65, 1.8,   7, 3),
        ]
        for rx, ry, off, outer, inner in _SPARKLE_DATA:
            t = 0.5 + 0.5 * math.sin(now * 2.5 + off)
            alpha = int(60 + 160 * t)
            self._draw_4star(surface,
                             int(rx * self.width), int(ry * self.height),
                             outer, inner, (90, 70, 110), alpha)

        # --- Drifting flowers ---
        _FLOWER_DATA = [
            (0.88, 0.60, 0.6, (244, 182, 213)),
            (0.30, 0.15, 1.4, (220, 160, 230)),
            (0.60, 0.80, 2.2, (244, 182, 213)),
        ]
        for rx, ry, off, color in _FLOWER_DATA:
            dx = math.sin(now * 0.7 + off) * 6
            dy = math.sin(now * 1.0 + off) * 12
            t = 0.5 + 0.5 * math.sin(now * 1.0 + off)
            alpha = int(90 + 120 * t)
            self._draw_flower(surface,
                              int(rx * self.width + dx),
                              int(ry * self.height + dy),
                              14, color, alpha)

        # --- Floating title ---
        float_offset = int(math.sin(now * 2.0) * 6)
        title_y = int(self.height * 0.13) + float_offset

        title_text = "IRL Fruit Ninja"
        title_cx = self.width // 2

        # Soft drop shadow
        sh = self._font_xl.render(title_text, True, (180, 130, 210))
        sh_rect = sh.get_rect(centerx=title_cx, top=title_y + 3)
        sh.set_alpha(70)
        surface.blit(sh, sh_rect)
        # Main title
        title_surf = self._font_xl.render(title_text, True, _TITLE_COLOR)
        title_rect = title_surf.get_rect(centerx=title_cx, top=title_y)
        surface.blit(title_surf, title_rect)

        # --- Subtitle ---
        sub_y = title_y + self._font_xl.get_height() + 10
        sub_surf = self._font_sm.render("Slice fruits with your real hand!", True, _SUBTITLE_COLOR)
        sub_rect = sub_surf.get_rect(centerx=self.width // 2, top=sub_y)
        surface.blit(sub_surf, sub_rect)

        # --- Glassmorphism instructions panel ---
        pw = min(520, int(self.width * 0.72))
        ph = 220
        px = (self.width - pw) // 2
        py = sub_y + self._font_sm.get_height() + 24

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (255, 255, 255, 38),  (0, 0, pw, ph), border_radius=18)
        pygame.draw.rect(panel, (244, 182, 213, 102), (0, 0, pw, ph), 1, border_radius=18)
        pygame.draw.rect(panel, (255, 255, 255, 25),  (1, 1, pw - 2, 2), border_radius=18)
        surface.blit(panel, (px, py))

        # Instruction lines — coloured bullet + text, no emoji
        lines = [
            ("Stand in front of your webcam",  _INSTR_NEUTRAL),
            ("Raise your hand to the camera",  _INSTR_PURPLE),
            ("Swipe fast to slice fruits",     _INSTR_GREEN),
            ("Avoid slicing the bombs!",       _INSTR_ORANGE),
            ("3 misses = game over",           _INSTR_RED),
        ]
        line_h = (ph - 20) // len(lines)
        bullet_r = 5
        text_indent = 46

        for i, (line, color) in enumerate(lines):
            row_y = py + 12 + i * line_h
            mid_y = row_y + self._font_sm.get_height() // 2
            # Coloured circle bullet
            self._draw_bullet(surface, px + 22, mid_y, bullet_r, color)
            txt = self._font_sm.render(line, True, color)
            surface.blit(txt, (px + text_indent, row_y))

        # --- High score (below panel) ---
        hs_y = py + ph + 10
        if high_score > 0:
            hs_surf = self._font_sm.render(f"Best: {high_score:,}", True, _ORANGE)
            hs_rect = hs_surf.get_rect(centerx=self.width // 2, top=hs_y)
            surface.blit(hs_surf, hs_rect)
            btn_y = hs_y + self._font_sm.get_height() + 16
        else:
            btn_y = hs_y + 6

        # --- Start button — lavender-to-pink gradient pill ---
        btn_label = "Start Game"
        btn_surf  = self._font_md.render(btn_label, True, (255, 255, 255))
        btn_w     = btn_surf.get_width() + 96
        btn_h     = 54
        btn_x     = (self.width - btn_w) // 2
        btn_r     = btn_h // 2          # pill radius

        # Soft pulsing outer glow
        glow_t     = 0.5 + 0.5 * math.sin(now * 2.2)
        glow_alpha = int(30 + 30 * glow_t)
        glow_color = (199, 146, 234)    # lavender
        for extra in (22, 14, 7):
            gw, gh = btn_w + extra * 2, btn_h + extra * 2
            gs = pygame.Surface((gw, gh), pygame.SRCALPHA)
            a  = max(0, glow_alpha - extra)
            pygame.draw.rect(gs, (*glow_color, a), (0, 0, gw, gh), border_radius=gh)
            surface.blit(gs, (btn_x - extra, btn_y - extra))

        # Gradient fill: lavender (left) → pink (right) via scanlines
        grad_btn = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        lav = (199, 146, 234)
        pnk = (244, 182, 213)
        for bx in range(btn_w):
            t2 = bx / max(btn_w - 1, 1)
            col = (
                int(lav[0] + (pnk[0] - lav[0]) * t2),
                int(lav[1] + (pnk[1] - lav[1]) * t2),
                int(lav[2] + (pnk[2] - lav[2]) * t2),
                230,
            )
            pygame.draw.line(grad_btn, col, (bx, 0), (bx, btn_h))
        # clip to pill shape by masking
        mask = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, btn_w, btn_h), border_radius=btn_r)
        grad_btn.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # Thin top highlight for depth
        hl = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        pygame.draw.rect(hl, (255, 255, 255, 50), (3, 3, btn_w - 6, btn_h // 2 - 3),
                         border_radius=btn_r)
        grad_btn.blit(hl, (0, 0))

        surface.blit(grad_btn, (btn_x, btn_y))

        # White label
        lbl_rect = btn_surf.get_rect(center=(self.width // 2, btn_y + btn_h // 2))
        surface.blit(btn_surf, lbl_rect)

        # --- Controls hint ---
        hint_y = btn_y + btn_h + 14
        hint = self._font_xs.render("Space or click to start   |   ESC / Q to quit",
                                    True, (150, 110, 180))
        hint_rect = hint.get_rect(centerx=self.width // 2, top=hint_y)
        surface.blit(hint, hint_rect)

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
        now = time.monotonic()

        # --- Same pastel gradient background as the menu ---
        grad = self._get_or_create_gradient(self.width, self.height)
        surface.blit(grad, (0, 0))

        # --- Background sparkles (same positions as menu) ---
        _SPARKLE_DATA = [
            (0.10, 0.12, 0.0,  10, 4),
            (0.85, 0.20, 0.8,   8, 3),
            (0.20, 0.75, 1.5,  10, 4),
            (0.92, 0.40, 0.4,   7, 3),
            (0.75, 0.85, 2.0,   8, 3),
            (0.45, 0.08, 1.2,   9, 4),
            (0.08, 0.65, 1.8,   7, 3),
        ]
        for rx, ry, off, outer, inner in _SPARKLE_DATA:
            t = 0.5 + 0.5 * math.sin(now * 2.5 + off)
            alpha = int(60 + 160 * t)
            self._draw_4star(surface,
                             int(rx * self.width), int(ry * self.height),
                             outer, inner, (90, 70, 110), alpha)

        # --- Drifting flowers ---
        _FLOWER_DATA = [
            (0.88, 0.60, 0.6, (244, 182, 213)),
            (0.30, 0.15, 1.4, (220, 160, 230)),
            (0.60, 0.80, 2.2, (244, 182, 213)),
        ]
        for rx, ry, off, color in _FLOWER_DATA:
            dx = math.sin(now * 0.7 + off) * 6
            dy = math.sin(now * 1.0 + off) * 12
            t = 0.5 + 0.5 * math.sin(now * 1.0 + off)
            alpha = int(90 + 120 * t)
            self._draw_flower(surface,
                              int(rx * self.width + dx),
                              int(ry * self.height + dy),
                              14, color, alpha)

        # --- "Game Over" title in theme colours ---
        title_y = int(self.height * 0.10)
        sh = self._font_xl.render("Game Over", True, (180, 130, 210))
        sh.set_alpha(70)
        surface.blit(sh, sh.get_rect(centerx=self.width // 2, top=title_y + 3))
        title_s = self._font_xl.render("Game Over", True, _TITLE_COLOR)
        surface.blit(title_s, title_s.get_rect(centerx=self.width // 2, top=title_y))

        # --- Score panel — glassmorphism card matching menu style ---
        pw, ph = 420, 160 if (score < high_score or score == 0) else 190
        px = (self.width - pw) // 2
        py = title_y + self._font_xl.get_height() + 28

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (255, 255, 255, 38),  (0, 0, pw, ph), border_radius=18)
        pygame.draw.rect(panel, (244, 182, 213, 102), (0, 0, pw, ph), 1, border_radius=18)
        pygame.draw.rect(panel, (255, 255, 255, 25),  (1, 1, pw - 2, 2), border_radius=18)
        surface.blit(panel, (px, py))

        # Score lines inside panel
        y_off = py + 24
        your_s = self._font_lg.render(f"Your score:  {score:,}", True, _TITLE_COLOR)
        surface.blit(your_s, your_s.get_rect(centerx=self.width // 2, top=y_off))
        y_off += self._font_lg.get_height() + 10

        best_s = self._font_md.render(f"Best score:  {high_score:,}", True, (170, 110, 220))
        surface.blit(best_s, best_s.get_rect(centerx=self.width // 2, top=y_off))
        y_off += self._font_md.get_height() + 10

        if score >= high_score and score > 0:
            # Pulsing gold "NEW HIGH SCORE!" badge
            pulse_t = 0.5 + 0.5 * math.sin(now * 4.0)
            badge_color = (
                int(220 + 35 * pulse_t),
                int(160 + 30 * pulse_t),
                int(40),
            )
            badge_s = self._font_sm.render("NEW HIGH SCORE!", True, badge_color)
            # small star bullet beside it
            star_cx = self.width // 2 - badge_s.get_width() // 2 - 14
            star_cy = y_off + badge_s.get_height() // 2
            self._draw_4star(surface, star_cx, star_cy, 7, 3, badge_color, 220)
            surface.blit(badge_s, badge_s.get_rect(centerx=self.width // 2 + 7, top=y_off))

        # --- Two buttons: Play Again + Main Menu ---
        btn_y = py + ph + 28

        def _draw_pill_btn(label: str, cy: int, grad_l, grad_r) -> int:
            """Draw a gradient pill button centred at cy; return its bottom y."""
            bs = self._font_md.render(label, True, (255, 255, 255))
            bw = bs.get_width() + 80
            bh = 50
            bx = (self.width - bw) // 2
            br = bh // 2

            # glow
            ga = int(30 + 25 * (0.5 + 0.5 * math.sin(now * 2.2)))
            for extra in (18, 11, 5):
                gw2, gh2 = bw + extra * 2, bh + extra * 2
                gs = pygame.Surface((gw2, gh2), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*grad_r, max(0, ga - extra)),
                                 (0, 0, gw2, gh2), border_radius=gh2)
                surface.blit(gs, (bx - extra, cy - extra))

            # gradient body
            gb = pygame.Surface((bw, bh), pygame.SRCALPHA)
            for bxi in range(bw):
                t2 = bxi / max(bw - 1, 1)
                col = (
                    int(grad_l[0] + (grad_r[0] - grad_l[0]) * t2),
                    int(grad_l[1] + (grad_r[1] - grad_l[1]) * t2),
                    int(grad_l[2] + (grad_r[2] - grad_l[2]) * t2),
                    225,
                )
                pygame.draw.line(gb, col, (bxi, 0), (bxi, bh))
            mask = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, bw, bh), border_radius=br)
            gb.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            # highlight
            hl = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(hl, (255, 255, 255, 45), (3, 3, bw - 6, bh // 2 - 3),
                             border_radius=br)
            gb.blit(hl, (0, 0))
            surface.blit(gb, (bx, cy))
            surface.blit(bs, bs.get_rect(center=(self.width // 2, cy + bh // 2)))
            return cy + bh

        # Primary: lavender → pink
        bottom = _draw_pill_btn("Play Again", btn_y, (199, 146, 234), (244, 182, 213))

        # Secondary: smaller, outlined-style (same gradient but dimmer)
        menu_y = bottom + 14
        menu_s = self._font_sm.render("Main Menu  (ESC)", True, _SUBTITLE_COLOR)
        surface.blit(menu_s, menu_s.get_rect(centerx=self.width // 2, top=menu_y))
