# UI Rewrite - Blocks V2 Migration

## Что было переписано

### ✅ LoginMenu (nine/ui/login_menu.py)

**ДО:** Использовал blocks_v2 для полей + BG1Button для кнопок (вне системы блоков)
**ПОСЛЕ:** Полностью на blocks_v2, кнопки внутри блока

#### Изменения:
- ❌ Удалён `BG1Button` - кнопки создаются через `row.button()`
- ✅ Все элементы внутри одного Block
- ✅ Кнопки в одной строке с `justify="center"`
- ✅ Компактный дизайн (width=1.0 вместо 1.2)
- ✅ Правильный gap между кнопками (0.08)

#### Структура:
```python
block.label("ПОДКЛЮЧЕНИЕ К СЕРВЕРУ", style="title", align="center")
block.spacer(lg)

block.label("IP Адрес:", style="label")
row_ip.entry(name="ip", width=24, max_width=0.8, focus=True)

block.label("Имя персонажа:", style="label")
row_name.entry(name="name", width=24, max_width=0.8)

block.label("Пароль:", style="label")
row_pass.entry(name="password", width=24, max_width=0.8, obscured=True)

btn_row.button("ВОЙТИ", command=..., small=False)
btn_row.button("НАЗАД", command=..., small=False)
```

#### Тесты:
```
✓ LoginMenu создан успешно
✓ Block существует
✓ IP: '127.0.0.1' (совпадает)
✓ Name: 'TestPlayer' (совпадает)
✓ Password: '' (пустой)
✓ Зарегистрированные элементы: ip, name, password
```

---

### ✅ InGameMenu (nine/ui/in_game_menu.py)

**ДО:** Использовал blocks_v2 но кнопки в отдельных row
**ПОСЛЕ:** Упрощённая структура

#### Изменения:
- ✅ Более компактный (width=0.7 вместо 0.8)
- ✅ Больший padding (0.08)
- ✅ Кнопки `small=False` для большего размера
- ✅ Упрощённая структура - каждая кнопка в своей row

#### Структура:
```python
block.label("ПАУЗА", style="title", align="center")
block.spacer(xl)

row1.button("ПРОДОЛЖИТЬ", command=..., small=False)
row2.button("НАСТРОЙКИ", command=..., small=False)
row3.button("ОТКЛЮЧИТЬСЯ", command=..., small=False)
```

---

### ✅ SettingsMenu (nine/ui/settings_menu.py)

**РАНЕЕ ОБНОВЛЁН:** Уже использовал blocks_v2 с max_width для Entry

---

## Fixes в blocks_v2.py

### 1. Row.entry() max_width parameter
```python
def entry(self, name: str = None, initial: str = "", width: int = 12,
          obscured: bool = False, focus: bool = False, margin: Margin = None,
          max_width: float = None) -> "Row":  # ← Добавлен max_width
```

### 2. Named elements tracking
```python
class Block:
    def __init__(self, ...):
        self._named_elements: dict = {}  # ← Трекинг элементов

    def get(self, name: str):
        """Get value of a named element."""
        elem = self._named_elements.get(name)
        if elem and hasattr(elem, 'get_value'):
            return elem.get_value()
        return None
```

### 3. Row registration
```python
class Row:
    def __init__(self, gap=None, justify="start", parent_block=None):
        self.parent_block = parent_block  # ← Ссылка на Block

    def entry(self, ...):
        # ...
        if name and self.parent_block:
            self.parent_block._named_elements[name] = elem  # ← Регистрация
```

---

## Что НЕ переписано

### MainMenu (nine/ui/main_menu.py)
- ❌ НЕ переписан - использует AnimatedBackground + BG1Button
- Причина: Сложная структура с GIF-анимацией, музыкой, градиентами
- Статус: Оставлен как есть (работает)

### CharacterSelectUI, CharacterCreateUI (DnD plugin)
- ❌ НЕ переписаны - используют старый blocks.py
- Причина: Специфичны для D&D плагина
- Статус: Требуют отдельной миграции

---

## Преимущества нового дизайна

1. **Консистентность**: Все меню используют одинаковый паттерн blocks_v2
2. **Простота**: Нет смешивания BG1Button и blocks_v2
3. **Читаемость**: Код проще читать и модифицировать
4. **Надёжность**: Все элементы внутри одной системы блоков
5. **Тестируемость**: Легко тестировать через программные вызовы

---

## Миграция других компонентов

Если нужно мигрировать другие UI компоненты, используй этот паттерн:

```python
from .blocks_v2 import Block
from .ui_config import ui

class MyMenu(BaseUIComponent):
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        self._block = None
        self._setup()

    def _setup(self):
        # Background (опционально)
        bg = DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=ui.colors.bg_dark,
        )
        bg.setTransparency(TransparencyAttrib.M_alpha)
        self._add_element('background', bg)

        # Main block
        self._block = Block(
            parent=self.base.aspect2d,
            width=1.0,
            padding=0.08,
            bg_color=ui.colors.bg_medium,
            pos=(0, 0, 0)
        )

        # Title
        self._block.label("ЗАГОЛОВОК", style="title", align="center")
        self._block.spacer(ui.spacing.lg)

        # Content
        row1 = self._block.row(justify="center")
        row1.entry(name="field1", initial="", width=20, max_width=0.8)

        # Buttons
        btn_row = self._block.row(justify="center", gap=0.08)
        btn_row.button("OK", command=self._on_ok, small=False)
        btn_row.button("CANCEL", command=self._on_cancel, small=False)

        # Build
        frame = self._block.build()
        self._add_element('panel', frame)

    def destroy(self):
        if self._block:
            self._block.destroy()
            self._block = None
        super().destroy()
```

---

## Итоги

- ✅ LoginMenu - переписан и протестирован
- ✅ InGameMenu - переписан
- ✅ SettingsMenu - уже обновлён ранее
- ✅ blocks_v2.py - исправлены баги с get() и max_width
- ❌ MainMenu - оставлен как есть (сложная структура)

**Все основные меню теперь используют чистый blocks_v2!**
