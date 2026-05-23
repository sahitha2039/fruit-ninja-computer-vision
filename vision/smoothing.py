"""
smoothing.py
------------
Exponential Moving Average (EMA) smoother for 2-D hand positions.
Eliminates jitter from MediaPipe's raw landmark coordinates without
adding noticeable latency.
"""


class PositionSmoother:
    """
    EMA smoother: ``smoothed = alpha * new + (1 - alpha) * prev``

    Parameters
    ----------
    alpha : float
        Blending factor in (0, 1].  Higher = more responsive (less smooth);
        lower = smoother (more lag).  0.4 is a good default for 30+ FPS.
    """

    def __init__(self, alpha: float = 0.4):
        if not (0 < alpha <= 1):
            raise ValueError("alpha must be in (0, 1]")
        self._alpha = alpha
        self._x: float | None = None
        self._y: float | None = None

    # ------------------------------------------------------------------

    def smooth(self, pos) -> tuple:
        """
        Accept a new ``(x, y)`` sample and return the smoothed position.
        On the first call the raw position is returned as-is (warm-up).
        """
        x, y = float(pos[0]), float(pos[1])

        if self._x is None:
            self._x, self._y = x, y
        else:
            self._x = self._alpha * x + (1 - self._alpha) * self._x
            self._y = self._alpha * y + (1 - self._alpha) * self._y

        return (self._x, self._y)

    def reset(self):
        """Discard accumulated state (call when hand disappears)."""
        self._x = self._y = None
