import os
import importlib.util
from pathlib import Path
from typing import List

from .events import EventManager

class BasePlugin:
    """
    Базовый класс для всех плагинов.
    Плагины должны наследоваться от этого класса и самостоятельно
    подписываться на необходимые события в методах on_load/on_unload.
    """
    name = "BasePlugin"

    def __init__(self, app, event_manager: EventManager, plugin_path: Path):
        self.app = app
        self.event_manager = event_manager
        self.plugin_path = plugin_path

    def on_load(self):
        """Вызывается при загрузке плагина."""
        pass

    def on_unload(self):
        """Вызывается при выгрузке плагина."""
        pass

class PluginManager:
    """
    Загружает и выгружает плагины.
    Плагины сами управляют своими подписками на события.
    """

    def __init__(self, app, event_manager: EventManager):
        self.app = app
        self.event_manager = event_manager
        self.plugins: List[BasePlugin] = []

    def load_plugins(self, plugin_dirs: List[str] = None):
        """
        Загружает все плагины из указанных директорий.
        По умолчанию ищет в ['nine/plugins', 'plugins'].
        """
        if plugin_dirs is None:
            plugin_dirs = ['nine/plugins', 'plugins']

        for directory in plugin_dirs:
            plugins_path = Path(directory)
            if not plugins_path.is_dir():
                continue

            print(f"Поиск плагинов в: {directory}")
            for item in sorted(plugins_path.iterdir()):
                if item.name.startswith(("_", ".")):
                    continue

                if item.is_file() and item.suffix == ".py":
                    self._load_plugin_from_file(item)
                elif item.is_dir() and (item / "__init__.py").exists():
                    self._load_plugin_from_package(item)

    def _load_plugin_from_file(self, file_path: Path):
        plugin_name = file_path.stem
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            if spec is None: raise ImportError(f"Не удалось создать спецификацию для {plugin_name}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._initialize_plugin_classes(module, file_path)
        except Exception as e:
            print(f"Ошибка загрузки плагина из файла {file_path.name}: {e}")

    def _load_plugin_from_package(self, dir_path: Path):
        plugin_name = dir_path.name
        init_path = dir_path / "__init__.py"
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, init_path)
            if spec is None: raise ImportError(f"Не удалось создать спецификацию для {plugin_name}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._initialize_plugin_classes(module, dir_path)
        except Exception as e:
            print(f"Ошибка загрузки плагина из пакета {dir_path.name}: {e}")

    def _initialize_plugin_classes(self, module, path: Path):
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isinstance(attribute, type) and issubclass(attribute, BasePlugin) and attribute is not BasePlugin:
                
                # Determine plugin type, default to 'common' if not specified
                plugin_type = getattr(attribute, 'plugin_type', 'common')
                
                # Server loads 'server' and 'common' plugins
                if self.app.is_server and plugin_type not in ['server', 'common']:
                    continue
                
                # Client loads 'client' and 'common' plugins
                if not self.app.is_server and plugin_type not in ['client', 'common']:
                    continue

                try:
                    instance = attribute(self.app, self.event_manager, path)
                    self.plugins.append(instance)
                    instance.on_load() # on_load() теперь отвечает за подписки
                    print(f"Плагин успешно загружен: {instance.name} из {path.name}")
                except Exception as e:
                    print(f"Ошибка инициализации класса плагина {attribute.__name__}: {e}")

    def unload_plugins(self):
        """Выгружает все загруженные плагины."""
        for plugin in reversed(self.plugins): # Выгружаем в обратном порядке
            try:
                plugin.on_unload()
            except Exception as e:
                print(f"Ошибка выгрузки плагина {plugin.name}: {e}")
        self.plugins = []

