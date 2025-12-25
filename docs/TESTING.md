# Руководство по тестированию niNE

Это руководство описывает методы и инструменты для тестирования проекта niNE.

---

## 1. Быстрый старт

### Запуск сервера

```bash
# Обычный запуск
python server.py

# Запуск в фоновом режиме
python server.py &

# Запуск с ограничением по времени (для автотестов)
timeout 30 python server.py
```

### Запуск клиентов

```bash
# Полный клиент с UI
python client.py

# Dev-клиент с предсказанием движения
python client.py --dev

# CLI-клиент без 3D (для автоматизации)
python dev_cli_client.py --name TestPlayer --host localhost --port 9009
```

---

## 2. CLI-клиент для автоматизированного тестирования

`dev_cli_client.py` — это headless-клиент без 3D-рендеринга, идеальный для автотестов.

### Базовое использование

```bash
# Подключение с таймаутом
timeout 10 python dev_cli_client.py --name TestPlayer --host localhost --port 9009
```

### Фильтрация вывода

Клиент выводит все полученные сообщения. Используйте `grep` для анализа:

```bash
# Только позиции игрока
timeout 10 python dev_cli_client.py --name Test --host localhost --port 9009 2>&1 | grep "pos"

# Welcome-сообщение (проверка подключения)
timeout 5 python dev_cli_client.py --name Test --host localhost --port 9009 2>&1 | grep "welcome"

# Состояние мира
timeout 10 python dev_cli_client.py --name Test --host localhost --port 9009 2>&1 | grep "world_state"
```

### Ограничение вывода

```bash
# Первые 20 сообщений
... | head -20

# Последние 30 сообщений (после завершения)
... | tail -30

# Первые 10 позиций
... | grep "pos" | head -10
```

---

## 3. Мониторинг серверных логов

Сервер пишет логи в `server.log`. Это основной инструмент диагностики.

### Просмотр логов

```bash
# Весь лог
cat server.log

# Последние 50 строк
tail -50 server.log

# Следить за логом в реальном времени
tail -f server.log

# После теста — последние записи
tail -30 server.log
```

### Фильтрация логов

```bash
# Только логи игрока
cat server.log | grep "\[Player\]"

# Логи мира (спавн, удаление игроков)
cat server.log | grep "\[World\]"

# Ошибки физики
cat server.log | grep -E "\[Physics\]|EXPLOSION"

# Предупреждения и ошибки
cat server.log | grep -E "WARNING|ERROR"
```

### Пример полного теста

```bash
# Очистить старый лог
rm -f server.log

# Запустить сервер в фоне
python server.py &
SERVER_PID=$!
sleep 3

# Запустить тестового клиента
timeout 15 python dev_cli_client.py --name PhysicsTest --host localhost --port 9009

# Остановить сервер
kill $SERVER_PID

# Проверить результаты
echo "=== Результаты теста ==="
cat server.log | grep "\[Player\]" | tail -20
```

---

## 4. Изолированное тестирование компонентов

### Тест физики (без сети)

Файл `test_physics.py` тестирует Bullet Physics изолированно:

```bash
python test_physics.py
```

**Что проверяется:**
- Создание физического мира
- Падение объекта под действием гравитации
- Коллизия с полом
- Корректность `globalClock.getDt()` в headless-режиме

**Пример вывода:**
```
==================================================
PHYSICS TEST - Ball falling onto floor
==================================================
[Test] World gravity: LVector3f(0, 0, -30)
[Test] Floor created at z=0 (top surface)
[Test] Ball created at z=10, should land at z=0.5 (radius 0.5)
...
[SUCCESS] Ball landed at z=0.500!
```

### Создание собственных изолированных тестов

```python
#!/usr/bin/env python3
"""Шаблон изолированного теста."""

from panda3d.core import loadPrcFileData, Vec3
loadPrcFileData("", """
    window-type none
    audio-library-name null
""")

from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletWorld

class MyTest(ShowBase):
    def __init__(self):
        super().__init__()

        # Настройка физики
        self.physics = BulletWorld()
        self.physics.setGravity(Vec3(0, 0, -30))

        # ... ваша тестовая логика ...

        self.taskMgr.add(self.test_update, "test")

    def test_update(self, task):
        # Логика теста
        # Вызовите self.userExit() для завершения
        return task.cont

if __name__ == "__main__":
    test = MyTest()
    test.run()
```

---

## 5. Управление процессами

### Проверка запущенных серверов

```bash
# Найти процесс сервера
pgrep -f "python server.py"

# Подробная информация
ps aux | grep server.py
```

### Остановка серверов

```bash
# По PID
kill <PID>

# Все серверы
pkill -f "python server.py"

# Принудительно
pkill -9 -f "python server.py"

# Все Python-процессы (осторожно!)
killall python
```

### Проверка порта

```bash
# Кто слушает порт 9009
lsof -i :9009

# Или через ss
ss -tlnp | grep 9009
```

---

## 6. Pytest (Unit-тесты)

### Структура тестов

```
tests/
├── __init__.py
├── test_network.py      # Тесты сетевого протокола
├── test_events.py       # Тесты EventManager
├── test_database.py     # Тесты DatabaseManager
└── conftest.py          # Общие фикстуры
```

### Запуск тестов

```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# Конкретный файл
pytest tests/test_network.py

# Конкретный тест
pytest tests/test_network.py::test_message_framing

# С покрытием кода
pytest --cov=nine --cov-report=html
```

### Пример теста

```python
# tests/test_events.py
import pytest
from nine.core.events import EventManager

class TestEventManager:
    def test_subscribe_and_post(self):
        """Тест подписки и публикации события."""
        em = EventManager()
        received = []

        def handler(data):
            received.append(data)

        em.subscribe("test_event", handler)
        em.post("test_event", {"value": 42})

        assert len(received) == 1
        assert received[0]["value"] == 42

    def test_unsubscribe(self):
        """Тест отписки от события."""
        em = EventManager()
        call_count = 0

        def handler(data):
            nonlocal call_count
            call_count += 1

        em.subscribe("event", handler)
        em.post("event", {})
        assert call_count == 1

        em.unsubscribe("event", handler)
        em.post("event", {})
        assert call_count == 1  # Не увеличилось
```

### Фикстуры для интеграционных тестов

```python
# tests/conftest.py
import pytest
import subprocess
import time

@pytest.fixture(scope="module")
def game_server():
    """Запускает сервер на время тестов."""
    proc = subprocess.Popen(
        ["python", "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)  # Ждём запуска

    yield proc

    proc.terminate()
    proc.wait()

@pytest.fixture
def clean_log():
    """Очищает server.log перед тестом."""
    import os
    if os.path.exists("server.log"):
        os.remove("server.log")
    yield
    # Можно добавить проверку лога после теста
```

---

## 7. Отладка физики

### Детектор "взрывов"

В `character_controller.py` встроен детектор резких изменений позиции:

```python
if delta > 10.0:
    logger.warning(f"[Player] EXPLOSION! Delta={delta:.2f} ...")
```

Ищите в логе:
```bash
grep "EXPLOSION" server.log
```

### Проверка delta time

```bash
# Логи физики показывают проблемы с dt
grep "\[Physics\]" server.log
```

**Нормальный вывод:** нет предупреждений
**Проблема:** `[Physics] Large dt detected: 0.8722, capping to 0.1`

### Тест падения

```bash
# Запустить сервер и клиента
rm -f server.log
python server.py &
sleep 3
timeout 20 python dev_cli_client.py --name FallTest --host localhost --port 9009 2>&1 | grep "pos" | head -30
pkill -f server.py

# Проверить, что персонаж приземлился
tail -10 server.log | grep "\[Player\]"
```

**Ожидаемый результат:**
- Z-координата уменьшается (падение)
- Финальная позиция стабильна
- `onGround=True`

---

## 8. Типичные проблемы и решения

### Персонаж не падает

1. Проверьте `globalClock.getDt()` — может возвращать ~0 в headless
2. Убедитесь, что `use_test_floor = False` в `world.py` отключён для тестов с картой
3. Проверьте маски коллизии: `setCollideMask(BitMask32.allOn())`

### Персонаж проваливается сквозь пол

1. Проверьте параметр `is_local` в `setLinearMovement()` — должен быть `False`
2. Убедитесь, что геометрия карты загружена: `grep "Map collision loaded" server.log`
3. Проверьте количество geoms: должно быть > 0

### Сервер не принимает подключения

1. Проверьте, не занят ли порт: `lsof -i :9009`
2. Убедитесь в наличии сертификатов: `ls certs/`
3. Проверьте `server_config.json`

### Клиент не подключается

1. Проверьте хост и порт
2. Убедитесь, что `allow_dev_client: true` в `server_config.json` для dev-клиентов
3. Проверьте SSL: клиент должен доверять самоподписанному сертификату

---

## 9. Чеклист перед коммитом

- [ ] `python server.py` запускается без ошибок
- [ ] `python client.py --dev` подключается и показывает игрока
- [ ] `python dev_cli_client.py` получает `welcome` сообщение
- [ ] `grep "ERROR\|WARNING" server.log` не показывает критических ошибок
- [ ] Физика работает: персонаж падает и приземляется
- [ ] `pytest` (если есть тесты) проходит
