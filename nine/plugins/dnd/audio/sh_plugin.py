"""
DnD Audio Plugin - метаданные плагина звуковой системы.
"""

PLUGIN_INFO = {
    "name": "nine.dnd.audio",
    "version": "1.0.0",
    "description": "Звуковая система для D&D режима: BGM, эмбиент, SFX, шаги",
    "author": "niNE Team",
    "dependencies": ["nine.dnd"],

    # Модули плагина
    "client_modules": [
        "cl_audio_integration.AudioIntegration",
        "cl_footsteps.FootstepSystem",
    ],
    "server_modules": [],
}
