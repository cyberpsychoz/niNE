# nine/ui/settings_menu.py
"""
Меню настроек с вкладками.
Минималистичный тёмный дизайн.
"""

from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectEntry, DirectLabel,
    DirectOptionMenu, DGG, DirectSlider, DirectCheckButton
)
from panda3d.core import TextNode, WindowProperties, TransparencyAttrib

from .base_component import BaseUIComponent
from .theme import NineTheme
from nine.core.config import config


class SettingsMenu(BaseUIComponent):
    """Меню настроек с вкладками."""

    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client
        self.from_in_game = False  # Флаг: открыто из игрового меню
        self.current_tab = "general"  # Текущая вкладка
        self.tab_frames = {}  # Фреймы вкладок
        self.tab_buttons = {}  # Кнопки вкладок
        self._setup()

    def _setup(self):
        """Создает элементы меню настроек."""
        # Полупрозрачный тёмный фон
        bg = self._add_element('background', DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=NineTheme.BG_DARK,
        ))
        bg.setTransparency(TransparencyAttrib.M_alpha)

        # Центральная панель (увеличена для вкладок)
        panel_width = 2.2
        panel_height = 1.5
        self.panel = self._add_element('panel', DirectFrame(
            parent=self.base.aspect2d,
            frameSize=(-panel_width/2, panel_width/2, -panel_height/2, panel_height/2),
            frameColor=NineTheme.BG_MEDIUM,
            pos=(0, 0, 0),
            sortOrder=10
        ))
        self.panel.setTransparency(TransparencyAttrib.M_alpha)

        # Заголовок
        self._add_element('title', DirectLabel(
            parent=self.panel,
            text="НАСТРОЙКИ",
            scale=NineTheme.TITLE_SCALE,
            pos=(0, 0, panel_height/2 - 0.10),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        ))

        # Создаём вкладки
        self._create_tabs(panel_width, panel_height)

        # Создаём контент для каждой вкладки
        self._create_general_tab(panel_width, panel_height)
        self._create_controls_tab(panel_width, panel_height)
        self._create_graphics_tab(panel_width, panel_height)
        self._create_audio_tab(panel_width, panel_height)

        # Кнопки внизу
        btn_y = -panel_height/2 + 0.12
        btn_spacing = 0.35

        self._add_element('save_button', DirectButton(
            parent=self.panel,
            text="Сохранить",
            scale=NineTheme.BUTTON_SCALE,
            pos=(-btn_spacing/2 - 0.15, 0, btn_y),
            command=self._on_save_click,
            frameColor=NineTheme.accent_button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        ))

        self._add_element('back_button', DirectButton(
            parent=self.panel,
            text="Назад",
            scale=NineTheme.BUTTON_SCALE,
            pos=(btn_spacing/2 + 0.15, 0, btn_y),
            command=self._on_back_click,
            frameColor=NineTheme.button_colors(),
            text_fg=NineTheme.TEXT_PRIMARY,
            text_align=TextNode.ACenter,
            pressEffect=True,
            relief=DGG.FLAT,
            frameSize=(-3.5, 3.5, -0.8, 1.1),
        ))

        # Показываем первую вкладку
        self._switch_tab("general")
        self.hide()

    def _create_tabs(self, panel_width, panel_height):
        """Создаёт кнопки вкладок."""
        tabs = [
            ("general", "Общие"),
            ("controls", "Управление"),
            ("graphics", "Графика"),
            ("audio", "Звук"),
        ]

        tab_y = panel_height/2 - 0.22
        tab_width = 0.55
        start_x = -len(tabs) * tab_width / 2 + tab_width / 2

        for i, (tab_id, tab_name) in enumerate(tabs):
            x_pos = start_x + i * tab_width
            btn = self._add_element(f'tab_{tab_id}', DirectButton(
                parent=self.panel,
                text=tab_name,
                scale=NineTheme.LABEL_SCALE,
                pos=(x_pos, 0, tab_y),
                command=lambda tid=tab_id: self._switch_tab(tid),
                frameColor=NineTheme.button_colors(),
                text_fg=NineTheme.TEXT_PRIMARY,
                text_align=TextNode.ACenter,
                pressEffect=True,
                relief=DGG.FLAT,
                frameSize=(-4.5, 4.5, -1.0, 1.3),
            ))
            self.tab_buttons[tab_id] = btn

    def _create_general_tab(self, panel_width, panel_height):
        """Создаёт содержимое вкладки 'Общие'."""
        frame = DirectFrame(
            parent=self.panel,
            frameSize=(-panel_width/2 + 0.05, panel_width/2 - 0.05, -0.45, 0.35),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.05),
        )
        self.tab_frames["general"] = frame

        label_x = -panel_width/2 + 0.15
        value_x = 0.05
        row_height = 0.15
        row_y = 0.25

        # Никнейм
        DirectLabel(
            parent=frame,
            text="Никнейм:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )
        self.nickname_entry = DirectEntry(
            parent=frame,
            scale=NineTheme.ENTRY_SCALE,
            pos=(value_x, 0, row_y),
            initialText=config.get("nickname"),
            numLines=1,
            width=12,
            text_align=TextNode.ALeft,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            cursorKeys=True,
        )

        # Разрешение
        row_y -= row_height
        DirectLabel(
            parent=frame,
            text="Разрешение:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        available_resolutions = config.get("available_resolutions")
        current_resolution = config.get("resolution")

        self.resolution_menu = DirectOptionMenu(
            parent=frame,
            text=current_resolution,
            scale=NineTheme.ENTRY_SCALE,
            pos=(value_x, 0, row_y),
            items=available_resolutions,
            initialitem=available_resolutions.index(current_resolution) if current_resolution in available_resolutions else 0,
            highlightColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.ENTRY_BG,
            text_fg=NineTheme.TEXT_PRIMARY,
            popupMarker_frameColor=NineTheme.BTN_NORMAL,
            sortOrder=11,
        )

    def _create_controls_tab(self, panel_width, panel_height):
        """Создаёт содержимое вкладки 'Управление'."""
        frame = DirectFrame(
            parent=self.panel,
            frameSize=(-panel_width/2 + 0.05, panel_width/2 - 0.05, -0.45, 0.35),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.05),
        )
        self.tab_frames["controls"] = frame

        label_x = -panel_width/2 + 0.15
        value_x = 0.05
        row_height = 0.13
        row_y = 0.28

        # Чувствительность мыши
        DirectLabel(
            parent=frame,
            text="Чувствительность:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        initial_sensitivity = config.get("camera_sensitivity", 1.0)

        self.sensitivity_slider = DirectSlider(
            parent=frame,
            range=(0.1, 3.0),
            value=initial_sensitivity,
            scale=0.35,
            pos=(value_x + 0.15, 0, row_y),
            thumb_frameColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.BG_LIGHT,
            command=self._on_sensitivity_changed
        )

        self.sensitivity_value_label = DirectLabel(
            parent=frame,
            text=f"{initial_sensitivity:.2f}",
            scale=NineTheme.LABEL_SCALE,
            pos=(panel_width/2 - 0.15, 0, row_y),
            text_align=TextNode.ARight,
            text_fg=NineTheme.TEXT_PRIMARY,
            frameColor=(0, 0, 0, 0),
        )

        # Инверсия мыши X
        row_y -= row_height
        DirectLabel(
            parent=frame,
            text="Инверсия мыши X:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        self.invert_x_checkbox = DirectCheckButton(
            parent=frame,
            scale=NineTheme.ENTRY_SCALE,
            pos=(value_x, 0, row_y),
            text="",
            indicatorValue=config.get("invert_mouse_x", False),
            boxImage=None,
            boxImageColor=NineTheme.BTN_NORMAL,
            boxImageScale=1.0,
            boxRelief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),
            command=self._on_invert_x_changed
        )

        # Инверсия мыши Y
        row_y -= row_height
        DirectLabel(
            parent=frame,
            text="Инверсия мыши Y:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        self.invert_y_checkbox = DirectCheckButton(
            parent=frame,
            scale=NineTheme.ENTRY_SCALE,
            pos=(value_x, 0, row_y),
            text="",
            indicatorValue=config.get("invert_mouse_y", False),
            boxImage=None,
            boxImageColor=NineTheme.BTN_NORMAL,
            boxImageScale=1.0,
            boxRelief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),
            command=self._on_invert_y_changed
        )

        # Вид от третьего лица
        row_y -= row_height
        DirectLabel(
            parent=frame,
            text="Вид от третьего лица:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        self.third_person_checkbox = DirectCheckButton(
            parent=frame,
            scale=NineTheme.ENTRY_SCALE,
            pos=(value_x, 0, row_y),
            text="",
            indicatorValue=config.get("third_person_camera", True),
            boxImage=None,
            boxImageColor=NineTheme.BTN_NORMAL,
            boxImageScale=1.0,
            boxRelief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),
            command=self._on_camera_mode_changed
        )

    def _create_graphics_tab(self, panel_width, panel_height):
        """Создаёт содержимое вкладки 'Графика'."""
        frame = DirectFrame(
            parent=self.panel,
            frameSize=(-panel_width/2 + 0.05, panel_width/2 - 0.05, -0.45, 0.35),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.05),
        )
        self.tab_frames["graphics"] = frame

        label_x = -panel_width/2 + 0.15
        value_x = 0.05
        row_height = 0.15
        row_y = 0.25

        # FOV (поле зрения)
        DirectLabel(
            parent=frame,
            text="Поле зрения (FOV):",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        initial_fov = config.get("fov", 70)

        self.fov_slider = DirectSlider(
            parent=frame,
            range=(50, 120),
            value=initial_fov,
            scale=0.35,
            pos=(value_x + 0.15, 0, row_y),
            thumb_frameColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.BG_LIGHT,
            command=self._on_fov_changed
        )

        self.fov_value_label = DirectLabel(
            parent=frame,
            text=f"{int(initial_fov)}°",
            scale=NineTheme.LABEL_SCALE,
            pos=(panel_width/2 - 0.15, 0, row_y),
            text_align=TextNode.ARight,
            text_fg=NineTheme.TEXT_PRIMARY,
            frameColor=(0, 0, 0, 0),
        )

        # Подсказка
        row_y -= row_height * 2
        DirectLabel(
            parent=frame,
            text="Больше настроек графики\nбудет добавлено позже",
            scale=NineTheme.LABEL_SCALE * 0.8,
            pos=(0, 0, row_y),
            text_align=TextNode.ACenter,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

    def _create_audio_tab(self, panel_width, panel_height):
        """Создаёт содержимое вкладки 'Звук'."""
        frame = DirectFrame(
            parent=self.panel,
            frameSize=(-panel_width/2 + 0.05, panel_width/2 - 0.05, -0.45, 0.35),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.05),
        )
        self.tab_frames["audio"] = frame

        label_x = -panel_width/2 + 0.15
        value_x = 0.05
        row_height = 0.13
        row_y = 0.28

        # Общая громкость
        DirectLabel(
            parent=frame,
            text="Общая громкость:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        initial_master = config.get("audio_master_volume", 100)

        self.master_volume_slider = DirectSlider(
            parent=frame,
            range=(0, 100),
            value=initial_master,
            scale=0.35,
            pos=(value_x + 0.15, 0, row_y),
            thumb_frameColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.BG_LIGHT,
            command=self._on_master_volume_changed
        )

        self.master_volume_label = DirectLabel(
            parent=frame,
            text=f"{int(initial_master)}%",
            scale=NineTheme.LABEL_SCALE,
            pos=(panel_width/2 - 0.15, 0, row_y),
            text_align=TextNode.ARight,
            text_fg=NineTheme.TEXT_PRIMARY,
            frameColor=(0, 0, 0, 0),
        )

        # Громкость музыки
        row_y -= row_height
        DirectLabel(
            parent=frame,
            text="Музыка:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        initial_bgm = config.get("audio_bgm_volume", 70)

        self.bgm_volume_slider = DirectSlider(
            parent=frame,
            range=(0, 100),
            value=initial_bgm,
            scale=0.35,
            pos=(value_x + 0.15, 0, row_y),
            thumb_frameColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.BG_LIGHT,
            command=self._on_bgm_volume_changed
        )

        self.bgm_volume_label = DirectLabel(
            parent=frame,
            text=f"{int(initial_bgm)}%",
            scale=NineTheme.LABEL_SCALE,
            pos=(panel_width/2 - 0.15, 0, row_y),
            text_align=TextNode.ARight,
            text_fg=NineTheme.TEXT_PRIMARY,
            frameColor=(0, 0, 0, 0),
        )

        # Громкость звуковых эффектов
        row_y -= row_height
        DirectLabel(
            parent=frame,
            text="Звуки (SFX):",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        initial_sfx = config.get("audio_sfx_volume", 80)

        self.sfx_volume_slider = DirectSlider(
            parent=frame,
            range=(0, 100),
            value=initial_sfx,
            scale=0.35,
            pos=(value_x + 0.15, 0, row_y),
            thumb_frameColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.BG_LIGHT,
            command=self._on_sfx_volume_changed
        )

        self.sfx_volume_label = DirectLabel(
            parent=frame,
            text=f"{int(initial_sfx)}%",
            scale=NineTheme.LABEL_SCALE,
            pos=(panel_width/2 - 0.15, 0, row_y),
            text_align=TextNode.ARight,
            text_fg=NineTheme.TEXT_PRIMARY,
            frameColor=(0, 0, 0, 0),
        )

        # Громкость эмбиента
        row_y -= row_height
        DirectLabel(
            parent=frame,
            text="Окружение:",
            scale=NineTheme.LABEL_SCALE,
            pos=(label_x, 0, row_y),
            text_align=TextNode.ALeft,
            text_fg=NineTheme.TEXT_SECONDARY,
            frameColor=(0, 0, 0, 0),
        )

        initial_ambient = config.get("audio_ambient_volume", 60)

        self.ambient_volume_slider = DirectSlider(
            parent=frame,
            range=(0, 100),
            value=initial_ambient,
            scale=0.35,
            pos=(value_x + 0.15, 0, row_y),
            thumb_frameColor=NineTheme.BTN_HOVER,
            frameColor=NineTheme.BG_LIGHT,
            command=self._on_ambient_volume_changed
        )

        self.ambient_volume_label = DirectLabel(
            parent=frame,
            text=f"{int(initial_ambient)}%",
            scale=NineTheme.LABEL_SCALE,
            pos=(panel_width/2 - 0.15, 0, row_y),
            text_align=TextNode.ARight,
            text_fg=NineTheme.TEXT_PRIMARY,
            frameColor=(0, 0, 0, 0),
        )

    def _switch_tab(self, tab_id):
        """Переключает активную вкладку."""
        self.current_tab = tab_id

        # Скрываем все фреймы и обновляем стиль кнопок
        for tid, frame in self.tab_frames.items():
            if tid == tab_id:
                frame.show()
            else:
                frame.hide()

        # Обновляем стиль кнопок вкладок
        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                btn['frameColor'] = NineTheme.accent_button_colors()
            else:
                btn['frameColor'] = NineTheme.button_colors()

    # === Callbacks ===

    def _on_sensitivity_changed(self):
        """Callback при изменении чувствительности."""
        new_value = self.sensitivity_slider.getValue()
        self.sensitivity_value_label['text'] = f"{new_value:.2f}"
        # Применяем сразу
        if self.client and self.client.camera_controller:
            self.client.camera_controller.sensitivity = new_value * 30.0

    def _on_fov_changed(self):
        """Callback при изменении FOV."""
        new_value = int(self.fov_slider.getValue())
        self.fov_value_label['text'] = f"{new_value}°"
        # Применяем сразу
        if self.client and self.client.camera_controller:
            self.client.camera_controller.set_fov(new_value)

    def _on_invert_x_changed(self, status):
        """Callback при изменении инверсии X."""
        if self.client and self.client.camera_controller:
            self.client.camera_controller.invert_x = bool(status)

    def _on_invert_y_changed(self, status):
        """Callback при изменении инверсии Y."""
        if self.client and self.client.camera_controller:
            self.client.camera_controller.invert_y = bool(status)

    def _on_camera_mode_changed(self, status):
        """Callback при изменении режима камеры."""
        third_person = bool(status)
        if self.client and self.client.camera_controller:
            self.client.camera_controller.set_third_person(third_person)
            self.client.update_player_model_visibility()

    def _on_master_volume_changed(self):
        """Callback при изменении общей громкости."""
        new_value = int(self.master_volume_slider.getValue())
        self.master_volume_label['text'] = f"{new_value}%"
        # Применяем сразу
        if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            self.base.audio_manager.set_master_volume(new_value / 100.0)

    def _on_bgm_volume_changed(self):
        """Callback при изменении громкости музыки."""
        new_value = int(self.bgm_volume_slider.getValue())
        self.bgm_volume_label['text'] = f"{new_value}%"
        # Применяем сразу
        if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            self.base.audio_manager.set_channel_volume(AudioChannel.BGM, new_value / 100.0)

    def _on_sfx_volume_changed(self):
        """Callback при изменении громкости SFX."""
        new_value = int(self.sfx_volume_slider.getValue())
        self.sfx_volume_label['text'] = f"{new_value}%"
        # Применяем сразу
        if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            self.base.audio_manager.set_channel_volume(AudioChannel.SFX, new_value / 100.0)

    def _on_ambient_volume_changed(self):
        """Callback при изменении громкости эмбиента."""
        new_value = int(self.ambient_volume_slider.getValue())
        self.ambient_volume_label['text'] = f"{new_value}%"
        # Применяем сразу
        if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            self.base.audio_manager.set_channel_volume(AudioChannel.BGS, new_value / 100.0)

    def _on_save_click(self):
        """Сохраняет все настройки."""
        # Общие
        new_nickname = self.nickname_entry.get()
        selected_resolution = self.resolution_menu.get()

        # Управление
        new_sensitivity = self.sensitivity_slider.getValue()
        invert_x = bool(self.invert_x_checkbox['indicatorValue'])
        invert_y = bool(self.invert_y_checkbox['indicatorValue'])
        third_person = bool(self.third_person_checkbox['indicatorValue'])

        # Графика
        new_fov = int(self.fov_slider.getValue())

        # Звук
        master_volume = int(self.master_volume_slider.getValue())
        bgm_volume = int(self.bgm_volume_slider.getValue())
        sfx_volume = int(self.sfx_volume_slider.getValue())
        ambient_volume = int(self.ambient_volume_slider.getValue())

        # Сохраняем в конфиг
        config.set("nickname", new_nickname)
        config.set("resolution", selected_resolution)
        config.set("camera_sensitivity", new_sensitivity)
        config.set("invert_mouse_x", invert_x)
        config.set("invert_mouse_y", invert_y)
        config.set("third_person_camera", third_person)
        config.set("fov", new_fov)
        config.set("audio_master_volume", master_volume)
        config.set("audio_bgm_volume", bgm_volume)
        config.set("audio_sfx_volume", sfx_volume)
        config.set("audio_ambient_volume", ambient_volume)

        # Применяем настройки
        if self.client:
            self.client.character_name = new_nickname
            self.client.third_person_camera = third_person
            self.client.invert_mouse_x = invert_x
            self.client.invert_mouse_y = invert_y
            self.client.fov = new_fov

            if self.client.camera_controller:
                self.client.camera_controller.set_third_person(third_person)
                self.client.camera_controller.invert_x = invert_x
                self.client.camera_controller.invert_y = invert_y
                self.client.camera_controller.set_fov(new_fov)
                self.client.update_player_model_visibility()

            # Применяем разрешение
            width, height = map(int, selected_resolution.split('x'))
            props = WindowProperties()
            props.setSize(width, height)
            self.client.win.requestProperties(props)

        self._go_back()

    def _on_back_click(self):
        """Возврат без сохранения."""
        # Восстанавливаем все настройки к сохранённым значениям
        if self.client and self.client.camera_controller:
            saved_third_person = config.get("third_person_camera", True)
            saved_invert_x = config.get("invert_mouse_x", False)
            saved_invert_y = config.get("invert_mouse_y", False)
            saved_fov = config.get("fov", 70)
            saved_sensitivity = config.get("camera_sensitivity", 1.0)

            self.client.camera_controller.set_third_person(saved_third_person)
            self.client.camera_controller.invert_x = saved_invert_x
            self.client.camera_controller.invert_y = saved_invert_y
            self.client.camera_controller.set_fov(saved_fov)
            self.client.camera_controller.sensitivity = saved_sensitivity * 30.0
            self.client.update_player_model_visibility()

        # Восстанавливаем аудио настройки
        if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            saved_master = config.get("audio_master_volume", 100)
            saved_bgm = config.get("audio_bgm_volume", 70)
            saved_sfx = config.get("audio_sfx_volume", 80)
            saved_ambient = config.get("audio_ambient_volume", 60)

            self.base.audio_manager.set_master_volume(saved_master / 100.0)
            self.base.audio_manager.set_channel_volume(AudioChannel.BGM, saved_bgm / 100.0)
            self.base.audio_manager.set_channel_volume(AudioChannel.SFX, saved_sfx / 100.0)
            self.base.audio_manager.set_channel_volume(AudioChannel.BGS, saved_ambient / 100.0)

        self._go_back()

    def _go_back(self):
        """Возврат в предыдущее меню."""
        self.ui_manager.hide_settings_menu()
        if self.from_in_game:
            self.ui_manager.show_in_game_menu(self.client)
        else:
            self.ui_manager.show_main_menu()
