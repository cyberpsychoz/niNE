"""
Audio Manager - ядро звуковой системы niNE.

Управляет тремя типами аудио:
- BGM (Background Music) — фоновая музыка с плейлистами
- BGS (Background Sound) — эмбиент окружения
- SFX (Sound Effects) — короткие звуковые эффекты

Поддерживает:
- Плавные переходы между треками (crossfade)
- Раздельную громкость для BGM/BGS/SFX
- 3D позиционные звуки
- Авто-shuffle плейлистов
"""

import random
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from panda3d.core import AudioSound, Filename


class AudioChannel(Enum):
    """Каналы аудио."""
    BGM = auto()      # Фоновая музыка
    BGS = auto()      # Эмбиент
    SFX = auto()      # Эффекты
    UI = auto()       # Звуки интерфейса
    VOICE = auto()    # Голос/диалоги


@dataclass
class AudioTrack:
    """Информация о звуковом треке."""
    path: str
    volume: float = 1.0
    loop: bool = False
    channel: AudioChannel = AudioChannel.SFX


@dataclass
class Playlist:
    """Плейлист с треками."""
    name: str
    tracks: List[str] = field(default_factory=list)
    shuffle: bool = True
    loop: bool = True
    crossfade: float = 2.0  # Время кроссфейда в секундах


class AudioManager:
    """
    Менеджер аудио системы.

    Использование:
        audio = AudioManager(base)
        audio.play_bgm("adventure")
        audio.play_sfx("sword_attack")
        audio.set_ambient("forest_day")
    """

    # Базовый путь к звукам
    SOUNDS_PATH = "nine/assets/materials/sounds"

    def __init__(self, base):
        """
        Args:
            base: Экземпляр ShowBase
        """
        self.base = base
        self.logger = None

        # Загружаем настройки громкости из конфига
        from nine.core.config import config

        # Громкость по каналам (0.0 - 1.0)
        self._volumes = {
            AudioChannel.BGM: config.get("audio_bgm_volume", 70) / 100.0,
            AudioChannel.BGS: config.get("audio_ambient_volume", 60) / 100.0,
            AudioChannel.SFX: config.get("audio_sfx_volume", 80) / 100.0,
            AudioChannel.UI: 0.6,
            AudioChannel.VOICE: 1.0,
        }

        # Мастер-громкость
        self._master_volume = config.get("audio_master_volume", 100) / 100.0

        # Текущие звуки
        self._current_bgm: Optional[AudioSound] = None
        self._current_bgs: Optional[AudioSound] = None
        self._bgm_fading: Optional[AudioSound] = None  # Для кроссфейда

        # Плейлисты
        self._playlists: Dict[str, Playlist] = {}
        self._current_playlist: Optional[str] = None
        self._playlist_index: int = 0
        self._shuffled_tracks: List[str] = []

        # Пул SFX для одновременного воспроизведения
        self._sfx_pool: List[AudioSound] = []
        self._max_sfx = 16  # Максимум одновременных SFX

        # Кеш загруженных звуков
        self._sound_cache: Dict[str, AudioSound] = {}

        # Callbacks
        self._on_bgm_end: Optional[Callable] = None

        # Инициализация
        self._init_default_playlists()

        # Задача обновления
        if hasattr(base, 'taskMgr'):
            base.taskMgr.add(self._update_task, "audio-manager-update")

    def _init_default_playlists(self):
        """Инициализирует стандартные плейлисты."""
        # Плейлисты BGM
        self._playlists = {
            "adventure": Playlist(
                name="adventure",
                tracks=[
                    "bgm/adventure_1.mp3",
                    "bgm/adventure_2.mp3",
                    "bgm/adventure_3.mp3",
                    "bgm/acventure_4.mp3",
                ],
                shuffle=True,
                loop=True,
            ),
            "combat": Playlist(
                name="combat",
                tracks=["bgm/fight_1.mp3"],
                shuffle=False,
                loop=True,
            ),
            "dungeon": Playlist(
                name="dungeon",
                tracks=[
                    "bgm/catacombs_1.mp3",
                    "bgm/catacombs_2.mp3",
                    "bgm/catacombs_3.mp3",
                ],
                shuffle=True,
                loop=True,
            ),
            "dark_forest": Playlist(
                name="dark_forest",
                tracks=[
                    "bgm/dark_forest_1.mp3",
                    "bgm/dark_forest_2.mp3",
                    "bgm/dark_forest_3.mp3",
                ],
                shuffle=True,
                loop=True,
            ),
            "city": Playlist(
                name="city",
                tracks=["bgm/city_1.mp3"],
                shuffle=False,
                loop=True,
            ),
        }

        # Эмбиенты (BGS)
        self._ambients = {
            "beach": "bgs/Beach.ogg",
            "beach_rain": "bgs/Beach Rain.ogg",
            "beach_storm": "bgs/Beach Storm.ogg",
            "cave": "bgs/Cave.ogg",
            "cave_rain": "bgs/Cave Rain.ogg",
            "cave_storm": "bgs/Cave Storm.ogg",
            "forest_day": "bgs/Forest Day.ogg",
            "forest_day_rain": "bgs/Forest Day Rain.ogg",
            "forest_day_storm": "bgs/Forest Day Storm.ogg",
            "forest_night": "bgs/Forest Night.ogg",
            "forest_night_rain": "bgs/Forest Night Rain.ogg",
            "forest_night_storm": "bgs/Forest Night Storm.ogg",
            "inside_day": "bgs/Inside Day.ogg",
            "inside_day_rain": "bgs/Inside Day Rain.ogg",
            "inside_day_storm": "bgs/Inside Day Storm.ogg",
            "inside_night": "bgs/Inside Night.ogg",
            "inside_night_rain": "bgs/Inside Night Rain.ogg",
            "inside_night_storm": "bgs/Inside Night Storm.ogg",
            "sea": "bgs/Sea.ogg",
            "sea_rain": "bgs/Sea Rain.ogg",
            "sea_storm": "bgs/Sea Storm.ogg",
        }

        # SFX маппинги для удобного доступа
        self._sfx_aliases = {
            # Атаки мечом
            "sword_attack": ["sfx/Attacks/Sword Attacks Hits and Blocks/Sword Attack 1.ogg",
                            "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Attack 2.ogg",
                            "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Attack 3.ogg"],
            "sword_hit": ["sfx/Attacks/Sword Attacks Hits and Blocks/Sword Impact Hit 1.ogg",
                         "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Impact Hit 2.ogg",
                         "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Impact Hit 3.ogg"],
            "sword_blocked": ["sfx/Attacks/Sword Attacks Hits and Blocks/Sword Blocked 1.ogg",
                             "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Blocked 2.ogg",
                             "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Blocked 3.ogg"],
            "sword_parry": ["sfx/Attacks/Sword Attacks Hits and Blocks/Sword Parry 1.ogg",
                           "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Parry 2.ogg",
                           "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Parry 3.ogg"],
            "sword_unsheath": ["sfx/Attacks/Sword Attacks Hits and Blocks/Sword Unsheath 1.ogg",
                              "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Unsheath 2.ogg"],
            "sword_sheath": ["sfx/Attacks/Sword Attacks Hits and Blocks/Sword Sheath 1.ogg",
                            "sfx/Attacks/Sword Attacks Hits and Blocks/Sword Sheath 2.ogg"],

            # Атаки луком
            "bow_attack": ["sfx/Attacks/Bow Attacks Hits and Blocks/Bow Attack 1.ogg",
                          "sfx/Attacks/Bow Attacks Hits and Blocks/Bow Attack 2.ogg"],
            "bow_hit": ["sfx/Attacks/Bow Attacks Hits and Blocks/Bow Impact Hit 1.ogg",
                       "sfx/Attacks/Bow Attacks Hits and Blocks/Bow Impact Hit 2.ogg",
                       "sfx/Attacks/Bow Attacks Hits and Blocks/Bow Impact Hit 3.ogg"],
            "bow_blocked": ["sfx/Attacks/Bow Attacks Hits and Blocks/Bow Blocked 1.ogg",
                           "sfx/Attacks/Bow Attacks Hits and Blocks/Bow Blocked 2.ogg",
                           "sfx/Attacks/Bow Attacks Hits and Blocks/Bow Blocked 3.ogg"],

            # Двери и сундуки
            "door_open": ["sfx/Doors Gates and Chests/Door Open 1.ogg",
                         "sfx/Doors Gates and Chests/Door Open 2.ogg"],
            "door_close": ["sfx/Doors Gates and Chests/Door Close 1.ogg",
                          "sfx/Doors Gates and Chests/Door Close 2.ogg"],
            "chest_open": ["sfx/Doors Gates and Chests/Chest Open 1.ogg",
                          "sfx/Doors Gates and Chests/Chest Open 2.ogg"],
            "chest_close": ["sfx/Doors Gates and Chests/Chest Close 1.ogg",
                           "sfx/Doors Gates and Chests/Chest Close 2.ogg"],
            "gate_open": ["sfx/Doors Gates and Chests/Gate Open.ogg"],
            "gate_close": ["sfx/Doors Gates and Chests/Gate Close.ogg"],
            "lock_unlock": ["sfx/Doors Gates and Chests/Lock Unlock.ogg"],

            # Добыча
            "chop": ["sfx/Chopping and Mining/chop 1.ogg",
                    "sfx/Chopping and Mining/chop 2.ogg",
                    "sfx/Chopping and Mining/chop 3.ogg",
                    "sfx/Chopping and Mining/chop 4.ogg"],
            "mine": ["sfx/Chopping and Mining/mine 1.ogg",
                    "sfx/Chopping and Mining/mine 2.ogg",
                    "sfx/Chopping and Mining/mine 3.ogg",
                    "sfx/Chopping and Mining/mine 4.ogg",
                    "sfx/Chopping and Mining/mine 5.ogg"],
        }

        # Шаги по поверхностям
        self._footstep_surfaces = ["Dirt", "Stone", "Water", "Wood"]
        for surface in self._footstep_surfaces:
            surface_lower = surface.lower()

            # Обычные шаги
            self._sfx_aliases[f"footstep_{surface_lower}_walk"] = [
                f"sfx/Footsteps/{surface}/{surface} Walk {i}.ogg" for i in range(1, 6)
            ]
            self._sfx_aliases[f"footstep_{surface_lower}_run"] = [
                f"sfx/Footsteps/{surface}/{surface} Run {i}.ogg" for i in range(1, 6)
            ]
            self._sfx_aliases[f"footstep_{surface_lower}_jump"] = [
                f"sfx/Footsteps/{surface}/{surface} Jump.ogg"
            ]
            self._sfx_aliases[f"footstep_{surface_lower}_land"] = [
                f"sfx/Footsteps/{surface}/{surface} Land.ogg"
            ]

            # Шаги в кольчуге
            self._sfx_aliases[f"footstep_{surface_lower}_chain_walk"] = [
                f"sfx/Footsteps/{surface}/{surface} Chain Walk {i}.ogg" for i in range(1, 6)
            ]
            self._sfx_aliases[f"footstep_{surface_lower}_chain_run"] = [
                f"sfx/Footsteps/{surface}/{surface} Chain Run {i}.ogg" for i in range(1, 6)
            ]
            self._sfx_aliases[f"footstep_{surface_lower}_chain_jump"] = [
                f"sfx/Footsteps/{surface}/{surface} Chain Jump.ogg"
            ]
            self._sfx_aliases[f"footstep_{surface_lower}_chain_land"] = [
                f"sfx/Footsteps/{surface}/{surface} Chain Land.ogg"
            ]

    # =========================================================================
    # Загрузка звуков
    # =========================================================================

    def _get_full_path(self, relative_path: str) -> str:
        """Возвращает полный путь к звуковому файлу."""
        return f"{self.SOUNDS_PATH}/{relative_path}"

    def _load_sound(self, relative_path: str, positional: bool = False) -> Optional[AudioSound]:
        """
        Загружает звуковой файл.

        Args:
            relative_path: Относительный путь от папки sounds
            positional: True для 3D позиционного звука
        """
        full_path = self._get_full_path(relative_path)

        # Проверяем кеш
        cache_key = f"{full_path}_{positional}"
        if cache_key in self._sound_cache:
            return self._sound_cache[cache_key]

        try:
            if positional:
                sound = self.base.loader.loadSfx(full_path)
            else:
                sound = self.base.loader.loadMusic(full_path)

            if sound:
                self._sound_cache[cache_key] = sound
                return sound
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load sound: {full_path} - {e}")

        return None

    # =========================================================================
    # BGM (Background Music)
    # =========================================================================

    def play_bgm(self, playlist_name: str, crossfade: float = 2.0):
        """
        Запускает плейлист фоновой музыки.

        Args:
            playlist_name: Имя плейлиста (adventure, combat, dungeon...)
            crossfade: Время кроссфейда в секундах
        """
        playlist = self._playlists.get(playlist_name)
        if not playlist:
            if self.logger:
                self.logger.warning(f"Playlist not found: {playlist_name}")
            return

        # Если тот же плейлист уже играет - не перезапускаем
        if self._current_playlist == playlist_name and self._current_bgm:
            return

        self._current_playlist = playlist_name

        # Подготавливаем треки
        if playlist.shuffle:
            self._shuffled_tracks = playlist.tracks.copy()
            random.shuffle(self._shuffled_tracks)
        else:
            self._shuffled_tracks = playlist.tracks.copy()

        self._playlist_index = 0

        # Запускаем первый трек
        self._play_next_bgm_track(crossfade)

    def _play_next_bgm_track(self, crossfade: float = 2.0):
        """Воспроизводит следующий трек плейлиста."""
        if not self._shuffled_tracks:
            return

        # Получаем следующий трек
        track_path = self._shuffled_tracks[self._playlist_index]

        # Загружаем
        new_bgm = self._load_sound(track_path)
        if not new_bgm:
            # Пропускаем битый трек
            self._playlist_index = (self._playlist_index + 1) % len(self._shuffled_tracks)
            return

        # Кроссфейд
        if self._current_bgm and crossfade > 0:
            self._bgm_fading = self._current_bgm
            self._fade_out(self._bgm_fading, crossfade)
        elif self._current_bgm:
            self._current_bgm.stop()

        # Запускаем новый
        self._current_bgm = new_bgm
        self._current_bgm.setLoop(False)  # Мы сами управляем переключением
        self._current_bgm.setVolume(0 if crossfade > 0 else self._get_channel_volume(AudioChannel.BGM))
        self._current_bgm.play()

        if crossfade > 0:
            self._fade_in(self._current_bgm, crossfade, AudioChannel.BGM)

        # Обновляем индекс
        self._playlist_index = (self._playlist_index + 1) % len(self._shuffled_tracks)

    def play_bgm_track(self, track_path: str, loop: bool = True, crossfade: float = 2.0):
        """
        Воспроизводит конкретный трек BGM.

        Args:
            track_path: Путь к треку относительно папки sounds
            loop: Зациклить трек
            crossfade: Время кроссфейда
        """
        self._current_playlist = None  # Сбрасываем плейлист

        new_bgm = self._load_sound(track_path)
        if not new_bgm:
            return

        if self._current_bgm and crossfade > 0:
            self._bgm_fading = self._current_bgm
            self._fade_out(self._bgm_fading, crossfade)
        elif self._current_bgm:
            self._current_bgm.stop()

        self._current_bgm = new_bgm
        self._current_bgm.setLoop(loop)
        self._current_bgm.setVolume(0 if crossfade > 0 else self._get_channel_volume(AudioChannel.BGM))
        self._current_bgm.play()

        if crossfade > 0:
            self._fade_in(self._current_bgm, crossfade, AudioChannel.BGM)

    def stop_bgm(self, fadeout: float = 2.0):
        """
        Останавливает фоновую музыку.

        Args:
            fadeout: Время затухания
        """
        self._current_playlist = None

        if self._current_bgm:
            if fadeout > 0:
                self._fade_out(self._current_bgm, fadeout, stop_after=True)
            else:
                self._current_bgm.stop()
            self._current_bgm = None

    def pause_bgm(self):
        """Ставит BGM на паузу."""
        if self._current_bgm:
            self._current_bgm.setPlayRate(0)

    def resume_bgm(self):
        """Возобновляет BGM."""
        if self._current_bgm:
            self._current_bgm.setPlayRate(1)

    # =========================================================================
    # BGS (Background Sound / Ambient)
    # =========================================================================

    def set_ambient(self, ambient_name: str, crossfade: float = 3.0):
        """
        Устанавливает эмбиент окружения.

        Args:
            ambient_name: Имя эмбиента (forest_day, cave, beach_storm...)
            crossfade: Время кроссфейда
        """
        ambient_path = self._ambients.get(ambient_name)
        if not ambient_path:
            if self.logger:
                self.logger.warning(f"Ambient not found: {ambient_name}")
            return

        new_bgs = self._load_sound(ambient_path)
        if not new_bgs:
            return

        if self._current_bgs and crossfade > 0:
            old_bgs = self._current_bgs
            self._fade_out(old_bgs, crossfade, stop_after=True)
        elif self._current_bgs:
            self._current_bgs.stop()

        self._current_bgs = new_bgs
        self._current_bgs.setLoop(True)
        self._current_bgs.setVolume(0 if crossfade > 0 else self._get_channel_volume(AudioChannel.BGS))
        self._current_bgs.play()

        if crossfade > 0:
            self._fade_in(self._current_bgs, crossfade, AudioChannel.BGS)

    def stop_ambient(self, fadeout: float = 2.0):
        """Останавливает эмбиент."""
        if self._current_bgs:
            if fadeout > 0:
                self._fade_out(self._current_bgs, fadeout, stop_after=True)
            else:
                self._current_bgs.stop()
            self._current_bgs = None

    # =========================================================================
    # SFX (Sound Effects)
    # =========================================================================

    def play_sfx(self, sfx_name: str, volume: float = 1.0,
                 pitch_variance: float = 0.0) -> Optional[AudioSound]:
        """
        Воспроизводит звуковой эффект.

        Args:
            sfx_name: Имя эффекта (sword_attack, door_open...) или путь к файлу
            volume: Множитель громкости (0.0 - 1.0)
            pitch_variance: Случайное отклонение высоты тона (0.0 - 0.5)

        Returns:
            AudioSound объект или None
        """
        # Получаем путь(и) к звуку
        if sfx_name in self._sfx_aliases:
            paths = self._sfx_aliases[sfx_name]
            path = random.choice(paths)  # Случайный вариант
        else:
            path = sfx_name  # Прямой путь

        # Загружаем
        sound = self._load_sound(path)
        if not sound:
            return None

        # Настраиваем
        final_volume = self._get_channel_volume(AudioChannel.SFX) * volume
        sound.setVolume(final_volume)
        sound.setLoop(False)

        # Вариация высоты тона
        if pitch_variance > 0:
            pitch = 1.0 + random.uniform(-pitch_variance, pitch_variance)
            sound.setPlayRate(pitch)

        # Воспроизводим
        sound.play()

        return sound

    def play_footstep(self, surface: str = "dirt", is_running: bool = False,
                      has_chain_armor: bool = False) -> Optional[AudioSound]:
        """
        Воспроизводит звук шага.

        Args:
            surface: Тип поверхности (dirt, stone, water, wood)
            is_running: True если бег
            has_chain_armor: True если персонаж в кольчуге
        """
        surface = surface.lower()
        action = "run" if is_running else "walk"
        armor = "_chain" if has_chain_armor else ""

        sfx_name = f"footstep_{surface}{armor}_{action}"
        return self.play_sfx(sfx_name, volume=0.6, pitch_variance=0.1)

    def play_jump(self, surface: str = "dirt", has_chain_armor: bool = False):
        """Воспроизводит звук прыжка."""
        surface = surface.lower()
        armor = "_chain" if has_chain_armor else ""
        sfx_name = f"footstep_{surface}{armor}_jump"
        return self.play_sfx(sfx_name, volume=0.7)

    def play_land(self, surface: str = "dirt", has_chain_armor: bool = False):
        """Воспроизводит звук приземления."""
        surface = surface.lower()
        armor = "_chain" if has_chain_armor else ""
        sfx_name = f"footstep_{surface}{armor}_land"
        return self.play_sfx(sfx_name, volume=0.8)

    # =========================================================================
    # Громкость
    # =========================================================================

    def set_master_volume(self, volume: float):
        """Устанавливает мастер-громкость (0.0 - 1.0)."""
        self._master_volume = max(0.0, min(1.0, volume))
        self._apply_volumes()

    def get_master_volume(self) -> float:
        """Возвращает мастер-громкость."""
        return self._master_volume

    def set_channel_volume(self, channel: AudioChannel, volume: float):
        """Устанавливает громкость канала (0.0 - 1.0)."""
        self._volumes[channel] = max(0.0, min(1.0, volume))
        self._apply_volumes()

    def get_channel_volume(self, channel: AudioChannel) -> float:
        """Возвращает громкость канала."""
        return self._volumes.get(channel, 1.0)

    def _get_channel_volume(self, channel: AudioChannel) -> float:
        """Возвращает итоговую громкость канала с учётом мастера."""
        return self._master_volume * self._volumes.get(channel, 1.0)

    def _apply_volumes(self):
        """Применяет текущие настройки громкости."""
        if self._current_bgm:
            self._current_bgm.setVolume(self._get_channel_volume(AudioChannel.BGM))
        if self._current_bgs:
            self._current_bgs.setVolume(self._get_channel_volume(AudioChannel.BGS))

    # =========================================================================
    # Fade эффекты
    # =========================================================================

    def _fade_in(self, sound: AudioSound, duration: float, channel: AudioChannel):
        """Плавное нарастание громкости."""
        target_volume = self._get_channel_volume(channel)

        def fade_task(task):
            elapsed = task.time
            progress = min(elapsed / duration, 1.0)
            sound.setVolume(target_volume * progress)

            if progress >= 1.0:
                return task.done
            return task.cont

        self.base.taskMgr.add(fade_task, f"fade-in-{id(sound)}")

    def _fade_out(self, sound: AudioSound, duration: float, stop_after: bool = False):
        """Плавное затухание громкости."""
        start_volume = sound.getVolume()

        def fade_task(task):
            elapsed = task.time
            progress = min(elapsed / duration, 1.0)
            sound.setVolume(start_volume * (1.0 - progress))

            if progress >= 1.0:
                if stop_after:
                    sound.stop()
                return task.done
            return task.cont

        self.base.taskMgr.add(fade_task, f"fade-out-{id(sound)}")

    # =========================================================================
    # Обновление
    # =========================================================================

    def _update_task(self, task):
        """Задача обновления аудио системы."""
        # Проверяем окончание текущего BGM трека для плейлиста
        if self._current_playlist and self._current_bgm:
            if self._current_bgm.status() == AudioSound.READY:
                # Трек закончился - играем следующий
                playlist = self._playlists.get(self._current_playlist)
                if playlist and playlist.loop:
                    self._play_next_bgm_track(playlist.crossfade)

        return task.cont

    # =========================================================================
    # Утилиты
    # =========================================================================

    def get_available_playlists(self) -> List[str]:
        """Возвращает список доступных плейлистов."""
        return list(self._playlists.keys())

    def get_available_ambients(self) -> List[str]:
        """Возвращает список доступных эмбиентов."""
        return list(self._ambients.keys())

    def get_available_sfx(self) -> List[str]:
        """Возвращает список доступных SFX алиасов."""
        return list(self._sfx_aliases.keys())

    def cleanup(self):
        """Очистка ресурсов."""
        self.stop_bgm(fadeout=0)
        self.stop_ambient(fadeout=0)

        for sound in self._sound_cache.values():
            sound.stop()
        self._sound_cache.clear()

        if hasattr(self.base, 'taskMgr'):
            self.base.taskMgr.remove("audio-manager-update")
