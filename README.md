# 🍉 IRL Fruit Ninja

A real-time computer-vision game that turns your webcam and your real hand into a fruit-slicing blade.

---

## Features

| Phase | What's included |
|-------|----------------|
| 1 | Webcam feed + MediaPipe hand tracking |
| 2 | Glowing sword-trail with EMA smoothing |
| 3 | Fruit physics — projectile motion + gravity + rotation |
| 4 | Line-segment collision detection (no missed slices at high speed) |
| 5 | Juice-splatter particles, slice halves, screen shake, synthesised sounds |
| 6 | Score, combo multiplier, 3 lives, difficulty scaling, high-score tracking |
| 7 | Emoji fruit rendering (Pillow), FPS display, bomb objects |

---

## Quick start

### 1  — Install Python 3.10 +

Download from https://python.org if needed.

### 2  — Install dependencies

```bash
cd fruit_ninja
pip install -r requirements.txt
```

> **Emoji fruits** require Pillow and a colour-emoji font on your system:
> - **macOS** — Apple Color Emoji is built in ✅
> - **Windows** — Segoe UI Emoji is built in ✅
> - **Linux** — install with `sudo apt install fonts-noto-color-emoji`
>
> If no emoji font is found the game falls back to coloured circles with short labels — fully playable either way.

### 3  — Run the game

```bash
python main.py
```

---

## How to play

1. **Stand in front of your webcam** — your hand should be clearly visible.
2. **Raise your hand** into frame — you'll see a white dot tracking your index fingertip.
3. **Swipe fast** across a fruit to slice it.  Slow motion won't register.
4. **Avoid the 💣 bombs** — slicing one costs a life.
5. **Missing a fruit** (letting it fall off-screen) also costs a life.
6. **3 lives** then game over.  Combos multiply your score!

### Controls

| Key | Action |
|-----|--------|
| `Space` / Click | Start / restart |
| `Esc` | Pause / return to menu |
| `Q` | Quit |

---

## Project layout

```
fruit_ninja/
├── main.py                 # Entry point & game loop
│
├── game/
│   ├── fruit.py            # Fruit, SlicedHalf, emoji rendering
│   ├── physics.py          # Gravity & position updates
│   ├── collision.py        # Line-segment ↔ circle intersection
│   ├── effects.py          # Particles, ScreenShake, SliceTrail
│   └── ui.py               # HUD, menus, score popups
│
├── vision/
│   ├── hand_tracking.py    # MediaPipe Hands wrapper
│   ├── swipe_detection.py  # Velocity-threshold swipe detector
│   └── smoothing.py        # EMA position smoother
│
├── assets/                 # (reserved for custom sounds/images)
├── requirements.txt
└── README.md
```

---

## Tuning tips

| Parameter | File | What it does |
|-----------|------|-------------|
| `velocity_threshold` | `main.py` | How fast you must swipe to slice (px/s) |
| `BOMB_CHANCE` | `main.py` | Probability a spawn is a bomb (0–1) |
| `INITIAL_SPAWN_INTERVAL` | `main.py` | Seconds between fruit waves at start |
| `alpha` in `PositionSmoother` | `main.py` | Trail smoothness vs. responsiveness |
| `MAX_SIMULTANEOUS` | `main.py` | Cap on fruits on screen at once |

---

## Troubleshooting

**No webcam detected** — the game prints a warning and runs in "demo mode" (no background feed, fruits still spawn).

**Hand not detected** — ensure good lighting, keep your hand in frame, and avoid wearing gloves.

**Low FPS** — reduce `WIN_W` / `WIN_H` in `main.py` or lower `MAX_SIMULTANEOUS`.

**No emoji** on Linux — `sudo apt install fonts-noto-color-emoji` then restart the game.

---

## Possible extensions

- Dual-hand mode (track both hands)
- Power-ups: freeze time, giant blade, double score
- Background music that speeds up as combo grows
- AR overlay using a projector or secondary display
- Online leaderboard via a simple REST API
