"""
fruit.py
--------
Fruit, SlicedHalf, and supporting data.

Emoji rendering strategy
~~~~~~~~~~~~~~~~~~~~~~~~
1. On first run, download Twemoji PNG files (Twitter's open-source emoji set)
   from the jsDelivr CDN into assets/emoji/.  These are high-quality 72×72
   PNGs that render identically on every platform.
2. On subsequent runs, load from the local cache (instant).
3. If the download fails (no internet), fall back to the programmatic shapes
   so the game always works.
"""
from __future__ import annotations

import math
import os
import random
import urllib.request
from typing import Optional, Tuple

import pygame


# ---------------------------------------------------------------------------
# Emoji asset config
# ---------------------------------------------------------------------------

_HERE       = os.path.dirname(os.path.abspath(__file__))
_EMOJI_DIR  = os.path.join(_HERE, "..", "assets", "emoji")
_CDN_BASE   = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"

# Map fruit type → Twemoji codepoint (hex, lower-case)
_CODEPOINTS: dict[str, str] = {
    "watermelon": "1f349",
    "apple":      "1f34e",
    "orange":     "1f34a",
    "grape":      "1f347",
    "banana":     "1f34c",
    "peach":      "1f351",
    "lemon":      "1f34b",
    "strawberry": "1f353",
    "bomb":       "1f4a3",
}


def _ensure_emoji_assets():
    """Download any missing Twemoji PNGs into assets/emoji/."""
    os.makedirs(_EMOJI_DIR, exist_ok=True)
    for name, cp in _CODEPOINTS.items():
        path = os.path.join(_EMOJI_DIR, f"{name}.png")
        if not os.path.exists(path):
            url = f"{_CDN_BASE}/{cp}.png"
            try:
                urllib.request.urlretrieve(url, path)
                print(f"[emoji] downloaded {name}")
            except Exception as exc:
                print(f"[emoji] could not download {name}: {exc}")


# Call once at import time — skips instantly if all files already exist
_ensure_emoji_assets()


# ---------------------------------------------------------------------------
# Per-fruit surface cache
# ---------------------------------------------------------------------------

_SURF_CACHE: dict[tuple, pygame.Surface] = {}


def _load_emoji_surface(ftype: str, size: int) -> Optional[pygame.Surface]:
    """Load the Twemoji PNG for *ftype*, scaled to *size*×*size* px."""
    path = os.path.join(_EMOJI_DIR, f"{ftype}.png")
    if not os.path.exists(path):
        return None
    try:
        raw  = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(raw, (size, size))
    except Exception:
        return None


def _make_fruit_surface(ftype: str, radius: int) -> pygame.Surface:
    """
    Return a pre-rendered SRCALPHA surface for *ftype* at *radius*.
    Tries the Twemoji PNG first; falls back to programmatic shapes.
    """
    key = (ftype, radius)
    if key in _SURF_CACHE:
        return _SURF_CACHE[key]

    diameter = radius * 2
    emoji_surf = _load_emoji_surface(ftype, diameter)
    if emoji_surf is not None:
        _SURF_CACHE[key] = emoji_surf
        return emoji_surf

    # Fallback: draw programmatically
    size = diameter + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    _DRAW_FN.get(ftype, _draw_generic)(surf, cx, cy, radius, ftype)
    _SURF_CACHE[key] = surf
    return surf


# ---------------------------------------------------------------------------
# Fruit catalogue
# ---------------------------------------------------------------------------

FRUIT_TYPES: dict[str, dict] = {
    "watermelon": {"color": (60,  180,  60), "juice": (220,  60,  80), "radius": 42},
    "apple":      {"color": (210,  40,  40), "juice": (240, 100,  80), "radius": 32},
    "orange":     {"color": (240, 140,  30), "juice": (255, 180,   0), "radius": 32},
    "grape":      {"color": (120,  50, 170), "juice": (160,  80, 200), "radius": 28},
    "banana":     {"color": (240, 220,  20), "juice": (255, 240,  80), "radius": 30},
    "peach":      {"color": (240, 160, 100), "juice": (255, 180, 120), "radius": 30},
    "lemon":      {"color": (230, 220,  30), "juice": (255, 250,  60), "radius": 26},
    "strawberry": {"color": (210,  35,  55), "juice": (255,  80, 100), "radius": 26},
    "bomb":       {"color": ( 45,  45,  45), "juice": ( 80,  80,  80), "radius": 28},
}

FRUIT_NAMES = [k for k in FRUIT_TYPES if k != "bomb"]


# ---------------------------------------------------------------------------
# Programmatic fallback drawing functions
# ---------------------------------------------------------------------------

def _draw_generic(s, cx, cy, r, ftype):
    info = FRUIT_TYPES.get(ftype, {"color": (180, 180, 180)})
    pygame.draw.circle(s, info["color"], (cx, cy), r)
    pygame.draw.circle(s, (255, 255, 255), (cx, cy), r, 2)


def _draw_watermelon(s, cx, cy, r, _=None):
    pygame.draw.circle(s, (50, 175, 55), (cx, cy), r)
    pygame.draw.circle(s, (30, 130, 35), (cx, cy), r, max(1, r // 5))
    pygame.draw.circle(s, (215, 55, 75), (cx, cy), int(r * 0.75))
    for angle in [20, 80, 150, 230, 300]:
        rad = math.radians(angle)
        sx = cx + int(r * 0.42 * math.cos(rad))
        sy = cy + int(r * 0.42 * math.sin(rad))
        pygame.draw.ellipse(s, (25, 20, 20), (sx - 3, sy - 5, 6, 10))


def _draw_apple(s, cx, cy, r, _=None):
    pygame.draw.circle(s, (215, 40, 40), (cx, cy), r)
    pygame.draw.circle(s, (240, 100, 100), (cx - r//3, cy - r//3), r//4)
    pygame.draw.rect(s, (100, 60, 20), (cx - 1, cy - r - 6, 4, 8))
    pygame.draw.polygon(s, (60, 160, 50),
        [(cx+2, cy-r-2), (cx+r//3, cy-r-r//3), (cx+2, cy-r+2)])


def _draw_orange(s, cx, cy, r, _=None):
    pygame.draw.circle(s, (240, 138, 28), (cx, cy), r)
    for angle in range(0, 180, 30):
        rad = math.radians(angle)
        pygame.draw.line(s, (210, 110, 15),
            (cx + int(r*math.cos(rad)), cy + int(r*math.sin(rad))),
            (cx - int(r*math.cos(rad)), cy - int(r*math.sin(rad))), 1)
    pygame.draw.circle(s, (255, 185, 80), (cx - r//3, cy - r//3), r//5)


def _draw_grape(s, cx, cy, r, _=None):
    gr = max(5, r // 3)
    positions = [
        (cx, cy - int(r*0.55)), (cx-gr, cy-int(r*0.15)), (cx+gr, cy-int(r*0.15)),
        (cx-gr*2, cy+int(r*0.25)), (cx, cy+int(r*0.25)), (cx+gr*2, cy+int(r*0.25)),
    ]
    for gx, gy in positions:
        pygame.draw.circle(s, (80, 30, 110), (gx+1, gy+1), gr)
        pygame.draw.circle(s, (130, 55, 175), (gx, gy), gr)
        pygame.draw.circle(s, (170, 100, 220), (gx-gr//3, gy-gr//3), gr//3)


def _draw_banana(s, cx, cy, r, _=None):
    pts_out, pts_in = [], []
    for i in range(13):
        t = i / 12
        ang = math.radians(-20 + t * 200)
        pts_out.append((cx + int(r*0.9*math.cos(ang)), cy + int(r*0.55*math.sin(ang)) - r//5))
        pts_in.append( (cx + int(r*0.6*math.cos(ang)), cy + int(r*0.35*math.sin(ang))))
    if len(pts_out) >= 3:
        pygame.draw.polygon(s, (240, 218, 18), pts_out + list(reversed(pts_in)))


def _draw_peach(s, cx, cy, r, _=None):
    pygame.draw.circle(s, (245, 165, 100), (cx, cy), r)
    pygame.draw.circle(s, (255, 200, 150), (cx - r//3, cy - r//3), r//4)
    pygame.draw.rect(s, (100, 65, 20), (cx - 1, cy - r - 5, 3, 7))


def _draw_lemon(s, cx, cy, r, _=None):
    rw, rh = int(r*1.25), int(r*0.85)
    pygame.draw.ellipse(s, (235, 222, 28), (cx-rw, cy-rh, rw*2, rh*2))
    pygame.draw.ellipse(s, (255, 248, 130), (cx-rw//2, cy-rh//2, rw//2, rh//2))


def _draw_strawberry(s, cx, cy, r, _=None):
    pts = []
    for i in range(40):
        ang = math.radians(i*9 - 90)
        scale_y = 1.0 if math.sin(ang) > 0 else 1.3
        pts.append((cx + int(r*0.9*math.cos(ang)),
                    cy + int(r*0.9*math.sin(ang)*scale_y) + r//6))
    pygame.draw.polygon(s, (215, 35, 55), pts)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        pygame.draw.circle(s, (240, 210, 50),
            (cx + int(r*0.45*math.cos(rad)), cy + int(r*0.45*math.sin(rad)) + r//8), 2)


def _draw_bomb(s, cx, cy, r, _=None):
    pygame.draw.circle(s, (40, 40, 40), (cx, cy), r)
    pygame.draw.circle(s, (90, 90, 90), (cx - r//3, cy - r//3), r//4)
    fb = (cx + int(r*0.6), cy - int(r*0.6))
    pygame.draw.rect(s, (140, 100, 40), (fb[0]-2, fb[1]-r//3, 4, r//3))
    pygame.draw.circle(s, (255, 200, 50), (fb[0], fb[1]-r//3-4), 5)
    pygame.draw.circle(s, (255, 100,  0), (fb[0], fb[1]-r//3-4), 3)


_DRAW_FN = {
    "watermelon": _draw_watermelon,
    "apple":      _draw_apple,
    "orange":     _draw_orange,
    "grape":      _draw_grape,
    "banana":     _draw_banana,
    "peach":      _draw_peach,
    "lemon":      _draw_lemon,
    "strawberry": _draw_strawberry,
    "bomb":       _draw_bomb,
}


# ---------------------------------------------------------------------------
# Fruit
# ---------------------------------------------------------------------------

class Fruit:
    """A single airborne fruit."""

    def __init__(self, ftype: str, x: float, y: float, vx: float, vy: float):
        self.type        = ftype
        self.x           = x
        self.y           = y
        self.vx          = vx
        self.vy          = vy
        info             = FRUIT_TYPES[ftype]
        self.radius:      int   = info["radius"]
        self.rotation:    float = random.uniform(0, 360)
        self.angular_vel: float = random.uniform(-4, 4)
        self.is_sliced:   bool  = False
        self._surf = _make_fruit_surface(ftype, self.radius)

    def draw(self, screen: pygame.Surface, offset: Tuple[int, int] = (0, 0)):
        cx = int(self.x) + offset[0]
        cy = int(self.y) + offset[1]
        rotated = pygame.transform.rotate(self._surf, self.rotation)
        screen.blit(rotated, rotated.get_rect(center=(cx, cy)))

    def slice(self, swipe_angle: float, velocity: Tuple[float, float]):
        perp  = swipe_angle + math.pi / 2
        speed = 3.0
        h1 = SlicedHalf(self.type, self.x, self.y,
                         self.vx + math.cos(perp)*speed,
                         self.vy + math.sin(perp)*speed,
                         self.rotation, self.angular_vel, half=0)
        h2 = SlicedHalf(self.type, self.x, self.y,
                         self.vx - math.cos(perp)*speed,
                         self.vy - math.sin(perp)*speed,
                         self.rotation, self.angular_vel, half=1)
        return h1, h2


# ---------------------------------------------------------------------------
# SlicedHalf
# ---------------------------------------------------------------------------

class SlicedHalf:
    """One half of a sliced fruit — fades out after a short time."""

    LIFESPAN = 1.2

    def __init__(self, ftype: str, x: float, y: float,
                 vx: float, vy: float,
                 rotation: float, angular_vel: float, half: int):
        self.type        = ftype
        self.x           = x
        self.y           = y
        self.vx          = vx
        self.vy          = vy
        self.rotation    = rotation
        self.angular_vel = angular_vel
        self.half        = half
        self.age:  float = 0.0
        self.radius      = FRUIT_TYPES[ftype]["radius"]

        full  = _make_fruit_surface(ftype, self.radius)
        fw, fh = full.get_size()
        half_surf = pygame.Surface((fw, fh // 2), pygame.SRCALPHA)
        src_y = 0 if half == 0 else fh // 2
        half_surf.blit(full, (0, 0), (0, src_y, fw, fh // 2))
        self._surf = half_surf

    def is_dead(self) -> bool:
        return self.age >= self.LIFESPAN

    def draw(self, screen: pygame.Surface, offset: Tuple[int, int] = (0, 0)):
        alpha   = max(0, int(255 * (1.0 - self.age / self.LIFESPAN)))
        cx      = int(self.x) + offset[0]
        cy      = int(self.y) + offset[1]
        rotated = pygame.transform.rotate(self._surf, self.rotation)
        rotated.set_alpha(alpha)
        screen.blit(rotated, rotated.get_rect(center=(cx, cy)))
