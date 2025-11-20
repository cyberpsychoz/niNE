# nine/ui/base_component.py
from panda3d.core import NodePath

class BaseUIComponent:
    """
    Базовый класс для всех компонентов пользовательского интерфейса.
    Предоставляет общие методы для управления элементами DirectGUI.
    """
    def __init__(self, ui_manager):
        self.ui_manager = ui_manager
        self.base = ui_manager.base
        self._elements = {}

    def show(self):
        """Показывает корневой элемент компонента."""
        if 'root' in self._elements:
            self._elements['root'].show()

    def hide(self):
        """Скрывает корневой элемент компонента."""
        if 'root' in self._elements:
            self._elements['root'].hide()

    def destroy(self):
        """Уничтожает все элементы DirectGUI, управляемые этим компонентом."""
        for name, element in list(self._elements.items()):
            if hasattr(element, 'destroy') and callable(element.destroy):
                element.destroy()
            elif isinstance(element, NodePath):
                element.removeNode()
        self._elements.clear()

    def _add_element(self, name, element):
        """Отслеживает элемент для автоматического уничтожения."""
        self._elements[name] = element
        return element
