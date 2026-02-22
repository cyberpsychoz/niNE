# niNE - Feature Summary

Multiplayer 3D game engine with D&D 5e game mode. Built with Panda3D (Python).

---

## Core Engine

- **Multiplayer** — client-server architecture, async networking, SSL/TLS encryption
- **Plugin system** — modular architecture, hot-loadable plugins with event-driven communication
- **ECS** — dual Entity system: static entities for items/inventory, dynamic ECS for NPCs/players
- **Audio** — AudioManager with playlists (BGM, ambient, SFX), crossfade, footstep system
- **Camera** — first-person / third-person modes, configurable FOV, mouse inversion
- **PostFX** — PS1-style pixelization shader (optional plugin)
- **Database** — SQLite with migrations, accounts, characters, factions
- **Config** — JSON-based settings with live preview in settings menu

## D&D 5e Game Mode

### Character System
- 8-step character creation wizard (name, race, class, stats, skills, background, faction, confirmation)
- 6 races with ability bonuses and racial features
- 12 classes with full 1st-level abilities, proficiencies, and starting equipment
- 10 backgrounds with skill proficiencies, equipment, and gold
- Point Buy / Standard Array / 4d6 stat generation
- 4 factions with unique spawn points
- Character sheet with 8 tabs: Inventory, Equipment, Description, Stats, Skills, Abilities, Quests, Spells

### Inventory & Equipment
- Entity-based item system (112+ registered items)
- Full D&D 5e PHB weapon set (30 weapons: simple/martial, melee/ranged)
- Full armor set (14 armors: light/medium/heavy + shields)
- 20+ magic accessories (rings, amulets, cloaks, boots, etc.)
- 35 mundane items (tools, clothing, quest items)
- Starting equipment auto-granted on character creation (class + background + gold)
- Equipment slots: head, chest, hands, legs, feet, weapon, off_hand, rings, neck, back, waist
- Stackable items, drag & drop

### Combat (Baldur's Gate 3 style)
- Turn-based with initiative rolls (d20 + DEX)
- Action economy: action, bonus action, movement, reaction
- D&D 5e dice system (any NdM+X rolls)
- Melee/ranged attacks with to-hit rolls vs AC
- 35 spells with spell slots, concentration, and school system
- D&D 5e conditions (Blinded, Paralyzed, Stunned, etc.)
- Short/Long rest with Hit Dice recovery
- Target selector, initiative display, action bar UI
- Spectator mode for non-combatants
- Dual combat: simulated NPC-vs-NPC + turn-based transition when player joins

### NPC System
- ECS-based AI with LOD (Level of Detail)
- Behaviors: idle, patrol, wander, hostile, pursuit, flee
- Needs-based AI: hunger, fatigue, social needs drive behavior
- Personality traits modify AI decisions
- Daily schedules (work, eat, sleep, socialize)
- Faction system with friend/foe detection
- Shared Mixamo animation pipeline
- Delta compression for network sync

### DM Panel (F2)
- Tabs: Players, Combat, Spawn, Audio, World
- Spawn NPCs with templates
- Control combat (start/end, manage turns)
- Teleport/heal/damage players
- Manage audio playlists
- Game time control (day/night cycle: 1 real minute = 1 game hour)

### Chat
- RP commands (/say, /yell, /whisper, /emote)
- Admin commands (/spawn, /startcombat, /endcombat, /charsetmodel, /charsetfaction)
- Help system with autocomplete

### Quest System
- Quest journal (J key)
- Objective types: kill, collect, talk, reach
- Quest tracking with progress indicators

## UI System

- **CEF** (recommended) — offscreen Chromium 131 via cef-capi-py, raw BGRA pixels, V8 bridge for JS-Python communication
- **Playwright** (legacy) — screenshot-based Chromium
- **DirectGUI** (fallback) — native Panda3D widgets
- HTML/CSS/JS overlay with medieval-themed design
- Local font serving (Cinzel, MedievalSharp)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Engine | Panda3D |
| Language | Python 3.12 |
| Networking | asyncio + SSL/TLS |
| Database | SQLite |
| UI | CEF (Chromium 131) |
| Audio | Panda3D AudioManager |
| 3D Models | BAM (Panda3D), Mixamo animations |
