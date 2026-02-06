# Playwright UI System

## Overview

The niNE project uses **Playwright** (headless Chromium) to render HTML/CSS UI as a texture overlay on the Panda3D 3D scene.

**Benefits:**
- Modern HTML/CSS/JS for UI development
- Browser DevTools for debugging
- Easy styling with CSS
- Responsive design support

## Architecture

```
┌──────────────────────────────────────┐
│  Playwright (headless Chromium)       │
│  - Renders HTML/CSS/JS               │
│  - Screenshots to RGBA buffer        │
└──────────────────────────────────────┘
              ↓ (every frame)
┌──────────────────────────────────────┐
│  Panda3D Texture (render2d overlay)  │
│  - Transparent background            │
│  - Mouse polling for input           │
└──────────────────────────────────────┘
              ↓ (composited on)
┌──────────────────────────────────────┐
│  Panda3D 3D Scene                    │
│  - Characters, map, effects          │
└──────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `nine/ui/playwright_manager.py` | Main Playwright manager |
| `nine/ui/webview_api.py` | Python API for JS calls |
| `nine/ui/web/index.html` | Root HTML |
| `nine/ui/web/css/` | Styles |
| `nine/ui/web/js/` | JavaScript |
| `nine/ui/web/templates/` | HTML templates |

## Configuration

Edit `config.json`:
```json
{
  "ui_backend": "playwright"
}
```

Fallback to DirectGUI:
```json
{
  "ui_backend": "directgui"
}
```

## JavaScript API

### Calling Python from JavaScript

```javascript
// PythonAPI wrapper handles both pywebview and playwright backends
const api = PythonAPI.getApi();

await api.exit_game();
await api.attempt_login(ip, nickname, password);
await api.send_chat_message(message);
await api.save_settings(settingsObject);
```

### Receiving events from Python

```javascript
// In router.js or components
window.receiveFromPython = function(data) {
    const { event, payload } = data;

    if (event === 'navigate') {
        router.navigate(payload.screen, payload.params);
    } else if (event === 'chat_message') {
        chatWindow.addMessage(payload);
    }
};
```

## Python API

### Sending to JavaScript

```python
# In playwright_manager.py or via webview_api.py
self.send_to_js("navigate", {"screen": "main-menu"})
self.send_to_js("chat_message", {"sender": "Bob", "text": "Hello!"})
self.send_to_js("combat_started", {"participants": [...]})
```

### Available API Methods (webview_api.py)

| Method | Description |
|--------|-------------|
| `exit_game()` | Exit the application |
| `open_login_menu()` | Show login screen |
| `attempt_login(ip, name, pw)` | Connect to server |
| `close_login_menu()` | Return to main menu |
| `open_settings()` | Show settings |
| `save_settings(dict)` | Save settings to config.json |
| `send_chat_message(msg)` | Send chat message |
| `disconnect()` | Disconnect from server |
| `hide_in_game_menu()` | Hide pause menu |

## UI Components

### Screens (managed by router.js)

| Screen | Template | Description |
|--------|----------|-------------|
| main-menu | `main-menu.html` | Main menu (Play, Settings, Exit) |
| login-menu | `login-menu.html` | Server connection form |
| settings-menu | `settings-menu.html` | Settings (4 tabs) |
| in-game-menu | `in-game-menu.html` | Pause menu |
| character-select | `character-select.html` | Character selection |
| character-create | `character-create.html` | Character creation |
| loading | `loading.html` | Loading screen |

### Persistent Components

| Component | Description |
|-----------|-------------|
| ChatWindow | Chat overlay (always visible in-game) |

## Styling

### Theme (css/theme.css)

BG1-inspired dark theme with gold accents:
- Background: Dark gray (#1a1a1a)
- Text: Light (#e0e0e0)
- Accent: Gold (#d4af37)
- Buttons: Dark with gold border on hover

### CSS Variables

```css
:root {
    --bg-dark: #1a1a1a;
    --bg-medium: #2a2a2a;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --gold: #d4af37;
    --gold-hover: #f0c040;
}
```

## Input Handling

Mouse input is handled via polling in `playwright_manager.py`:

```python
def _poll_mouse(self, task):
    mwn = self.app.mouseWatcherNode
    if mwn.isButtonDown('mouse1'):
        if not self._last_mouse_state:
            x, y = self._get_mouse_pos()
            self.to_browser_queue.put({'type': 'click', 'x': x, 'y': y})
            self._last_mouse_state = True
    else:
        self._last_mouse_state = False
    return Task.cont
```

Mouse coordinates are converted from Panda3D (-1 to 1) to browser pixels.

## Dependencies

```bash
pip install playwright
playwright install chromium
```

## Troubleshooting

### HTTP Server "Address already in use"
The local HTTP server (port 18599) may be blocked. Check for existing processes:
```bash
lsof -i :18599
```

### Transparent background not working
Ensure `omit_background=True` in screenshot options and CSS:
```css
body { background: transparent !important; }
```

### Clicks not registering
Mouse polling task must be running. Check logs for "mouse poll" task.

## Performance Notes

- Screenshots are taken at ~30 FPS to balance responsiveness and CPU
- RGBA buffer is written directly to Panda3D texture
- Chromium runs in a background thread to avoid blocking main loop
