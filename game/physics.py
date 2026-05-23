"""
physics.py
----------
Applies gravity and updates positions / rotations for Fruit and
SlicedHalf objects every frame.
"""
from __future__ import annotations

from typing import List

GRAVITY = 0.45          # pixels per frame² (added to vy each frame)
GRAVITY_HALVES = 0.55   # halves fall a bit faster for drama


class PhysicsEngine:
    """
    Stateless physics updater.  Call ``update`` and ``update_halves``
    once per frame with the lists of live objects.

    Parameters
    ----------
    width, height : int
        Screen dimensions — used only for out-of-bounds queries.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    # ------------------------------------------------------------------

    def update(self, fruits: List, dt: float):
        """
        Update position, velocity (gravity), and rotation for each fruit.

        *dt* is in seconds; gravity is frame-based so we scale by 60 to
        keep behaviour consistent regardless of frame rate.
        """
        g = GRAVITY * 60 * dt   # convert to pixels / second²

        for f in fruits:
            f.vy += g
            f.x += f.vx
            f.y += f.vy
            f.rotation += f.angular_vel

    def update_halves(self, halves: List, dt: float):
        """Same as ``update`` but for SlicedHalf instances (tracks age)."""
        g = GRAVITY_HALVES * 60 * dt

        for h in halves:
            h.vy += g
            h.x += h.vx
            h.y += h.vy
            h.rotation += h.angular_vel
            h.age += dt

    def is_off_screen(self, obj) -> bool:
        """Return *True* when *obj* has fallen below the visible area."""
        return obj.y > self.height + obj.radius + 20
