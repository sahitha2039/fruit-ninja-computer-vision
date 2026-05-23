"""
effects.py
----------
Three visual-effects subsystems:

  ParticleSystem  — juice splatter + bomb explosion particles
  ScreenShake     — impact camera shake
  SliceTrail      — glowing sword-trail rendered from hand history
"""
from __future__ import annotations

import math
import random
import time
from collections import deque
from typing import List, Optional, Tuple

import pygame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

Color = Tuple[int, int, int]
Vec2  = Tuple[float, float]


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Particle
# ---------------------------------------------------------------------------

class Particle:
    """A single juice or explosion particle."""

    def __init__(
        self,
        x: float, y: float,
        vx: float, vy: float,
        color: Color,
        lifespan: float,
        radius: float = 4.0,
        gravity: float = 0.25,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifespan = lifespan   # seconds
        self.age = 0.0
        self.radius = radius
        self.gravity = gravity

    @property
    def alive(self) -> bool:
        return self.age < self.lifespan

    @property
    def alpha(self) -> int:
        ratio = 1.0 - (self.age / self.lifespan)
        return int(_clamp(ratio * 255, 0, 255))

    def update(self, dt: float):
        self.vx *= 0.97
        self.vy += self.gravity * 60 * dt
        self.x += self.vx
        self.y += self.vy
        self.age += dt

    def draw(self, surface: pygame.Surface, offset: Vec2 = (0, 0)):
        r = max(1, int(self.radius * (1.0 - self.age / self.lifespan * 0.5)))
        cx = int(self.x) + offset[0]
        cy = int(self.y) + offset[1]
        alpha = self.alpha

        # Draw on a temp surface to support per-particle alpha
        tmp = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (*self.color, alpha), (r, r), r)
        surface.blit(tmp, (cx - r, cy - r))


# ---------------------------------------------------------------------------
# ParticleSystem
# ---------------------------------------------------------------------------

class ParticleSystem:
    """Manages all active particles."""

    MAX_PARTICLES = 300

    def __init__(self):
        self._particles: List[Particle] = []

    # ------------------------------------------------------------------

    def splash(self, x: float, y: float, color: Color, count: int = 20):
        """Burst of juice droplets from a sliced fruit."""
        for _ in range(count):
            if len(self._particles) >= self.MAX_PARTICLES:
                break
            angle = random.uniform(0, math.tau)
            speed = random.uniform(2, 7)
            lifespan = random.uniform(0.4, 0.9)
            radius = random.uniform(2, 5)
            self._particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - random.uniform(1, 3),  # bias upward
                color,
                lifespan,
                radius,
            ))

    def explode(self, x: float, y: float, color: Color, count: int = 35):
        """Bomb explosion — larger, faster, darker particles."""
        for _ in range(count):
            if len(self._particles) >= self.MAX_PARTICLES:
                break
            angle = random.uniform(0, math.tau)
            speed = random.uniform(3, 11)
            lifespan = random.uniform(0.3, 0.7)
            radius = random.uniform(3, 8)
            # Mix some orange/red into the debris colour
            jitter = (
                _clamp(color[0] + random.randint(-40, 80), 0, 255),
                _clamp(color[1] + random.randint(-20, 40), 0, 255),
                _clamp(color[2] + random.randint(-20, 20), 0, 255),
            )
            self._particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                jitter,
                lifespan,
                radius,
                gravity=0.4,
            ))

    def update(self, dt: float):
        self._particles = [p for p in self._particles if p.alive]
        for p in self._particles:
            p.update(dt)

    def draw(self, surface: pygame.Surface, offset: Vec2 = (0, 0)):
        for p in self._particles:
            p.draw(surface, offset)

    def clear(self):
        self._particles.clear()


# ---------------------------------------------------------------------------
# ScreenShake
# ---------------------------------------------------------------------------

class ScreenShake:
    """Camera-shake effect.  Returns a pixel offset to shift the entire scene."""

    def __init__(self):
        self._intensity: float = 0.0
        self._duration: float  = 0.0
        self._elapsed: float   = 0.0

    def trigger(self, intensity: float, duration: float):
        """
        Start or reinforce a shake.  *intensity* in pixels; *duration* in seconds.
        If a shake is already running the stronger one wins on intensity.
        """
        self._intensity = max(self._intensity, intensity)
        self._duration = max(self._duration, duration)
        self._elapsed = 0.0

    def update(self, dt: float):
        if self._elapsed < self._duration:
            self._elapsed += dt

    def get_offset(self) -> Vec2:
        if self._elapsed >= self._duration or self._duration == 0:
            return (0, 0)
        progress = self._elapsed / self._duration
        current_intensity = self._intensity * (1.0 - progress)
        ox = random.uniform(-current_intensity, current_intensity)
        oy = random.uniform(-current_intensity, current_intensity)
        return (int(ox), int(oy))

    def reset(self):
        self._intensity = 0.0
        self._duration = 0.0
        self._elapsed = 0.0


# ---------------------------------------------------------------------------
# SliceTrail
# ---------------------------------------------------------------------------

_TRAIL_COLOR   = (100, 220, 255)   # icy blue core
_GLOW_COLOR    = (180, 240, 255)   # outer glow
_ACTIVE_COLOR  = (255, 255, 255)   # when actively swiping
_BOMB_COLOR    = (255, 80,  60)    # warm colour after bombing


class TrailPoint:
    __slots__ = ("pos", "t", "speed")

    def __init__(self, pos: Vec2, speed: float):
        self.pos   = pos
        self.t     = time.monotonic()
        self.speed = speed


class SliceTrail:
    """
    Maintains a deque of recent hand positions and renders a glowing
    sword-trail effect using a temporary SRCALPHA surface.
    """

    FADE_DURATION = 0.25   # seconds until a point fully fades

    def __init__(self, max_points: int = 22):
        self._max = max_points
        self._points: deque[Optional[TrailPoint]] = deque(maxlen=max_points)

    # ------------------------------------------------------------------

    def add_point(self, pos: Optional[Vec2], velocity: Vec2):
        speed = math.hypot(velocity[0], velocity[1]) if velocity else 0.0
        if pos is None:
            self._points.append(None)   # gap marker
        else:
            self._points.append(TrailPoint(pos, speed))

    def get_points(self) -> List[Optional[Vec2]]:
        """Return just the positions (with Nones for gaps)."""
        now = time.monotonic()
        result = []
        for tp in self._points:
            if tp is None:
                result.append(None)
            elif now - tp.t <= self.FADE_DURATION:
                result.append(tp.pos)
            else:
                result.append(None)
        return result

    def draw(self, screen: pygame.Surface, is_swiping: bool):
        now    = time.monotonic()
        pts    = list(self._points)
        n      = len(pts)

        if n < 2:
            return

        # Collect valid (alive) points with their fade ratio
        alive: List[Tuple[Vec2, float, float]] = []   # pos, ratio, speed
        for tp in pts:
            if tp is None:
                alive.append(None)  # type: ignore
            else:
                age   = now - tp.t
                ratio = max(0.0, 1.0 - age / self.FADE_DURATION)
                if ratio > 0:
                    alive.append((tp.pos, ratio, tp.speed))
                else:
                    alive.append(None)  # type: ignore

        # Build segment list (skip None gaps)
        trail_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        base_color = _ACTIVE_COLOR if is_swiping else _TRAIL_COLOR

        for i in range(len(alive) - 1):
            a = alive[i]
            b = alive[i + 1]
            if a is None or b is None:
                continue

            pos_a, ratio_a, speed_a = a
            pos_b, ratio_b, speed_b = b

            avg_ratio = (ratio_a + ratio_b) / 2
            avg_speed = (speed_a + speed_b) / 2

            # Width and alpha scale with ratio and speed
            speed_factor = _clamp(avg_speed / 1200.0, 0.0, 1.0)
            base_width   = int(6 + speed_factor * 10)
            glow_width   = base_width + 8
            core_alpha   = int(avg_ratio * 230)
            glow_alpha   = int(avg_ratio * 90)

            # Outer glow pass
            pygame.draw.line(
                trail_surf,
                (*_GLOW_COLOR, glow_alpha),
                (int(pos_a[0]), int(pos_a[1])),
                (int(pos_b[0]), int(pos_b[1])),
                glow_width,
            )
            # Core pass
            pygame.draw.line(
                trail_surf,
                (*base_color, core_alpha),
                (int(pos_a[0]), int(pos_a[1])),
                (int(pos_b[0]), int(pos_b[1])),
                base_width,
            )
            # Bright centre line
            pygame.draw.line(
                trail_surf,
                (255, 255, 255, int(avg_ratio * 200)),
                (int(pos_a[0]), int(pos_a[1])),
                (int(pos_b[0]), int(pos_b[1])),
                max(1, base_width - 4),
            )

        screen.blit(trail_surf, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)

    def clear(self):
        self._points.clear()
