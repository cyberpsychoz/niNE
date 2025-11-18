from .events import EventManager

class Application:
    """
    Центральный класс приложения.
    Управляет основным циклом и компонентами ядра.
    """

    def __init__(self, is_server: bool = False):
        self.is_server = is_server
        self.running = False
        self.event_manager = EventManager()

    def run(self):
        """Запускает основной цикл приложения."""
        self.running = True
        self.event_manager.post("app_start")

        try:
            while self.running:
                self.tick()
        except KeyboardInterrupt:
            print("Приложение завершает работу...")
        finally:
            self.stop()

    def tick(self):
        """Выполняет один такт игрового цикла."""
        self.event_manager.post("app_tick")

    def stop(self):
        """Останавливает приложение."""
        if self.running:
            self.running = False
            self.event_manager.post("app_stop")

