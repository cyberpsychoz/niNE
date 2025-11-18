import os
import importlib.util
from pathlib import Path
from typing import List

from .events import EventManager
from .network import MessageReceivedEvent, ClientConnectedEvent, ClientDisconnectedEvent


class BasePlugin:
    """
    Базовый класс для всех плагинов.
    Плагины должны наследоваться от этого класса.
    """
    name = "BasePlugin"

    def __init__(self, event_manager: EventManager, plugin_path: Path):
        self.event_manager = event_manager
        self.plugin_path = plugin_path

    def on_load(self):
        """Вызывается при загрузке плагина."""
        pass

    def on_unload(self):
        """Вызывается при выгрузке плагина."""
        pass

    def on_tick(self, data):
        """Вызывается на каждом такте приложения."""
        pass

    def on_client_connected(self, event: ClientConnectedEvent):
        """Вызывается при подключении нового клиента."""
        pass

    def on_client_disconnected(self, event: ClientDisconnectedEvent):
        """Вызывается при отключении клиента."""
        pass

    def on_message_received(self, event: MessageReceivedEvent):
        """Вызывается при получении сообщения от клиента."""
        pass


class PluginManager:
    """
    Загружает плагины, управляет ими и перенаправляет им события.
    """

    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.plugins: List[BasePlugin] = []
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """Подписывает менеджер на события ядра для перенаправления плагинам."""
        self.event_manager.subscribe("app_tick", self._dispatch_tick)
        self.event_manager.subscribe("network_client_connected", self._dispatch_client_connected)
        self.event_manager.subscribe("network_client_disconnected", self._dispatch_client_disconnected)
        self.event_manager.subscribe("network_message_received", self._dispatch_message_received)

    def load_plugins(self, plugin_dir: str = "plugins"):
        """
        Загружает все плагины из указанной директории.
        """
        plugins_path = Path(plugin_dir)
        if not plugins_path.is_dir():
            print(f"Директория плагинов не найдена: {plugin_dir}")
            return

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
            if spec is None:
                raise ImportError(f"Не удалось создать спецификацию для {plugin_name}")
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
            if spec is None:
                raise ImportError(f"Не удалось создать спецификацию для {plugin_name}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._initialize_plugin_classes(module, dir_path)
        except Exception as e:
            print(f"Ошибка загрузки плагина из пакета {dir_path.name}: {e}")

    def _initialize_plugin_classes(self, module, path: Path):
        """Находит и инициализирует все подклассы BasePlugin в модуле."""
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isinstance(attribute, type) and issubclass(attribute, BasePlugin) and attribute is not BasePlugin:
                try:
                    instance = attribute(self.event_manager, path)
                    self.plugins.append(instance)
                    instance.on_load()
                    print(f"Плагин успешно загружен: {instance.name} из {path.name}")
                except Exception as e:
                    print(f"Ошибка инициализации класса плагина {attribute.__name__}: {e}")

    def unload_plugins(self):
        """Выгружает все загруженные плагины."""
        for plugin in self.plugins:
            try:
                plugin.on_unload()
            except Exception as e:
                print(f"Ошибка выгрузки плагина {plugin.name}: {e}")
        self.plugins = []

    def _dispatch_tick(self, data):
        for plugin in self.plugins:
            plugin.on_tick(data)

    def _dispatch_client_connected(self, event: ClientConnectedEvent):
        for plugin in self.plugins:
            plugin.on_client_connected(event)

    def _dispatch_client_disconnected(self, event: ClientDisconnectedEvent):
        for plugin in self.plugins:
            plugin.on_client_disconnected(event)

    def _dispatch_message_received(self, event: MessageReceivedEvent):
        for plugin in self.plugins:
            plugin.on_message_received(event)
