"""
Клиентский UI модуль плагина.

Этот файл загружается ТОЛЬКО на клиенте.
Используйте для UI компонентов, рендеринга, эффектов и обработки ввода.
"""
from nine.core.plugins import PluginModule
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton
from panda3d.core import TextNode


class UIModule(PluginModule):
    """
    Клиентский модуль для отображения UI.

    События, на которые подписывается:
    - game_state_changed: Показ/скрытие UI в зависимости от состояния
    - author.plugin_name.data_update: Обновление данных от сервера

    События, которые отправляет:
    - author.plugin_name.button_clicked: Когда пользователь нажал кнопку
    """

    def on_load(self):
        """
        Инициализация клиентского модуля.
        Создайте UI и подпишитесь на события.
        """
        self.logger.info("🎨 Клиентский UI модуль загружен")

        # UI элементы
        self.ui_frame = None
        self.title_label = None
        self.info_label = None
        self.button = None

        # Данные
        self.data = {}

        # Подписка на события
        self.event_manager.subscribe("game_state_changed", self.on_game_state_changed)
        self.event_manager.subscribe("author.plugin_name.data_update", self.on_data_update)

        # Привязка клавиш
        # self.app.accept("f1", self.toggle_ui)  # F1 для открытия/закрытия

        # Создание UI
        self.create_ui()

        # Доступ к Panda3D
        # self.app.render - Сцена рендеринга
        # self.app.camera - Камера
        # self.app.taskMgr - Менеджер задач
        # self.app.loader - Загрузчик ресурсов

    def on_unload(self):
        """
        Очистка ресурсов при выгрузке.
        Удалите UI и отпишитесь от событий.
        """
        # Удаление UI
        if self.ui_frame:
            self.ui_frame.destroy()
            self.ui_frame = None

        # Отписка от событий
        self.event_manager.unsubscribe("game_state_changed", self.on_game_state_changed)
        self.event_manager.unsubscribe("author.plugin_name.data_update", self.on_data_update)

        self.logger.info("🎨 Клиентский UI модуль выгружен")

    # ========================================================================
    # СОЗДАНИЕ UI
    # ========================================================================

    def create_ui(self):
        """
        Создание UI элементов с использованием DirectGUI.
        """
        # Главный фрейм (контейнер)
        self.ui_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 0.85),  # Темный полупрозрачный фон
            frameSize=(-0.6, 0.6, -0.4, 0.4),  # Размер (лево, право, низ, верх)
            pos=(0, 0, 0),  # Позиция (центр экрана)
        )

        # Заголовок
        self.title_label = DirectLabel(
            text="Plugin Name",
            parent=self.ui_frame,
            scale=0.08,
            pos=(0, 0, 0.3),
            text_fg=(1, 1, 0.5, 1),  # Желтоватый цвет
            text_shadow=(0, 0, 0, 1),  # Черная тень
            text_shadowOffset=(0.05, 0.05),
            text_align=TextNode.ACenter,
        )

        # Информационная метка
        self.info_label = DirectLabel(
            text="Информация будет здесь",
            parent=self.ui_frame,
            scale=0.06,
            pos=(0, 0, 0.1),
            text_fg=(0.9, 0.9, 0.9, 1),  # Светло-серый
            text_shadow=(0, 0, 0, 1),
            text_shadowOffset=(0.05, 0.05),
            text_align=TextNode.ACenter,
        )

        # Кнопка
        self.button = DirectButton(
            text="Нажми меня",
            parent=self.ui_frame,
            scale=0.07,
            pos=(0, 0, -0.2),
            text_fg=(1, 1, 1, 1),
            frameColor=(0.3, 0.5, 0.8, 1),  # Синий фон
            command=self.on_button_clicked,  # Обработчик нажатия
            rolloverSound=None,
            clickSound=None,
        )

        # Скрыть UI по умолчанию
        self.ui_frame.hide()

    # ========================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ========================================================================

    def on_game_state_changed(self, data: dict):
        """
        Обработчик смены состояния игры.

        Args:
            data (dict): Данные события
                - state (str): "MENU" | "CONNECTING" | "IN_GAME"
        """
        state = data.get("state")

        if state == "IN_GAME":
            # Показать UI когда в игре
            # self.ui_frame.show()
            pass
        else:
            # Скрыть UI в меню
            self.ui_frame.hide()

    def on_data_update(self, data: dict):
        """
        Обработчик обновления данных от сервера.

        Args:
            data (dict): Данные от сервера
        """
        self.logger.info(f"📨 Получено обновление данных: {data}")

        # Сохранить данные
        self.data = data

        # Обновить UI
        self.refresh_ui()

    def on_button_clicked(self):
        """
        Обработчик нажатия на кнопку.
        """
        self.logger.info("🖱️ Кнопка нажата")

        # Отправить событие (например, на сервер через GameClient)
        self.event_manager.post("author.plugin_name.button_clicked", {})

    # ========================================================================
    # МЕТОДЫ UI
    # ========================================================================

    def toggle_ui(self):
        """Переключить видимость UI."""
        if self.ui_frame.isHidden():
            self.ui_frame.show()
            self.logger.info("UI открыт")
        else:
            self.ui_frame.hide()
            self.logger.info("UI закрыт")

    def show_ui(self):
        """Показать UI."""
        self.ui_frame.show()

    def hide_ui(self):
        """Скрыть UI."""
        self.ui_frame.hide()

    def refresh_ui(self):
        """
        Обновить UI на основе текущих данных.
        """
        # Пример: обновить текст метки
        if "message" in self.data:
            self.info_label["text"] = self.data["message"]

        if "score" in self.data:
            self.info_label["text"] = f"Счет: {self.data['score']}"

    def update_task(self, task):
        """
        Задача обновления, вызываемая каждый кадр.

        Используйте для анимаций, обновления позиций и т.д.

        Returns:
            task.cont - продолжить выполнение
            task.done - завершить задачу
        """
        # Пример: обновление каждый кадр
        # dt = globalClock.getDt()
        # self.some_value += dt

        return task.cont

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================

    def load_texture(self, texture_path: str):
        """
        Загрузить текстуру.

        Args:
            texture_path: Путь к текстуре относительно assets

        Returns:
            Texture или None
        """
        try:
            texture = self.app.loader.loadTexture(texture_path)
            self.logger.info(f"Текстура загружена: {texture_path}")
            return texture
        except Exception as e:
            self.logger.error(f"Ошибка загрузки текстуры {texture_path}: {e}")
            return None

    def play_sound(self, sound_path: str):
        """
        Воспроизвести звук.

        Args:
            sound_path: Путь к звуку
        """
        try:
            sound = self.app.loader.loadSfx(sound_path)
            sound.play()
            self.logger.info(f"Звук воспроизведен: {sound_path}")
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения звука {sound_path}: {e}")
