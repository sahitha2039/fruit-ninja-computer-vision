"""
fruit.py
--------
Fruit, SlicedHalf, and supporting data.

Emoji rendering strategy
~~~~~~~~~~~~~~~~~~~~~~~~
1. Try to locate a system colour-emoji font (macOS → Apple Color Emoji,
   Windows → Segoe UI Emoji, Linux → Noto Color Emoji) and render via
   Pillow so we get real colour glyphs.
2. If Pillow or the font is absent fall back to drawing a filled circle
   in the fruit's accent colour with a short text label — still readable
   and always works.
"""
from __future__ import annotations

import math
import os
import random
import sys
from typing import Optional, Tuple

import pygame

# ---------------------------------------------------------------------------
# Emoji font helpers
# ---------------------------------------------------------------------------

_EMOJI_CACHE: dict[str, pygame.Surface] = {}

_EMOJI_FONT_PATHS = [
    # macOS
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    # Windows
    "C:/Windows/Fonts/seguiemj.ttf",
    # Linux (various distros)
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto-color-emoji/NotoColorEmoji.ttf",
    "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",
]


def _find_emoji_font() -> Optional[str]:
    for p in _EMOJI_FONT_PATHS:
        if os.path.exists(p):
            return p
    return None


def _render_emoji_pil(emoji: str, size: int) -> Optional[pygame.Surface]:
    """Render *emoji* at *size* px using Pillow → pygame Surface, or None."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError:
        return None

    font_path = _find_emoji_font()
    if font_path is None:
        return None

    try:
        canvas_size = size + 8
        img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, size)
        # embedded_color renders colour glyphs (Pillow ≥ 8.0)
        draw.text((4, 4), emoji, font=font, embedded_color=True)
        # crop to content
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        raw = img.tobytes()
        surf = pygame.image.fromstring(raw, img.size, img.mode).convert_alpha()
        return surf
    except Exception:
        return None


def _get_emoji_surface(emoji: str, size: int) -> Optional[pygame.Surface]:
    key = f"{emoji}_{size}"
    if key not in _EMOJI_CACHE:
        _EMOJI_CACHE[key] = _render_emoji_pil(emoji, size)
    return _EMOJI_CACHE[key]


# ---------------------------------------------------------------------------
# Fruit catalogue
# ---------------------------------------------------------------------------

FRUIT_TYPES: dict[str, dict] = {
    "watermelon": {
        "emoji": "🍉",
        "color": (80, 200, 80),
        "juice": (220, 60, 80),
        "radius": 42,
        "label": "WM",
    },
    "apple": {
        "emoji": "🍎",
        "color": (220, 50, 50),
        "juice": (240, 100, 80),
        "radius": 32,
        "label": "AP",
    },
    "orange": {
        "emoji": "🍊",
        "color": (240, 140, 30),
        "juice": (255, 180, 0),
        "radius": 32,
        "label": "OR",
    },
    "grape": {
        "emoji": "🍇",
        "color": (130, 60, 180),
        "juice": (160, 80, 200),
        "radius": 28,
        "label": "GR",
    },
    "banana": {
        "emoji": "🍌",
        "color": (240, 220, 20),
        "juice": (255, 240, 80),
        "radius": 30,
        "label": "BN",
    },
    "peach": {
        "emoji": "🍑",
        "color": (240, 160, 100),
        "juice": (255, 180, 120),
        "radius": 30,
        "label": "PC",
    },
    "lemon": {
        "emoji": "🍋",
        "color": (240, 230, 40),
        "juice": (255, 250, 60),
        "radius": 26,
        "label": "LM",
    },
    "strawberry": {
        "emoji": "🍓",
        "color": (220, 40, 60),
        "juice": (255, 80, 100),
        "radius": 26,
        "label": "SB",
    },
    "bomb": {
        "emoji": "💣",
        "color": (40, 40, 40),
        "juice": (80, 80, 80),
        "radius": 28,
        "label": "💣",
    },
}

FRUIT_NAMES = [k for k in FRUIT_TYPES if k != "bomb"]


# ---------------------------------------------------------------------------
# Fallback renderer (no Pillow / no emoji font)
# ---------------------------------------------------------------------------

def _draw_fallback(surface: pygame.Surface, ftype: str, cx: int, cy: int,
                   radius: int, rotation: float):
    """Draw a coloured circle with a 2-char label as fallback."""
    info = FRUIT_TYPES[ftype]
    color = info["color"]

    pygame.draw.circle(surface, color, (cx, cy), radius)
    pygame.draw.circle(surface, (255, 255, 255), (cx, cy), radius, 2)

    if not hasattr(_draw_fallback, "_font"):
        _draw_fallback._font = pygame.font.SysFont("Arial", 14, bold=True)  # type: ignore

    label_surf = _draw_fallback._font.render(info["label"], True, (255, 255, 255))
    label_rect = label_surf.get_rect(center=(cx, cy))
    surface.blit(label_surf, label_rect)


# ---------------------------------------------------------------------------
# Fruit
# ---------------------------------------------------------------------------

class Fruit:
    """A single airborne fruit."""

    def __init__(
        self,
        ftype: str,
        x: float,
        y: float,
        vx: float,
        vy: float,
    ):
        self.type = ftype
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

        info = FRUIT_TYPES[ftype]
        self.radius: int = info["radius"]
        self.rotation: float = random.uniform(0, 360)
        self.angular_vel: float = random.uniform(-4, 4)   # deg / frame
        self.is_sliced: bool = False

        # Pre-render emoji surface (sized to 2× radius for quality)
        emoji_size = self.radius * 2
        self._surf = _get_emoji_surface(info["emoji"], emoji_size)

    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, offset: Tuple[int, int] = (0, 0)):
        cx = int(self.x) + offset[0]
        cy = int(self.y) + offset[1]

        if self._surf is not None:
            # Rotate the pre-rendered emoji surface
            rotated = pygame.transform.rotate(self._surf, self.rotation)
            rect = rotated.get_rect(center=(cx, cy))
            screen.blit(rotated, rect)
        else:
            _draw_fallback(screen, self.type, cx, cy,
                           self.radius, self.rotation)

    def slice(self, swipe_angle: float, velocity: Tuple[float, float]):
        """Return two SlicedHalf objects moving apart along the slice axis."""
        perp = swipe_angle + math.pi / 2
        speed = 3.0

        half1 = SlicedHalf(
            self.type,
            self.x, self.y,
            self.vx + math.cos(perp) * speed,
            self.vy + math.sin(perp) * speed,
            self.rotation, self.angular_vel,
            half=0,
        )
        half2 = SlicedHalf(
            self.type,
            self.x, self.y,
            self.vx - math.cos(perp) * speed,
            self.vy - math.sin(perp) * speed,
            self.rotation, self.angular_vel,
            half=1,
        )
        return half1, half2


# ---------------------------------------------------------------------------
# SlicedHalf
# ---------------------------------------------------------------------------

class SlicedHalf:
    """One half of a sliced fruit — fades out after a short time."""

    LIFESPAN = 1.2   # seconds before removal

    def __init__(
        self,
        ftype: str,
        x: float, y: float,
        vx: float, vy: float,
        rotation: float,
        angular_vel: float,
        half: int,       # 0 or 1
    ):
        self.type = ftype
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.rotation = rotation
        self.angular_vel = angular_vel
        self.half = half
        self.age: float = 0.0   # seconds

        info = FRUIT_TYPES[ftype]
        self.radius = info["radius"]

        # Grab emoji surface and crop to one half
        emoji_size = self.radius * 2
        full_surf = _get_emoji_surface(info["emoji"], emoji_size)
        if full_surf is not None:
            w, h = full_surf.get_size()
            half_surf = pygame.Surface((w, h // 2), pygame.SRCALPHA)
            src_y = 0 if half == 0 else h // 2
            half_surf.blit(full_surf, (0, 0), (0, src_y, w, h // 2))
            self._surf: Optional[pygame.Surface] = half_surf
        else:
            self._surf = None

    def is_dead(self) -> bool:
        return self.age >= self.LIFESPAN

    def draw(self, screen: pygame.Surface, offset: Tuple[int, int] = (0, 0)):
        alpha = max(0, int(255 * (1.0 - self.age / self.LIFESPAN)))
        cx = int(self.x) + offset[0]
        cy = int(self.y) + offset[1]

        if self._surf is not None:
            rotated = pygame.transform.rotate(self._surf, self.rotation)
            rotated.set_alpha(alpha)
            rect = rotated.get_rect(center=(cx, cy))
            screen.blit(rotated, rect)
        else:
            # Fallback: fading circle half
            info = FRUIT_TYPES[self.type]
            r = max(2, self.radius - 4)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*info["color"], alpha), (r, r), r)
            screen.blit(surf, (cx - r, cy - r))
