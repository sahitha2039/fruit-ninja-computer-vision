"""
collision.py
------------
Line-segment ↔ circle collision detection for the sword trail.

For each consecutive pair of trail points we check whether the segment
intersects the circular hitbox of each unsliced fruit.  This is far more
reliable than a simple point check when the hand moves fast.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


Vec2 = Tuple[float, float]


def _segment_circle_intersect(
    p1: Vec2,
    p2: Vec2,
    centre: Vec2,
    radius: float,
) -> bool:
    """
    Return *True* if line segment *p1→p2* passes within *radius* of *centre*.

    Uses the closest-point-on-segment formula to avoid false positives from
    the infinite-line extension.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq == 0:
        # Degenerate segment (single point)
        dist_sq = (centre[0] - p1[0]) ** 2 + (centre[1] - p1[1]) ** 2
        return dist_sq <= radius * radius

    # Project centre onto segment; clamp to [0, 1]
    t = ((centre[0] - p1[0]) * dx + (centre[1] - p1[1]) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))

    closest_x = p1[0] + t * dx
    closest_y = p1[1] + t * dy

    dist_sq = (centre[0] - closest_x) ** 2 + (centre[1] - closest_y) ** 2
    return dist_sq <= radius * radius


class CollisionDetector:
    """
    Checks the sword trail against all live fruits each frame and returns
    the ones that are hit.
    """

    def check(self, trail_points: List[Optional[Vec2]], fruits: List) -> List:
        """
        Return every unsliced fruit whose hitbox is intersected by any
        segment of *trail_points*.

        ``None`` entries in *trail_points* indicate a gap (hand disappeared
        for a frame) and are skipped without forming a cross-gap segment.
        """
        sliced: List = []

        # Build valid segments from consecutive non-None points
        segments: List[Tuple[Vec2, Vec2]] = []
        for i in range(len(trail_points) - 1):
            a, b = trail_points[i], trail_points[i + 1]
            if a is not None and b is not None:
                segments.append((a, b))

        if not segments:
            return sliced

        for fruit in fruits:
            if fruit.is_sliced:
                continue
            centre = (fruit.x, fruit.y)
            r = float(fruit.radius)

            for seg in segments:
                if _segment_circle_intersect(seg[0], seg[1], centre, r):
                    sliced.append(fruit)
                    break   # each fruit can only be sliced once

        return sliced
