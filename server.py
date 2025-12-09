import asyncio
import sys
import logging

def main():
    # It's important to import Panda3D and the  GameServer class after
    # the asyncio event loop is running, especially on some platforms.
    try:
        from nine.server.game_server import GameServer
    except ImportError:
        logging.basicConfig(level=logging.CRITICAL)
        logging.critical("Could not import Panda3D or other dependencies. Please ensure Panda3D is installed.")
        sys.exit(1)

    server = GameServer()
    server.run()

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Server shutting down.")