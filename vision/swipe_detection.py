"""
swipe_detection.py
------------------
Determines whether the current hand motion qualifies as a slicing swipe,
and exposes velocity, speed, and direction angle.
"""
import math
import time
from collections import deque


class SwipeDetector:
    """
    Maintains a short history of (position, timestamp) samples and
    derives velocity, speed, and swipe state from them.

    A swipe is detected when the smoothed speed exceeds *velocity_threshold*
    pixels per second.
    """

    def __init__(
        self,
        history_size: int = 8,
        velocity_threshold: float = 400.0,   # px / second
    ):
        self._history_size = history_size
        self._threshold = velocity_threshold
        self._history: deque = deque(maxlen=history_size)

        # Most-recently computed state
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._speed: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, pos) -> tuple:
        """
        Record *pos* ``(x, y)`` with the current timestamp and recompute
        velocity.  Returns ``(vx, vy)`` in px / second.
        """
        now = time.monotonic()
        self._history.append((pos, now))

        if len(self._history) >= 2:
            (x0, y0), t0 = self._history[0]
            (x1, y1), t1 = self._history[-1]
            dt = t1 - t0
            if dt > 0:
                self._vx = (x1 - x0) / dt
                self._vy = (y1 - y0) / dt
                self._speed = math.hypot(self._vx, self._vy)
            else:
                self._vx = self._vy = self._speed = 0.0
        else:
            self._vx = self._vy = self._speed = 0.0

        return (self._vx, self._vy)

    def is_swiping(self) -> bool:
        """Return *True* if the current speed exceeds the threshold."""
        return self._speed >= self._threshold

    def get_velocity(self) -> tuple:
        """Return ``(vx, vy)`` in px / second."""
        return (self._vx, self._vy)

    def get_speed(self) -> float:
        """Return scalar speed in px / second."""
        return self._speed

    def get_angle(self) -> float:
        """Return the swipe direction in radians (atan2(vy, vx))."""
        return math.atan2(self._vy, self._vx)

    def reset(self):
        """Clear history and reset state."""
        self._history.clear()
        self._vx = self._vy = self._speed = 0.0
