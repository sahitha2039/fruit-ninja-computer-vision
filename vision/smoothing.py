"""
smoothing.py
------------
One Euro Filter for 2-D hand positions.

The One Euro Filter adapts its cutoff frequency based on the speed of
movement:
  - When the hand is still  → heavy smoothing, jitter disappears.
  - When the hand moves fast → light smoothing, no lag on quick swipes.

This beats a fixed-alpha EMA for hand tracking because slicing gestures
need both: stability at rest AND zero lag at speed.

Reference: Géry Casiez, Nicolas Roussel, Daniel Vogel. "1€ Filter: A
Simple Speed-based Low-pass Filter for Noisy Input in Interactive
Systems." CHI 2012.

Parameters (tune these if needed)
----------
min_cutoff : float
    Minimum cutoff frequency in Hz.  Lower = smoother when still,
    but more lag.  0.5–1.5 is typical for hand tracking.
beta : float
    Speed coefficient.  Higher = less lag during fast motion.
    0.05–0.2 is typical; raise if slicing feels sluggish.
d_cutoff : float
    Cutoff for the derivative (speed estimate).  1 Hz is a safe default.
"""
from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Internal 1-D filter
# ---------------------------------------------------------------------------

class _OneEuro1D:
    """One Euro Filter for a single scalar value."""

    def __init__(self, min_cutoff: float, beta: float, d_cutoff: float):
        self._min_cutoff = min_cutoff
        self._beta       = beta
        self._d_cutoff   = d_cutoff

        self._x_prev:  float | None = None   # last filtered value
        self._dx_prev: float        = 0.0    # last filtered derivative

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        """EMA alpha derived from a cutoff frequency and timestep."""
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, dt: float) -> float:
        if self._x_prev is None:
            self._x_prev = x
            return x

        # Derivative estimate (filtered)
        dx_raw    = (x - self._x_prev) / dt
        a_d       = self._alpha(self._d_cutoff, dt)
        dx        = a_d * dx_raw + (1.0 - a_d) * self._dx_prev

        # Adaptive cutoff: higher speed → higher cutoff → less smoothing
        cutoff    = self._min_cutoff + self._beta * abs(dx)
        a         = self._alpha(cutoff, dt)
        x_hat     = a * x + (1.0 - a) * self._x_prev

        self._x_prev  = x_hat
        self._dx_prev = dx
        return x_hat

    def reset(self):
        self._x_prev  = None
        self._dx_prev = 0.0


# ---------------------------------------------------------------------------
# Public 2-D smoother (drop-in replacement for PositionSmoother)
# ---------------------------------------------------------------------------

class PositionSmoother:
    """
    One Euro Filter for 2-D (x, y) hand positions.

    Drop-in replacement for the old EMA-based PositionSmoother — same
    ``smooth(pos)`` and ``reset()`` API.

    Parameters
    ----------
    min_cutoff : float
        Smoothing strength at rest (Hz).  Lower = smoother but more lag.
    beta : float
        How quickly smoothing relaxes during fast motion.  Higher = less
        lag on swipes.
    d_cutoff : float
        Cutoff for the internal derivative filter.  Leave at 1.0.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta:       float = 0.1,
        d_cutoff:   float = 1.0,
        # Legacy kwarg — ignored, kept so old code that passes alpha= still works
        alpha:      float | None = None,
    ):
        self._fx = _OneEuro1D(min_cutoff, beta, d_cutoff)
        self._fy = _OneEuro1D(min_cutoff, beta, d_cutoff)
        self._last_t: float | None = None

    # ------------------------------------------------------------------

    def smooth(self, pos, timestamp: float | None = None) -> tuple:
        """
        Accept a new ``(x, y)`` sample and return the filtered position.

        ``timestamp`` is optional seconds since epoch.  If omitted the
        filter uses a fixed assumed dt of 1/60 s (fine for 60 fps loops).
        """
        import time as _time
        now = timestamp if timestamp is not None else _time.monotonic()

        if self._last_t is None:
            dt = 1.0 / 60.0
        else:
            dt = max(now - self._last_t, 1e-6)   # guard against zero dt
        self._last_t = now

        x, y = float(pos[0]), float(pos[1])
        return (self._fx.filter(x, dt), self._fy.filter(y, dt))

    def reset(self):
        """Discard state — call when the hand disappears from frame."""
        self._fx.reset()
        self._fy.reset()
        self._last_t = None
