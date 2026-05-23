"""
hand_tracking.py
----------------
MediaPipe Hands wrapper. Returns the index-fingertip position
(landmark 8) in pixel coordinates for each frame.
"""
import mediapipe as mp
import numpy as np


class HandTracker:
    """
    Wraps MediaPipe Hands to extract the index-fingertip position
    from an RGB frame.  Also provides the palm centre (landmark 0)
    and mid-finger tip (landmark 12) for richer swipe data.
    """

    # MediaPipe landmark indices
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_TIP = 12
    WRIST = 0

    def __init__(
        self,
        max_hands: int = 1,
        detection_confidence: float = 0.6,
        tracking_confidence: float = 0.5,
    ):
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._last_result = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, frame_rgb: np.ndarray):
        """Run MediaPipe on *frame_rgb* and cache the result."""
        self._last_result = self._hands.process(frame_rgb)

    def get_fingertip(self, frame_rgb: np.ndarray):
        """
        Process *frame_rgb* and return the index-fingertip position as
        ``(x_px, y_px)`` in the frame's coordinate space, or ``None``
        when no hand is visible.
        """
        h, w = frame_rgb.shape[:2]
        self.process(frame_rgb)

        if not (
            self._last_result
            and self._last_result.multi_hand_landmarks
        ):
            return None

        # Use the first detected hand
        landmarks = self._last_result.multi_hand_landmarks[0].landmark
        lm = landmarks[self.INDEX_FINGER_TIP]
        return (lm.x * w, lm.y * h)

    def get_blade_points(self, frame_rgb: np.ndarray):
        """
        Return a richer set of hand points — index tip, middle tip,
        and wrist — as a dict, or *None* when no hand is visible.
        """
        h, w = frame_rgb.shape[:2]
        self.process(frame_rgb)

        if not (
            self._last_result
            and self._last_result.multi_hand_landmarks
        ):
            return None

        lms = self._last_result.multi_hand_landmarks[0].landmark

        def to_px(lm):
            return (lm.x * w, lm.y * h)

        return {
            "index_tip": to_px(lms[self.INDEX_FINGER_TIP]),
            "middle_tip": to_px(lms[self.MIDDLE_FINGER_TIP]),
            "wrist": to_px(lms[self.WRIST]),
        }

    def close(self):
        """Release MediaPipe resources."""
        self._hands.close()
