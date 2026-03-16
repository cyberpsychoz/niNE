# niNE

Multiplayer 3D game engine built with Panda3D and Python.

## Features

- **Panda3D Rendering** — 3D world with lighting, skybox, post-processing
- **Client-Server Architecture** — SSL/TLS encrypted multiplayer with asyncio networking
- **Plugin System** — Modular architecture with hot-loadable plugins (`sh_`, `cl_`, `sv_` prefixes)
- **ECS (Entity-Component-System)** — Unified PooledECSWorld with component registry and systems
- **Physics** — PhysicsTier system (FULL for players, SIMPLE for NPCs, NONE for sleeping)
- **CEF Web UI** — Chromium-based UI via cef-capi-py with JS-Python bridge
- **NPC AI** — LOD-based AI with needs, behaviors, wander, schedules
- **Living World** — Day/night cycle, NPC routines, spatial awareness
- **Chat System** — In-game chat with commands
- **Inventory & Equipment** — Slot-based equipment system
- **Player Stats** — Configurable stat tracking

## Architecture

```
nine/
├── core/           # Engine core (ECS, physics, events, plugins, networking)
├── server/         # Game server
├── ui/             # UI system (CEF, DirectGUI, web assets)
└── plugins/        # Plugin modules
    ├── chat/         # Chat system
    ├── inventory/    # Inventory & equipment
    ├── stats/        # Player statistics
    ├── npc/          # NPC AI & rendering
    ├── living_npc/   # Living world behaviors
    ├── lighting/     # Dynamic lighting
    ├── skybox/       # Skybox rendering
    ├── postfx/       # Post-processing effects
    ├── world_config/ # World configuration
    └── quests/       # Quest journal
```

## Quick Start

```bash
# Install dependencies
pip install panda3d panda3d-gltf

# Server
python -m nine.server.game_server

# Client
python client.py

# Dev client (auto-connect)
python dev_client.py
```

## UI Backends

| Backend | Description |
|---------|-------------|
| `cef` | CEF offscreen Chromium (recommended) |
| `directgui` | Native Panda3D DirectGUI (fallback) |

Set via `config.json`: `"ui_backend": "cef"`

## Plugin Development

```python
from nine.core.plugins import PluginModule

class MyPlugin(PluginModule):
    def on_load(self):
        self.app.taskMgr.add(self.update, "my-task")
        self.event_manager.subscribe("event", self.handler)

    def on_unload(self):
        self.event_manager.unsubscribe("event", self.handler)
```

Plugins use prefix naming: `sh_` (shared), `cl_` (client-only), `sv_` (server-only).

## Game Modes

Game-specific content lives in separate branches:
- `dnd-gamemode-v0.1.0-alpha` — D&D 5e tabletop RPG mode

## License

See [LICENSE](LICENSE).
