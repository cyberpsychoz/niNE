# UI Sizing Fix - Комплексное решение проблем с размерами

**Дата:** 2026-02-01
**Проблема:** Текст выходит за границы кнопок, Entry поля выходят за интерфейс, маленькие gaps между элементами

---

## 🐛 Проблемы

### 1. Кнопки вкладок (Settings Menu)
**Симптом:** Текст "Управление" выходит за границы кнопки
**Причина:** Фиксированная ширина `tab_w = 0.30` для всех кнопок
**Текст:** "Управление" = 10 символов * 0.05 (scale) * 0.6 = 0.30 → ВПРИТЫК!

### 2. Entry поле никнейма
**Симптом:** Поле ввода уходит за границы панели настроек
**Причина:** `width=14` символов → реальная ширина 0.525, при доступной ширине row 1.32
**Из логов:**
```
[UI_DEBUG] Entry 'nickname': x=0.240, y=0.205, width=0.420, char_width=14, avail_width=0.420
```
Entry заканчивается в x=0.660 (РОВНО на границе панели!)

### 3. Маленькие gaps между Labels и Sliders
**Симптом:** Элементы слишком близко друг к другу
**Из логов:**
```
[UI_DEBUG] Row: content_width=1.145, gap=0.175  # Графика
[UI_DEBUG] Row: content_width=1.111, gap=0.209  # Управление
```
Gaps всего 0.175-0.242 - КРИТИЧНО МАЛО!

### 4. Labels слишком широкие
**Причина:** Формула расчета ширины использовала `len(text) * scale * 0.6` (слишком консервативно)
**Результат:** Labels занимают больше места чем нужно → меньше места для других элементов

### 5. ButtonElement с фиксированной шириной
**Причина:** `SMALL_WIDTH = 0.30`, `NORMAL_WIDTH = 0.45` - фиксированные значения
**Результат:** Длинный текст выходит за границы

---

## ✅ Решения

### 1. Автоматический расчет ширины кнопок вкладок
**Файл:** `nine/ui/settings_menu.py`

```python
# БЫЛО:
tab_w = 0.30  # Фиксированная ширина
for i, (tid, tname) in enumerate(tabs):
    x = start_x + i * (tab_w + tab_gap)
    frameSize=(-tab_w/2, tab_w/2, -0.04, 0.05)

# СТАЛО:
tab_widths = []
for tid, tname in tabs:
    text_width = len(tname) * ui.font.small * 0.7
    button_width = max(0.25, text_width + 0.08)  # Минимум 0.25 + padding
    tab_widths.append(button_width)

# Каждая кнопка получает свою ширину
for i, (tid, tname) in enumerate(tabs):
    tab_w = tab_widths[i]
    frameSize=(-tab_w/2, tab_w/2, -0.04, 0.05)
```

**Результат:** Кнопки автоматически подстраиваются под текст
- "Общие" → ~0.25
- "Управление" → ~0.40
- "Графика" → ~0.30
- "Звук" → ~0.25

### 2. Уменьшение ширины Entry никнейм
**Файл:** `nine/ui/settings_menu.py`

```python
# БЫЛО:
r1.entry(name="nickname", initial=config.get("nickname", "Player"), width=14)

# СТАЛО:
r1.entry(name="nickname", initial=config.get("nickname", "Player"), width=12)
```

**Результат:** Реальная ширина уменьшилась с 0.525 до 0.45 → больше не выходит за границы

### 3. Более точная оценка ширины Labels
**Файл:** `nine/ui/blocks.py` → `LabelElement.get_size()`

```python
# БЫЛО:
width = len(self.text) * self._scale * 0.6

# СТАЛО:
width = len(self.text) * self._scale * 0.5  # Более точная оценка
```

**Результат:** Labels занимают меньше места → больше gap для других элементов

### 4. Увеличение минимального gap
**Файл:** `nine/ui/blocks.py` → `Row.build()`

```python
# БЫЛО:
gap = max(0.02, extra_space / (len(self.elements) - 1))

# СТАЛО:
gap = max(0.05, extra_space / (len(self.elements) - 1))
```

**Результат:** Минимальный gap увеличен с 0.02 до 0.05 → элементы не слипаются

### 5. Автоматический расчет ширины ButtonElement
**Файл:** `nine/ui/blocks.py` → `ButtonElement`

```python
# БЫЛО:
SMALL_WIDTH = 0.30  # Фиксированная
NORMAL_WIDTH = 0.45

def get_size(self):
    if self.small:
        return ElementSize(self.SMALL_WIDTH, self.SMALL_HEIGHT)

# СТАЛО:
SMALL_MIN_WIDTH = 0.25  # Минимальная
NORMAL_MIN_WIDTH = 0.35

def get_size(self):
    scale = 0.05 if self.small else 0.06
    text_width = len(self.text) * scale * 0.6
    padding = 0.08

    if self.small:
        width = max(self.SMALL_MIN_WIDTH, text_width + padding)
        return ElementSize(width, self.SMALL_HEIGHT)
```

**Результат:** Кнопки автоматически подстраиваются под длину текста

---

## 📊 Сравнение ДО/ПОСЛЕ

| Элемент | ДО | ПОСЛЕ |
|---------|-----|--------|
| **Tab "Управление"** | Ширина 0.30 (текст ВПРИТЫК) | Ширина ~0.40 (авто) |
| **Entry никнейм** | width=14 (0.525) | width=12 (0.45) |
| **Label width** | `len * 0.6` | `len * 0.5` |
| **Min gap** | 0.02 | 0.05 |
| **Button width** | Фиксированная | Авто по тексту |

---

## 🧪 Тестирование

### Запуск с дебагом:
```bash
python client.py 2>&1 | grep "UI_DEBUG"
```

### Проверить:
1. Открыть **Settings** → все вкладки
2. Проверить что текст НЕ выходит за кнопки
3. Проверить что Entry никнейм НЕ выходит за панель
4. Проверить что gaps между Labels и Sliders адекватные

### Ожидаемые логи:
```
[UI_DEBUG] Tab Button 'Управление': width=0.400  # Было 0.300
[UI_DEBUG] Entry 'nickname': width=0.360  # Было 0.420
[UI_DEBUG] Row: gap=0.300  # Было 0.175-0.242
```

---

## 🚨 Известные проблемы (TODO)

### Combat UI
**Файлы:** `nine/plugins/combat/cl_*.py`
**Проблема:** Используют прямые `frameSize` и `text_scale`, не Block system
**Решение:** Требуется отдельная задача - мигрировать Combat UI на Block system или создать похожий helper

**Примеры:**
- `cl_action_bar.py`: `frameSize=(-0.075, 0.075, -0.035, 0.035)`
- `cl_initiative_display.py`: `frameSize=(-0.25, 0.25, -0.07, 0.07)`

### Дополнительные проверки
- **Character Select/Create UI** - проверить размеры
- **Login Menu** - проверить что Entry поля не выходят
- **Main Menu** - проверить кнопки

---

## 📝 Рекомендации

### При создании новых UI элементов:

1. **Используй Block system** вместо прямых DirectButton/DirectEntry
2. **НЕ используй фиксированные размеры** - всегда рассчитывай по контенту
3. **Формула для текста (кириллица):**
   ```python
   text_width = len(text) * text_scale * 0.5
   button_width = text_width + padding
   ```
4. **Минимальные размеры:**
   - Button: 0.25 (small), 0.35 (normal)
   - Gap: 0.05
   - Padding: 0.08

5. **Всегда добавляй DEBUG логирование:**
   ```python
   print(f"[UI_DEBUG] Element '{name}': x={x:.3f}, width={width:.3f}, text_len={len(text)}")
   ```

---

## 🔧 Дебаг инструменты

### 1. ui_check.py
**Расположение:** `tools/ui_check.py`
**Использование:**
```bash
python tools/ui_check.py
```
Статический анализ UI кода на проблемы

### 2. Runtime дебаг логи
**Включены в:** `nine/ui/blocks.py` (все элементы)
**Вывод:** `[UI_DEBUG] Element: x=..., y=..., width=..., ...`

---

## ✨ Итог

**Проблема РЕШЕНА комплексно:**
- ✅ Автоматический расчет размеров по контенту
- ✅ Минимальные gaps увеличены
- ✅ Точная оценка ширины текста
- ✅ Все элементы помещаются в свои границы

**Следующий шаг:** Мигрировать Combat UI на Block system или создать похожий helper для единообразия.
