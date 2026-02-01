# UI Files Reference - Полный справочник

## 📁 Структура UI файлов

```
nine/
├── ui/                          # Основные UI компоненты
│   ├── manager.py              # UIManager - центральное управление
│   ├── base_component.py       # BaseUIComponent - базовый класс
│   ├── blocks_v2.py            # Block system - layout engine
│   ├── ui_config.py            # UI конфигурация (цвета, шрифты)
│   ├── theme.py                # NineTheme (deprecated)
│   ├── bg1_button.py           # BG1-style кнопки
│   │
│   ├── main_menu.py            # Главное меню
│   ├── login_menu.py           # Меню подключения ✅ blocks_v2
│   ├── settings_menu.py        # Настройки ✅ blocks_v2
│   ├── in_game_menu.py         # Меню паузы ✅ blocks_v2
│   ├── chat_window.py          # Окно чата
│   └── loading_screen.py       # Экран загрузки
│
└── plugins/
    ├── dnd/                    # D&D плагин UI
    │   ├── cl_character_select_ui.py
    │   └── cl_character_create_ui.py
    │
    ├── combat/                 # Combat плагин UI
    │   ├── cl_combat_ui.py
    │   ├── cl_action_bar.py
    │   ├── cl_initiative_display.py
    │   ├── cl_spectator_mode.py
    │   └── cl_target_selector.py
    │
    ├── inventory/              # Инвентарь UI
    │   └── cl_character_sheet.py
    │
    ├── stats/                  # Stats HUD
    │   └── cl_dnd_hud.py
    │
    └── quests/                 # Quest Log UI
        └── cl_quest_log.py
```

---

## 🎯 Основные меню (nine/ui/)

### MainMenu (main_menu.py)

**Назначение:** Главное меню игры
**Статус:** ❌ Не переписан на blocks_v2
**Layout:** BG1Button + AnimatedBackground

**Кнопки:**
- ИГРАТЬ → открывает LoginMenu
- НАСТРОЙКИ → открывает SettingsMenu
- ВЫХОД → exit_game()

**Особенности:**
- Анимированный GIF фон (через PIL)
- Случайный выбор фона из `nine/assets/materials/textures/backgrounds/`
- Музыка главного меню
- Заголовок "DUNGEONS & DRAGONS"
- Подзаголовок "niNE Game Mode"

**Зависимости:**
- `AnimatedBackground` - класс для GIF
- `BG1Button` - стилизованные кнопки
- PIL (опционально) для GIF

---

### LoginMenu (login_menu.py)

**Назначение:** Форма подключения к серверу
**Статус:** ✅ Полностью переписан на blocks_v2
**Layout:** Pure blocks_v2

**Поля:**
- IP Адрес (Entry, name="ip", focus=True)
- Имя персонажа (Entry, name="name")
- Пароль (Entry, name="password", obscured=True)

**Кнопки:**
- ВОЙТИ → attempt_login()
- НАЗАД → close_login_menu()

**API:**
```python
login_menu = LoginMenu(ui_manager, default_ip="127.0.0.1", default_name="Player")
credentials = login_menu.get_credentials()
# {"ip": "...", "name": "...", "password": "..."}
```

---

### SettingsMenu (settings_menu.py)

**Назначение:** Настройки игры (4 вкладки)
**Статус:** ✅ Использует blocks_v2 + max_width fix
**Layout:** Tabs + blocks_v2

**Вкладки:**

1. **Общие (general)**
   - Никнейм (Entry)
   - Разрешение (Dropdown)

2. **Управление (controls)**
   - Чувствительность мыши (Slider)
   - Инвертировать X/Y (Checkbox)
   - 3rd person камера (Checkbox)

3. **Графика (graphics)**
   - FOV (Slider)
   - PS1 эффект (Checkbox)
   - PS1 разрешение (Slider)

4. **Звук (audio)**
   - Master/BGM/SFX/Ambient/UI (Sliders)
   - UI звуковой пакет (Dropdown)
   - Включить UI звуки (Checkbox)

**Кнопки:**
- СОХРАНИТЬ → сохраняет в config.json
- НАЗАД → возврат без сохранения

---

### InGameMenu (in_game_menu.py)

**Назначение:** Меню паузы (ESC в игре)
**Статус:** ✅ Переписан на blocks_v2
**Layout:** Pure blocks_v2

**Кнопки:**
- ПРОДОЛЖИТЬ → скрывает меню, возвращает в игру
- НАСТРОЙКИ → открывает SettingsMenu
- ОТКЛЮЧИТЬСЯ → disconnect_from_server()

**Особенности:**
- Затемняющий оверлей (bg_overlay)
- Автоматически скрывается при создании

---

### ChatWindow (chat_window.py)

**Назначение:** Окно чата
**Статус:** ❌ Не blocks_v2
**Layout:** Custom DirectGUI

**Режимы:**
- Закрытый: временные сообщения с fade-out (10 сек + 2.5 сек исчезновение)
- Открытый: полная история + input поле (T для открытия)

**Типы сообщений:**
- `say` - обычный чат (белый)
- `me` - действие (*делает*) (жёлтый)
- `ooc` - out of character ((текст)) (серый)
- `it` - описание окружения (курсив, голубой)
- `dm` - DM сообщение (золотой)
- `system` - системное (зелёный)

---

## 🧩 UI Infrastructure

### UIManager (manager.py)

**Назначение:** Центральное управление всеми UI
**Главный файл:** `nine/ui/manager.py`

**Состояния (GameState):**
- `MENU` - главное меню, логин, настройки
- `CONNECTING` - процесс подключения
- `IN_GAME` - в игре

**API:**
```python
# Создание
ui_manager = UIManager(base, callbacks={
    "attempt_login": self._attempt_login,
    "exit_game": self.exit_game,
    ...
})

# Управление состояниями
ui_manager.set_game_state(GameState.IN_GAME)

# Показ/скрытие меню
ui_manager.show_main_menu()
ui_manager.show_login_menu()
ui_manager.show_settings_menu(client)
ui_manager.show_in_game_menu()
ui_manager.hide_in_game_menu()
```

**Callbacks:**
- `attempt_login` - попытка подключения
- `close_login_menu` - закрыть меню входа
- `exit_game` - выход из игры
- `connect` - открыть LoginMenu
- `settings` - открыть SettingsMenu

---

### BaseUIComponent (base_component.py)

**Назначение:** Базовый класс для всех UI компонентов

**Обязательные методы:**
```python
class MyUI(BaseUIComponent):
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        # self.base - доступ к ShowBase
        # self.ui_manager - доступ к UIManager

    def show(self):
        """Показать UI."""
        pass

    def hide(self):
        """Скрыть UI."""
        pass

    def destroy(self):
        """Уничтожить UI и очистить ресурсы."""
        super().destroy()  # Очищает self._elements
```

**Утилиты:**
- `_add_element(name, widget)` - регистрация элемента для автоочистки
- `_play_open_sound()` - звук открытия меню
- `_play_click_sound()` - звук клика
- `_create_bg1_button(...)` - создание BG1-style кнопки

---

### Block System V2 (blocks_v2.py)

**Назначение:** Декларативный layout engine (аналог HTML/CSS)
**Документация:** `docs/BLOCKS_V2_IMPROVEMENTS.md`

**Основные классы:**
- `Block` - контейнер (как <div>)
- `Row` - горизонтальный ряд
- `Margin` / `Padding` - отступы (CSS-like)
- `ElementSize` - размеры с min/max constraints

**Элементы:**
- `LabelElement` - текст
- `ButtonElement` - кнопка
- `EntryElement` - текстовое поле
- `SliderElement` - слайдер
- `DropdownElement` - выпадающий список
- `CheckboxElement` - чекбокс
- `SpacerElement` - вертикальный отступ
- `HSpacerElement` - горизонтальный отступ

**Пример:**
```python
from nine.ui.blocks_v2 import Block, Margin

block = Block(
    parent=base.aspect2d,
    width=1.0,
    padding=0.08,
    bg_color=(0.18, 0.18, 0.18, 0.95),
    pos=(0, 0, 0)
)

# Заголовок
block.label("ЗАГОЛОВОК", style="title", align="center")
block.spacer(0.05)

# Поле ввода
row1 = block.row(justify="center")
row1.entry(name="username", initial="Player", width=20, max_width=0.8)

# Кнопки
btn_row = block.row(justify="center", gap=0.08)
btn_row.button("OK", command=on_ok, small=False)
btn_row.button("CANCEL", command=on_cancel, small=False)

# Строим
frame = block.build()

# Получение значений
username = block.get("username")
```

**Преимущества:**
- ✅ CSS-like margin/padding
- ✅ Min/Max size constraints
- ✅ Автоматический layout
- ✅ Named elements (get/get_element)
- ✅ Size caching для производительности
- ✅ Точное измерение текста (TextNode)

---

### UI Config (ui_config.py)

**Назначение:** Централизованная конфигурация UI

**Структура:**
```python
ui.colors.bg_dark        # Тёмный фон
ui.colors.bg_medium      # Средний фон
ui.colors.bg_overlay     # Оверлей (затемнение)
ui.colors.text_primary   # Основной текст
ui.colors.text_secondary # Второстепенный текст
ui.colors.gold           # Золотой (заголовки)

ui.font.title   # Размер заголовка
ui.font.heading # Размер подзаголовка
ui.font.body    # Размер обычного текста
ui.font.label   # Размер лейбла
ui.font.small   # Мелкий текст

ui.spacing.xs   # Extra small
ui.spacing.sm   # Small
ui.spacing.md   # Medium
ui.spacing.lg   # Large
ui.spacing.xl   # Extra large
```

---

## 🎮 Plugin UI

### D&D Plugin (nine/plugins/dnd/)

#### cl_character_select_ui.py
- Список персонажей игрока
- Кнопки: ВЫБРАТЬ, СОЗДАТЬ, УДАЛИТЬ

#### cl_character_create_ui.py
- Создание D&D персонажа
- Поля: Имя, Раса, Класс, Распределение характеристик
- Кнопки: СОЗДАТЬ, ОТМЕНА

---

### Combat Plugin (nine/plugins/combat/)

#### cl_combat_ui.py
**Главный UI боя - координирует все компоненты**

#### cl_action_bar.py
- Панель действий внизу экрана
- Кнопки: Attack, Cast Spell, Dodge, Dash, End Turn

#### cl_initiative_display.py
- Отображение порядка инициативы
- Список участников боя с HP

#### cl_spectator_mode.py
- Режим наблюдателя (не твой ход)
- Скрывает панель действий

#### cl_target_selector.py
- Выбор цели для атаки/заклинаний
- Подсветка доступных целей

---

### Inventory Plugin (nine/plugins/inventory/)

#### cl_character_sheet.py
- Лист персонажа (K для открытия)
- Вкладки: Stats, Inventory, Equipment
- Отображение характеристик, инвентаря, экипировки

---

### Stats Plugin (nine/plugins/stats/)

#### cl_dnd_hud.py
- HUD в игре (верхний левый угол)
- Отображает: HP, AC, Initiative

---

### Quests Plugin (nine/plugins/quests/)

#### cl_quest_log.py
- Журнал квестов (J для открытия)
- Список активных/завершённых квестов
- Детали квеста, прогресс

---

## 📝 Naming Convention

### Префиксы плагинов:
- `cl_` - Client-only UI
- `sh_` - Shared (не UI)
- `sv_` - Server-only (не UI)

### Суффиксы:
- `_ui.py` - UI компонент
- `_menu.py` - Меню/экран
- `_window.py` - Окно
- `_hud.py` - HUD элемент
- `_display.py` - Отображение данных

---

## 🔧 Migration Status

| Файл | Blocks V2 | Статус |
|------|-----------|--------|
| `login_menu.py` | ✅ | Полностью переписан |
| `settings_menu.py` | ✅ | Обновлён с max_width |
| `in_game_menu.py` | ✅ | Переписан |
| `main_menu.py` | ❌ | Оставлен как есть (AnimatedBackground) |
| `chat_window.py` | ❌ | Custom DirectGUI |
| `loading_screen.py` | ❌ | Simple DirectGUI |
| D&D plugin UI | ❌ | Требуют миграции |
| Combat plugin UI | ❌ | Требуют миграции |

---

## 📚 Документация

- `docs/BLOCKS_V2_IMPROVEMENTS.md` - Подробная документация blocks_v2
- `docs/UI_SIZING_FIX.md` - История фиксов sizing
- `docs/UI_REWRITE_V2.md` - Результаты миграции
- `docs/DOCS.md` (строки 84-177) - Общая информация о UI

---

## 🚀 Quick Start

### Создать новое меню:

```python
from nine.ui.base_component import BaseUIComponent
from nine.ui.blocks_v2 import Block
from nine.ui.ui_config import ui

class MyMenu(BaseUIComponent):
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        self._block = None
        self._setup()

    def _setup(self):
        self._block = Block(
            parent=self.base.aspect2d,
            width=1.0,
            padding=0.08,
            bg_color=ui.colors.bg_medium,
            pos=(0, 0, 0)
        )

        self._block.label("MY MENU", style="title", align="center")
        self._block.spacer(ui.spacing.lg)

        row = self._block.row(justify="center")
        row.button("CLOSE", command=self._on_close, small=False)

        frame = self._block.build()
        self._add_element('panel', frame)

    def _on_close(self):
        self.destroy()

    def destroy(self):
        if self._block:
            self._block.destroy()
            self._block = None
        super().destroy()
```

### Зарегистрировать в UIManager:

```python
# В nine/ui/manager.py
def show_my_menu(self):
    self._clear_menu_ui()
    self.my_menu = MyMenu(self)
```
