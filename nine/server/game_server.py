import asyncio
import ipaddress
import json
import logging
import math
import os
import ssl
import struct
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData, Vec3, ClockObject

# Global clock for delta time
globalClock = ClockObject.getGlobalClock()

from nine.core.world import GameWorld
from nine.core.events import EventManager
from nine.core.plugins import PluginManager
from nine.core.database import DatabaseManager


# =============================================================================
# Interest Management - Network Optimization
# =============================================================================

@dataclass
class ClientInterest:
    """Tracks which entities a client is interested in."""
    client_id: int
    position: Tuple[float, float, float] = (0, 0, 0)
    full_update_entities: Set[str] = field(default_factory=set)
    reduced_update_entities: Set[str] = field(default_factory=set)
    last_sent_state: Dict[str, Dict] = field(default_factory=dict)


class InterestManager:
    """
    Manages which NPCs each client should receive updates for.

    Clients only receive:
    - Full updates for nearby NPCs (position, animation, stats)
    - Reduced updates for mid-range NPCs (position only)
    - No updates for far NPCs

    This significantly reduces network bandwidth for large NPC counts.
    """

    # Distance thresholds
    FULL_UPDATE_RADIUS = 50.0      # Full state updates
    REDUCED_UPDATE_RADIUS = 100.0  # Position-only updates
    # Beyond REDUCED_UPDATE_RADIUS: no updates

    # Delta compression settings
    POSITION_THRESHOLD = 0.1       # Min position change to send
    ROTATION_THRESHOLD = 1.0       # Min rotation change to send

    def __init__(self):
        """Initialize interest manager."""
        self._client_interests: Dict[int, ClientInterest] = {}
        self._logger = logging.getLogger(__name__)

    def register_client(self, client_id: int) -> None:
        """Register a new client."""
        self._client_interests[client_id] = ClientInterest(client_id=client_id)

    def unregister_client(self, client_id: int) -> None:
        """Unregister a client."""
        self._client_interests.pop(client_id, None)

    def update_client_position(
        self,
        client_id: int,
        x: float,
        y: float,
        z: float
    ) -> None:
        """Update client's known position."""
        interest = self._client_interests.get(client_id)
        if interest:
            interest.position = (x, y, z)

    def get_npcs_for_client(
        self,
        client_id: int,
        all_npcs: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Get NPCs that should be sent to a client.

        Args:
            client_id: Client ID
            all_npcs: List of all NPC states

        Returns:
            Tuple of (full_update_npcs, reduced_update_npcs)
        """
        interest = self._client_interests.get(client_id)
        if not interest:
            return [], []

        px, py, pz = interest.position
        full_updates = []
        reduced_updates = []

        for npc in all_npcs:
            npc_pos = npc.get("position", {})
            nx = npc_pos.get("x", 0)
            ny = npc_pos.get("y", 0)

            # Calculate distance
            dx = nx - px
            dy = ny - py
            dist = math.sqrt(dx * dx + dy * dy)

            npc_id = npc.get("entity_id", "")

            if dist <= self.FULL_UPDATE_RADIUS:
                # Full update - check for delta compression
                if self._should_send_full_update(interest, npc_id, npc):
                    full_updates.append(npc)
                    interest.full_update_entities.add(npc_id)
                    interest.reduced_update_entities.discard(npc_id)
                    interest.last_sent_state[npc_id] = npc.copy()

            elif dist <= self.REDUCED_UPDATE_RADIUS:
                # Reduced update - position only
                if self._should_send_reduced_update(interest, npc_id, npc):
                    reduced_npc = self._create_reduced_state(npc)
                    reduced_updates.append(reduced_npc)
                    interest.reduced_update_entities.add(npc_id)
                    interest.full_update_entities.discard(npc_id)
                    interest.last_sent_state[npc_id] = reduced_npc

            else:
                # Out of range - clear tracking
                if npc_id in interest.full_update_entities:
                    interest.full_update_entities.discard(npc_id)
                if npc_id in interest.reduced_update_entities:
                    interest.reduced_update_entities.discard(npc_id)
                interest.last_sent_state.pop(npc_id, None)

        return full_updates, reduced_updates

    def _should_send_full_update(
        self,
        interest: ClientInterest,
        npc_id: str,
        npc: Dict
    ) -> bool:
        """Check if full update should be sent (delta compression)."""
        last_state = interest.last_sent_state.get(npc_id)
        if not last_state:
            return True  # First update

        # Check position delta
        npc_pos = npc.get("position", {})
        last_pos = last_state.get("position", {})

        dx = abs(npc_pos.get("x", 0) - last_pos.get("x", 0))
        dy = abs(npc_pos.get("y", 0) - last_pos.get("y", 0))

        if dx > self.POSITION_THRESHOLD or dy > self.POSITION_THRESHOLD:
            return True

        # Check rotation delta
        dr = abs(npc_pos.get("rotation", 0) - last_pos.get("rotation", 0))
        if dr > self.ROTATION_THRESHOLD:
            return True

        # Check animation change
        if npc.get("animation") != last_state.get("animation"):
            return True

        # Check HP change
        if npc.get("hp_current") != last_state.get("hp_current"):
            return True

        # Check state change
        if npc.get("ai_state") != last_state.get("ai_state"):
            return True

        return False

    def _should_send_reduced_update(
        self,
        interest: ClientInterest,
        npc_id: str,
        npc: Dict
    ) -> bool:
        """Check if reduced update should be sent."""
        last_state = interest.last_sent_state.get(npc_id)
        if not last_state:
            return True

        # Only check position for reduced updates
        npc_pos = npc.get("position", {})
        last_pos = last_state.get("position", {})

        dx = abs(npc_pos.get("x", 0) - last_pos.get("x", 0))
        dy = abs(npc_pos.get("y", 0) - last_pos.get("y", 0))

        return dx > self.POSITION_THRESHOLD or dy > self.POSITION_THRESHOLD

    def _create_reduced_state(self, npc: Dict) -> Dict:
        """Create reduced state with position only."""
        return {
            "entity_id": npc.get("entity_id"),
            "position": npc.get("position"),
            "is_reduced": True  # Flag for client
        }

    def get_stats(self) -> Dict:
        """Get interest management statistics."""
        total_full = 0
        total_reduced = 0

        for interest in self._client_interests.values():
            total_full += len(interest.full_update_entities)
            total_reduced += len(interest.reduced_update_entities)

        return {
            "clients": len(self._client_interests),
            "total_full_updates": total_full,
            "total_reduced_updates": total_reduced,
            "full_radius": self.FULL_UPDATE_RADIUS,
            "reduced_radius": self.REDUCED_UPDATE_RADIUS,
        }

# Load server-specific PRC file data
loadPrcFileData("", """
    window-type none
    audio-library-name null
    threading-model None
""")

class GameServer(ShowBase):
    def __init__(self):
        super().__init__()

        # Setup logging - configure root logger to capture all modules
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # File handler - всё логируется в файл (INFO+)
        file_handler = logging.FileHandler("server.log", mode='w')
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)

        # Console handler - только важные сообщения (WARNING+)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.WARNING)  # Только WARNING, ERROR, CRITICAL в консоль

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)  # Общий уровень INFO
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)

        # Load config (create default if not exists)
        config = self._load_or_create_config()

        # Ensure SSL certificates exist
        if not self._ensure_certificates():
            raise SystemExit("SSL certificates required to start server.")

        self.host = config.get("host", "localhost")
        self.port = config.get("port", 9009)
        self.tick_rate = config.get("tick_rate", 30)
        self.allow_dev_client = config.get("allow_dev_client", False)

        # Init asyncio loop
        self.asyncio_loop = asyncio.get_event_loop()

        # Networking state
        self.clients = {}  # map client_id to writer
        self.client_addresses: Dict[int, str] = {}  # client_id -> IP string
        self.client_id_counter = 0
        self.message_queue = deque()

        # Ban system
        self.banned_ips: Set[str] = set()
        self._load_banlist()

        # Noclip tracking
        self.noclip_clients: Set[int] = set()

        # Setup World (uses Panda3D collision system, no Bullet)
        self.world = GameWorld(self.render)

        # Database for accounts and characters
        self.db = DatabaseManager("nine.db")

        # Event system and plugins
        self.is_server = True  # Plugins check this flag
        self.event_manager = EventManager()
        self.plugin_manager = PluginManager(self, self.event_manager)

        # Subscribe to chat events from plugins
        self.event_manager.subscribe("chat_send_to_clients", self.handle_chat_send)
        # Subscribe to stats events from plugins
        self.event_manager.subscribe("stats_send_to_client", self.handle_stats_send)
        # Subscribe to world config events from plugins
        self.event_manager.subscribe("world_config_send_to_client", self.handle_world_config_send)
        # Subscribe to inventory events from plugins
        self.event_manager.subscribe("inventory_send_to_client", self.handle_inventory_send)
        # Subscribe to equipment events from plugins
        self.event_manager.subscribe("equipment_send_to_client", self.handle_equipment_send)
        # Subscribe to system messages
        self.event_manager.subscribe("system_message_to_client", self.handle_system_message)

        # Subscribe to generic plugin-to-client forwarding
        self.event_manager.subscribe("send_to_client", self.handle_send_to_client)

        # NPC Manager will be set by NPC plugin during load
        self.npc_manager = None

        # Interest manager for network optimization
        self.interest_manager = InterestManager()

        # Load plugins
        self.plugin_manager.load_plugins()

        # NPC Manager reference is set by the NPC plugin during load_plugins()
        # (see nine/plugins/npc/sv_plugin.py:30)

        # Enable unified ECS mode for NPC manager if available
        self._setup_unified_ecs()

        # Game time system (day/night cycle)
        self._game_time = 8.0   # Start at 8:00 AM
        self._game_hour = 8
        self._time_scale = 60.0  # 1 real minute = 1 game hour (full day = 24 min)

        # Flag for unified world_state format
        self.use_unified_world_state = True

        # Notify plugins that world is loaded (initializes pathfinder, spawns test NPCs)
        self._post_world_loaded()

        # Setup game loop
        self.taskMgr.add(self.game_loop, "game_loop")
        self.taskMgr.add(self.poll_asyncio, "asyncio-poll")

        self.logger.info("Game Server initialized.")

    def _setup_unified_ecs(self) -> None:
        """
        Setup unified ECS mode where NPCs share the same ECS world as players.

        This enables:
        - Shared physics system
        - Unified world_state format with pawns
        - Consistent entity management
        """
        if self.npc_manager is None:
            self.logger.debug("[ECS] NPC Manager not available, skipping unified ECS setup")
            return

        try:
            # Get the ECS world from GameWorld
            ecs_world = self.world.get_ecs_world()

            # Set shared ECS world in NPC manager
            if hasattr(self.npc_manager, 'set_shared_ecs_world'):
                self.npc_manager.set_shared_ecs_world(ecs_world)
                self.logger.info("[ECS] Unified ECS mode enabled - NPCs and Players share ECS world")
            else:
                self.logger.debug("[ECS] NPC Manager doesn't support unified mode")

        except Exception as e:
            self.logger.warning(f"[ECS] Failed to setup unified ECS mode: {e}")

    def _post_world_loaded(self) -> None:
        """
        Post world_loaded event to initialize NPC pathfinder and spawn test NPCs.
        """
        # Get world bounds from collision mesh or use defaults
        bounds = (-50, -50, 50, 50)  # min_x, min_y, max_x, max_y

        # Try to get actual bounds from map
        if hasattr(self.world, 'get_bounds'):
            bounds = self.world.get_bounds()

        self.event_manager.post("world_loaded", {
            "bounds": bounds,
            "map_path": "nine/assets/models/maps/map3.bam"
        })
        self.logger.info(f"[World] world_loaded event posted with bounds: {bounds}")

    # =========================================================================
    # Ban System
    # =========================================================================

    def _load_banlist(self):
        """Load banned IPs from banlist.txt."""
        try:
            with open("banlist.txt", "r") as f:
                for line in f:
                    ip = line.strip()
                    if ip and not ip.startswith("#"):
                        self.banned_ips.add(ip)
            if self.banned_ips:
                self.logger.info(f"Loaded {len(self.banned_ips)} banned IPs")
        except FileNotFoundError:
            pass

    def _save_banlist(self):
        """Save banned IPs to banlist.txt."""
        with open("banlist.txt", "w") as f:
            for ip in sorted(self.banned_ips):
                f.write(ip + "\n")

    def kick_player(self, client_id: int, reason: str = ""):
        """Kick a player from the server."""
        writer = self.clients.get(client_id)
        if not writer:
            return
        self.logger.info(f"Kicking client {client_id}: {reason}")
        asyncio.run_coroutine_threadsafe(
            self.send_to_client(client_id, {
                "type": "kicked",
                "reason": reason or "You have been kicked"
            }),
            self.asyncio_loop
        )

        def _do_disconnect(task):
            self.handle_disconnect(client_id)
            if not writer.is_closing():
                writer.close()
            return task.done

        self.taskMgr.doMethodLater(0.1, _do_disconnect, f"kick-{client_id}")

    def ban_player(self, client_id: int, reason: str = ""):
        """Ban a player's IP and kick them."""
        ip = self.client_addresses.get(client_id)
        if ip:
            self.banned_ips.add(ip)
            self._save_banlist()
            self.logger.info(f"Banned IP {ip} (client {client_id}): {reason}")
        self.kick_player(client_id, reason or "You have been banned")

    def unban_ip(self, ip: str):
        """Remove an IP from the ban list."""
        self.banned_ips.discard(ip)
        self._save_banlist()
        self.logger.info(f"Unbanned IP {ip}")

    def _load_or_create_config(self) -> dict:
        """Load server config from file, or create default if not exists."""
        config_path = "server_config.json"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Invalid config file, recreating: {e}")

        # Create default config
        default_config = {
            "host": "localhost",
            "port": 9009,
            "tick_rate": 30,
            "allow_dev_client": False,
            "world": {
                "map": {"model": "nine/assets/models/maps/map3.bam"},
                "lighting": {
                    "ambient": {"color": [0.15, 0.1, 0.2, 1.0], "enabled": True},
                    "sun": {"color": [1.2, 0.7, 0.6, 1.0], "direction": [45, -30, 0], "enabled": True},
                    "fill": {"color": [0.2, 0.25, 0.4, 1.0], "direction": [150, -30, 0], "enabled": True},
                    "rim": {"color": [0.4, 0.2, 0.1, 1.0], "direction": [-120, -10, 0], "enabled": False}
                },
                "skybox": {
                    "texture": "nine/assets/materials/textures/sky.png",
                    "radius": 1000,
                    "segments": 64,
                    "rings": 32,
                    "uv_scale": {"v_offset": 0.15, "v_scale": 0.9}
                },
                "fog": {"enabled": False}
            }
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

        self.logger.info(f"Created default config: {config_path}")
        return default_config

    def _ensure_certificates(self) -> bool:
        """Check for SSL certificates, offer to generate if missing. Returns True if certs exist."""
        cert_path = "certs/cert.pem"
        key_path = "certs/key.pem"

        if os.path.exists(cert_path) and os.path.exists(key_path):
            return True

        print("\n" + "=" * 50)
        print("SSL сертификаты не найдены!")
        print("=" * 50)
        print(f"Ожидаемые пути:")
        print(f"  - {cert_path}")
        print(f"  - {key_path}")
        print()

        while True:
            response = input("Сгенерировать самоподписанные сертификаты для разработки? [Y/n]: ").strip().lower()
            if response in ("", "y", "yes", "д", "да"):
                return self._generate_certificates()
            elif response in ("n", "no", "н", "нет"):
                print("Сервер не может запуститься без SSL сертификатов.")
                return False
            else:
                print("Пожалуйста, введите 'y' или 'n'")

    def _generate_certificates(self) -> bool:
        """Generate self-signed SSL certificates for development using Python."""
        certs_dir = "certs"
        cert_path = os.path.join(certs_dir, "cert.pem")
        key_path = os.path.join(certs_dir, "key.pem")

        # Create certs directory
        os.makedirs(certs_dir, exist_ok=True)

        print("Генерация SSL сертификатов...")

        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            import datetime

            # Generate RSA key
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )

            # Generate self-signed certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
                .add_extension(
                    x509.SubjectAlternativeName([
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    ]),
                    critical=False,
                )
                .sign(key, hashes.SHA256(), default_backend())
            )

            # Write private key
            with open(key_path, "wb") as f:
                f.write(key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Write certificate
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            print(f"Сертификаты успешно созданы в папке '{certs_dir}/'")
            self.logger.info("Self-signed certificates generated successfully.")
            return True

        except ImportError:
            print("Ошибка: библиотека 'cryptography' не установлена!")
            print("Установите её командой: pip install cryptography")
            self.logger.error("cryptography library not installed.")
            return False
        except Exception as e:
            print(f"Ошибка при генерации сертификатов: {e}")
            self.logger.error(f"Certificate generation error: {e}")
            return False

    def poll_asyncio(self, task):
        self.asyncio_loop.call_soon(self.asyncio_loop.stop)
        self.asyncio_loop.run_forever()
        return task.cont

    def game_loop(self, task):
        # CRITICAL FIX: Limit tick rate to prevent multiple ticks per millisecond
        if not hasattr(self, '_last_tick_time'):
            self._last_tick_time = globalClock.getRealTime()
            self._tick_id = 0

        # Calculate time since last tick
        current_time = globalClock.getRealTime()
        time_since_last_tick = current_time - self._last_tick_time
        target_tick_interval = 1.0 / self.tick_rate

        # Skip this frame if not enough time has passed
        if time_since_last_tick < target_tick_interval:
            return task.cont

        # Update last tick time
        self._last_tick_time = current_time
        self._tick_id += 1

        # Use fixed dt based on tick_rate for consistent physics
        dt = target_tick_interval

        # 1. Process network messages
        while self.message_queue:
            client_id, data = self.message_queue.popleft()
            self.process_message(client_id, data)

        # 2. Update game world (includes collision traversal)
        if self._tick_id < 5:  # Log only first 5 ticks (startup)
            self.logger.debug(f"[GameServer TICK #{self._tick_id}] world.update(dt={dt:.4f})")
        self.world.update(dt)

        # 2.5. Update NPC system
        if self.npc_manager:
            self.npc_manager.update(dt)
            # Обновляем кэш игроков для AI targeting
            players_data = []
            for cid, player in self.world.players.items():
                state = player.get_state()
                players_data.append({
                    "uuid": str(cid),
                    "name": player.name,
                    "position": {"x": state["pos"][0], "y": state["pos"][1], "z": state["pos"][2]}
                })
            self.event_manager.post("player_update", {"players": players_data})

        # 2.6. Update game time (day/night cycle)
        delta_hours = dt * (self._time_scale / 3600.0)
        self._game_time += delta_hours
        if self._game_time >= 24.0:
            self._game_time -= 24.0
        new_hour = int(self._game_time)
        if new_hour != self._game_hour:
            self._game_hour = new_hour
            self.event_manager.post("game_hour_changed", {"hour": new_hour})
            self.logger.info(f"[Time] Game hour: {new_hour}:00")

        # Post game_tick for living world systems (needs decay, memory decay)
        self.event_manager.post("game_tick", {"delta_hours": delta_hours})

        # 3. Update client positions in interest manager
        for cid, player in self.world.players.items():
            state = player.get_state()
            pos = state["pos"]
            self.interest_manager.update_client_position(cid, pos[0], pos[1], pos[2])

        # 4. Broadcast state (with interest management for NPCs)
        if self.use_unified_world_state:
            # Use per-client filtered NPC updates
            asyncio.run_coroutine_threadsafe(
                self._broadcast_with_interest_management(), self.asyncio_loop
            )
        else:
            world_state = self.world.get_world_state()
            # Add NPC states (legacy format)
            if self.npc_manager:
                world_state["npcs"] = self.npc_manager.get_npc_states()

            if world_state.get("players") or world_state.get("pawns") or world_state.get("npcs"):
                asyncio.run_coroutine_threadsafe(
                    self.broadcast(world_state), self.asyncio_loop
                )

        return task.cont

    def _get_unified_world_state(self) -> dict:
        """
        Get world state in unified format with pawns list.

        Returns:
            {
                "type": "world_state",
                "players": {...},  # Legacy format for backward compatibility
                "pawns": [...],    # Unified pawn list (players + NPCs)
                "npcs": [...]      # Legacy NPC format for backward compatibility
            }
        """
        # Get base state from world
        world_state = self.world.get_unified_world_state()

        # Add NPC pawns to the unified pawns list
        if self.npc_manager:
            npc_pawns = self.npc_manager.get_npc_pawn_states()
            if "pawns" in world_state:
                world_state["pawns"].extend(npc_pawns)
            else:
                world_state["pawns"] = npc_pawns

            # Also include legacy NPC format for backward compatibility
            world_state["npcs"] = self.npc_manager.get_npc_states()

        return world_state

    async def _broadcast_with_interest_management(self):
        """
        Broadcast world state with per-client NPC filtering.

        Uses InterestManager to send only nearby NPCs to each client,
        reducing network bandwidth significantly.
        """
        # Get base world state (without NPCs)
        base_state = self.world.get_unified_world_state()

        # Get all NPC states
        all_npcs = []
        if self.npc_manager:
            all_npcs = self.npc_manager.get_npc_states()

        # Send filtered state to each client
        for client_id, writer in self.clients.items():
            if writer.is_closing():
                continue

            # Get filtered NPCs for this client
            full_npcs, reduced_npcs = self.interest_manager.get_npcs_for_client(
                client_id, all_npcs
            )

            # Build state for this client
            client_state = base_state.copy()
            client_state["npcs"] = full_npcs

            # Add reduced NPCs as separate list
            if reduced_npcs:
                client_state["npcs_reduced"] = reduced_npcs

            # Only send if there's something to send
            if not client_state.get("players") and not client_state.get("pawns") and not client_state.get("npcs"):
                continue

            try:
                payload = json.dumps(client_state).encode("utf-8")
                header = struct.pack("!I", len(payload))
                writer.write(header + payload)
                await writer.drain()
            except Exception as e:
                self.logger.error(f"Error sending filtered state to client {client_id}: {e}")
        
    def process_message(self, client_id, data):
        msg_type = data.get("type")

        if msg_type == "auth":
            self.handle_auth(client_id, data)
        elif msg_type == "dev_auth":
            self.handle_dev_auth(client_id, data)
        elif msg_type == "input":
             self.world.handle_input(client_id, data.get("state", {}))
        elif msg_type == "move":  # Dev clients send their own position
            if self.allow_dev_client:
                self.world.handle_move(client_id, data)
        elif msg_type == "chat_message":
            player = self.world.players.get(client_id)
            if player:
                player_pos = player.get_state()["pos"]
                self.event_manager.post("chat_message_received", {
                    "client_id": client_id,
                    "player_name": player.name,
                    "message": data.get("message", ""),
                    "player_pos": player_pos
                })
        elif msg_type == "item_use":
            # Отправляем событие плагину инвентаря
            self.event_manager.post("item_use", {
                "uuid": client_id,
                "slot": data.get("slot", 0),
            })
        elif msg_type == "item_drop":
            # Получаем позицию игрока для спавна предмета
            player = self.world.players.get(client_id)
            position = None
            if player:
                pos = player.get_state()["pos"]
                # Спавним перед игроком
                position = (pos[0], pos[1] + 1, pos[2])

            self.event_manager.post("item_drop", {
                "uuid": client_id,
                "slot": data.get("slot", 0),
                "count": data.get("count", 1),
                "position": position,
            })
        elif msg_type == "equip_item":
            self.event_manager.post("equip_item", {
                "uuid": client_id,
                "inventory_slot": data.get("inventory_slot", 0),
                "equipment_slot": data.get("equipment_slot"),
            })
        elif msg_type == "unequip_item":
            self.event_manager.post("unequip_item", {
                "uuid": client_id,
                "equipment_slot": data.get("equipment_slot", ""),
            })
        elif msg_type == "admin_action":
            self.event_manager.post("dm_panel_admin_action", {
                "client_id": client_id,
                **{k: v for k, v in data.items() if k != "type"}
            })
        elif msg_type == "inspect_request":
            self._handle_inspect_request(client_id, data)
        elif msg_type == "noclip_request":
            self.event_manager.post("admin_toggle_noclip", {
                "client_id": client_id,
            })
        elif data.get("type") == "internal_disconnect":
            self.handle_disconnect(client_id)

    def handle_dev_auth(self, client_id, data):
        if not self.allow_dev_client:
            self.logger.warning(f"Client {client_id} attempted dev_auth, but it is disabled. Disconnecting.")
            writer = self.clients.get(client_id)
            if writer:
                self.asyncio_loop.call_soon_threadsafe(writer.close)
            return
        
        player_name = data.get("name", f"DevPlayer_{client_id}")
        
        # Dev clients can have duplicate names, just log a warning.
        for p in self.world.players.values():
            if p.name == player_name:
                self.logger.warning(f"Player '{player_name}' is already logged in. Allowing duplicate for dev client.")
                break

        player = self.world.add_player(client_id, player_name)
        self.logger.info(f"Dev player '{player_name}' (Client #{client_id}) authenticated.")

        # Notify plugins about player join
        self.event_manager.post("player_joined", {"uuid": client_id, "name": player_name})

        other_players_state = {pid: p.get_state() for pid, p in self.world.players.items() if pid != client_id}
        welcome_data = {
            "type": "welcome",
            "id": client_id,
            "pos": player.get_state()["pos"],
            "players": other_players_state
        }
        asyncio.run_coroutine_threadsafe(self.send_to_client(client_id, welcome_data), self.asyncio_loop)

        join_data = {"type": "player_joined", "id": client_id, "player_info": player.get_state()}
        asyncio.run_coroutine_threadsafe(self.broadcast(join_data, exclude_ids=[client_id]), self.asyncio_loop)

    def handle_auth(self, client_id, data):
        """
        Simple name+password authentication.
        If account exists - verify password.
        If not - create a new account.
        On success, add the player to the world and send welcome.
        """
        import uuid as uuid_module

        player_name = data.get("name", "").strip()
        password = data.get("password", "")

        if not player_name:
            self.logger.warning(f"Client {client_id} sent auth request with no name.")
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, {"type": "auth_failed", "reason": "No name provided"}),
                self.asyncio_loop
            )
            return

        if not password:
            self.logger.warning(f"Client {client_id} sent auth request with no password.")
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, {"type": "auth_failed", "reason": "No password provided"}),
                self.asyncio_loop
            )
            return

        # Check if account exists
        existing_account = self.db.get_player_by_name(player_name)

        if existing_account:
            # Account exists - verify password
            if not self.db.verify_player_password_by_name(player_name, password):
                self.logger.warning(f"Wrong password for account '{player_name}' from client {client_id}")
                asyncio.run_coroutine_threadsafe(
                    self.send_to_client(client_id, {"type": "auth_failed", "reason": "wrong_password"}),
                    self.asyncio_loop
                )
                return

            self.logger.info(f"Account '{player_name}' authenticated (Client #{client_id})")
        else:
            # Account does not exist - create new
            account_uuid = str(uuid_module.uuid4())
            success = self.db.create_player(account_uuid, player_name, password)
            if not success:
                self.logger.error(f"Failed to create account '{player_name}'")
                asyncio.run_coroutine_threadsafe(
                    self.send_to_client(client_id, {"type": "auth_failed", "reason": "Failed to create account"}),
                    self.asyncio_loop
                )
                return
            self.logger.info(f"New account '{player_name}' created (Client #{client_id})")

        # Check that name is not already in use by another connected player
        for pid, p in self.world.players.items():
            if p.name == player_name and pid != client_id:
                self.logger.warning(f"Name '{player_name}' already in use by client {pid}")
                asyncio.run_coroutine_threadsafe(
                    self.send_to_client(client_id, {"type": "auth_failed", "reason": "Name already in use"}),
                    self.asyncio_loop
                )
                return

        # Add player to the world
        player = self.world.add_player(client_id, player_name)
        self.logger.info(f"Player '{player_name}' (Client #{client_id}) entered the game world")

        # Register client in interest manager
        self.interest_manager.register_client(client_id)
        pos = player.get_state()["pos"] if player else [0, 0, 0]
        self.interest_manager.update_client_position(client_id, pos[0], pos[1], pos[2])

        # Notify plugins about player join
        self.event_manager.post("player_joined", {"uuid": client_id, "name": player_name})

        # Send welcome message
        other_players_state = {
            pid: p.get_state()
            for pid, p in self.world.players.items()
            if pid != client_id
        }

        welcome_data = {
            "type": "welcome",
            "id": client_id,
            "pos": pos,
            "players": other_players_state
        }
        asyncio.run_coroutine_threadsafe(
            self.send_to_client(client_id, welcome_data), self.asyncio_loop
        )

        # Notify other players about the new player
        join_data = {
            "type": "player_joined",
            "id": client_id,
            "player_info": player.get_state() if player else {"name": player_name}
        }
        asyncio.run_coroutine_threadsafe(
            self.broadcast(join_data, exclude_ids=[client_id]), self.asyncio_loop
        )

    def handle_chat_send(self, event_data: dict):
        """
        Handles chat_send_to_clients event from chat plugin.
        event_data = {
            "data": broadcast_data,
            "recipients": list of client_ids or None for all
        }
        """
        broadcast_data = event_data.get("data", {})
        recipients = event_data.get("recipients")

        if recipients is None:
            # Send to all clients
            asyncio.run_coroutine_threadsafe(
                self.broadcast(broadcast_data), self.asyncio_loop
            )
        else:
            # Send only to specific clients
            asyncio.run_coroutine_threadsafe(
                self.send_to_clients(broadcast_data, recipients), self.asyncio_loop
            )

    def handle_stats_send(self, event_data: dict):
        """
        Handles stats_send_to_client event from stats plugin.
        event_data = {
            "client_id": client_id,
            "data": stats_data
        }
        """
        client_id = event_data.get("client_id")
        stats_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, stats_data), self.asyncio_loop
            )

    def handle_world_config_send(self, event_data: dict):
        """
        Handles world_config_send_to_client event from world_config plugin.
        event_data = {
            "client_id": client_id,
            "data": world_config_data
        }
        """
        client_id = event_data.get("client_id")
        config_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, config_data), self.asyncio_loop
            )

    def handle_inventory_send(self, event_data: dict):
        """
        Handles inventory_send_to_client event from inventory plugin.
        event_data = {
            "client_id": client_id,
            "data": inventory_data
        }
        """
        client_id = event_data.get("client_id")
        inventory_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, inventory_data), self.asyncio_loop
            )

    def handle_equipment_send(self, event_data: dict):
        """
        Handles equipment_send_to_client event from equipment plugin.
        event_data = {
            "client_id": client_id,
            "data": equipment_data
        }
        """
        client_id = event_data.get("client_id")
        equipment_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, equipment_data), self.asyncio_loop
            )

    def handle_system_message(self, event_data: dict):
        """
        Отправляет системное сообщение клиенту через чат.
        event_data = {
            "client_id": client_id,
            "message": str
        }
        """
        client_id = event_data.get("client_id")
        message = event_data.get("message", "")

        if client_id is not None and message:
            chat_data = {
                "type": "chat_broadcast",
                "chat_type": "system",
                "from_name": "Система",
                "message": message,
            }
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, chat_data), self.asyncio_loop
            )

    def handle_send_to_client(self, event_data: dict):
        """
        Generic handler to send a message to a specific client.
        event_data = {
            "client_id": client_id,
            "data": message_data
        }
        """
        client_id = event_data.get("client_id")
        message_data = event_data.get("data", {})

        if client_id is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_to_client(client_id, message_data), self.asyncio_loop
            )

    # =========================================================================
    # Inspect System
    # =========================================================================

    def _handle_inspect_request(self, client_id: int, data: dict):
        """Handle inspect_request from a client — look up entity and send back name+description."""
        entity_id = data.get("entity_id", "")
        if not entity_id:
            return

        name = "Неизвестный"
        description = ""

        # Check if it's a player
        try:
            target_client_id = int(entity_id)
            if target_client_id in self.world.players:
                name = self._resolve_player_name_for_inspect(client_id, target_client_id)
                asyncio.run_coroutine_threadsafe(
                    self.send_to_client(client_id, {
                        "type": "inspect_result",
                        "entity_id": entity_id,
                        "name": name,
                        "description": description,
                    }),
                    self.asyncio_loop
                )
                return
        except (ValueError, TypeError):
            pass

        # Check if it's an NPC
        if self.npc_manager:
            for npc in self.npc_manager.get_npc_states():
                if npc.get("entity_id") == entity_id:
                    name = npc.get("display_name", npc.get("template_id", "NPC"))
                    description = npc.get("description", "")
                    break

        asyncio.run_coroutine_threadsafe(
            self.send_to_client(client_id, {
                "type": "inspect_result",
                "entity_id": entity_id,
                "name": name,
                "description": description,
            }),
            self.asyncio_loop
        )

    def _resolve_player_name_for_inspect(self, viewer_client_id: int, target_client_id: int) -> str:
        """Resolve player name for inspect."""
        player = self.world.players.get(target_client_id)
        return player.name if player else "Unknown"

    async def send_to_clients(self, data, client_ids):
        """Sends a message to specific clients."""
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))

        for client_id in client_ids:
            writer = self.clients.get(client_id)
            if writer and not writer.is_closing():
                try:
                    writer.write(header + payload)
                    await writer.drain()
                except Exception as e:
                    self.logger.error(f"Error sending to client {client_id}: {e}")

    def handle_disconnect(self, client_id):
        self.logger.info(f"Client #{client_id} processing disconnection.")
        if client_id in self.clients:
            del self.clients[client_id]
        self.client_addresses.pop(client_id, None)
        self.noclip_clients.discard(client_id)

        # Unregister from interest manager
        self.interest_manager.unregister_client(client_id)

        # Notify plugins about player leave before removing
        self.event_manager.post("player_left", {"uuid": client_id})

        player_id = self.world.remove_player(client_id)
        if player_id is not None:
            leave_data = {"type": "player_left", "id": player_id}
            asyncio.run_coroutine_threadsafe(self.broadcast(leave_data), self.asyncio_loop)

    async def handle_connection(self, reader, writer):
        self.client_id_counter += 1
        client_id = self.client_id_counter
        addr = writer.get_extra_info('peername')
        client_ip = addr[0] if addr else "unknown"

        # Check ban before accepting
        if client_ip in self.banned_ips:
            self.logger.info(f"Rejected banned IP {client_ip}")
            try:
                payload = json.dumps({"type": "auth_failed", "reason": "You are banned"}).encode("utf-8")
                header = struct.pack("!I", len(payload))
                writer.write(header + payload)
                await writer.drain()
            except Exception:
                pass
            writer.close()
            return

        self.clients[client_id] = writer
        self.client_addresses[client_id] = client_ip
        self.logger.info(f"Client #{client_id} connected from {addr}.")

        try:
            while True:
                header = await reader.readexactly(4)
                msg_len = struct.unpack("!I", header)[0]
                payload = await reader.readexactly(msg_len)
                data = json.loads(payload.decode("utf-8"))
                # Add to a queue to be processed in the main thread
                self.message_queue.append((client_id, data))
        except (asyncio.IncompleteReadError, ConnectionResetError, struct.error):
            # Pass to main thread to handle cleanup
            self.message_queue.append((client_id, {"type": "internal_disconnect"}))
        finally:
            # Final cleanup in case the connection is force-closed
             if client_id in self.clients:
                self.message_queue.append((client_id, {"type": "internal_disconnect"}))

    async def broadcast(self, data, exclude_ids=None):
        if exclude_ids is None:
            exclude_ids = []
        
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))
        
        for client_id, writer in self.clients.items():
            if client_id not in exclude_ids:
                if writer.is_closing():
                    continue
                try:
                    writer.write(header + payload)
                    await writer.drain()
                except Exception as e:
                    self.logger.error(f"Error broadcasting to client {client_id}: {e}")

    async def send_to_client(self, client_id, data):
        writer = self.clients.get(client_id)
        if writer and not writer.is_closing():
            payload = json.dumps(data).encode("utf-8")
            header = struct.pack("!I", len(payload))
            try:
                writer.write(header + payload)
                await writer.drain()
            except Exception as e:
                self.logger.error(f"Error sending to client {client_id}: {e}")

    async def start_server_async(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try:
            ssl_context.load_cert_chain('certs/cert.pem', 'certs/key.pem')
            self.logger.info("SSL context loaded.")
        except FileNotFoundError:
            self.logger.critical("Certificate files not found! Server will not start.")
            self.userExit()
            return
            
        server = await asyncio.start_server(
            self.handle_connection, self.host, self.port, ssl=ssl_context
        )
        
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        self.logger.info(f'Serving on {addrs}')

        # This will run until the server is closed
        await server.serve_forever()

    def run(self):
        # Start the asyncio server coroutine
        self.asyncio_loop.create_task(self.start_server_async())
        # This will start Panda3D's internal loop
        super().run()
        self.logger.info("Server has shut down.")