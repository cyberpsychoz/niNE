# Бэклог известных проблем

## Критические

### Unicode ошибки в логах (Windows cp1251)
**Статус:** Открыто
**Файлы:**
- `nine/core/world.py:57` - эмодзи в логе прыжка
- `nine/core/world.py:472` - эмодзи в логе ввода
- `nine/core/character_controller.py:242` - эмодзи в логе приземления

**Ошибка:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f3ae'
```

**Решение:** Удалить эмодзи из логов или настроить UTF-8 кодировку для логгера.

---

## Combat плагин (клиент)

### cl_spectator_mode.py - неправильный импорт globalClock
**Статус:** Открыто
**Файл:** `nine/plugins/combat/cl_spectator_mode.py:320`

**Ошибка:**
```
ImportError: cannot import name 'globalClock' from 'direct.showbase.ShowBase'
```

**Решение:** Использовать `from panda3d.core import ClockObject; globalClock = ClockObject.getGlobalClock()`

---

### cl_target_selector.py - отсутствует атрибут base
**Статус:** Открыто
**Файл:** `nine/plugins/combat/cl_target_selector.py:81`

**Ошибка:**
```
AttributeError: 'TargetSelector' object has no attribute 'base'
```

**Решение:** В PluginModule нужно использовать `self.app` вместо `self.base`, или добавить `self.base = self.app` в конструкторе.

---

## Низкий приоритет

### Аудио система
**Статус:** Не реализовано
**Описание:** Плагин аудио не создан. Команды `/music`, `/ambient`, `/sfx` не работают.

---

## Исправлено

- [x] Относительные импорты в плагинах combat/npc (январь 2026)
- [x] Двойной инвентарь (январь 2026)
- [x] Эмодзи в character_controller.py:250 (январь 2026)
