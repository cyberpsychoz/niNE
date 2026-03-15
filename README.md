# niNE — Multiplayer 3D Game Engine

> **Branch:** `dnd-gamemode-v0.1.0-alpha` — D&D 5e game mode development

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Panda3D](https://img.shields.io/badge/engine-Panda3D%201.10-orange.svg)
![UI](https://img.shields.io/badge/UI-CEF%20Chromium%20131-green.svg)

Multiplayer 3D game engine built with Panda3D, featuring a D&D 5e game mode with turn-based combat, NPC AI, and a living world system.

## Architecture

- **Unified ECS** — single `PooledECSWorld` for players and NPC with entity pooling
- **Physics Tiers** — FULL (Panda3D collision) for players, SIMPLE (velocity-based) for NPC
- **Plugin System** — modular GMod-inspired architecture with `sh_`/`cl_`/`sv_` naming
- **CEF UI** — offscreen Chromium 131 via cef-capi-py, HTML/CSS/JS overlay
- **Networking** — asyncio + SSL/TLS encrypted client-server communication

## Current Status (March 2026)

| System | Status |
|--------|--------|
| D&D Characters | 6 races, 12 classes, 8-step creation wizard |
| Combat | Turn-based with initiative, action economy, D&D 5e rules |
| NPC AI | LOD system, patrol, wander, needs, personality, schedules |
| NPC Physics | PhysicsTier.SIMPLE, world bounds, kill plane |
| Living World | Needs, relationships, memories, daily schedules |
| Inventory & Equipment | D&D items, equipment slots, character sheet |
| Spells | 35 spells, slots, concentration |
| UI | CEF offscreen, HTML/CSS/JS, game HUD, DM panel |
| Audio | BGM playlists, ambient, SFX, footsteps |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate SSL certs (development)
mkdir certs
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem \
  -days 365 -nodes -subj "/CN=localhost"

# Run server
python -m nine.server.game_server

# Run client
python client.py
```

## Documentation

| Document | Description |
|----------|-------------|
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development roadmap and status |
| [ECS_ARCHITECTURE.md](docs/ECS_ARCHITECTURE.md) | Unified ECS architecture |
| [PLUGINS.md](docs/PLUGINS.md) | Plugin system documentation |
| [EVENT_API.md](docs/EVENT_API.md) | Event reference |
| [NPC_SYSTEM.md](docs/NPC_SYSTEM.md) | NPC system documentation |
| [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | Server administration |
| [BACKLOG.md](docs/BACKLOG.md) | Known issues |

## Project Structure

```
nine/
  core/           # ECS, physics, components, systems, networking
  server/         # Game server
  client/         # Game client
  ui/             # CEF manager, webview API, HTML/CSS/JS
  plugins/        # Plugin system
    chat/         # Chat
    combat/       # D&D combat (turn manager, dice, action economy)
    npc/          # NPC (AI, renderer, living world)
    inventory/    # Inventory, equipment, items
    dnd/          # D&D character system
    spells/       # Spell system
    conditions/   # D&D conditions
    quests/       # Quest journal
    rest/         # Short/long rest
  assets/         # Models, textures, sounds
```

## License

MIT License — see [LICENSE](LICENSE).
