# ISWC 2026 AR Glass Demo

International conference demo application combining a 2D menu launcher with a VR sniper mini-game, controlled via serial input from custom hardware.

## Attribution

This project builds on [pyvr-example](https://github.com/DaFluffyPotato/pyvr-example) by **DaFluffyPotato (Chris Maltby)**.

The following components are derived from or based on that repository:

| Component | Location |
|-----------|----------|
| Game / VR library | `mgllib/` |
| 3D models | `data/models/` |
| Shaders | `data/shaders/` |
| Sound effects | `data/sfx/` |
| Textures & font | `data/textures/`, `data/rubik_medium.ttf` |

Attribution is also recorded in code: see [`credits.py`](credits.py) and [`mgllib/__init__.py`](mgllib/__init__.py).

Original project reference: https://github.com/DaFluffyPotato/pyvr-example

## Project structure

```
.
├── main.py              # Entry point (menu launcher)
├── pico_sniper.py       # VR sniper mini-game
├── mgllib/              # VR game library (from pyvr-example)
├── assets/
│   ├── icons/           # Menu icons
│   └── videos/          # Demo videos
├── data/
│   ├── models/          # 3D models (from pyvr-example + balloon)
│   ├── shaders/         # GLSL shaders (from pyvr-example)
│   ├── sfx/             # Sound effects (from pyvr-example)
│   └── textures/        # Textures (from pyvr-example)
└── docs/images/         # Documentation images (from pyvr-example)
```

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.10+ and a VR headset with OpenXR support for the sniper game.

## Usage

```bash
python main.py
```

The launcher opens in a window. Navigate the menu with serial/controller input and select **Pico Sniper** to launch the VR mini-game.

Serial ports are configured in `main.py` and `pico_sniper.py` (`/dev/cu.usbmodem...`). Adjust or leave empty for keyboard-only debugging.

## Original pyvr-example notes

The upstream project includes additional documentation on VR controls, architecture, and OpenXR compatibility. See [`docs/images/architecture.png`](docs/images/architecture.png) for the original architecture diagram.

![example](docs/images/example.gif)
