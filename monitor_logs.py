"""
Монитор логов для отладки.
Показывает последние N строк из client.log и server.log в реальном времени.

Запуск:
    python monitor_logs.py
"""

import time
import os
from pathlib import Path

CLIENT_LOG = Path("client.log")
SERVER_LOG = Path("server.log")
LINES_TO_SHOW = 50


def tail_file(filepath: Path, num_lines: int = 50):
    """Возвращает последние N строк файла."""
    if not filepath.exists():
        return []

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        return lines[-num_lines:]


def monitor_logs(interval: float = 2.0):
    """Мониторит логи каждые N секунд."""
    client_last_size = 0
    server_last_size = 0

    print("=== LOG MONITOR STARTED ===")
    print(f"Monitoring: {CLIENT_LOG}, {SERVER_LOG}")
    print(f"Refresh interval: {interval}s")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')

            print("=" * 80)
            print("CLIENT LOG (last 30 lines)".center(80))
            print("=" * 80)

            client_lines = tail_file(CLIENT_LOG, 30)
            for line in client_lines:
                print(line.rstrip())

            print("\n")
            print("=" * 80)
            print("SERVER LOG (last 30 lines)".center(80))
            print("=" * 80)

            server_lines = tail_file(SERVER_LOG, 30)
            for line in server_lines:
                print(line.rstrip())

            print("\n")
            print(f"[{time.strftime('%H:%M:%S')}] Refreshing in {interval}s... (Ctrl+C to stop)")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n=== LOG MONITOR STOPPED ===")


if __name__ == "__main__":
    monitor_logs(interval=2.0)
