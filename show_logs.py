"""
Быстрый просмотр последних логов клиента и сервера.

Использование:
    python show_logs.py           # Последние 50 строк
    python show_logs.py 100       # Последние 100 строк
    python show_logs.py client    # Только client.log
    python show_logs.py server    # Только server.log
"""

import sys
from pathlib import Path


def tail_file(filepath: Path, num_lines: int = 50):
    """Возвращает последние N строк файла."""
    if not filepath.exists():
        return [f"[FILE NOT FOUND: {filepath}]"]

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        return lines[-num_lines:]


def show_logs(lines=50, which="both"):
    """Показывает логи."""
    client_log = Path("client.log")
    server_log = Path("server.log")

    if which in ("both", "client"):
        print("=" * 80)
        print(f"CLIENT LOG (last {lines} lines)".center(80))
        print("=" * 80)
        for line in tail_file(client_log, lines):
            print(line.rstrip())
        print()

    if which in ("both", "server"):
        print("=" * 80)
        print(f"SERVER LOG (last {lines} lines)".center(80))
        print("=" * 80)
        for line in tail_file(server_log, lines):
            print(line.rstrip())
        print()


if __name__ == "__main__":
    lines = 50
    which = "both"

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.isdigit():
            lines = int(arg)
        elif arg in ("client", "server", "both"):
            which = arg

    if len(sys.argv) > 2:
        arg2 = sys.argv[2]
        if arg2.isdigit():
            lines = int(arg2)
        elif arg2 in ("client", "server", "both"):
            which = arg2

    show_logs(lines, which)
