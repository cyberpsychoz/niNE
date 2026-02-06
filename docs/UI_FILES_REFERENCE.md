# UI Files Reference

## UI Backends

The project supports multiple UI backends. Set in `config.json`:

```json
{
  "ui_backend": "playwright"  // Recommended
}
```

| Backend | Status | Files |
|---------|--------|-------|
| `playwright` | **Recommended** | `nine/ui/playwright_manager.py`, `nine/ui/web/` |
| `directgui` | Fallback | `nine/ui/manager.py`, `nine/ui/*.py` |

---

## Playwright UI (Recommended)

### Core Files

```
nine/ui/
├── playwright_manager.py    # Chromium offscreen rendering
├── webview_api.py          # Python API for JavaScript
└── web/                    # Web UI assets
    ├── index.html          # Root HTML
    ├── css/
    │   ├── theme.css       # BG1-style theme
    │   ├── main.css        # Layout
    │   ├── components.css  # UI components
    │   └── animations.css  # Animations
    ├── js/
    │   ├── api.js          # Python API wrapper
    │   ├── router.js       # SPA router
    │   ├── main.js         # Entry point
    │   └── components/     # Screen components
    │       ├── MainMenu.js
    │       ├── LoginMenu.js
    │       ├── SettingsMenu.js
    │       ├── InGameMenu.js
    │       ├── ChatWindow.js
    │       ├── CharacterSelect.js
    │       └── CharacterCreate.js
    └── templates/          # HTML templates
        ├── main-menu.html
        ├── login-menu.html
        ├── settings-menu.html
        ├── in-game-menu.html
        ├── character-select.html
        └── character-create.html
```

### JavaScript API

```javascript
// api.js provides PythonAPI class
const api = PythonAPI.getApi();

await api.exit_game();
await api.attempt_login(ip, name, password);
await api.send_chat_message(message);
await api.save_settings(settings);
await api.disconnect();
```

### Python → JavaScript

```python
# In playwright_manager.py
self.send_to_js("navigate", {"screen": "main-menu"})
self.send_to_js("chat_message", {"sender": "Bob", "text": "Hi!"})
```

---

## DirectGUI Fallback

### Core Files

```
nine/ui/
├── manager.py           # UIManager - state machine
├── base_component.py    # BaseUIComponent base class
├── blocks_v2.py         # Declarative layout engine
├── ui_config.py         # Colors, fonts, spacing
├── theme.py             # NineTheme (deprecated)
├── bg1_button.py        # BG1-style buttons
│
├── main_menu.py         # Main menu
├── login_menu.py        # Login form
├── settings_menu.py     # Settings (4 tabs)
├── in_game_menu.py      # Pause menu
├── chat_window.py       # Chat overlay
└── loading_screen.py    # Loading screen
```

### Plugin UI (DirectGUI)

```
nine/plugins/
├── dnd/
│   ├── cl_character_select_ui.py
│   └── cl_character_create_ui.py
│
├── combat/
│   ├── cl_combat_ui.py
│   ├── cl_action_bar.py
│   ├── cl_initiative_display.py
│   ├── cl_spectator_mode.py
│   └── cl_target_selector.py
│
├── inventory/
│   └── cl_character_sheet.py
│
├── stats/
│   └── cl_dnd_hud.py
│
└── quests/
    └── cl_quest_log.py
```

---

## Naming Convention

### Plugin Prefixes
- `cl_` - Client-only
- `sh_` - Shared (client + server)
- `sv_` - Server-only

### File Suffixes
- `_ui.py` - UI component
- `_menu.py` - Menu/screen
- `_window.py` - Window
- `_hud.py` - HUD element
- `_display.py` - Data display

---

## Documentation

- `docs/WEBVIEW_UI.md` - Playwright UI details
- `docs/BLOCKS_V2_IMPROVEMENTS.md` - DirectGUI blocks_v2 system
- `docs/DOCS.md` - General architecture (UI section)
