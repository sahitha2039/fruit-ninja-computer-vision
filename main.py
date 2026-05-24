"""
main.py  —  IRL Fruit Ninja
============================
Entry point.  Wires together:

  • Webcam capture     (OpenCV)
  • Hand tracking      (MediaPipe via vision/hand_tracking.py)
  • Swipe detection    (vision/swipe_detection.py)
  • Position smoothing (vision/smoothing.py)
  • Fruit physics      (game/physics.py)
  • Collision          (game/collision.py)
  • Visual effects     (game/effects.py)
  • HUD / menus        (game/ui.py)
  • Pygame rendering

Run:
    python main.py
"""
from __future__ import annotations

import os
import random
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import cv2
import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Path setup so sub-packages are importable regardless of cwd
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from game.collision import CollisionDetector
from game.effects   import ParticleSystem, ScreenShake, SliceTrail
from game.fruit     import Fruit, SlicedHalf, FRUIT_NAMES, FRUIT_TYPES
from game.physics   import PhysicsEngine
from game.ui        import UI
from vision.hand_tracking  import HandTracker
from vision.smoothing      import PositionSmoother
from vision.swipe_detection import SwipeDetector


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIN_W  = 1280
WIN_H  = 720
CAM_W  = 320
CAM_H  = 240
TARGET_FPS = 60

# Game states
MENU      = "menu"
PLAYING   = "playing"
GAME_OVER = "gameover"

# Difficulty parameters
INITIAL_SPAWN_INTERVAL = 1.6   # seconds between spawn waves
MIN_SPAWN_INTERVAL     = 0.65
SPAWN_RAMP             = 0.008 # reduce interval per wave
BOMB_CHANCE            = 0.10  # probability that a spawned object is a bomb
MAX_SIMULTANEOUS       = 9     # cap on live fruits

COMBO_TIMEOUT = 1.5            # seconds before combo resets
LIVES_START   = 3


# ---------------------------------------------------------------------------
# Sound generation (simple beeps using pygame.sndarray)
# ---------------------------------------------------------------------------

def _make_beep(freq: float, duration_ms: int, volume: float = 0.4) -> pygame.mixer.Sound:
    """Synthesise a simple sine-wave beep."""
    sample_rate = 44100
    n_samples   = int(sample_rate * duration_ms / 1000)
    t           = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
    wave        = (np.sin(2 * np.pi * freq * t) * volume * 32767).astype(np.int16)
    # Stereo
    stereo = np.column_stack([wave, wave])
    sound  = pygame.sndarray.make_sound(stereo)
    return sound


def _load_sounds() -> dict:
    """Create synthesised sound effects."""
    try:
        return {
            "slice":   _make_beep(880,  80,  0.35),
            "combo":   _make_beep(1200, 120, 0.4),
            "bomb":    _make_beep(120,  300, 0.5),
            "miss":    _make_beep(220,  180, 0.3),
            "gameover":_make_beep(100,  600, 0.45),
        }
    except Exception:
        return {}   # silently degrade if audio is unavailable


# ---------------------------------------------------------------------------
# Main game class
# ---------------------------------------------------------------------------

class FruitNinjaGame:

    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Welcome to IRL Fruit Ninja")
        self.clock  = pygame.time.Clock()

        # --- Webcam ---
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[WARNING] Could not open webcam — running in demo mode.")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

        # --- Vision ---
        self.hand_tracker = HandTracker()
        self.swipe        = SwipeDetector(velocity_threshold=380.0)
        self.swipe2       = SwipeDetector(velocity_threshold=380.0)
        self.smoother     = PositionSmoother(alpha=0.38)
        self.smoother2    = PositionSmoother(alpha=0.38)

        # --- Game systems ---
        self.physics   = PhysicsEngine(WIN_W, WIN_H)
        self.collision = CollisionDetector()
        self.particles = ParticleSystem()
        self.shake     = ScreenShake()
        self.trail     = SliceTrail(max_points=24)
        self.trail2    = SliceTrail(max_points=24)
        self.ui        = UI(WIN_W, WIN_H)

        # --- State ---
        self.state      = MENU
        self.fruits:     list[Fruit]      = []
        self.halves:     list[SlicedHalf] = []
        self.score       = 0
        self.high_score  = 0
        self.lives       = LIVES_START
        self.combo       = 0
        self.last_slice  = 0.0
        self.spawn_timer = 0.0
        self.spawn_interval = INITIAL_SPAWN_INTERVAL

        # Webcam background surface (updated each frame)
        self._cam_surf: pygame.Surface | None = None

        # Sounds
        self._sounds = _load_sounds()

        self.running = True

    # ------------------------------------------------------------------
    # Sound helpers
    # ------------------------------------------------------------------

    def _play(self, name: str):
        s = self._sounds.get(name)
        if s:
            try:
                s.play()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def _start_game(self):
        self.state          = PLAYING
        self.fruits         = []
        self.halves         = []
        self.score          = 0
        self.lives          = LIVES_START
        self.combo          = 0
        self.last_slice     = 0.0
        self.spawn_timer    = 0.0
        self.spawn_interval = INITIAL_SPAWN_INTERVAL
        self.particles.clear()
        self.trail.clear()
        self.shake.reset()
        self.swipe.reset()
        self.swipe2.reset()
        self.smoother.reset()
        self.smoother2.reset()
        self.trail2.clear()
        self.ui.popups.clear()

    def _game_over(self):
        self.high_score = max(self.high_score, self.score)
        self.state      = GAME_OVER
        self._play("gameover")

    # ------------------------------------------------------------------
    # Fruit spawning
    # ------------------------------------------------------------------

    def _spawn_wave(self):
        """Launch 1–3 fruits in a coordinated wave."""
        if len(self.fruits) >= MAX_SIMULTANEOUS:
            return

        count = random.randint(1, 4)
        for _ in range(count):
            if len(self.fruits) >= MAX_SIMULTANEOUS:
                break

            is_bomb  = random.random() < BOMB_CHANCE
            ftype    = "bomb" if is_bomb else random.choice(FRUIT_NAMES)

            # Horizontal position
            x  = random.randint(80, WIN_W - 80)

            # Upward velocity — enough to reach ~60-80 % of screen height
            vy = random.uniform(-35, -30)
            vx = random.uniform(-2.5, 2.5)

            self.fruits.append(Fruit(ftype, x, WIN_H + 60, vx, vy))

    # ------------------------------------------------------------------
    # Update logic
    # ------------------------------------------------------------------

    def _update_playing(
        self,
        dt: float,
        hands: list,
        is_swiping_list: list,
        velocities: list,
    ):
        now = time.monotonic()

        # Combo timeout
        if self.combo > 0 and (now - self.last_slice) > COMBO_TIMEOUT:
            self.combo = 0

        # Spawn timer
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self._spawn_wave()
            self.spawn_interval = max(
                MIN_SPAWN_INTERVAL,
                self.spawn_interval - SPAWN_RAMP,
            )

        # Physics
        self.physics.update(self.fruits, dt)
        self.physics.update_halves(self.halves, dt)

        # Remove dead halves
        self.halves = [h for h in self.halves if not h.is_dead()]

        # Fruits that fell off screen
        fallen = [f for f in self.fruits if self.physics.is_off_screen(f)]
        for f in fallen:
            self.fruits.remove(f)
            if not f.is_sliced and f.type != "bomb":
                self.lives -= 1
                self._play("miss")
                self.shake.trigger(8, 0.2)
                if self.lives <= 0:
                    self.lives = 0
                    self._game_over()
                    return

        # Particle / shake update
        self.particles.update(dt)
        self.shake.update(dt)
        self.ui.update_popups(dt)

        # Collision — check each active hand independently
        swipe_detectors = [self.swipe, self.swipe2]
        trails          = [self.trail, self.trail2]

        for i, (hand_pos, is_swiping, velocity) in enumerate(
            zip(hands, is_swiping_list, velocities)
        ):
            if not (hand_pos and is_swiping):
                continue

            trail_pts = trails[i].get_points()
            sliced    = self.collision.check(trail_pts, self.fruits)

            for fruit in sliced:
                if fruit.is_sliced:
                    continue
                fruit.is_sliced = True

                if fruit.type == "bomb":
                    self._play("bomb")
                    self.shake.trigger(25, 0.5)
                    self.particles.explode(fruit.x, fruit.y,
                                          FRUIT_TYPES["bomb"]["juice"], 40)
                    self.combo = 0
                    self.lives -= 1
                    if self.lives <= 0:
                        self.lives = 0
                        if fruit in self.fruits:
                            self.fruits.remove(fruit)
                        self._game_over()
                        return
                else:
                    self.combo   += 1
                    self.last_slice = now

                    pts      = 10 * self.combo
                    self.score += pts

                    # Effects
                    self.shake.trigger(5, 0.15)
                    color = FRUIT_TYPES[fruit.type]["juice"]
                    self.particles.splash(fruit.x, fruit.y, color, 22)
                    self.ui.add_popup(fruit.x, fruit.y, pts, self.combo)

                    # Halves
                    h1, h2 = fruit.slice(swipe_detectors[i].get_angle(), velocity)
                    self.halves.extend([h1, h2])

                    if self.combo >= 2:
                        self._play("combo")
                    else:
                        self._play("slice")

                if fruit in self.fruits:
                    self.fruits.remove(fruit)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_menu(self):
        self.ui.draw_menu(self.screen, self.high_score)

    def _render_game_over(self):
        self.ui.draw_game_over(self.screen, self.score, self.high_score)

    def _render_playing(self, hands: list, is_swiping_list: list):
        ox, oy = self.shake.get_offset()
        offset  = (ox, oy)

        # --- Webcam background ---
        if self._cam_surf is not None:
            self.screen.blit(self._cam_surf, offset)
        else:
            self.screen.fill((25, 25, 50))

        # --- Darkening overlay for readability ---
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 55))
        self.screen.blit(ov, offset)

        # --- Fruits ---
        for f in self.fruits:
            f.draw(self.screen, offset)

        # --- Sliced halves ---
        for h in self.halves:
            h.draw(self.screen, offset)

        # --- Particles ---
        self.particles.draw(self.screen, offset)

        # --- Sword trails and hand dots (one per hand) ---
        trails = [self.trail, self.trail2]
        for i, (hand_pos, is_swiping) in enumerate(zip(hands, is_swiping_list)):
            trails[i].draw(self.screen, is_swiping)
            if hand_pos:
                px = int(hand_pos[0]) + ox
                py = int(hand_pos[1]) + oy
                pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 9, 2)
                if is_swiping:
                    pygame.draw.circle(self.screen, (100, 220, 255), (px, py), 15, 1)

        # --- HUD ---
        self.ui.draw_hud(self.screen, self.score, self.lives, self.combo)

    # ------------------------------------------------------------------
    # Webcam frame
    # ------------------------------------------------------------------

    def _capture_frame(self):
        """Read a frame, run hand tracking, return (cam_surface, hands, velocities).

        *hands* is a list of up to 2 smoothed (x, y) positions (or None per slot).
        *velocities* is a matching list of (vx, vy) tuples.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None, [None, None], [(0.0, 0.0), (0.0, 0.0)]

        # Mirror
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        scale_x = WIN_W / frame_rgb.shape[1]
        scale_y = WIN_H / frame_rgb.shape[0]

        raw_tips = self.hand_tracker.get_all_fingertips(frame_rgb)

        smoothers = [self.smoother, self.smoother2]
        swipes    = [self.swipe,    self.swipe2]
        trails    = [self.trail,    self.trail2]

        hands      = []
        velocities = []

        for i in range(2):
            if i < len(raw_tips):
                scaled   = (raw_tips[i][0] * scale_x, raw_tips[i][1] * scale_y)
                pos      = smoothers[i].smooth(scaled)
                vel      = swipes[i].update(pos)
                trails[i].add_point(pos, vel)
                hands.append(pos)
                velocities.append(vel)
            else:
                smoothers[i].reset()
                trails[i].add_point(None, (0.0, 0.0))
                hands.append(None)
                velocities.append((0.0, 0.0))

        # Convert to pygame surface (resize to window)
        display_frame = cv2.resize(frame_rgb, (WIN_W, WIN_H))
        cam_surf = pygame.surfarray.make_surface(
            display_frame.transpose(1, 0, 2)
        )
        return cam_surf, hands, velocities

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.running = False
                elif event.key == pygame.K_ESCAPE:
                    if self.state in (PLAYING, GAME_OVER):
                        self.state = MENU
                    else:
                        self.running = False
                elif event.key == pygame.K_SPACE:
                    if self.state in (MENU, GAME_OVER):
                        self._start_game()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state in (MENU, GAME_OVER):
                    self._start_game()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        while self.running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0
            dt = min(dt, 0.05)   # cap to avoid physics explosions on lag spikes

            self._handle_events()
            if not self.running:
                break

            # Capture + hand tracking every frame
            cam_surf, hands, velocities = self._capture_frame()
            if cam_surf is not None:
                self._cam_surf = cam_surf

            is_swiping  = self.swipe.is_swiping()
            is_swiping2 = self.swipe2.is_swiping()

            # State machine
            if self.state == PLAYING:
                self._update_playing(dt, hands, [is_swiping, is_swiping2], velocities)
                self._render_playing(hands, [is_swiping, is_swiping2])
            elif self.state == MENU:
                self._render_menu()
            elif self.state == GAME_OVER:
                self._render_game_over()

            # FPS counter (small, top-centre)
            fps_text = pygame.font.Font(None, 22).render(
                f"{self.clock.get_fps():.0f} fps", True, (120, 120, 160)
            )
            self.screen.blit(fps_text, (WIN_W // 2 - 24, 4))

            pygame.display.flip()

        self.cap.release()
        self.hand_tracker.close()
        pygame.quit()
        sys.exit(0)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    game = FruitNinjaGame()
    game.run()
