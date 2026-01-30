```markdown
# Автоматизированное тестирование niNE

Полностью автоматическая система тестирования с визуальными отчётами.

## Быстрый старт

### Вариант 1: Один клик (Windows)
```cmd
run_automated_tests.bat
```

Скрипт:
1. Запустит сервер в фоне
2. Запустит тесты
3. Сделает скриншоты
4. Откроет HTML отчёт
5. Остановит сервер

### Вариант 2: Вручную

```bash
# Терминал 1: Сервер
python -m nine.server.game_server

# Терминал 2: Тесты (через 5 секунд после сервера)
python -m tests.automated_test_suite
```

## Что тестируется

### UI Тесты
1. **Main Menu** - главное меню
2. **Login Menu** - проверка кнопок "Войти", "Назад", полей ввода
3. **Settings Menu** - проверка поля имени персонажа

### Gameplay Тесты
4. **Game World** - загрузка карты
5. **NPC Spawn** - спавн гоблина командой `/spawn goblin`
6. **Camera Angles** - разные углы обзора на NPC
7. **Combat System** - запуск боя командой `/startcombat`

### Технические проверки
- Подключение к серверу
- Аутентификация
- Синхронизация world_state
- Цвет NPC модели (RGB проблема)
- Позиционирование UI элементов

## Результаты

После выполнения создаётся папка `test_report_YYYYMMDD_HHMMSS/`:

```
test_report_20260130_160000/
├── report.html          # Визуальный отчёт (откроется автоматически)
├── screenshots/         # Все скриншоты
│   ├── 001_main_menu.png
│   ├── 002_login_menu.png
│   ├── 003_settings_menu.png
│   ├── 004_game_world.png
│   ├── 005_goblin_spawned.png
│   ├── 006_camera_angle_1.png
│   ├── 007_camera_angle_2.png
│   └── 008_combat_started.png
└── logs/                # Копии логов (если добавлено)
```

## Отчёт содержит

- Все скриншоты в хронологическом порядке
- Описание каждого шага теста
- Временные метки
- Информацию об ошибках

## Проверка проблем

### UI проблемы
Скриншоты 001-003 покажут:
- Налазят ли кнопки друг на друга
- Корректен ли размер полей ввода
- Вылезает ли текст за границы

### NPC проблемы
Скриншоты 005-007 покажут:
- Заспавнился ли гоблин
- Какого он цвета (синий = проблема)
- Видна ли модель или T-поза
- Правильно ли позиционирован

### Combat проблемы
Скриншот 008 покажет:
- Появился ли UI боя
- Отображаются ли индикаторы Д, Б, Р
- Корректна ли инициатива

## Troubleshooting

### Сервер не запускается
```bash
# Проверьте что не запущен другой сервер
tasklist | findstr python
# Убейте старые процессы
taskkill /F /IM python.exe
```

### Тесты не подключаются к серверу
1. Убедитесь что `server_config.json` содержит:
   ```json
   "allow_dev_client": true
   ```
2. Подождите 10 секунд после запуска сервера

### Чёрные скриншоты
- Это нормально для offscreen режима
- Главное что логи покажут что произошло
- Для визуальных тестов используйте обычный клиент

### NPC не спавнится
Проверьте логи:
```bash
python show_logs.py server
# Ищите строки с "spawn" или "goblin"
```

## Расширение тестов

Чтобы добавить свои тесты, отредактируйте `tests/automated_test_suite.py`:

```python
async def run_test_sequence(self):
    # ... existing tests ...

    # Ваш тест
    logger.info("Test X: My custom test")
    # Выполните действия
    await self.send_message({
        "type": "chat_message",
        "message": "/mycommand"
    })
    await asyncio.sleep(2)
    self.take_screenshot("09_my_test", "Описание теста")
```

## Известные проблемы

1. **RGB проблема** - NPC отображается не тем цветом
   - Проверка: скриншот 005_goblin_spawned.png
   - Ожидается: зелёный
   - Если синий = цвет не применяется

2. **NPC не спавнится** - команда /spawn не работает
   - Проверка: логи сервера
   - Возможно: нужны права DM

3. **UI overlap** - элементы налазят друг на друга
   - Проверка: скриншоты 001-003
   - Причина: блочная layout система

## Для разработчиков

### Добавить проверку в отчёт
```python
self.test_results.append({
    "step": self.screenshot_counter,
    "name": "TEST_NAME",
    "description": "Что проверяем",
    "screenshot": None,  # Или путь к скриншоту
    "timestamp": datetime.now().isoformat(),
    "status": "PASS",  # или "FAIL"
    "details": {"key": "value"}  # Доп. информация
})
```

### Запуск в CI/CD
```bash
# Без GUI
export DISPLAY=:99
python -m tests.automated_test_suite

# Проверка результата
if [ -f "test_report_*/report.html" ]; then
    echo "Tests passed"
else
    echo "Tests failed"
    exit 1
fi
```
