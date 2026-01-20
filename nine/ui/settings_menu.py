# nine/ui/settings_menu.py
"""
Меню настроек с вкладками.
Простая блочная структура.
"""

from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DGG
from panda3d.core import TextNode, TransparencyAttrib

from .base_component import BaseUIComponent
from .blocks import Block
from .ui_config import ui
from nine.core.config import config


class SettingsMenu(BaseUIComponent):
    """Меню настроек."""

    # Размеры панели
    PANEL_WIDTH = 1.6
    PANEL_HEIGHT = 1.4  # Увеличена высота для лучшего размещения
    TAB_CONTENT_HEIGHT = 0.6  # Высота области контента вкладки

    def __init__(self, ui_manager, client):
        super().__init__(ui_manager)
        self.client = client
        self.from_in_game = False
        self.current_tab = "general"

        self._tab_blocks = {}
        self._tab_buttons = {}

        self._setup()

    def _setup(self):
        """Создает меню."""
        # Затемнение фона
        bg = DirectFrame(
            parent=self.base.render2d,
            frameSize=(-2, 2, -2, 2),
            frameColor=ui.colors.bg_overlay,
        )
        bg.setTransparency(TransparencyAttrib.M_alpha)
        self._add_element('bg', bg)

        # Главная панель
        hw = self.PANEL_WIDTH / 2
        hh = self.PANEL_HEIGHT / 2

        panel = DirectFrame(
            parent=self.base.aspect2d,
            frameSize=(-hw, hw, -hh, hh),
            frameColor=ui.colors.bg_medium,
            pos=(0, 0, 0)
        )
        panel.setTransparency(TransparencyAttrib.M_alpha)
        self._add_element('panel', panel)
        self._panel = panel

        # Расчёт позиций
        title_y = hh - 0.1
        tab_btn_y = title_y - 0.14
        content_top_y = tab_btn_y - 0.1
        btn_row_y = -hh + 0.12

        # === ЗАГОЛОВОК ===
        DirectLabel(
            parent=panel,
            text="НАСТРОЙКИ",
            text_scale=ui.font.title,
            text_fg=ui.colors.gold,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, title_y)
        )

        # === КНОПКИ ВКЛАДОК ===
        tabs = [("general", "Общие"), ("controls", "Управление"),
                ("graphics", "Графика"), ("audio", "Звук")]

        tab_w = 0.30
        tab_gap = 0.03
        total_tabs_w = len(tabs) * tab_w + (len(tabs) - 1) * tab_gap
        start_x = -total_tabs_w / 2 + tab_w / 2

        for i, (tid, tname) in enumerate(tabs):
            x = start_x + i * (tab_w + tab_gap)
            btn = DirectButton(
                parent=panel,
                text=tname,
                text_scale=ui.font.small,
                text_fg=ui.colors.text_primary,
                text_align=TextNode.ACenter,
                frameColor=ui.colors.btn_normal,
                frameSize=(-tab_w/2, tab_w/2, -0.04, 0.05),
                relief=DGG.FLAT,
                pos=(x, 0, tab_btn_y),
                command=lambda t=tid: self._switch_tab(t)
            )
            self._tab_buttons[tid] = btn

        # === ОБЛАСТЬ КОНТЕНТА ВКЛАДОК ===
        content_center_y = content_top_y - self.TAB_CONTENT_HEIGHT / 2

        self._create_general_tab(content_center_y)
        self._create_controls_tab(content_center_y)
        self._create_graphics_tab(content_center_y)
        self._create_audio_tab(content_center_y)

        # === КНОПКИ ВНИЗУ ===
        self._create_bg1_button(
            name='save_btn',
            text="Сохранить",
            command=self._on_save,
            parent=panel,
            pos=(-0.22, 0, btn_row_y),
            small=True
        )

        self._create_bg1_button(
            name='back_btn',
            text="Назад",
            command=self._on_back,
            parent=panel,
            pos=(0.22, 0, btn_row_y),
            small=True
        )

        # Показать первую вкладку
        self._switch_tab("general")
        self.hide()

    def _create_general_tab(self, center_y: float):
        """Вкладка Общие."""
        block = Block(
            parent=self._panel,
            width=1.4,
            padding=0.04,
            bg_color=(0, 0, 0, 0),
            pos=(0, 0, center_y)
        )

        # Никнейм
        r1 = block.row(justify="space-between")
        r1.label("Никнейм:")
        r1.entry(name="nickname", initial=config.get("nickname", "Player"), width=14)

        block.spacer(0.06)

        # Разрешение
        resolutions = config.get("available_resolutions", ["1280x720", "1920x1080"])
        current_res = config.get("resolution", "1280x720")

        r2 = block.row(justify="space-between")
        r2.label("Разрешение:")
        r2.dropdown(name="resolution", items=resolutions, initial=current_res)

        block.build(height=self.TAB_CONTENT_HEIGHT)
        self._tab_blocks["general"] = block

    def _create_controls_tab(self, center_y: float):
        """Вкладка Управление."""
        block = Block(
            parent=self._panel,
            width=1.4,
            padding=0.04,
            bg_color=(0, 0, 0, 0),
            pos=(0, 0, center_y)
        )

        # Чувствительность
        r1 = block.row(justify="space-between")
        r1.label("Чувствительность:")
        r1.slider(name="sensitivity", min_val=0.1, max_val=3.0,
                  initial=config.get("camera_sensitivity", 1.0),
                  value_format="{:.2f}", command=self._on_sensitivity_change)

        block.spacer(0.04)

        # Инверсия X
        r2 = block.row(justify="space-between")
        r2.label("Инверсия мыши X:")
        r2.checkbox(name="invert_x", initial=config.get("invert_mouse_x", False),
                    command=self._on_invert_x_change)

        block.spacer(0.04)

        # Инверсия Y
        r3 = block.row(justify="space-between")
        r3.label("Инверсия мыши Y:")
        r3.checkbox(name="invert_y", initial=config.get("invert_mouse_y", False),
                    command=self._on_invert_y_change)

        block.spacer(0.04)

        # Камера
        r4 = block.row(justify="space-between")
        r4.label("От 3-го лица:")
        r4.checkbox(name="third_person", initial=config.get("third_person_camera", True),
                    command=self._on_camera_change)

        block.build(height=self.TAB_CONTENT_HEIGHT)
        self._tab_blocks["controls"] = block

    def _create_graphics_tab(self, center_y: float):
        """Вкладка Графика."""
        block = Block(
            parent=self._panel,
            width=1.4,
            padding=0.04,
            bg_color=(0, 0, 0, 0),
            pos=(0, 0, center_y)
        )

        # FOV
        r1 = block.row(justify="space-between")
        r1.label("Поле зрения (FOV):")
        r1.slider(name="fov", min_val=50, max_val=120,
                  initial=config.get("fov", 70),
                  value_format="{:.0f}", command=self._on_fov_change)

        block.spacer(0.08)

        block.label("Больше настроек будет добавлено", style="small", align="center")

        block.build(height=self.TAB_CONTENT_HEIGHT)
        self._tab_blocks["graphics"] = block

    def _create_audio_tab(self, center_y: float):
        """Вкладка Звук."""
        block = Block(
            parent=self._panel,
            width=1.4,
            padding=0.04,
            bg_color=(0, 0, 0, 0),
            pos=(0, 0, center_y)
        )

        # Общая громкость
        r1 = block.row(justify="space-between")
        r1.label("Общая громкость:")
        r1.slider(name="master", min_val=0, max_val=100,
                  initial=config.get("audio_master_volume", 100),
                  value_format="{:.0f}%", command=self._on_master_change)

        block.spacer(0.035)

        # Музыка
        r2 = block.row(justify="space-between")
        r2.label("Музыка:")
        r2.slider(name="bgm", min_val=0, max_val=100,
                  initial=config.get("audio_bgm_volume", 70),
                  value_format="{:.0f}%", command=self._on_bgm_change)

        block.spacer(0.035)

        # SFX
        r3 = block.row(justify="space-between")
        r3.label("Звуки (SFX):")
        r3.slider(name="sfx", min_val=0, max_val=100,
                  initial=config.get("audio_sfx_volume", 80),
                  value_format="{:.0f}%", command=self._on_sfx_change)

        block.spacer(0.035)

        # Ambient
        r4 = block.row(justify="space-between")
        r4.label("Окружение:")
        r4.slider(name="ambient", min_val=0, max_val=100,
                  initial=config.get("audio_ambient_volume", 60),
                  value_format="{:.0f}%", command=self._on_ambient_change)

        block.build(height=self.TAB_CONTENT_HEIGHT)
        self._tab_blocks["audio"] = block

    def _switch_tab(self, tab_id: str):
        """Переключает вкладку."""
        self.current_tab = tab_id

        for tid, block in self._tab_blocks.items():
            if tid == tab_id:
                block.show()
            else:
                block.hide()

        for tid, btn in self._tab_buttons.items():
            if tid == tab_id:
                btn['frameColor'] = ui.colors.btn_accent_normal
            else:
                btn['frameColor'] = ui.colors.btn_normal

    # === CALLBACKS ===

    def _on_sensitivity_change(self):
        val = self._tab_blocks["controls"].get("sensitivity")
        if val and self.client and self.client.camera_controller:
            self.client.camera_controller.sensitivity = val * 30.0

    def _on_invert_x_change(self, status):
        if self.client and self.client.camera_controller:
            self.client.camera_controller.invert_x = bool(status)

    def _on_invert_y_change(self, status):
        if self.client and self.client.camera_controller:
            self.client.camera_controller.invert_y = bool(status)

    def _on_camera_change(self, status):
        if self.client and self.client.camera_controller:
            self.client.camera_controller.set_third_person(bool(status))
            self.client.update_player_model_visibility()

    def _on_fov_change(self):
        val = self._tab_blocks["graphics"].get("fov")
        if val and self.client and self.client.camera_controller:
            self.client.camera_controller.set_fov(int(val))

    def _on_master_change(self):
        val = self._tab_blocks["audio"].get("master")
        if val is not None and hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            self.base.audio_manager.set_master_volume(val / 100.0)

    def _on_bgm_change(self):
        val = self._tab_blocks["audio"].get("bgm")
        if val is not None and hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            self.base.audio_manager.set_channel_volume(AudioChannel.BGM, val / 100.0)

    def _on_sfx_change(self):
        val = self._tab_blocks["audio"].get("sfx")
        if val is not None and hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            self.base.audio_manager.set_channel_volume(AudioChannel.SFX, val / 100.0)

    def _on_ambient_change(self):
        val = self._tab_blocks["audio"].get("ambient")
        if val is not None and hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            self.base.audio_manager.set_channel_volume(AudioChannel.BGS, val / 100.0)

    def _on_save(self):
        """Сохранить настройки."""
        from panda3d.core import WindowProperties

        # General
        gen = self._tab_blocks.get("general")
        if gen:
            nick = gen.get("nickname")
            res = gen.get("resolution")
            if nick:
                config.set("nickname", nick)
            if res:
                config.set("resolution", res)
                try:
                    w, h = map(int, res.split('x'))
                    props = WindowProperties()
                    props.setSize(w, h)
                    self.client.win.requestProperties(props)
                except:
                    pass

        # Controls
        ctrl = self._tab_blocks.get("controls")
        if ctrl:
            sens = ctrl.get("sensitivity")
            inv_x = ctrl.get("invert_x")
            inv_y = ctrl.get("invert_y")
            tp = ctrl.get("third_person")
            if sens is not None:
                config.set("camera_sensitivity", sens)
            if inv_x is not None:
                config.set("invert_mouse_x", inv_x)
            if inv_y is not None:
                config.set("invert_mouse_y", inv_y)
            if tp is not None:
                config.set("third_person_camera", tp)

        # Graphics
        gfx = self._tab_blocks.get("graphics")
        if gfx:
            fov = gfx.get("fov")
            if fov is not None:
                config.set("fov", int(fov))

        # Audio
        aud = self._tab_blocks.get("audio")
        if aud:
            for key in ["master", "bgm", "sfx", "ambient"]:
                val = aud.get(key)
                if val is not None:
                    cfg_key = f"audio_{key}_volume" if key != "master" else "audio_master_volume"
                    config.set(cfg_key, int(val))

        self._go_back()

    def _on_back(self):
        """Назад без сохранения."""
        # Восстановить настройки камеры
        if self.client and self.client.camera_controller:
            self.client.camera_controller.set_third_person(config.get("third_person_camera", True))
            self.client.camera_controller.invert_x = config.get("invert_mouse_x", False)
            self.client.camera_controller.invert_y = config.get("invert_mouse_y", False)
            self.client.camera_controller.set_fov(config.get("fov", 70))
            self.client.camera_controller.sensitivity = config.get("camera_sensitivity", 1.0) * 30.0
            self.client.update_player_model_visibility()

        # Восстановить аудио
        if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
            from nine.core.audio_manager import AudioChannel
            am = self.base.audio_manager
            am.set_master_volume(config.get("audio_master_volume", 100) / 100.0)
            am.set_channel_volume(AudioChannel.BGM, config.get("audio_bgm_volume", 70) / 100.0)
            am.set_channel_volume(AudioChannel.SFX, config.get("audio_sfx_volume", 80) / 100.0)
            am.set_channel_volume(AudioChannel.BGS, config.get("audio_ambient_volume", 60) / 100.0)

        self._go_back()

    def _go_back(self):
        """Вернуться."""
        self.ui_manager.hide_settings_menu()
        if self.from_in_game:
            self.ui_manager.show_in_game_menu(self.client)
        else:
            self.ui_manager.show_main_menu()

    def show(self):
        for el in self._elements.values():
            if hasattr(el, 'show'):
                el.show()
        self._switch_tab(self.current_tab)

    def hide(self):
        for el in self._elements.values():
            if hasattr(el, 'hide'):
                el.hide()

    def destroy(self):
        for block in self._tab_blocks.values():
            block.destroy()
        self._tab_blocks.clear()
        self._tab_buttons.clear()
        super().destroy()
