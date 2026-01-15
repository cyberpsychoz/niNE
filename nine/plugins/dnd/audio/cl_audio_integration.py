"""
Audio Integration - интеграция звуковой системы с игровыми событиями.

Автоматически воспроизводит:
- Фоновую музыку по ситуации
- Боевые звуки при атаках
- Звуки окружения
"""

from nine.core.plugins import PluginModule


class AudioIntegration(PluginModule):
    """
    Интеграция аудио с игровыми событиями.
    Реагирует на события и воспроизводит соответствующие звуки.
    """

    def on_load(self):
        self.logger.info("Audio Integration loaded")

        # Получаем audio manager
        self.audio = None
        self._init_audio_manager()

        # Текущее состояние
        self.in_combat = False
        self.previous_playlist = "adventure"

        # Подписки на события
        self.event_manager.subscribe("combat_started", self._on_combat_started)
        self.event_manager.subscribe("combat_ended", self._on_combat_ended)
        self.event_manager.subscribe("combat_action_result", self._on_action_result)
        self.event_manager.subscribe("combat_turn_start", self._on_turn_start)

        # События игрока
        self.event_manager.subscribe("player_spawned", self._on_player_spawned)
        self.event_manager.subscribe("player_died", self._on_player_died)
        self.event_manager.subscribe("player_jump", self._on_player_jump)
        self.event_manager.subscribe("player_land", self._on_player_land)

        # DM команды аудио
        self.event_manager.subscribe("dm_audio_command", self._on_dm_audio_command)

        # Автозапуск музыки
        self.base.taskMgr.doMethodLater(1.0, self._start_default_music, "start-music")

    def on_unload(self):
        self.event_manager.unsubscribe("combat_started", self._on_combat_started)
        self.event_manager.unsubscribe("combat_ended", self._on_combat_ended)
        self.event_manager.unsubscribe("combat_action_result", self._on_action_result)
        self.event_manager.unsubscribe("combat_turn_start", self._on_turn_start)
        self.event_manager.unsubscribe("player_spawned", self._on_player_spawned)
        self.event_manager.unsubscribe("player_died", self._on_player_died)
        self.event_manager.unsubscribe("player_jump", self._on_player_jump)
        self.event_manager.unsubscribe("player_land", self._on_player_land)
        self.event_manager.unsubscribe("dm_audio_command", self._on_dm_audio_command)

        self.logger.info("Audio Integration unloaded")

    def _init_audio_manager(self):
        """Инициализирует AudioManager."""
        try:
            from nine.core.audio_manager import AudioManager

            # Проверяем, есть ли уже audio manager
            if hasattr(self.base, 'audio_manager') and self.base.audio_manager:
                self.audio = self.base.audio_manager
            else:
                self.audio = AudioManager(self.base)
                self.audio.logger = self.logger
                self.base.audio_manager = self.audio

            self.logger.info("AudioManager initialized")
        except Exception as e:
            self.logger.error(f"Failed to init AudioManager: {e}")
            self.audio = None

    def _start_default_music(self, task):
        """Запускает фоновую музыку по умолчанию."""
        if self.audio:
            self.audio.play_bgm("adventure")
            self.audio.set_ambient("forest_day")
            self.logger.info("Default music started")
        return task.done

    # =========================================================================
    # Боевые события
    # =========================================================================

    def _on_combat_started(self, data: dict):
        """Начало боя — переключаем на боевую музыку."""
        if not self.audio:
            return

        self.in_combat = True
        self.previous_playlist = "adventure"  # Запоминаем для возврата

        # Переключаем музыку
        self.audio.play_bgm("combat", crossfade=1.5)

        # Звук начала боя
        self.audio.play_sfx("sword_unsheath", volume=0.7)

        self.logger.info("Combat music started")

    def _on_combat_ended(self, data: dict):
        """Конец боя — возвращаем обычную музыку."""
        if not self.audio:
            return

        self.in_combat = False

        # Звук конца боя
        reason = data.get("reason", "")
        if reason == "VICTORY":
            # TODO: victory fanfare
            pass

        # Возвращаем музыку
        self.audio.play_bgm(self.previous_playlist, crossfade=2.0)

        self.logger.info("Combat music ended, returning to exploration")

    def _on_action_result(self, data: dict):
        """Результат боевого действия — воспроизводим соответствующие звуки."""
        if not self.audio:
            return

        result = data.get("result", {})
        action_id = result.get("action", "")

        if action_id == "attack":
            self._play_attack_sounds(result)
        elif action_id == "dash":
            # Звук рывка (шорох одежды/шаги)
            pass
        elif action_id == "dodge":
            # Звук уклонения
            pass

    def _play_attack_sounds(self, result: dict):
        """Воспроизводит звуки атаки."""
        hit = result.get("hit", False)
        is_critical = result.get("is_critical", False)
        is_fumble = result.get("is_fumble", False)

        # Звук взмаха оружием
        self.audio.play_sfx("sword_attack", volume=0.8, pitch_variance=0.1)

        # Звук результата (с небольшой задержкой)
        def play_hit_sound(task):
            if is_fumble:
                # Промах — только воздух
                pass
            elif hit:
                if is_critical:
                    # Критический удар — громче
                    self.audio.play_sfx("sword_hit", volume=1.0)
                else:
                    # Обычное попадание
                    self.audio.play_sfx("sword_hit", volume=0.7, pitch_variance=0.15)
            else:
                # Заблокировано
                self.audio.play_sfx("sword_blocked", volume=0.6, pitch_variance=0.1)
            return task.done

        self.base.taskMgr.doMethodLater(0.15, play_hit_sound, "play-hit-sound")

    def _on_turn_start(self, data: dict):
        """Начало хода — звуковой сигнал для игрока."""
        if not self.audio:
            return

        is_my_turn = data.get("is_player", False)
        if is_my_turn:
            # TODO: звук "ваш ход"
            pass

    # =========================================================================
    # События игрока
    # =========================================================================

    def _on_player_spawned(self, data: dict):
        """Игрок заспавнился."""
        # Можно добавить звук появления
        pass

    def _on_player_died(self, data: dict):
        """Игрок умер."""
        if self.audio:
            # Драматический звук смерти
            pass

    def _on_player_jump(self, data: dict):
        """Игрок прыгнул."""
        if self.audio:
            surface = data.get("surface", "dirt")
            has_armor = data.get("has_chain_armor", False)
            self.audio.play_jump(surface, has_armor)

    def _on_player_land(self, data: dict):
        """Игрок приземлился."""
        if self.audio:
            surface = data.get("surface", "dirt")
            has_armor = data.get("has_chain_armor", False)
            self.audio.play_land(surface, has_armor)

    # =========================================================================
    # DM команды
    # =========================================================================

    def _on_dm_audio_command(self, data: dict):
        """Обрабатывает DM команды управления аудио."""
        if not self.audio:
            return

        command = data.get("command", "")
        args = data.get("args", [])

        if command == "music_play":
            playlist = args[0] if args else "adventure"
            self.audio.play_bgm(playlist)

        elif command == "music_stop":
            fadeout = float(args[0]) if args else 2.0
            self.audio.stop_bgm(fadeout)

        elif command == "music_track":
            track = args[0] if args else ""
            if track:
                self.audio.play_bgm_track(f"bgm/{track}")

        elif command == "ambient_set":
            ambient = args[0] if args else "forest_day"
            self.audio.set_ambient(ambient)

        elif command == "ambient_stop":
            fadeout = float(args[0]) if args else 2.0
            self.audio.stop_ambient(fadeout)

        elif command == "sfx_play":
            sfx = args[0] if args else ""
            if sfx:
                self.audio.play_sfx(sfx)

        elif command == "volume_master":
            vol = float(args[0]) / 100.0 if args else 1.0
            self.audio.set_master_volume(vol)

    # =========================================================================
    # Публичные методы
    # =========================================================================

    def play_ui_sound(self, sound_name: str):
        """Воспроизводит UI звук."""
        if self.audio:
            # TODO: добавить UI звуки
            pass

    def set_ambient_for_location(self, location_type: str, weather: str = "clear"):
        """Устанавливает эмбиент для локации."""
        if not self.audio:
            return

        # Маппинг локация -> эмбиент
        location_ambients = {
            "forest": "forest_day",
            "cave": "cave",
            "beach": "beach",
            "sea": "sea",
            "inside": "inside_day",
        }

        base_ambient = location_ambients.get(location_type, "forest_day")

        # Добавляем погоду
        if weather == "rain":
            base_ambient += "_rain"
        elif weather == "storm":
            base_ambient += "_storm"

        self.audio.set_ambient(base_ambient)
