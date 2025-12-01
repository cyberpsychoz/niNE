# niNE Development Plan

This document outlines the recent architectural changes and provides a roadmap for turning the project into a full-fledged "Roleplay Constructor."

---

## 1. Recent Architectural Overhaul (Completed)

The project has recently undergone a significant refactoring to improve stability, maintainability, and architectural clarity.

-   **Client Unification:**
    -   The redundant `dev_client.py` and `client.py` were merged. The main `client.py` now supports a `--dev` flag for development, which enables client-side movement prediction and developer authentication.
    -   A dedicated, auto-connecting `dev_client.py` was re-created for rapid testing, using the same underlying `GameClient` logic but without a main menu.

-   **Decoupled Configuration:**
    -   Clients no longer read `server_config.json`. This enforces a strict separation of concerns, where clients are unaware of server-specific settings.
    -   Connection details (host, port) are now passed as command-line arguments or through the UI, with sensible defaults.

-   **Centralized Networking:**
    -   All low-level networking logic (sending and receiving length-prefixed JSON messages over SSL) has been centralized into the `nine.core.network` module.
    -   All clients (`client.py`, `dev_client.py`, `dev_cli_client.py`) now use this shared module, eliminating duplicated code.

-   **Improved Server Authentication:**
    -   The server now has a dedicated `dev_auth` flow. When `allow_dev_client` is `true` in `server_config.json`, developers can connect multiple clients without being blocked by unique name checks.

---

## 2. Roadmap: The Roleplay Constructor

To transform the project into a true "Roleplay Constructor," we need to build systems that allow for deep customization of characters, worlds, and stories. The following is a proposed roadmap.

### Phase 1: Foundational Systems

#### A. Advanced Character Persistence
-   **Goal:** Move beyond saving just the player's name and position. We need to store detailed character data.
-   **Implementation:**
    1.  **Database Schema:** Extend the SQLite database (`nine.db`) with new tables: `characters`, `character_stats`, `character_appearance`, etc.
    2.  **Player Class:** Modify the `Player` class in `nine/core/world.py` to hold complex data (e.g., stats, level, health, appearance attributes).
    3.  **Data Loading/Saving:** Enhance `DatabaseManager` to load this data on `auth`/`dev_auth` and save it periodically or on `disconnect`. The current implementation of saving on disconnect is a good start, but periodic saving would prevent data loss on server crash.
    4.  **Character Selection:** The `welcome` message should be preceded by a character selection step if an account has multiple characters. This will require a new UI screen.

#### B. World & Zone Management
-   **Goal:** The server needs to be able to manage multiple zones or areas (e.g., a city, a dungeon) and persist the state of objects within them.
-   **Implementation:**
    1.  **Database Schema:** Add tables for `zones`, `world_objects` (with position, rotation, scale, type), and `object_properties`.
    2.  **World Class:** Refactor `GameWorld` to manage a dictionary of `Zone` objects. Each `Zone` would contain its own set of objects and players.
    3.  **Zone Streaming:** Implement logic to load/unload zones as players move between them. The server would only send `world_state` updates for the player's current zone.

### Phase 2: Content Creation Tools

#### A. In-Game World Editor ("Game Master Mode")
-   **Goal:** Allow users with special permissions to create and modify the world in real-time.
-   **Implementation:**
    1.  **Permissions System:** Add a `role` field to the `accounts` or `characters` table in the database (e.g., `player`, `moderator`, `admin`).
    2.  **GM Client Mode:** Create a new client mode (e.g., `client.py --gm`) that enables editor-specific UI and controls.
    3.  **New Network Messages:**
        -   `gm_spawn_object(object_id, pos, rot)`
        -   `gm_delete_object(world_object_id)`
        -   `gm_set_object_property(world_object_id, key, value)`
    4.  **Server Logic:** The server would validate that the client has 'admin' permissions before processing these messages and updating the database.
    5.  **UI:** The GM client would have a simple UI for selecting objects to spawn and modifying their properties.

#### B. Data-Driven Quest & Dialogue System
-   **Goal:** Create a system for writing quests and NPC dialogues that doesn't require writing new Python code for each one.
-   **Implementation:**
    1.  **Quest/Dialogue Files:** Define a format (JSON or YAML) for quest and dialogue files. These files would live in a new `content` directory.
        -   A quest file might define objectives (e.g., `FETCH_ITEM`, `KILL_MONSTER`, `GO_TO_AREA`), rewards, and links to dialogue.
        -   A dialogue file would define a tree of NPC text, player responses, and associated events (e.g., `start_quest`, `give_item`).
    2.  **Server-Side Engines:**
        -   **Quest Engine:** A new class on the server that loads all quest files, tracks player progress in the database (`player_quests` table), and checks for objective completion.
        -   **Dialogue Engine:** A class that processes dialogue files and sends `show_dialogue_ui` messages to the client.
    3.  **NPCs:** Create a basic `NPC` class. In the database, an NPC could have a `dialogue_id` that links it to a specific dialogue file.

### Phase 3: Polish and Expansion

#### A. Advanced Character Customization UI
-   **Goal:** A full in-game UI for creating a character's appearance.
-   **Implementation:**
    1.  **Modular Characters:** The player model (`player.egg`) would need to be broken into modular parts (head, torso, legs) or support morph targets.
    2.  **UI Screen:** A new UI screen with sliders and color pickers for modifying appearance.
    3.  **Data Flow:** The UI would generate an appearance data structure (e.g., `{"hair_style": 3, "hair_color": [0.8, 0.2, 0.1]}`), which would be saved in the database. When a player enters the world, this data is sent to all clients, who then apply it to the character model.

#### B. Skills and Abilities
-   **Goal:** Implement a basic skill system.
-   **Implementation:**
    1.  **Data-Driven Skills:** Define skills in JSON files (e.g., `{"id": "fireball", "damage": 10, "mana_cost": 5}`).
    2.  **Server Logic:** The server validates if a player can use a skill and calculates its effect on the target.
    3.  **Client-Side Feedback:** The client would need to play animations and visual effects when a skill is used. This is a perfect use case for the `EventManager` (`skill_used_event`, `damage_taken_event`).