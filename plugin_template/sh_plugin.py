"""
Plugin Name - Краткое описание плагина

Подробное описание того, что делает плагин.
"""
from nine.core.plugins import PluginInfo

# ============================================================================
# МЕТАДАННЫЕ ПЛАГИНА (ОБЯЗАТЕЛЬНО)
# ============================================================================

PLUGIN_INFO = PluginInfo(
    # Уникальный идентификатор плагина (формат: author.plugin_name)
    unique_id="author.plugin_name",

    # Отображаемое имя плагина
    name="Plugin Name",

    # Описание функционала
    description="Описание того, что делает плагин",

    # Автор плагина
    author="YourName",

    # Версия плагина (формат: major.minor.patch)
    version="1.0.0",

    # Список зависимостей (unique_id других плагинов)
    # Пример: dependencies=["nine.inventory", "nine.stats"]
    dependencies=[],

    # Порядок загрузки (10-100, меньше = раньше)
    # 10-20: Ядро (world config, базовые системы)
    # 20-30: Визуальные системы (lighting, skybox)
    # 30-40: Игровые системы (stats, physics)
    # 40-50: Высокоуровневая логика (inventory, quests)
    # 50-60: UI и взаимодействие (chat, menus)
    # 60-100: Пользовательские плагины
    load_order=60,

    # Включен ли плагин (True/False)
    enabled=True,
)


# ============================================================================
# ХУКИ ЖИЗНЕННОГО ЦИКЛА (ОПЦИОНАЛЬНО)
# ============================================================================

def on_plugin_load(context):
    """
    Вызывается ОДИН РАЗ после загрузки всех модулей плагина.

    Используйте для:
    - Инициализации общих данных в context.shared_data
    - Логирования информации о загрузке
    - Настройки глобальных переменных плагина

    Args:
        context (PluginContext): Контекст выполнения плагина
            - app: GameClient или GameServer
            - event_manager: Менеджер событий
            - plugin_info: Метаданные плагина
            - plugin_path: Path к папке плагина
            - is_server: True на сервере, False на клиенте
            - shared_data: Общий словарь для всех модулей
            - logger: Логгер плагина
    """
    context.logger.info(f"✅ {PLUGIN_INFO.name} v{PLUGIN_INFO.version} загружен!")

    # Инициализация общих данных
    context.shared_data["initialized"] = True
    context.shared_data["data"] = {}

    # Пример условной инициализации
    if context.is_server:
        context.logger.info("Плагин загружен на сервере")
    else:
        context.logger.info("Плагин загружен на клиенте")
