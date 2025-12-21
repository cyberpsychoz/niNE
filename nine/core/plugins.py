"""
Система плагинов в стиле Garry's Mod Helix.

Структура плагина:
    nine/plugins/my_plugin/
        sh_plugin.py      # Метаданные плагина (обязательный)
        sh_*.py           # Shared модули (сервер + клиент)
        cl_*.py           # Клиентские модули
        sv_*.py           # Серверные модули

Префиксы файлов:
    sh_ - shared (выполняется на сервере и клиенте)
    cl_ - client only (только на клиенте)
    sv_ - server only (только на сервере)
"""

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .events import EventManager


@dataclass
class PluginInfo:
    """Метаданные плагина, определяются в sh_plugin.py."""
    unique_id: str                                          # Уникальный ID (например, "nine.chat")
    name: str                                               # Человекочитаемое имя
    description: str = ""                                   # Описание
    author: str = "Unknown"                                 # Автор
    version: str = "1.0.0"                                  # Версия
    dependencies: List[str] = field(default_factory=list)   # Зависимости (unique_id других плагинов)
    load_order: int = 50                                    # Порядок загрузки (меньше = раньше)
    enabled: bool = True                                    # Включен ли плагин


@dataclass
class PluginContext:
    """Контекст выполнения, предоставляемый каждому модулю плагина."""
    app: Any                            # GameClient или GameServer
    event_manager: EventManager         # EventManager для подписок
    plugin_info: PluginInfo             # Метаданные плагина
    plugin_path: Path                   # Путь к папке плагина
    is_server: bool                     # True если выполняется на сервере
    shared_data: Dict[str, Any]         # Общие данные между модулями плагина
    logger: logging.Logger              # Логгер для плагина

    def get_resource_path(self, filename: str) -> Path:
        """Возвращает путь к ресурсу внутри папки плагина."""
        return self.plugin_path / filename


class PluginModule:
    """
    Базовый класс для модулей внутри плагина.
    Каждый sh_*.py, cl_*.py, sv_*.py файл может содержать класс-наследник.
    """

    def __init__(self, context: PluginContext):
        self.context = context
        self.app = context.app
        self.event_manager = context.event_manager
        self.logger = context.logger
        self.plugin_path = context.plugin_path

    def on_load(self):
        """Вызывается при загрузке модуля."""
        pass

    def on_unload(self):
        """Вызывается при выгрузке модуля."""
        pass


@dataclass
class LoadedPlugin:
    """Информация о загруженном плагине."""
    info: PluginInfo
    context: PluginContext
    modules: List[PluginModule]
    plugin_module: Any  # Загруженный sh_plugin.py модуль


class PluginManager:
    """
    Менеджер плагинов в стиле Helix.
    Поддерживает папочную структуру с префиксами sh_, cl_, sv_.
    """

    def __init__(self, app, event_manager: EventManager):
        self.app = app
        self.event_manager = event_manager
        self.is_server: bool = getattr(app, 'is_server', False)

        self.loaded_plugins: Dict[str, LoadedPlugin] = {}  # unique_id -> LoadedPlugin
        self.load_order: List[str] = []  # Порядок загрузки для корректной выгрузки

        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger("PluginManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def load_plugins(self, plugin_dirs: List[str] = None):
        """Загружает все плагины из указанных директорий."""
        if plugin_dirs is None:
            plugin_dirs = ['nine/plugins', 'plugins']

        # 1. Обнаружение плагинов
        discovered = self._discover_plugins(plugin_dirs)

        # 2. Сортировка по зависимостям и load_order
        sorted_plugins = self._sort_by_dependencies(discovered)

        # 3. Загрузка плагинов
        for plugin_dir, plugin_info, plugin_module in sorted_plugins:
            self._load_single_plugin(plugin_dir, plugin_info, plugin_module)

    def _discover_plugins(self, plugin_dirs: List[str]) -> List[tuple]:
        """Обнаруживает все плагины в директориях."""
        discovered = []

        for directory in plugin_dirs:
            plugins_path = Path(directory)
            if not plugins_path.is_dir():
                continue

            self.logger.info(f"Поиск плагинов в: {directory}")

            for item in sorted(plugins_path.iterdir()):
                if item.name.startswith(("_", ".")):
                    continue

                # Новая структура: папка с sh_plugin.py
                if item.is_dir():
                    sh_plugin_file = item / "sh_plugin.py"
                    if sh_plugin_file.exists():
                        result = self._load_plugin_info(item, sh_plugin_file)
                        if result:
                            discovered.append(result)
                    else:
                        self.logger.warning(
                            f"Папка '{item.name}' не содержит sh_plugin.py, пропускаем"
                        )

        return discovered

    def _load_plugin_info(self, plugin_dir: Path, sh_plugin_path: Path) -> Optional[tuple]:
        """Загружает метаданные плагина из sh_plugin.py."""
        try:
            module_name = f"plugin_{plugin_dir.name}_sh_plugin"
            spec = importlib.util.spec_from_file_location(module_name, sh_plugin_path)
            if spec is None:
                raise ImportError(f"Не удалось создать спецификацию")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Проверяем наличие PLUGIN_INFO
            plugin_info = getattr(module, 'PLUGIN_INFO', None)
            if not isinstance(plugin_info, PluginInfo):
                raise ValueError(
                    f"PLUGIN_INFO должен быть экземпляром PluginInfo"
                )

            if not plugin_info.enabled:
                self.logger.info(f"Плагин '{plugin_info.name}' отключен")
                return None

            return (plugin_dir, plugin_info, module)

        except Exception as e:
            self.logger.error(
                f"Ошибка загрузки метаданных плагина '{plugin_dir.name}': {e}"
            )
            return None

    def _sort_by_dependencies(self, discovered: List[tuple]) -> List[tuple]:
        """Сортирует плагины по зависимостям и load_order."""
        # Создаем словарь для быстрого доступа
        by_id = {info.unique_id: (dir_, info, mod) for dir_, info, mod in discovered}

        # Топологическая сортировка
        sorted_list = []
        visited = set()
        temp_visited = set()

        def visit(unique_id: str):
            if unique_id in temp_visited:
                raise ValueError(f"Циклическая зависимость обнаружена: {unique_id}")
            if unique_id in visited:
                return

            temp_visited.add(unique_id)

            plugin_tuple = by_id.get(unique_id)
            if plugin_tuple:
                plugin_info = plugin_tuple[1]
                for dep_id in plugin_info.dependencies:
                    if dep_id not in by_id:
                        raise ValueError(
                            f"Плагин '{unique_id}' зависит от '{dep_id}', "
                            f"который не найден"
                        )
                    visit(dep_id)

            temp_visited.remove(unique_id)
            visited.add(unique_id)
            if plugin_tuple:
                sorted_list.append(plugin_tuple)

        for unique_id in by_id:
            visit(unique_id)

        # Дополнительная сортировка по load_order внутри независимых групп
        sorted_list.sort(key=lambda x: x[1].load_order)

        return sorted_list

    def _load_single_plugin(
        self,
        plugin_dir: Path,
        plugin_info: PluginInfo,
        plugin_module: Any
    ):
        """Загружает один плагин со всеми его модулями."""
        try:
            # Создаем логгер для плагина
            plugin_logger = logging.getLogger(f"Plugin.{plugin_info.unique_id}")
            if not plugin_logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
                plugin_logger.addHandler(handler)
            plugin_logger.setLevel(logging.INFO)

            # Создаем контекст
            context = PluginContext(
                app=self.app,
                event_manager=self.event_manager,
                plugin_info=plugin_info,
                plugin_path=plugin_dir,
                is_server=self.is_server,
                shared_data={},
                logger=plugin_logger
            )

            # Загружаем модули
            modules = self._load_plugin_modules(plugin_dir, context)

            # Вызываем on_load для каждого модуля
            for module in modules:
                module.on_load()

            # Вызываем on_plugin_load из sh_plugin.py
            on_load_func = getattr(plugin_module, 'on_plugin_load', None)
            if callable(on_load_func):
                on_load_func(context)

            # Сохраняем загруженный плагин
            loaded = LoadedPlugin(
                info=plugin_info,
                context=context,
                modules=modules,
                plugin_module=plugin_module
            )
            self.loaded_plugins[plugin_info.unique_id] = loaded
            self.load_order.append(plugin_info.unique_id)

            self.logger.info(
                f"Плагин загружен: {plugin_info.name} v{plugin_info.version} "
                f"({len(modules)} модулей)"
            )

        except Exception as e:
            self.logger.error(
                f"Ошибка загрузки плагина '{plugin_info.unique_id}': {e}"
            )
            import traceback
            traceback.print_exc()

    def _load_plugin_modules(
        self,
        plugin_dir: Path,
        context: PluginContext
    ) -> List[PluginModule]:
        """Загружает все модули плагина."""
        modules = []

        # Собираем файлы по типам
        all_files = list(plugin_dir.glob("*.py"))

        sh_files = sorted([f for f in all_files if f.name.startswith("sh_") and f.name != "sh_plugin.py"])
        cl_files = sorted([f for f in all_files if f.name.startswith("cl_")])
        sv_files = sorted([f for f in all_files if f.name.startswith("sv_")])

        # Загружаем shared модули (на всех платформах)
        for file_path in sh_files:
            module_instances = self._load_module_file(file_path, context)
            modules.extend(module_instances)

        # Загружаем платформо-специфичные модули
        if context.is_server:
            for file_path in sv_files:
                module_instances = self._load_module_file(file_path, context)
                modules.extend(module_instances)
        else:
            for file_path in cl_files:
                module_instances = self._load_module_file(file_path, context)
                modules.extend(module_instances)

        return modules

    def _load_module_file(
        self,
        file_path: Path,
        context: PluginContext
    ) -> List[PluginModule]:
        """Загружает модули из одного файла."""
        instances = []

        try:
            module_name = f"plugin_{context.plugin_info.unique_id.replace('.', '_')}_{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                raise ImportError(f"Не удалось создать спецификацию для {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Ищем все классы-наследники PluginModule
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, PluginModule) and
                    attr is not PluginModule):

                    instance = attr(context)
                    instances.append(instance)
                    context.logger.debug(
                        f"Загружен модуль: {attr_name} из {file_path.name}"
                    )

        except Exception as e:
            context.logger.error(
                f"Ошибка загрузки модуля {file_path.name}: {e}"
            )
            import traceback
            traceback.print_exc()

        return instances

    def unload_plugins(self):
        """Выгружает все плагины в обратном порядке."""
        for unique_id in reversed(self.load_order):
            loaded = self.loaded_plugins.get(unique_id)
            if not loaded:
                continue

            try:
                # Вызываем on_unload для модулей в обратном порядке
                for module in reversed(loaded.modules):
                    module.on_unload()

                # Вызываем on_plugin_unload из sh_plugin.py
                on_unload_func = getattr(loaded.plugin_module, 'on_plugin_unload', None)
                if callable(on_unload_func):
                    on_unload_func(loaded.context)

                self.logger.info(f"Плагин выгружен: {loaded.info.name}")

            except Exception as e:
                self.logger.error(
                    f"Ошибка выгрузки плагина '{unique_id}': {e}"
                )

        self.loaded_plugins.clear()
        self.load_order.clear()

    def get_plugin(self, unique_id: str) -> Optional[LoadedPlugin]:
        """Возвращает загруженный плагин по ID."""
        return self.loaded_plugins.get(unique_id)

    def is_plugin_loaded(self, unique_id: str) -> bool:
        """Проверяет, загружен ли плагин."""
        return unique_id in self.loaded_plugins

    def reload_plugin(self, unique_id: str) -> bool:
        """Перезагружает плагин без перезапуска приложения."""
        if unique_id not in self.loaded_plugins:
            self.logger.warning(f"Плагин '{unique_id}' не загружен")
            return False

        loaded = self.loaded_plugins[unique_id]
        plugin_dir = loaded.context.plugin_path

        # 1. Выгружаем плагин
        try:
            for module in reversed(loaded.modules):
                module.on_unload()

            on_unload_func = getattr(loaded.plugin_module, 'on_plugin_unload', None)
            if callable(on_unload_func):
                on_unload_func(loaded.context)
        except Exception as e:
            self.logger.error(f"Ошибка выгрузки при перезагрузке: {e}")

        del self.loaded_plugins[unique_id]
        self.load_order.remove(unique_id)

        # 2. Очищаем кэш импорта
        modules_to_remove = [
            name for name in sys.modules
            if name.startswith(f"plugin_{unique_id.replace('.', '_')}")
        ]
        for mod_name in modules_to_remove:
            del sys.modules[mod_name]

        # 3. Загружаем заново
        sh_plugin_path = plugin_dir / "sh_plugin.py"
        result = self._load_plugin_info(plugin_dir, sh_plugin_path)
        if result:
            plugin_dir, plugin_info, plugin_module = result
            self._load_single_plugin(plugin_dir, plugin_info, plugin_module)
            return True

        return False


# Обратная совместимость (deprecated)
class BasePlugin:
    """
    DEPRECATED: Используйте PluginModule вместо BasePlugin.
    Этот класс оставлен для обратной совместимости.
    """
    name = "BasePlugin"

    def __init__(self, app, event_manager: EventManager, plugin_path: Path):
        self.app = app
        self.event_manager = event_manager
        self.plugin_path = plugin_path
        import warnings
        warnings.warn(
            "BasePlugin устарел. Используйте PluginModule и папочную структуру.",
            DeprecationWarning
        )

    def on_load(self):
        pass

    def on_unload(self):
        pass
