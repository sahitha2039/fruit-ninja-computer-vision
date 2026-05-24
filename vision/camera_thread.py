"""
camera_thread.py
----------------
Runs webcam capture and MediaPipe hand-tracking in a dedicated daemon
thread so the main game loop never blocks waiting for a camera frame.

Usage
-----
    cam = CameraThread(win_w=1280, win_h=720)
    cam.start()

    # Inside game loop (non-blocking):
    frame_rgb, raw_tips = cam.get_latest()

    cam.stop()
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import cv2
import numpy as np

from vision.hand_tracking import HandTracker


class CameraThread:
    """
    Background thread that continuously reads the webcam and runs
    MediaPipe.  The game loop calls ``get_latest()`` to receive the
    most recent processed frame without ever blocking.

    Parameters
    ----------
    cam_index : int
        OpenCV camera index (default 0).
    cap_w, cap_h : int
        Resolution fed to the camera capture.  Smaller = faster MediaPipe.
    win_w, win_h : int
        Resolution the frame is upscaled to before being stored (matches
        the pygame window so the game can blit it directly).
    max_hands : int
        Passed through to HandTracker.
    """

    def __init__(
        self,
        cam_index: int = 0,
        cap_w: int = 320,
        cap_h: int = 240,
        win_w: int = 1280,
        win_h: int = 720,
        max_hands: int = 2,
    ):
        self._cap_w  = cap_w
        self._cap_h  = cap_h
        self._win_w  = win_w
        self._win_h  = win_h

        # Webcam
        self._cap = cv2.VideoCapture(cam_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cap_w)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cap_h)
        # Keep the internal buffer tiny so we always get the newest frame
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.is_open: bool = self._cap.isOpened()

        # HandTracker is created inside _loop() so that MediaPipe's TFLite
        # runtime is initialised and used on the same thread (required).
        self._max_hands = max_hands
        self._tracker: HandTracker | None = None

        # Latest results — written by thread, read by game loop
        self._lock      = threading.Lock()
        self._frame_rgb: Optional[np.ndarray] = None   # win_w × win_h
        self._raw_tips:  list                 = []      # [(x,y), …] in cap space

        # Threading
        self._running = False
        self._thread  = threading.Thread(target=self._loop, daemon=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start the background capture thread."""
        self._running = True
        self._thread.start()

    def stop(self):
        """Signal the thread to stop and release resources."""
        self._running = False
        self._thread.join(timeout=2.0)
        self._cap.release()
        # _tracker is owned by the background thread; it closes itself in _loop

    def get_latest(self) -> tuple[Optional[np.ndarray], list]:
        """
        Return ``(frame_rgb, raw_tips)`` — the most recent processed
        result.  Always non-blocking.

        ``frame_rgb`` is an RGB numpy array sized ``(win_h, win_w, 3)``,
        or ``None`` if no frame has arrived yet.

        ``raw_tips`` is a list of ``(x_px, y_px)`` fingertip positions
        in **capture** (cap_w × cap_h) coordinate space — the caller is
        responsible for scaling to window coordinates.
        """
        with self._lock:
            return self._frame_rgb, list(self._raw_tips)

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    def _loop(self):
        # Create HandTracker HERE so MediaPipe lives entirely on this thread
        self._tracker = HandTracker(max_hands=self._max_hands)

        try:
            while self._running:
                ret, frame = self._cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                # Mirror so movements feel natural
                frame = cv2.flip(frame, 1)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Run MediaPipe on the small capture frame
                tips = self._tracker.get_all_fingertips(frame_rgb)

                # Upscale for display (fast — just a resize)
                display = cv2.resize(frame_rgb, (self._win_w, self._win_h))

                with self._lock:
                    self._frame_rgb = display
                    self._raw_tips  = tips
        finally:
            self._tracker.close()
