"""
D&D Audio Plugin - звуковая система для D&D режима.
"""

from .cl_audio_integration import AudioIntegration
from .cl_footsteps import FootstepSystem

__all__ = [
    "AudioIntegration",
    "FootstepSystem",
]
