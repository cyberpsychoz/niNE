# niNE Project Documentation

This document provides a technical overview of the niNE project architecture, key components, and data flow.

---

## Core Architecture

The project uses a hybrid architecture combining **Panda3D** for 3D rendering and its task manager with Python's **asyncio** for modern, high-performance networking.

-   **Panda3D's Task Manager** is used for the main game loop (`game_loop` on the server, `update_movement_task` on the client), physics simulation, and other frame-by-frame updates.
-   **Asyncio** is used for all network communication, allowing the server to handle many concurrent clients efficiently and enabling non-blocking network calls on the client.
-   The two systems are integrated via a special task (`poll_asyncio`) that runs the asyncio event loop for one iteration within the Panda3D game loop.

---

## Client-Server Communication

Communication is handled by a custom, SSL-encrypted, JSON-based protocol.

-   **Transport:** All communication occurs over a single TCP socket, secured with SSL/TLS. The server uses a self-signed certificate (`certs/cert.pem` and `certs/key.pem`) which the client must have to verify the connection.
-   **Messaging Protocol:** Messages are sent as JSON strings. To handle message framing (i.e., knowing where one message ends and the next begins), each JSON payload is prefixed with a 4-byte header containing the length of the payload, packed as an unsigned integer.
-   **Centralized Logic:** The core logic for sending and receiving these length-prefixed messages is centralized in the `nine.core.network` module, which is used by all clients.

---

## The Server (`GameServer`)

**File:** `nine/server/game_server.py`

The server is the authoritative source of truth for the game world. It manages game state, physics, and all client interactions.

-   **Responsibilities:**
    -   Accepting and managing client connections.
    -   Processing incoming messages (authentication, input, etc.).
    -   Running the main game loop (`game_loop`) at a fixed `tick_rate`.
    -   Simulating the physics world (`BulletWorld`).
    -   Broadcasting the world state to all clients.
-   **Authentication:**
    -   **`auth`:** Standard authentication for regular clients. The server prevents multiple clients from logging in with the same name.
    -   **`dev_auth`:** A special authentication path for development clients. If `allow_dev_client` is `true` in `server_config.json`, the server will bypass the unique name check, allowing multiple dev clients to connect for testing purposes.

---

## The Clients

### 1. Main Game Client (`client.py`)

This is the primary user-facing client.

-   **Class:** `GameClient`
-   **Functionality:**
    -   Presents a full user interface (main menu, login screen, settings, etc.) managed by the `UIManager`.
    -   In standard mode, it acts as a "dumb" client: it captures raw keyboard input (`w`, `a`, `s`, `d`) and sends it to the server via an `input` message. The server then simulates the movement and sends the new position back in the `world_state` broadcast.
    -   **Dev Mode:** Can be launched in a development mode using the `--dev` flag. In this mode, it behaves similarly to the `DevGameClient`.

### 2. Development Client (`dev_client.py`)

This is a separate, streamlined client for rapid development and testing.

-   **Class:** `DevGameClient`
-   **Functionality:**
    -   Has no main menu; it connects automatically to a specified host/port on launch.
    -   Always uses `dev_auth`.
    -   Uses **client-side prediction**. It calculates its own movement based on player input each frame and sends the resulting position to the server via a `move` message. This provides a smoother gameplay experience for the local player but makes the client authoritative over its own position. The server simply accepts this position and broadcasts it to other clients.

---

## Plugin System (`PluginManager`)

**File:** `nine/core/plugins.py`

The project features a powerful, event-driven plugin system that allows for modular and decoupled feature development.

-   **Discovery:** The `PluginManager` automatically discovers and loads Python files and packages from the `nine/plugins/` directory.
-   **Filtering:** Each plugin class can have a `plugin_type` attribute, which can be `'client'`, `'server'`, or `'common'`. The manager will only load plugins appropriate for the current environment (e.g., it won't load a `'client'` plugin on the server).
-   **Decoupling:** Plugins do not directly reference the main app or other components. Instead, they communicate using an `EventManager`.
    -   **Subscribing:** A plugin can `subscribe` to events (e.g., a network message type like `"chat_broadcast"`, or a UI event like `"escape_key_pressed"`).
    -   **Posting:** A plugin can `post` its own events to trigger actions in the core systems or other plugins (e.g., posting `"client_send_chat_message"` to make the client send a network packet).
-   **Example:** The `chat_ui.py` plugin listens for the `"chat_broadcast"` network event to display messages and posts a `"client_send_chat_message"` event when the user enters text.

---

## UI System (`UIManager`)

**File:** `nine/ui/manager.py`

The UI is managed by a central `UIManager` that acts as a state machine, controlling which screen is currently active.

-   **Base Component:** All UI screens (e.g., `MainMenu`, `LoginMenu`) inherit from `BaseUIComponent`, which ensures they have a consistent interface (`show`, `hide`, `destroy`) and that all DirectGUI elements are properly cleaned up to prevent memory leaks.
-   **Callbacks:** The `UIManager` is initialized with a dictionary of callbacks, which allows the UI components to trigger actions in the main client class (e.g., `attempt_login`, `exit_game`) without being directly coupled to it.

---

## Configuration

The project uses a clean separation between client and server configuration.

-   **`config.json`:** Contains client-side settings like nickname, resolution, and camera sensitivity. It is only read by the clients.
-   **`server_config.json`:** Contains server-side settings like host, port, tick rate, and the `allow_dev_client` flag. **This file should never be read by a client.** This separation was a key part of the recent architectural refactoring.
