# nine/core/ui.py
from direct.gui.DirectGui import (
    DirectFrame,
    DirectButton,
    DirectEntry,
    DGG,
    OnscreenImage,
)
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    LColor, TextNode, Loader, WindowProperties,
    NodePath, PGTop
)

class UIManager:
    """
    Управляет всеми элементами пользовательского интерфейса (DirectGUI),
    используя относительное позиционирование и якоря для адаптивности.
    """
    def __init__(self, base, callbacks: dict):
        self.base = base
        self.loader = base.loader
        self.callbacks = callbacks
        
        # Контейнеры для элементов UI
        self.elements = {}
        self.chat_lines = []

        # Стили
        self.font = self._load_font(self.loader)
        DGG.setDefaultFont(self.font)
        self.button_color = (LColor(0.1, 0.1, 0.1, 0.8), LColor(0.2, 0.2, 0.2, 0.8), LColor(0.3, 0.3, 0.3, 0.8), LColor(0.1, 0.1, 0.1, 0.5))

        # Привязываемся к событию изменения размера окна
        self.base.accept('window-event', self._on_window_event)
        # Первоначальное позиционирование
        self._on_window_event(self.base.win)
        
    def _load_font(self, loader: Loader):
        """Загружает кастомный шрифт, поддерживающий кириллицу."""
        font_path = "nine/assets/fonts/DejaVuSans.ttf"
        try:
            font = loader.loadFont(font_path)
            font.setPixelsPerUnit(100) # Улучшает четкость
            print(f"Шрифт '{font_path}' успешно загружен.")
            return font
        except Exception:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Не удалось загрузить шрифт '{font_path}'.")
            return DGG.getDefaultFont()

    def _on_window_event(self, window):
        """Вызывается при изменении окна, пересчитывает позиции UI."""
        if not window or not self.base.win.has_size():
            return
        
        # Обновляем фоновое изображение
        if 'background_image' in self.elements:
            self._update_bg_scale(self.elements['background_image'])
        
        # Обновляем другие элементы, если нужно
        # В этой реализации DirectGUI многое делает сам, если использовать якоря.
        # Этот обработчик остается для более сложных случаев.

    def _update_bg_scale(self, bg_image: OnscreenImage):
        """Масштабирует фоновое изображение, чтобы оно заполняло окно, сохраняя пропорции."""
        if not bg_image or not self.base.win:
            return
        
        win_props = self.base.win.getProperties()
        if not win_props.hasSize():
            return

        win_w, win_h = win_props.getXSize(), win_props.getYSize()
        if win_w == 0 or win_h == 0: return

        # Сбрасываем старые трансформации
        bg_image.set_scale(1)
        bg_image.set_pos(0)
        
        # Panda3D рендерит 2D-UI в квадрат с координатами от -1 до 1.
        # a2d* ноды помогают с позиционированием, но для фона на render2d нужен пересчет.
        win_aspect = win_w / win_h

        tex = bg_image.get_texture()
        img_w, img_h = tex.get_orig_file_x_size(), tex.get_orig_file_y_size()
        if img_w == 0 or img_h == 0: return
        img_aspect = img_w / img_h
        
        # Parent to render2d, which spans -1 to 1 in both axes based on the shorter window dimension
        parent = self.base.render2d
        
        if win_aspect > img_aspect:
            # Window is wider than image, scale image height to match window height
            bg_image.set_scale(img_aspect, 1, 1) # Scale X to match image aspect ratio
            bg_image.set_pos(0, 0, 0)
        else:
            # Window is taller than image, scale image width to match window width
            bg_image.set_scale(1, 1, 1/img_aspect * 1/win_aspect)
            bg_image.set_pos(0,0,0)


    def _destroy_element(self, name: str):
        """Уничтожает элемент UI и удаляет его из менеджера."""
        if name in self.elements:
            self.elements[name].destroy()
            del self.elements[name]
            
    # --- Методы создания/уничтожения меню ---

    def create_main_menu(self):
        """Создает главное меню с использованием якорей."""
        if 'main_menu_frame' in self.elements: return

        # Фон
        bg = OnscreenImage(parent=self.base.render2d, image="nine/assets/materials/main_menu.jpg")
        self.elements['background_image'] = bg
        self._on_window_event(self.base.win) # Первичная настройка
        
        # Фрейм для кнопок, привязан к центру экрана
        frame = DirectFrame(parent=self.base.a2dTopLeft, frameColor=(0,0,0,0), pos=(0.5, 0, -0.5))
        self.elements['main_menu_frame'] = frame

        buttons = [
            ("Подключиться", self.callbacks.get("connect"), -0.1),
            ("Настройки", self.callbacks.get("settings"), -0.2),
            ("Выход", self.callbacks.get("exit"), -0.3)
        ]

        # Используем a2dTopLeft для позиционирования относительно левого верхнего угла.
        # Координаты (0, 0, 0) будут в углу. 
        # (1, 0, -1) будет в центре экрана. (aspect2d)
        
        # Правильный подход - использовать a2dTopLeft, a2dBottomRight и тд
        # для размещения виджетов в нужных частях экрана
        menu_center = self.base.a2dTopLeft.attach_new_node("menu-center")
        menu_center.set_pos(self.base.get_aspect_ratio(), 0, -1) # Позиционируем в центр

        y_offset = -0.5
        for text, command, z_offset in buttons:
            DirectButton(
                parent=menu_center,
                text=text,
                scale=0.07,
                pos=(0, 0, y_offset),
                command=command,
                frameColor=self.button_color, text_fg=(1,1,1,1),
                pressEffect=True, relief=DGG.FLAT
            )
            y_offset -= 0.15

        self.elements['main_menu_buttons_anchor'] = menu_center

    def destroy_main_menu(self):
        self._destroy_element('background_image')
        self._destroy_element('main_menu_frame')
        self._destroy_element('main_menu_buttons_anchor')

    def create_login_menu(self, default_ip: str, default_name: str):
        if 'login_menu_frame' in self.elements: return
        
        frame = DirectFrame(parent=self.base.aspect2d, frameColor=(0, 0, 0, 0.7), frameSize=(-0.7, 0.7, -0.5, 0.5))
        self.elements['login_menu_frame'] = frame
        
        # IP Сервера
        self.elements['ip_entry'] = DirectEntry(
            parent=frame, scale=0.06, pos=(-0.6, 0, 0.35), initialText=default_ip,
            numLines=1, focus=1, text_align=TextNode.ALeft, width=20
        )
        DirectLabel(parent=frame, text="IP Сервера:", pos=(-0.6, 0, 0.42), scale=0.05, text_align=TextNode.ALeft)
        
        # Имя персонажа (логин)
        self.elements['character_name_entry'] = DirectEntry(
            parent=frame, scale=0.06, pos=(-0.6, 0, 0.15), initialText=default_name,
            numLines=1, text_align=TextNode.ALeft, width=20
        )
        DirectLabel(parent=frame, text="Имя персонажа:", pos=(-0.6, 0, 0.22), scale=0.05, text_align=TextNode.ALeft)

        # Пароль
        self.elements['password_entry'] = DirectEntry(
            parent=frame, scale=0.06, pos=(-0.6, 0, -0.05), initialText="",
            numLines=1, text_align=TextNode.ALeft, width=20, obscured=True
        )
        DirectLabel(parent=frame, text="Пароль:", pos=(-0.6, 0, 0.02), scale=0.05, text_align=TextNode.ALeft)

        # Кнопки
        DirectButton(parent=frame, text="Войти / Регистрация", scale=0.07, pos=(0, 0, -0.3), command=self.callbacks.get("attempt_login"), frameColor=self.button_color)
        DirectButton(parent=frame, text="Назад", scale=0.07, pos=(0, 0, -0.4), command=self.callbacks.get("close_login_menu"), frameColor=self.button_color)

    def destroy_login_menu(self):
        self._destroy_element('login_menu_frame')
        self.elements.pop('ip_entry', None)
        self.elements.pop('character_name_entry', None)
        self.elements.pop('password_entry', None)

    def get_login_credentials(self) -> dict:
        """Возвращает словарь с данными для входа."""
        return {
            "ip": self.elements['ip_entry'].get() if 'ip_entry' in self.elements else "",
            "name": self.elements['character_name_entry'].get() if 'character_name_entry' in self.elements else "",
            "password": self.elements['password_entry'].get() if 'password_entry' in self.elements else ""
        }
        
    def open_chat_input(self):
        if 'chat_input' in self.elements: return
        
        chat_anchor = self.base.a2dBottomLeft.attach_new_node("chat_anchor")
        chat_anchor.set_pos(0.05, 0, 0.1)
        self.elements['chat_anchor'] = chat_anchor

        self.elements['chat_input'] = DirectEntry(
            parent=chat_anchor,
            scale=0.05,
            width=self.base.win.get_x_size() / 25, # Динамическая ширина
            numLines=1,
            focus=1,
            command=self.callbacks.get("send_chat_message"),
        )
        self.base.accept('window-event', self._update_chat_width)


    def _update_chat_width(self, window=None):
        if 'chat_input' in self.elements:
            # Простое обновление ширины. 
            # 25 - магическое число, подобрано экспериментально
            new_width = self.base.win.get_x_size() / 25 
            self.elements['chat_input']['width'] = new_width


    def close_chat_input(self):
        self._destroy_element('chat_anchor')
        self._destroy_element('chat_input')
        self.base.ignore('window-event')

    def add_chat_message(self, sender_name: str, message: str):
        if len(self.chat_lines) >= 10:
            oldest_line = self.chat_lines.pop(0)
            oldest_line.destroy()

        for line in self.chat_lines:
            line.setZ(line.getZ() + 0.05)

        item = OnscreenText(
            text=f"{sender_name}: {message}",
            parent=self.base.a2dBottomLeft,
            scale=0.04,
            pos=(0.05, 0.15 + len(self.chat_lines) * 0.05),
            align=TextNode.ALeft,
            fg=(1, 1, 1, 1),
            mayChange=False
        )
        self.chat_lines.append(item)

    def clear_chat_lines(self):
        for line in self.chat_lines: line.destroy()
        self.chat_lines.clear()

    def get_chat_input(self) -> str:
        return self.elements['chat_input'].get() if 'chat_input' in self.elements else ""

    def clear_chat_input(self):
        if 'chat_input' in self.elements: self.elements['chat_input'].enterText("")

    def create_ingame_menu(self):
        if 'ingame_menu_frame' in self.elements: return
        
        frame = DirectFrame(parent=self.base.aspect2d, frameColor=(0, 0, 0, 0.5), frameSize=(-0.5, 0.5, -0.3, 0.3))
        self.elements['ingame_menu_frame'] = frame
        
        DirectButton(parent=frame, text="Продолжить", scale=0.07, pos=(0, 0, 0.1), command=self.callbacks.get("resume"), frameColor=self.button_color)
        DirectButton(parent=frame, text="Отключиться", scale=0.07, pos=(0, 0, -0.1), command=self.callbacks.get("disconnect"), frameColor=self.button_color)

    def destroy_ingame_menu(self):
        self._destroy_element('ingame_menu_frame')

    def create_settings_menu(self, current_name: str):
        if 'settings_frame' in self.elements: return
        
        frame = DirectFrame(parent=self.base.aspect2d, frameColor=(0, 0, 0, 0.7), frameSize=(-0.6, 0.6, -0.4, 0.4))
        self.elements['settings_frame'] = frame
        
        self.elements['character_name_entry'] = DirectEntry(
            parent=frame,
            scale=0.06,
            pos=(-0.5, 0, 0.2),
            initialText=current_name,
            numLines=1,
            focus=1,
            text_align=TextNode.ALeft,
            width=18
        )
        DirectLabel(parent=frame, text="Имя персонажа:", pos=(-0.5, 0, 0.3), scale=0.06, text_align=TextNode.ALeft)
        
        DirectButton(parent=frame, text="Сохранить", scale=0.07, pos=(-0.2, 0, -0.2), command=self.callbacks.get("save_settings"), frameColor=self.button_color)
        DirectButton(parent=frame, text="Назад", scale=0.07, pos=(0.2, 0, -0.2), command=self.callbacks.get("close_settings"), frameColor=self.button_color)

    def get_character_name(self) -> str:
        return self.elements['character_name_entry'].get() if 'character_name_entry' in self.elements else ""

    def destroy_settings_menu(self):
        self._destroy_element('settings_frame')
        self.elements.pop('character_name_entry', None)