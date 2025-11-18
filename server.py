import asyncio
import time

from nine.core.app import Application
from nine.core.network import NetworkManager
from nine.core.plugins import PluginManager
from nine.core.world import World

# Конфигурация
HOST = "localhost"
PORT = 9009
TICK_RATE = 60  # Тактов в секунду

class ServerApp(Application):
    def __init__(self):
        super().__init__(is_server=True)
        self.network = NetworkManager(self.event_manager)
        self.world = World(self.event_manager)
        self.plugin_manager = PluginManager(self.event_manager)

        # Сервер подписывается на события для отправки сообщений через NetworkManager
        self.event_manager.subscribe("server_send_message", self.network.send_message)
        self.event_manager.subscribe("server_broadcast", self.network.broadcast)

    async def main_loop(self):
        """Основной цикл обработки для серверного приложения."""
        self.running = True
        self.event_manager.post("app_start")
        
        self.plugin_manager.load_plugins()

        last_tick_time = time.monotonic()
        tick_interval = 1.0 / TICK_RATE

        try:
            while self.running:
                now = time.monotonic()
                delta_time = now - last_tick_time

                if delta_time >= tick_interval:
                    last_tick_time = now
                    self.tick(delta_time)
                
                # Уступаем управление циклу событий asyncio
                await asyncio.sleep(tick_interval / 2)

        except KeyboardInterrupt:
            print("Сервер завершает работу...")
        finally:
            self.stop()
    
    def tick(self, dt: float):
        """Переопределяет базовый такт для передачи delta_time."""
        self.event_manager.post("app_tick", dt)

    def stop(self):
        if self.running:
            self.plugin_manager.unload_plugins()
            super().stop()


async def main():
    server_app = ServerApp()
    
    server_task = asyncio.create_task(
        server_app.network.start_server(HOST, PORT)
    )
    
    main_loop_task = asyncio.create_task(server_app.main_loop())

    await asyncio.gather(server_task, main_loop_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Завершение работы.")

