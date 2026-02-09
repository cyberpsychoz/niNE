"""
Клиентский модуль DM Panel.

GUI панель управления для Игрового Мастера.
Открывается на клавишу F2 (только для dm/admin ролей).

Вкладки:
- Игроки: список игроков, телепорт, хил/урон
- Бой: управление боевыми сессиями
- Спавн NPC: создание и удаление NPC
- Аудио: музыка и эмбиент
- Мир: глобальные события
"""

from typing import Dict, List, Optional
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, DirectEntry,
    DirectScrolledFrame, DirectOptionMenu, DirectSlider, DGG
)
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode

from nine.core.plugins import PluginModule
from nine.core.game_state import GameState


class DMPanelClientModule(PluginModule, DirectObject):
    """
    Клиентский модуль DM Panel.

    Предоставляет GUI интерфейс для Игрового Мастера.
    """

    def __init__(self, context):
        PluginModule.__init__(self, context)
        DirectObject.__init__(self)

    def on_load(self):
        # Состояние UI
        self.is_open = False
        self.is_dm = False  # Проверяется при открытии
        self.current_tab = "players"

        # Данные
        self.players_data: List[dict] = []
        self.combats_data: List[dict] = []
        self.npcs_data: List[dict] = []
        self.npc_templates: List[str] = []

        # UI элементы
        self.main_frame: Optional[DirectFrame] = None
        self.tab_buttons: Dict[str, DirectButton] = {}
        self.content_frame: Optional[DirectFrame] = None

        # Подписки на события
        self.event_manager.subscribe("dm_panel_player_list", self._on_player_list)
        self.event_manager.subscribe("dm_panel_combat_list", self._on_combat_list)
        self.event_manager.subscribe("dm_panel_npc_list", self._on_npc_list)
        self.event_manager.subscribe("dm_panel_npc_templates", self._on_npc_templates)
        self.event_manager.subscribe("dm_role_check_result", self._on_role_check)
        self.event_manager.subscribe("game_state_changed", self._on_game_state_changed)

        # Клавиши (only for DirectGUI mode)
        if not self.app.ui_is_web:
            self.accept("f2", self.toggle_panel)
            self.accept("escape", self.on_escape)

        self.logger.info("DM Panel клиентский модуль загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("dm_panel_player_list", self._on_player_list)
        self.event_manager.unsubscribe("dm_panel_combat_list", self._on_combat_list)
        self.event_manager.unsubscribe("dm_panel_npc_list", self._on_npc_list)
        self.event_manager.unsubscribe("dm_panel_npc_templates", self._on_npc_templates)
        self.event_manager.unsubscribe("dm_role_check_result", self._on_role_check)
        self.event_manager.unsubscribe("game_state_changed", self._on_game_state_changed)
        self.ignoreAll()
        self._destroy_ui()
        self.logger.info("DM Panel клиентский модуль выгружен")

    def _on_game_state_changed(self, data: dict):
        """Закрываем UI при смене состояния."""
        new_state = data.get("new_state")
        if new_state != GameState.IN_GAME and self.is_open:
            self.close_panel()

    # =========================================================================
    # Data handlers
    # =========================================================================

    def _on_player_list(self, data: dict):
        """Обновление списка игроков."""
        self.players_data = data.get("players", [])
        if self.is_open and self.current_tab == "players":
            self._refresh_content()

    def _on_combat_list(self, data: dict):
        """Обновление списка боёв."""
        self.combats_data = data.get("combats", [])
        if self.is_open and self.current_tab == "combat":
            self._refresh_content()

    def _on_npc_list(self, data: dict):
        """Обновление списка NPC."""
        self.npcs_data = data.get("npcs", [])
        if self.is_open and self.current_tab == "spawn":
            self._refresh_content()

    def _on_npc_templates(self, data: dict):
        """Получение списка шаблонов NPC."""
        self.npc_templates = data.get("templates", [])
        if self.is_open and self.current_tab == "spawn":
            self._refresh_content()

    def _on_role_check(self, data: dict):
        """Результат проверки роли."""
        self.is_dm = data.get("is_dm", False)
        if self.is_dm and not self.is_open:
            self._do_open_panel()
        elif not self.is_dm:
            self._show_access_denied()

    # =========================================================================
    # UI Control
    # =========================================================================

    def toggle_panel(self):
        """Открывает/закрывает панель DM."""
        if self.is_open:
            self.close_panel()
        else:
            self.open_panel()

    def open_panel(self):
        """Открывает панель DM."""
        if self.is_open:
            return

        # Проверяем чат
        if hasattr(self.app, 'is_chat_active') and self.app.is_chat_active():
            return

        # Запрашиваем проверку роли у сервера
        self.event_manager.post("send_to_server", {
            "type": "dm_role_check"
        })

    def _do_open_panel(self):
        """Фактическое открытие панели после проверки роли."""
        self.is_open = True

        # Приостанавливаем управление камерой (камера остаётся прикреплённой)
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.pause()

        self._create_ui()

        # Запрашиваем данные
        self._request_all_data()

        self.logger.debug("DM Panel открыта")

    def _show_access_denied(self):
        """Показывает сообщение об отказе в доступе."""
        # Кратковременное уведомление
        text = OnscreenText(
            text="Доступ запрещён. Требуется роль DM или Admin.",
            pos=(0, 0),
            scale=0.06,
            fg=(1, 0.3, 0.3, 1),
            shadow=(0, 0, 0, 0.8),
            parent=self.app.aspect2d,
        )

        def remove_text(task):
            text.destroy()
            return task.done

        self.app.taskMgr.doMethodLater(2.0, remove_text, "dm-access-denied")

    def close_panel(self):
        """Закрывает панель DM."""
        if not self.is_open:
            return

        self.is_open = False
        self._destroy_ui()

        # Возобновляем управление камерой
        if hasattr(self.app, 'camera_controller') and self.app.camera_controller:
            self.app.camera_controller.resume()

        self.logger.debug("DM Panel закрыта")

    def on_escape(self):
        """Escape закрывает UI."""
        if self.is_open:
            self.close_panel()

    def _request_all_data(self):
        """Запрашивает все данные для панели."""
        self.event_manager.post("send_to_server", {"type": "dm_panel_player_list_request"})
        self.event_manager.post("send_to_server", {"type": "dm_panel_combat_list_request"})
        self.event_manager.post("send_to_server", {"type": "dm_panel_npc_list_request"})
        self.event_manager.post("send_to_server", {"type": "dm_panel_npc_templates_request"})

    # =========================================================================
    # Main UI Creation
    # =========================================================================

    def _create_ui(self):
        """Создаёт основной UI."""
        # Главный фрейм (шире чем лист персонажа)
        self.main_frame = DirectFrame(
            frameColor=(0.08, 0.08, 0.12, 0.98),
            frameSize=(-0.85, 0.85, -0.7, 0.6),
            pos=(0, 0, 0),
            parent=self.app.aspect2d,
        )

        # Заголовок
        DirectLabel(
            text="DM Panel",
            text_scale=0.055,
            text_fg=(0.9, 0.7, 0.3, 1),  # Золотой цвет для DM
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.52),
            parent=self.main_frame,
        )

        # Кнопка закрытия
        DirectButton(
            text="X",
            text_scale=0.04,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.6, 0.2, 0.2, 1),
            frameSize=(-0.03, 0.03, -0.025, 0.03),
            pos=(0.79, 0, 0.53),
            parent=self.main_frame,
            command=self.close_panel,
        )

        # Вкладки
        self._create_tabs()

        # Область контента
        self.content_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.14, 1),
            frameSize=(-0.8, 0.8, -0.65, 0.38),
            pos=(0, 0, 0),
            parent=self.main_frame,
        )

        # Загружаем контент текущей вкладки
        self._refresh_content()

    def _create_tabs(self):
        """Создаёт панель вкладок."""
        tabs = [
            ("players", "Игроки"),
            ("combat", "Бой"),
            ("spawn", "Спавн NPC"),
            ("audio", "Аудио"),
            ("world", "Мир"),
        ]

        start_x = -0.6
        tab_width = 0.24

        for i, (tab_id, tab_name) in enumerate(tabs):
            x = start_x + i * tab_width

            is_active = tab_id == self.current_tab
            color = (0.4, 0.35, 0.2, 1) if is_active else (0.2, 0.2, 0.25, 1)

            btn = DirectButton(
                text=tab_name,
                text_scale=0.032,
                text_fg=(1, 1, 1, 1),
                frameColor=color,
                frameSize=(-0.11, 0.11, -0.025, 0.035),
                pos=(x, 0, 0.43),
                parent=self.main_frame,
                command=self._switch_tab,
                extraArgs=[tab_id],
            )

            self.tab_buttons[tab_id] = btn

    def _switch_tab(self, tab_id: str):
        """Переключает вкладку."""
        if tab_id == self.current_tab:
            return

        self.current_tab = tab_id

        # Обновляем цвета кнопок
        for tid, btn in self.tab_buttons.items():
            is_active = tid == self.current_tab
            color = (0.4, 0.35, 0.2, 1) if is_active else (0.2, 0.2, 0.25, 1)
            btn["frameColor"] = color

        # Обновляем контент
        self._refresh_content()

    def _refresh_content(self):
        """Обновляет содержимое текущей вкладки."""
        # Очищаем контент
        if self.content_frame:
            for child in self.content_frame.getChildren():
                child.removeNode()

        # Загружаем контент в зависимости от вкладки
        if self.current_tab == "players":
            self._create_players_content()
        elif self.current_tab == "combat":
            self._create_combat_content()
        elif self.current_tab == "spawn":
            self._create_spawn_content()
        elif self.current_tab == "audio":
            self._create_audio_content()
        elif self.current_tab == "world":
            self._create_world_content()

    def _destroy_ui(self):
        """Уничтожает UI."""
        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None
        self.tab_buttons.clear()
        self.content_frame = None

    # =========================================================================
    # Players Tab
    # =========================================================================

    def _create_players_content(self):
        """Создаёт контент вкладки Игроки."""
        # Заголовок списка
        DirectLabel(
            text="Подключённые игроки:",
            text_scale=0.04,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.32),
            parent=self.content_frame,
        )

        # Скроллируемый список игроков
        scroll_frame = DirectScrolledFrame(
            frameColor=(0.12, 0.12, 0.16, 1),
            frameSize=(-0.75, 0.75, -0.55, 0.28),
            canvasSize=(-0.73, 0.7, -0.5, 0.25),
            scrollBarWidth=0.02,
            pos=(0, 0, 0),
            parent=self.content_frame,
        )

        if not self.players_data:
            DirectLabel(
                text="Нет подключённых игроков",
                text_scale=0.035,
                text_fg=(0.5, 0.5, 0.5, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0.1),
                parent=scroll_frame.getCanvas(),
            )
            return

        # Список игроков
        y = 0.2
        for player in self.players_data:
            self._create_player_row(scroll_frame.getCanvas(), player, y)
            y -= 0.12

        # Обновляем размер канваса
        canvas_height = len(self.players_data) * 0.12 + 0.1
        scroll_frame["canvasSize"] = (-0.73, 0.7, -canvas_height, 0.25)

    def _create_player_row(self, parent, player: dict, y: float):
        """Создаёт строку игрока."""
        player_id = player.get("id", -1)
        name = player.get("name", "Unknown")
        char_class = player.get("class", "")
        level = player.get("level", 1)
        hp = player.get("hp_current", 0)
        hp_max = player.get("hp_max", 0)

        # Фон строки
        row_frame = DirectFrame(
            frameColor=(0.15, 0.15, 0.2, 1),
            frameSize=(-0.72, 0.69, -0.05, 0.05),
            pos=(0, 0, y),
            parent=parent,
        )

        # Имя и класс
        DirectLabel(
            text=f"{name} ({char_class} Lv.{level})",
            text_scale=0.032,
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, 0),
            parent=row_frame,
        )

        # HP
        hp_color = (0.3, 0.9, 0.3, 1) if hp > hp_max * 0.5 else (0.9, 0.9, 0.3, 1) if hp > hp_max * 0.25 else (0.9, 0.3, 0.3, 1)
        DirectLabel(
            text=f"HP: {hp}/{hp_max}",
            text_scale=0.028,
            text_fg=hp_color,
            frameColor=(0, 0, 0, 0),
            pos=(-0.1, 0, 0),
            parent=row_frame,
        )

        # Кнопки действий
        DirectButton(
            text="TP",
            text_scale=0.025,
            frameColor=(0.3, 0.4, 0.6, 1),
            frameSize=(-0.04, 0.04, -0.025, 0.025),
            pos=(0.35, 0, 0),
            parent=row_frame,
            command=self._teleport_to_player,
            extraArgs=[player_id],
        )

        DirectButton(
            text="+HP",
            text_scale=0.025,
            frameColor=(0.3, 0.6, 0.3, 1),
            frameSize=(-0.04, 0.04, -0.025, 0.025),
            pos=(0.45, 0, 0),
            parent=row_frame,
            command=self._heal_player,
            extraArgs=[player_id],
        )

        DirectButton(
            text="-HP",
            text_scale=0.025,
            frameColor=(0.6, 0.3, 0.3, 1),
            frameSize=(-0.04, 0.04, -0.025, 0.025),
            pos=(0.55, 0, 0),
            parent=row_frame,
            command=self._damage_player,
            extraArgs=[player_id],
        )

        DirectButton(
            text="Kill",
            text_scale=0.025,
            frameColor=(0.5, 0.2, 0.2, 1),
            frameSize=(-0.04, 0.04, -0.025, 0.025),
            pos=(0.65, 0, 0),
            parent=row_frame,
            command=self._kill_player,
            extraArgs=[player_id],
        )

    def _teleport_to_player(self, player_id: int):
        """Телепортирует DM к игроку."""
        self.event_manager.post("send_to_server", {
            "type": "dm_panel_player_action",
            "action": "teleport_to",
            "player_id": player_id,
        })

    def _heal_player(self, player_id: int):
        """Хилит игрока на 10 HP."""
        self.event_manager.post("send_to_server", {
            "type": "dm_panel_player_action",
            "action": "heal",
            "player_id": player_id,
            "amount": 10,
        })

    def _damage_player(self, player_id: int):
        """Наносит урон игроку 10 HP."""
        self.event_manager.post("send_to_server", {
            "type": "dm_panel_player_action",
            "action": "damage",
            "player_id": player_id,
            "amount": 10,
        })

    def _kill_player(self, player_id: int):
        """Убивает игрока."""
        self.event_manager.post("send_to_server", {
            "type": "dm_panel_player_action",
            "action": "kill",
            "player_id": player_id,
        })

    # =========================================================================
    # Combat Tab
    # =========================================================================

    def _create_combat_content(self):
        """Создаёт контент вкладки Бой."""
        # Кнопки управления
        DirectButton(
            text="Начать бой",
            text_scale=0.035,
            frameColor=(0.4, 0.5, 0.3, 1),
            frameSize=(-0.12, 0.12, -0.03, 0.04),
            pos=(-0.55, 0, 0.32),
            parent=self.content_frame,
            command=self._start_combat,
        )

        DirectButton(
            text="Завершить бой",
            text_scale=0.035,
            frameColor=(0.5, 0.3, 0.3, 1),
            frameSize=(-0.12, 0.12, -0.03, 0.04),
            pos=(-0.25, 0, 0.32),
            parent=self.content_frame,
            command=self._end_combat,
        )

        DirectButton(
            text="Следующий ход",
            text_scale=0.035,
            frameColor=(0.3, 0.4, 0.5, 1),
            frameSize=(-0.12, 0.12, -0.03, 0.04),
            pos=(0.05, 0, 0.32),
            parent=self.content_frame,
            command=self._next_turn,
        )

        # Заголовок списка
        DirectLabel(
            text="Активные бои:",
            text_scale=0.04,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.22),
            parent=self.content_frame,
        )

        # Скроллируемый список боёв
        scroll_frame = DirectScrolledFrame(
            frameColor=(0.12, 0.12, 0.16, 1),
            frameSize=(-0.75, 0.75, -0.55, 0.18),
            canvasSize=(-0.73, 0.7, -0.5, 0.15),
            scrollBarWidth=0.02,
            pos=(0, 0, 0),
            parent=self.content_frame,
        )

        if not self.combats_data:
            DirectLabel(
                text="Нет активных боёв",
                text_scale=0.035,
                text_fg=(0.5, 0.5, 0.5, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0.05),
                parent=scroll_frame.getCanvas(),
            )
            return

        # Список боёв
        y = 0.1
        for combat in self.combats_data:
            self._create_combat_row(scroll_frame.getCanvas(), combat, y)
            y -= 0.15

    def _create_combat_row(self, parent, combat: dict, y: float):
        """Создаёт строку боя."""
        combat_id = combat.get("id", "")
        participants_count = combat.get("participants_count", 0)
        current_turn = combat.get("current_turn", "")
        round_num = combat.get("round", 1)

        row_frame = DirectFrame(
            frameColor=(0.15, 0.15, 0.2, 1),
            frameSize=(-0.72, 0.69, -0.06, 0.06),
            pos=(0, 0, y),
            parent=parent,
        )

        DirectLabel(
            text=f"Бой #{combat_id[:8]}... | Раунд {round_num} | Участников: {participants_count}",
            text_scale=0.028,
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, 0.02),
            parent=row_frame,
        )

        DirectLabel(
            text=f"Ход: {current_turn}",
            text_scale=0.025,
            text_fg=(0.7, 0.9, 0.7, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, -0.025),
            parent=row_frame,
        )

    def _start_combat(self):
        """Начинает бой."""
        self.event_manager.post("send_to_server", {
            "type": "dm_start_combat",
            "radius": 20,
        })

    def _end_combat(self):
        """Завершает бой."""
        self.event_manager.post("send_to_server", {
            "type": "dm_end_combat",
        })

    def _next_turn(self):
        """Переходит к следующему ходу."""
        self.event_manager.post("send_to_server", {
            "type": "dm_force_next_turn",
        })

    # =========================================================================
    # Spawn NPC Tab
    # =========================================================================

    def _create_spawn_content(self):
        """Создаёт контент вкладки Спавн NPC."""
        # Выбор шаблона
        DirectLabel(
            text="Шаблон NPC:",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.32),
            parent=self.content_frame,
        )

        templates = self.npc_templates if self.npc_templates else ["guard", "goblin", "merchant", "skeleton"]

        self.npc_template_menu = DirectOptionMenu(
            text="Выбрать",
            scale=0.05,
            items=templates,
            initialitem=0,
            highlightColor=(0.65, 0.65, 0.65, 1),
            pos=(-0.35, 0, 0.32),
            parent=self.content_frame,
        )

        # Координаты
        DirectLabel(
            text="X:",
            text_scale=0.03,
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0.1, 0, 0.32),
            parent=self.content_frame,
        )

        self.spawn_x_entry = DirectEntry(
            text="0",
            scale=0.04,
            width=4,
            pos=(0.22, 0, 0.32),
            parent=self.content_frame,
            initialText="0",
        )

        DirectLabel(
            text="Y:",
            text_scale=0.03,
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0.4, 0, 0.32),
            parent=self.content_frame,
        )

        self.spawn_y_entry = DirectEntry(
            text="0",
            scale=0.04,
            width=4,
            pos=(0.52, 0, 0.32),
            parent=self.content_frame,
            initialText="0",
        )

        # Кнопка спавна
        DirectButton(
            text="Заспавнить",
            text_scale=0.035,
            frameColor=(0.3, 0.5, 0.3, 1),
            frameSize=(-0.1, 0.1, -0.03, 0.04),
            pos=(-0.55, 0, 0.22),
            parent=self.content_frame,
            command=self._spawn_npc,
        )

        # Заголовок списка
        DirectLabel(
            text="Активные NPC:",
            text_scale=0.04,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.12),
            parent=self.content_frame,
        )

        # Скроллируемый список NPC
        scroll_frame = DirectScrolledFrame(
            frameColor=(0.12, 0.12, 0.16, 1),
            frameSize=(-0.75, 0.75, -0.55, 0.08),
            canvasSize=(-0.73, 0.7, -0.5, 0.05),
            scrollBarWidth=0.02,
            pos=(0, 0, 0),
            parent=self.content_frame,
        )

        if not self.npcs_data:
            DirectLabel(
                text="Нет активных NPC",
                text_scale=0.035,
                text_fg=(0.5, 0.5, 0.5, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0),
                parent=scroll_frame.getCanvas(),
            )
            return

        # Список NPC
        y = 0.0
        for npc in self.npcs_data:
            self._create_npc_row(scroll_frame.getCanvas(), npc, y)
            y -= 0.1

        canvas_height = len(self.npcs_data) * 0.1 + 0.1
        scroll_frame["canvasSize"] = (-0.73, 0.7, -canvas_height, 0.05)

    def _create_npc_row(self, parent, npc: dict, y: float):
        """Создаёт строку NPC."""
        npc_id = npc.get("id", "")
        name = npc.get("name", "NPC")
        template = npc.get("template", "unknown")
        pos = npc.get("position", [0, 0, 0])

        row_frame = DirectFrame(
            frameColor=(0.15, 0.15, 0.2, 1),
            frameSize=(-0.72, 0.69, -0.04, 0.04),
            pos=(0, 0, y),
            parent=parent,
        )

        DirectLabel(
            text=f"{name} ({template}) @ ({pos[0]:.1f}, {pos[1]:.1f})",
            text_scale=0.028,
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.7, 0, 0),
            parent=row_frame,
        )

        DirectButton(
            text="X",
            text_scale=0.025,
            frameColor=(0.6, 0.3, 0.3, 1),
            frameSize=(-0.03, 0.03, -0.02, 0.02),
            pos=(0.65, 0, 0),
            parent=row_frame,
            command=self._despawn_npc,
            extraArgs=[npc_id],
        )

    def _spawn_npc(self):
        """Спавнит NPC."""
        template = self.npc_template_menu.get()
        try:
            x = float(self.spawn_x_entry.get())
            y = float(self.spawn_y_entry.get())
        except ValueError:
            x, y = 0, 0

        self.event_manager.post("send_to_server", {
            "type": "dm_npc_spawn",
            "template_id": template,
            "position": [x, y, 1],
        })

    def _despawn_npc(self, npc_id: str):
        """Удаляет NPC."""
        self.event_manager.post("send_to_server", {
            "type": "dm_npc_despawn",
            "npc_id": npc_id,
        })

    # =========================================================================
    # Audio Tab
    # =========================================================================

    def _create_audio_content(self):
        """Создаёт контент вкладки Аудио."""
        # Музыка
        DirectLabel(
            text="Плейлист музыки:",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.32),
            parent=self.content_frame,
        )

        playlists = ["adventure", "combat", "catacombs", "city", "dark_forest"]
        self.music_menu = DirectOptionMenu(
            text="Выбрать",
            scale=0.05,
            items=playlists,
            initialitem=0,
            highlightColor=(0.65, 0.65, 0.65, 1),
            pos=(-0.25, 0, 0.32),
            parent=self.content_frame,
        )

        DirectButton(
            text="Play",
            text_scale=0.03,
            frameColor=(0.3, 0.5, 0.3, 1),
            frameSize=(-0.05, 0.05, -0.025, 0.03),
            pos=(0.15, 0, 0.32),
            parent=self.content_frame,
            command=self._play_music,
        )

        DirectButton(
            text="Stop",
            text_scale=0.03,
            frameColor=(0.5, 0.3, 0.3, 1),
            frameSize=(-0.05, 0.05, -0.025, 0.03),
            pos=(0.28, 0, 0.32),
            parent=self.content_frame,
            command=self._stop_music,
        )

        # Эмбиент
        DirectLabel(
            text="Эмбиент:",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.18),
            parent=self.content_frame,
        )

        ambients = ["forest_day", "forest_night", "cave", "beach", "sea", "inside_day", "inside_night"]
        self.ambient_menu = DirectOptionMenu(
            text="Выбрать",
            scale=0.05,
            items=ambients,
            initialitem=0,
            highlightColor=(0.65, 0.65, 0.65, 1),
            pos=(-0.25, 0, 0.18),
            parent=self.content_frame,
        )

        DirectButton(
            text="Set",
            text_scale=0.03,
            frameColor=(0.3, 0.4, 0.5, 1),
            frameSize=(-0.05, 0.05, -0.025, 0.03),
            pos=(0.15, 0, 0.18),
            parent=self.content_frame,
            command=self._set_ambient,
        )

        DirectButton(
            text="Stop",
            text_scale=0.03,
            frameColor=(0.5, 0.3, 0.3, 1),
            frameSize=(-0.05, 0.05, -0.025, 0.03),
            pos=(0.28, 0, 0.18),
            parent=self.content_frame,
            command=self._stop_ambient,
        )

        # Громкость
        DirectLabel(
            text="Громкость (для всех):",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.04),
            parent=self.content_frame,
        )

        self.volume_slider = DirectSlider(
            range=(0, 100),
            value=70,
            pageSize=5,
            scale=0.4,
            pos=(0.1, 0, 0.04),
            parent=self.content_frame,
            command=self._on_volume_change,
        )

        self.volume_label = DirectLabel(
            text="70%",
            text_scale=0.03,
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0.55, 0, 0.04),
            parent=self.content_frame,
        )

    def _play_music(self):
        """Включает музыку."""
        playlist = self.music_menu.get()
        self.event_manager.post("send_to_server", {
            "type": "dm_audio_command",
            "command": "music_play",
            "playlist": playlist,
        })

    def _stop_music(self):
        """Останавливает музыку."""
        self.event_manager.post("send_to_server", {
            "type": "dm_audio_command",
            "command": "music_stop",
        })

    def _set_ambient(self):
        """Устанавливает эмбиент."""
        zone = self.ambient_menu.get()
        self.event_manager.post("send_to_server", {
            "type": "dm_audio_command",
            "command": "ambient_set",
            "zone": zone,
        })

    def _stop_ambient(self):
        """Останавливает эмбиент."""
        self.event_manager.post("send_to_server", {
            "type": "dm_audio_command",
            "command": "ambient_stop",
        })

    def _on_volume_change(self):
        """Обработчик изменения громкости."""
        volume = int(self.volume_slider["value"])
        self.volume_label["text"] = f"{volume}%"

        self.event_manager.post("send_to_server", {
            "type": "dm_audio_command",
            "command": "volume_set",
            "volume": volume,
        })

    # =========================================================================
    # World Tab
    # =========================================================================

    def _create_world_content(self):
        """Создаёт контент вкладки Мир."""
        # Глобальное объявление
        DirectLabel(
            text="Объявление для всех:",
            text_scale=0.035,
            text_fg=(0.8, 0.8, 0.8, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.32),
            parent=self.content_frame,
        )

        self.announcement_entry = DirectEntry(
            text="",
            scale=0.04,
            width=25,
            pos=(-0.75, 0, 0.22),
            parent=self.content_frame,
        )

        DirectButton(
            text="Отправить",
            text_scale=0.035,
            frameColor=(0.3, 0.4, 0.5, 1),
            frameSize=(-0.1, 0.1, -0.03, 0.04),
            pos=(0.5, 0, 0.22),
            parent=self.content_frame,
            command=self._send_announcement,
        )

        # Будущие функции
        DirectLabel(
            text="Будущие функции:",
            text_scale=0.035,
            text_fg=(0.6, 0.6, 0.6, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.75, 0, 0.05),
            parent=self.content_frame,
        )

        features = [
            "- Управление временем суток",
            "- Погодные эффекты",
            "- Триггеры событий",
            "- Сохранение состояния мира",
        ]

        y = -0.02
        for feature in features:
            DirectLabel(
                text=feature,
                text_scale=0.028,
                text_fg=(0.5, 0.5, 0.5, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.72, 0, y),
                parent=self.content_frame,
            )
            y -= 0.06

    def _send_announcement(self):
        """Отправляет глобальное объявление."""
        text = self.announcement_entry.get()
        if text.strip():
            self.event_manager.post("send_to_server", {
                "type": "dm_announcement",
                "message": text,
            })
            self.announcement_entry.enterText("")
