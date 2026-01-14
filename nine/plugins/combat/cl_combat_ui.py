"""
Combat UI - главный модуль UI для пошагового боя.
Координирует все компоненты боевого интерфейса.
"""

from typing import Optional
from direct.gui.OnscreenText import OnscreenText

from nine.core.plugins import PluginModule


class CombatUI(PluginModule):
    """
    Главный контроллер боевого UI.
    - Координирует InitiativeDisplay, ActionBar, TargetSelector
    - Показывает индикатор хода
    - Отображает результаты действий
    """

    def on_load(self):
        self.logger.info("Combat UI loaded")

        # Состояние
        self.is_in_combat = False
        self.current_combat_id = None
        self.is_my_turn = False

        # UI элементы
        self.turn_indicator = None
        self.combat_log_text = None

        # Подписки
        self.event_manager.subscribe("combat_started", self._on_combat_started)
        self.event_manager.subscribe("combat_ended", self._on_combat_ended)
        self.event_manager.subscribe("combat_turn_start", self._on_turn_start)
        self.event_manager.subscribe("combat_action_result", self._on_action_result)
        self.event_manager.subscribe("combat_round_start", self._on_round_start)

    def on_unload(self):
        self.event_manager.unsubscribe("combat_started", self._on_combat_started)
        self.event_manager.unsubscribe("combat_ended", self._on_combat_ended)
        self.event_manager.unsubscribe("combat_turn_start", self._on_turn_start)
        self.event_manager.unsubscribe("combat_action_result", self._on_action_result)
        self.event_manager.unsubscribe("combat_round_start", self._on_round_start)

        self._cleanup_ui()

        self.logger.info("Combat UI unloaded")

    # =========================================================================
    # UI управление
    # =========================================================================

    def _show_turn_indicator(self, entity_name: str, is_my_turn: bool):
        """Показывает индикатор чьего хода."""
        self._hide_turn_indicator()

        if is_my_turn:
            text = "ВАШ ХОД!"
            color = (0.2, 1.0, 0.2, 1)
            scale = 0.08
        else:
            text = f"Ход: {entity_name}"
            color = (0.9, 0.9, 0.3, 1)
            scale = 0.06

        self.turn_indicator = OnscreenText(
            text=text,
            pos=(0, 0.7),
            scale=scale,
            fg=color,
            shadow=(0, 0, 0, 0.5),
            mayChange=True
        )

        # Автоскрытие через 3 секунды (если не наш ход)
        if not is_my_turn:
            self.base.taskMgr.doMethodLater(
                3.0,
                self._fade_turn_indicator,
                "fade-turn-indicator"
            )

    def _hide_turn_indicator(self):
        """Скрывает индикатор хода."""
        self.base.taskMgr.remove("fade-turn-indicator")
        if self.turn_indicator:
            self.turn_indicator.destroy()
            self.turn_indicator = None

    def _fade_turn_indicator(self, task):
        """Плавно скрывает индикатор."""
        if self.turn_indicator:
            self.turn_indicator.destroy()
            self.turn_indicator = None
        return task.done

    def _show_action_result(self, result: dict, actor_name: str, target_name: str = None):
        """Показывает результат действия."""
        action_id = result.get("action", "")

        if action_id == "attack":
            self._show_attack_result(result, actor_name, target_name)
        elif action_id == "dash":
            self._show_message(f"{actor_name} использует Рывок!", (0.5, 0.8, 1.0, 1))
        elif action_id == "dodge":
            self._show_message(f"{actor_name} уклоняется!", (0.5, 0.8, 1.0, 1))
        elif action_id == "disengage":
            self._show_message(f"{actor_name} отходит!", (0.5, 0.8, 1.0, 1))
        elif action_id == "help":
            self._show_message(f"{actor_name} помогает {target_name}!", (0.5, 0.8, 1.0, 1))
        elif action_id == "end_turn":
            pass  # Не показываем для конца хода

    def _show_attack_result(self, result: dict, actor_name: str, target_name: str):
        """Показывает результат атаки."""
        attack_roll = result.get("attack_roll", 0)
        attack_total = result.get("attack_total", 0)
        target_ac = result.get("target_ac", 10)
        hit = result.get("hit", False)
        is_critical = result.get("is_critical", False)
        is_fumble = result.get("is_fumble", False)
        damage = result.get("damage", 0)

        # Формируем сообщение
        if is_fumble:
            msg = f"{actor_name} ПРОМАХИВАЕТСЯ!"
            color = (0.8, 0.3, 0.3, 1)
        elif is_critical:
            msg = f"{actor_name} наносит КРИТИЧЕСКИЙ УДАР!"
            color = (1.0, 0.8, 0.2, 1)
            if damage > 0:
                msg += f"\n{damage} урона по {target_name}!"
        elif hit:
            msg = f"{actor_name} попадает по {target_name}!"
            color = (0.3, 0.8, 0.3, 1)
            if damage > 0:
                msg += f"\n{damage} урона!"
        else:
            msg = f"{actor_name} промахивается по {target_name}"
            color = (0.7, 0.7, 0.7, 1)

        self._show_message(msg, color, duration=3.0)

        # Логируем в чат
        self._log_to_chat(
            f"[Бой] {actor_name} атакует {target_name}: "
            f"d20({attack_roll})+{attack_total - attack_roll}={attack_total} vs AC {target_ac} "
            f"{'КРИТ!' if is_critical else 'Попадание!' if hit else 'Промах'}"
            + (f" Урон: {damage}" if hit else "")
        )

    def _show_message(self, text: str, color: tuple = (1, 1, 1, 1), duration: float = 2.0):
        """Показывает временное сообщение на экране."""
        msg = OnscreenText(
            text=text,
            pos=(0, 0.3),
            scale=0.05,
            fg=color,
            shadow=(0, 0, 0, 0.5),
            align=0  # Center
        )

        # Удаляем через duration секунд
        def cleanup(task):
            msg.destroy()
            return task.done

        self.base.taskMgr.doMethodLater(duration, cleanup, f"msg-cleanup-{id(msg)}")

    def _log_to_chat(self, message: str):
        """Логирует сообщение в чат."""
        self.event_manager.post("chat_add_local_message", {
            "chat_type": "system",
            "from_name": "Бой",
            "message": message,
        })

    def _show_combat_start_banner(self):
        """Показывает баннер начала боя."""
        banner = OnscreenText(
            text="БОЙ НАЧАЛСЯ!",
            pos=(0, 0),
            scale=0.12,
            fg=(1.0, 0.3, 0.3, 1),
            shadow=(0, 0, 0, 0.8)
        )

        def cleanup(task):
            banner.destroy()
            return task.done

        self.base.taskMgr.doMethodLater(2.0, cleanup, "combat-banner-cleanup")

    def _show_combat_end_banner(self, reason: str):
        """Показывает баннер окончания боя."""
        if reason == "VICTORY":
            text = "ПОБЕДА!"
            color = (0.2, 1.0, 0.2, 1)
        elif reason == "DEFEAT":
            text = "ПОРАЖЕНИЕ"
            color = (1.0, 0.2, 0.2, 1)
        elif reason == "DM_ENDED":
            text = "БОЙ ЗАВЕРШЁН"
            color = (0.8, 0.8, 0.3, 1)
        else:
            text = "БОЙ ОКОНЧЕН"
            color = (0.7, 0.7, 0.7, 1)

        banner = OnscreenText(
            text=text,
            pos=(0, 0),
            scale=0.12,
            fg=color,
            shadow=(0, 0, 0, 0.8)
        )

        def cleanup(task):
            banner.destroy()
            return task.done

        self.base.taskMgr.doMethodLater(3.0, cleanup, "combat-end-banner-cleanup")

    def _cleanup_ui(self):
        """Очищает все UI элементы."""
        self._hide_turn_indicator()

    # =========================================================================
    # Обработчики событий
    # =========================================================================

    def _on_combat_started(self, data: dict):
        """Обрабатывает начало боя."""
        self.is_in_combat = True
        self.current_combat_id = data.get("combat_id")

        self._show_combat_start_banner()
        self._log_to_chat("Бой начался!")

    def _on_combat_ended(self, data: dict):
        """Обрабатывает окончание боя."""
        self.is_in_combat = False
        self.current_combat_id = None
        self.is_my_turn = False

        reason = data.get("reason", "")
        self._show_combat_end_banner(reason)
        self._log_to_chat(f"Бой окончен: {reason}")

        self._cleanup_ui()

    def _on_turn_start(self, data: dict):
        """Обрабатывает начало хода."""
        is_my_turn = data.get("is_player", False)
        entity_id = data.get("entity_id", "")

        self.is_my_turn = is_my_turn

        # Получаем имя сущности
        entity_name = self._get_entity_name(entity_id)

        self._show_turn_indicator(entity_name, is_my_turn)

    def _on_action_result(self, data: dict):
        """Обрабатывает результат действия."""
        result = data.get("result", {})
        actor_id = data.get("actor_id", "")
        target_id = data.get("target_id")

        if not result.get("success"):
            error = result.get("error", "Ошибка")
            self._show_message(error, (1.0, 0.3, 0.3, 1))
            return

        actor_name = self._get_entity_name(actor_id)
        target_name = self._get_entity_name(target_id) if target_id else None

        self._show_action_result(result, actor_name, target_name)

    def _on_round_start(self, data: dict):
        """Обрабатывает начало нового раунда."""
        round_num = data.get("round", 1)
        self._show_message(f"Раунд {round_num}", (0.9, 0.8, 0.3, 1), duration=1.5)
        self._log_to_chat(f"Начинается раунд {round_num}")

    def _get_entity_name(self, entity_id: str) -> str:
        """Получает имя сущности по ID."""
        if not entity_id:
            return "???"

        # Пытаемся как игрока
        try:
            client_id = int(entity_id)
            if hasattr(self.app, 'world'):
                player = self.app.world.players.get(client_id)
                if player:
                    return player.name
        except ValueError:
            pass

        # Пытаемся как NPC
        if hasattr(self.app, 'plugin_manager'):
            dnd_plugin = self.app.plugin_manager.get_plugin("nine.dnd")
            if dnd_plugin:
                for module in dnd_plugin.modules:
                    if hasattr(module, 'get_npc_entity'):
                        entity = module.get_npc_entity(entity_id)
                        if entity:
                            from ..npc.sh_components import NPCInfoComponent
                            info = entity.get_component(NPCInfoComponent)
                            if info:
                                return info.display_name

        return entity_id[:8] + "..."  # Сокращённый ID
