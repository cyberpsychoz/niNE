# UI System — CEF (Chromium Embedded Framework)

## Overview

niNE использует **CEF** (через пакет `cef-capi-py`, Chromium 131) для рендеринга HTML/CSS/JS UI как текстурного overlay поверх 3D-сцены Panda3D.

**Преимущества CEF над Playwright:**
- Raw BGRA пиксели через OnPaint (без PNG encode/decode → нулевая задержка)
- V8 extension для нативного JS→Python моста
- Нативная обработка клавиатуры и буфера обмена (Ctrl+C/V/X)
- Работает на главном потоке — нет проблем с синхронизацией

## Architecture

```
┌─────────────────────────────────────┐
│  CEF (offscreen Chromium 131)        │
│  - V8 extension: window.pyapi       │
│  - OnPaint → raw BGRA pixels        │
│  - send_mouse_click_event            │
│  - send_key_event                    │
└─────────────────────────────────────┘
              ↓ (каждый кадр)
┌─────────────────────────────────────┐
│  Panda3D Texture (render2d overlay)  │
│  - Прозрачный фон                   │
│  - Нативный ввод мыши/клавиатуры    │
└─────────────────────────────────────┘
              ↓ (composited on)
┌─────────────────────────────────────┐
│  Panda3D 3D Scene                    │
│  - Персонажи, карта, эффекты        │
└─────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `nine/ui/cef_manager.py` | CEF offscreen менеджер |
| `nine/ui/webview_api.py` | Python API для JS вызовов |
| `nine/ui/web/index.html` | Root HTML |
| `nine/ui/web/css/theme.css` | @font-face, :root переменные, ресеты |
| `nine/ui/web/css/main.css` | Layout экранов |
| `nine/ui/web/css/components.css` | Переиспользуемые компоненты |
| `nine/ui/web/css/animations.css` | Keyframes и анимации |
| `nine/ui/web/js/api.js` | PythonAPI — обёртка JS→Python |
| `nine/ui/web/js/main.js` | Роутер, навигация |
| `nine/ui/web/js/panel-manager.js` | Менеджер HUD панелей |
| `nine/ui/web/js/sound-manager.js` | Звуковой менеджер UI |
| `nine/ui/web/js/components/` | JS компоненты экранов |
| `nine/ui/web/templates/` | HTML templates |

## Configuration

Edit `config.json`:
```json
{
  "ui_backend": "cef"
}
```

Альтернативы:
```json
{
  "ui_backend": "playwright"
}
```
```json
{
  "ui_backend": "directgui"
}
```

## JavaScript API

### JS → Python (V8 Extension)

CEF V8 extension предоставляет `window.pyapi` с нативной функцией `pyCall()`.
Обёртка `PythonAPI` (api.js) делает вызовы удобными:

```javascript
const api = PythonAPI.getApi();

await api.exit_game();
await api.attempt_login(ip, nickname, password);
await api.send_chat_message(message);
await api.create_character(characterData);
await api.combat_action(actionData);
await api.save_settings(settingsObject);
await api.select_character(charId);
await api.disconnect();
```

### Python → JavaScript

```python
# В cef_manager.py или через webview_api.py
self.send_to_js("navigate", {"screen": "main-menu"})
self.send_to_js("chat_message", {"sender": "Bob", "text": "Hello!"})
self.send_to_js("combat_started", {"participants": [...]})
self.send_to_js("character_sheet_data", {"stats": {...}})
self.send_to_js("game_state_changed", {"state": "IN_GAME"})
```

### Receiving events in JavaScript

```javascript
// В main.js или компонентах
window.receiveFromPython = function(data) {
    const { event, payload } = data;

    switch(event) {
        case 'navigate':
            navigateTo(payload.screen, payload.params);
            break;
        case 'chat_message':
            GameHUD.addChatMessage(payload);
            break;
        case 'combat_started':
            GameHUD.onCombatStarted(payload);
            break;
    }
};
```

## Python API Methods (webview_api.py)

| Method | Description |
|--------|-------------|
| `exit_game()` | Выход из приложения |
| `open_login_menu()` | Показать экран логина |
| `attempt_login(ip, name, pw)` | Подключиться к серверу |
| `close_login_menu()` | Вернуться в главное меню |
| `open_settings()` | Показать настройки |
| `save_settings(dict)` | Сохранить настройки в config.json |
| `send_chat_message(msg)` | Отправить сообщение в чат |
| `disconnect()` | Отключиться от сервера |
| `hide_in_game_menu()` | Скрыть паузу |
| `create_character(data)` | Создать персонажа |
| `select_character(id)` | Выбрать персонажа |
| `combat_action(data)` | Отправить боевое действие |
| `pause_input()` | Приостановить игровой ввод (при фокусе на UI) |
| `resume_input()` | Возобновить игровой ввод |

## UI Screens

| Screen | Template | JS Component | Description |
|--------|----------|--------------|-------------|
| main-menu | `main-menu.html` | `MainMenu.js` | Главное меню |
| login-menu | `login-menu.html` | `LoginMenu.js` | Подключение к серверу |
| settings-menu | `settings-menu.html` | `SettingsMenu.js` | Настройки (4 вкладки) |
| character-select | `character-select.html` | `CharacterSelect.js` | Выбор персонажа |
| character-create | `character-create.html` | `CharacterCreate.js` | 8-шаговое создание персонажа |
| game-hud | `game-hud.html` | `GameHUD.js` | Игровой HUD (чат, бой, панели) |
| in-game-menu | `in-game-menu.html` | `InGameMenu.js` | Пауза (ESC) |

### HUD Panels (in-game)

| Panel | Template | JS Component |
|-------|----------|--------------|
| Character Sheet | `character-sheet.html` | `CharacterSheet.js` |
| Spellbook | `spellbook.html` | `SpellbookPanel.js` |
| Quest Log | `quest-log.html` | `QuestLog.js` |
| Rest Dialog | `rest-dialog.html` | `RestDialog.js` |
| Context Menu | `context-menu.html` | `ContextMenu.js` |

## CSS Architecture

**Правила для CEF:**
1. **НИКОГДА** не использовать `@import url('https://...')` — блокирует загрузку CSS
2. **НИКОГДА** не ставить `<style>` блоки в HTML templates — CEF может их не обработать
3. Все шрифты — локальные TTF файлы через `@font-face` в theme.css
4. Глобальный `button { appearance: none; }` reset обязателен

**Файлы:**
- `theme.css` — @font-face (Cinzel, MedievalSharp), :root CSS переменные, глобальные ресеты
- `main.css` — Layout экранов (main-menu, settings, character-create и др.)
- `components.css` — Переиспользуемые компоненты (кнопки, инпуты, карточки)
- `animations.css` — Keyframes и animation utility классы

### CSS Variables (theme.css)

```css
:root {
    --bg-dark: #0a0a0f;
    --bg-medium: #1a1a2e;
    --text-primary: #e0d5c1;
    --text-secondary: #a09880;
    --gold: #d4a337;
    --gold-hover: #e8b84a;
    --accent-red: #8b2020;
    --font-heading: 'Cinzel', serif;
    --font-body: 'MedievalSharp', cursive;
}
```

## Input Handling

CEF использует нативные события ввода (не polling как Playwright):

```python
# Мышь
browser.send_mouse_click_event(x, y, button, mouseUp, clickCount)
browser.send_mouse_move_event(x, y, mouseLeave)
browser.send_mouse_wheel_event(x, y, deltaX, deltaY)

# Клавиатура
browser.send_key_event(event_type, key_code, modifiers)
```

Координаты мыши конвертируются из Panda3D (-1 to 1) в пиксели браузера.

## Input Conflict Resolution

Для предотвращения конфликтов между UI и 3D-вводом:

```python
# Когда UI поле активно (input, textarea)
cef_manager.pause_input()   # Блокирует WASD, мышь для 3D

# Когда фокус возвращается к 3D
cef_manager.resume_input()  # Восстанавливает игровой ввод
```

## Dependencies

```bash
pip install cef-capi-py  # Требует Python 3.11+
```

**Важно:** cef-capi-py использует `single_process=True` для корректной работы V8 extension.

## Legacy: Playwright UI

Playwright UI (`nine/ui/playwright_manager.py`) работает через screenshot loop:
- Скриншот → PNG encode → передача в Panda3D → PNG decode → текстура
- Задержка: 60-160ms
- Работает в фоновом потоке с Queue для команд
- Не рекомендуется для новой разработки
