# nine/ui/main_menu.py
from .base_component import BaseUIComponent
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG, OnscreenImage
from panda3d.core import LColor

class MainMenu(BaseUIComponent):
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        
        # Стили, специфичные для главного меню
        self.button_color = (LColor(0.1, 0.1, 0.1, 0.8), LColor(0.2, 0.2, 0.2, 0.8), LColor(0.3, 0.3, 0.3, 0.8), LColor(0.1, 0.1, 0.1, 0.5))

        self._create_window()

    def _create_window(self):
        """Создает элементы главного меню."""
        # Фон
        bg = self._add_element('background', OnscreenImage(
            parent=self.base.render2d, 
            image="nine/assets/materials/main_menu.png"
        ))
        self._update_bg_scale(bg)
        self.base.accept('window-event', self._on_window_event)

        # Якорь для кнопок, чтобы они были по центру
        menu_center = self._add_element('buttons_anchor', self.base.aspect2d.attach_new_node("menu-center"))
        # The anchor is now at the center of the screen by default.

        buttons = [
            ("Подключиться", self.ui_manager.callbacks.get("connect"), 0.15),
            ("Настройки", self.ui_manager.callbacks.get("settings"), 0),
            ("Выход", self.ui_manager.callbacks.get("exit"), -0.15)
        ]

        for i, (text, command, z_pos) in enumerate(buttons):
            btn = self._add_element(f'button_{i}', DirectButton(
                parent=menu_center, 
                text=text, 
                scale=0.07, 
                pos=(0, 0, z_pos),
                command=command, 
                frameColor=self.button_color, 
                text_fg=(1,1,1,1),
                pressEffect=True, 
                relief=DGG.FLAT
            ))

    def _on_window_event(self, window):
        """Пересчитывает фон при изменении размера окна."""
        if 'background' in self._elements:
            self._update_bg_scale(self._elements['background'])

    def _update_bg_scale(self, bg_image):
        """Масштабирует фоновое изображение для заполнения окна."""
        if not bg_image or not self.base.win: return
        win_props = self.base.win.getProperties()
        if not win_props.hasSize(): return

        win_w, win_h = win_props.getXSize(), win_props.getYSize()
        if win_w == 0 or win_h == 0: return

        img_aspect = bg_image.get_texture().get_x_size() / bg_image.get_texture().get_y_size()
        win_aspect = win_w / win_h

        if win_aspect > img_aspect:
            bg_image.set_scale(win_aspect / img_aspect, 1, 1)
        else:
            bg_image.set_scale(1, 1, img_aspect / win_aspect)
    
    def destroy(self):
        self.base.ignore('window-event')
        super().destroy()

