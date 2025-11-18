# niNE - это упрощенный 3D фреймворк для ролевых игр, вдохновленный SS14 и Garry's Mod. Он позволяет игрокам легко создавать серверы и расширять функциональность с помощью Python-плагинов с поддержкой дополнительных ресурсов.

![Версия Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Лицензия](https://img.shields.io/badge/license-MIT-green.svg)
![Panda3D](https://img.shields.io/badge/engine-Panda3D-orange.svg)

## Особенности

- **3D среда для ролевых игр**: Базовый 3D мир, в котором игроки могут подключаться и взаимодействовать
- **Простой хостинг серверов**: Запускайте серверы одним кликом или развертывайте отдельно
- **Расширенная система плагинов**: Поддержка плагинов как в виде файлов, так и папок с ресурсами
- **Сетевой мультиплеер**: Построен на asyncio и сокетах Python
- **Чат**: Внутриигровое текстовое общение

## Технологии

- **3D движок**: Panda3D
- **Сетевое взаимодействие**: asyncio с TCP сокетами
- **Сериализация**: JSON
- **Система плагинов**: Динамическая загрузка с поддержкой ресурсов

## Установка

### Предварительные требования

- Python 3.8 или выше
- Panda3D

```bash
pip install panda3d
```

### Быстрый старт

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/niNE.git
cd niNE
```

2. Запустите сервер:
```bash
python niNE_server.py
```

3. Запустите клиент:
```bash
python niNE_client.py
```

## Структура проекта

```
niNE/
├── niNE_server.py          # Главная точка входа сервера
├── niNE_client.py          # Главная точка входа клиента
├── core/                      # Ядро фреймворка
│   ├── __init__.py
│   ├── network.py            # Обработка сетевых сообщений
│   ├── world.py              # Управление объектами в мире
│   └── plugin_manager.py     # Менеджер загрузки плагинов
├── plugins/                  # Директория плагинов
│   ├── __init__.py
│   ├── chat.py               # Базовый плагин чата (файл)
│   ├── basic_rp/             # Плагин-папка с ресурсами
│   │   ├── __init__.py       # Главный файл плагина
│   │   ├── models/           # 3D модели плагина
│   │   ├── sounds/           # Звуки плагина
│   │   └── config.json       # Конфигурация плагина
│   └── base_plugin.py        # Базовый класс для плагинов
└── assets/                   # Статические ресурсы ядра
    └── models/
        └── player.glb        # Базовая 3D модель игрока
```

## Архитектура системы плагинов

### Загрузчик плагинов

Система поддерживает два типа плагинов:

1. **Плагины-файлы** - одиночные Python файлы в папке `plugins/`
2. **Плагины-папки** - директории с файлом `__init__.py` и дополнительными ресурсами

### Менеджер плагинов (`core/plugin_manager.py`)

```python
class PluginManager:
    def __init__(self, server):
        self.server = server
        self.plugins = {}
        self.plugin_resources = {}
    
    def load_plugins(self):
        """Загружает все плагины из директории plugins"""
        plugins_dir = "plugins"
        
        for item in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, item)
            
            # Загрузка плагина-файла
            if item.endswith('.py') and item != '__init__.py' and item != 'base_plugin.py':
                plugin_name = item[:-3]
                self._load_file_plugin(plugin_name, plugin_path)
            
            # Загрузка плагина-папки
            elif os.path.isdir(plugin_path) and os.path.exists(os.path.join(plugin_path, '__init__.py')):
                self._load_folder_plugin(item, plugin_path)
    
    def _load_file_plugin(self, name, path):
        """Загружает плагин из одиночного файла"""
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._initialize_plugin(module, name, path)
    
    def _load_folder_plugin(self, name, path):
        """Загружает плагин из папки с ресурсами"""
        # Добавляем путь к плагину в sys.path для импорта
        sys.path.insert(0, path)
        try:
            module = importlib.import_module(name)
            self._initialize_plugin(module, name, path)
            
            # Регистрируем ресурсы плагина
            self.plugin_resources[name] = {
                'path': path,
                'models': os.path.join(path, 'models'),
                'sounds': os.path.join(path, 'sounds'),
                'textures': os.path.join(path, 'textures')
            }
        finally:
            sys.path.pop(0)
    
    def get_plugin_resource(self, plugin_name, resource_type, filename):
        """Возвращает путь к ресурсу плагина"""
        if plugin_name in self.plugin_resources:
            resource_path = self.plugin_resources[plugin_name].get(resource_type)
            if resource_path and os.path.exists(resource_path):
                return os.path.join(resource_path, filename)
        return None
```

### Базовый класс плагина

```python
class BasePlugin:
    """Базовый класс для всех плагинов niNE"""
    
    name = "base_plugin"
    version = "1.0.0"
    author = "Unknown"
    
    def __init__(self):
        self.server = None
        self.plugin_path = None
    
    def on_load(self, server, plugin_path=None):
        """Вызывается при загрузке плагина"""
        self.server = server
        self.plugin_path = plugin_path
    
    def on_unload(self):
        """Вызывается при выгрузке плагина"""
        pass
    
    def on_client_connected(self, client_id):
        """Вызывается при подключении клиента"""
        pass
    
    def on_client_message(self, client_id, data):
        """Вызывается при получении сообщения от клиента"""
        pass
    
    def on_tick(self):
        """Вызывается на каждом тике сервера"""
        pass
    
    def get_resource_path(self, *args):
        """Возвращает абсолютный путь к ресурсу плагина"""
        if self.plugin_path:
            return os.path.join(self.plugin_path, *args)
        return None
```

## Разработка плагинов

### Простой плагин-файл

```python
# plugins/chat.py
from core.base_plugin import BasePlugin

class ChatPlugin(BasePlugin):
    name = "chat"
    version = "1.0.0"
    author = "niNE Team"

    def on_client_message(self, client_id, data):
        if data.get('type') == 'chat_message':
            chat_data = {
                'type': 'chat_broadcast',
                'from': client_id,
                'message': data['message']
            }
            self.server.broadcast_to_clients(chat_data)
```

### Плагин-папка с ресурсами

Структура:
```
plugins/custom_models/
├── __init__.py
├── models/
│   ├── furniture/
│   │   └── chair.glb
│   └── weapons/
│       └── sword.glb
└── config.json
```

```python
# plugins/custom_models/__init__.py
from core.base_plugin import BasePlugin
import json
import os

class CustomModelsPlugin(BasePlugin):
    name = "custom_models"
    version = "1.0.0"
    author = "Model Designer"

    def on_load(self, server, plugin_path):
        super().on_load(server, plugin_path)
        
        # Загружаем конфигурацию плагина
        config_path = self.get_resource_path('config.json')
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        
        # Регистрируем кастомные модели
        self.register_custom_models()

    def register_custom_models(self):
        """Регистрирует кастомные модели для использования в игре"""
        chair_path = self.get_resource_path('models', 'furniture', 'chair.glb')
        sword_path = self.get_resource_path('models', 'weapons', 'sword.glb')
        
        if chair_path and os.path.exists(chair_path):
            self.server.register_model('furniture_chair', chair_path)
        
        if sword_path and os.path.exists(sword_path):
            self.server.register_model('weapon_sword', sword_path)
```

## API для работы с ресурсами

Сервер предоставляет методы для работы с ресурсами плагинов:

```python
# В коде сервера
class niNEServer:
    def register_model(self, model_id, model_path):
        """Регистрирует модель для использования на клиентах"""
        self.registered_models[model_id] = model_path
    
    def spawn_plugin_entity(self, plugin_name, model_id, position):
        """Создает сущность с моделью из плагина"""
        if model_id in self.registered_models:
            entity_data = {
                'type': 'spawn_entity',
                'model_id': model_id,
                'position': position,
                'plugin': plugin_name
            }
            self.broadcast_to_clients(entity_data)
```

## Лицензия

Этот проект лицензирован под MIT License - подробности см. в файле [LICENSE](LICENSE).
