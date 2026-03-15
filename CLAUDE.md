# niNE Project - Claude Code Instructions

## Project Overview

**niNE** is a multiplayer 3D game engine built with Panda3D (Python), featuring a D&D 5e game mode.

**Current Branch:** `dnd-gamemode-v0.1.0-alpha` - D&D mode development branch

## Architecture Summary

### Core Technologies
- **Panda3D** - 3D rendering, physics, task manager
- **asyncio** - Network communication
- **SQLite** - Database (nine.db)
- **SSL/TLS** - Encrypted client-server communication

### Key Directories
```
nine/
├── core/           # Core systems (plugins, events, ECS, audio, config)
├── server/         # Game server (game_server.py)
├── client/         # Game client
├── ui/             # UI components (manager, theme, menus)
├── plugins/        # Plugin system
│   ├── chat/       # Chat system
│   ├── inventory/  # Inventory & equipment
│   ├── stats/      # Player stats
│   ├── combat/     # D&D combat system
│   ├── npc/        # NPC system (ECS-based)
│   └── dnd/        # D&D character system
└── assets/         # Models, textures, sounds
```

## Plugin System

Plugins use prefix naming convention:
- `sh_*.py` - **Sh**ared (client + server)
- `cl_*.py` - **Cl**ient only
- `sv_*.py` - **S**er**v**er only

### PluginModule Usage
```python
from nine.core.plugins import PluginModule

class MyModule(PluginModule):
    def on_load(self):
        # Use self.app (NOT self.base!) for ShowBase
        self.app.taskMgr.add(self.update, "my-task")
        self.event_manager.subscribe("event", self.handler)

    def on_unload(self):
        self.event_manager.unsubscribe("event", self.handler)
```

**CRITICAL:** In PluginModule classes, use `self.app` instead of `self.base` to access ShowBase.

## Current Systems Status (March 2026)

| System | Status | Plugin |
|--------|--------|--------|
| Characters | Working | `nine.dnd` |
| Chat | Working | `nine.chat` |
| Inventory | Working | `nine.inventory` |
| Equipment | Working | `nine.inventory` |
| Character Sheet | Working | `nine.inventory` |
| Combat | Integrated | `nine.combat` |
| NPC AI | Working | `nine.npc` (LOD, needs→behavior, traits, wander, schedules, ECS player query) |
| NPC Models | Working | Shared Mixamo animations, knight/shopkeeper/villager BAM models |
| NPC Physics | Working | PhysicsTier.SIMPLE — velocity-based, world bounds, kill plane |
| ECS | Unified | Single PooledECSWorld, all components in core/components.py, flush() |
| Game Time | Working | Day/night cycle in `game_server.py` |
| Audio | Working | `nine.dnd.audio` |
| **UI (CEF)** | **Working** | `nine.ui.cef_manager` |

## UI System

### UI Backends
The project supports multiple UI backends configured via `config.json`:

| Backend | Status | Description |
|---------|--------|-------------|
| `cef` | **Recommended** | CEF offscreen Chromium 131 via cef-capi-py |
| `playwright` | Legacy | Screenshot-based Chromium (high latency) |
| `directgui` | Fallback | Native Panda3D DirectGUI |

### CEF UI Architecture
```
nine/ui/
├── cef_manager.py        # CEF offscreen rendering (raw BGRA pixels)
├── webview_api.py        # Python API for JavaScript calls
└── web/                  # HTML/CSS/JS UI assets
    ├── index.html
    ├── css/              # Styles (theme.css, main.css, components.css, animations.css)
    ├── js/               # JavaScript (api.js, main.js, panel-manager.js, components/)
    └── templates/        # HTML templates (NO inline <style>!)
```

### Key UI Files
- `nine/ui/cef_manager.py` - CEF offscreen rendering, V8 extension bridge
- `nine/ui/webview_api.py` - JavaScript-to-Python API bridge
- `nine/ui/web/js/api.js` - `PythonAPI` class wrapping V8 `pyCall()`

### JavaScript API
```javascript
// JS → Python (via V8 extension window.pyapi)
await PythonAPI.getApi().exit_game()
await PythonAPI.getApi().attempt_login(ip, name, password)
await PythonAPI.getApi().send_chat_message(msg)
await PythonAPI.getApi().create_character(charData)
```

### Config
```json
{
  "ui_backend": "cef",  // or "playwright" or "directgui"
  ...
}
```

## Common Issues & Solutions

### 1. Unicode Errors (Windows cp1251)
**Problem:** Emojis in logs cause `UnicodeEncodeError`
**Solution:** Remove emojis from logger.info/debug calls

### 2. globalClock Import
**Correct:**
```python
from panda3d.core import ClockObject
globalClock = ClockObject.getGlobalClock()
```
**Wrong:** `from direct.showbase.ShowBase import globalClock`

### 3. self.base vs self.app
- `PluginModule` classes: use `self.app`
- `BaseUIComponent` classes: use `self.base` (inherited from ui_manager)

## Event System

Key events for D&D mode:

### Combat Events
- `combat_started` - Combat begins
- `combat_ended` - Combat ends
- `combat_turn_start` - Turn starts
- `combat_action_result` - Action result

### NPC Events
- `world_state_received` - NPC data from server
- `npc_interact_request` - Player interacts with NPC

### Chat Commands (DM/Admin)
- `/startcombat [radius]` - Start combat
- `/endcombat` - End combat
- `/spawn <template> [x] [y] [z]` - Spawn NPC

## Documentation

- `docs/DEVELOPMENT.md` - Development roadmap & status
- `docs/PLUGINS.md` - Plugin system documentation
- `docs/EVENT_API.md` - Event reference
- `docs/BACKLOG.md` - Known issues
- `docs/ADMIN_GUIDE.md` - Server admin guide

## Running the Project

```bash
# Server
python -m nine.server.game_server

# Client
python client.py

# Dev client (auto-connect)
python dev_client.py
```

## Git Workflow

- Main development on `dnd-gamemode-v0.1.0-alpha` branch
- Core niNE changes should be minimal (plugin-based architecture)
- Commit messages in English
