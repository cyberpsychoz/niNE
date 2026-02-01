"""
Интеграционный тест боевой системы с экипировкой.

Проверяет что TurnManager корректно использует:
- Экипированное оружие игрока
- Weapon.get_attack_modifier() для правильного STR/DEX
- Weapon.DAMAGE_DICE для урона
- Weapon.RANGE для проверки дальности
- Class proficiency с оружием
"""

import sys
import logging
from typing import Dict, Any
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WEAPON_INTEGRATION_TEST")


@dataclass
class MockWeapon:
    """Mock оружия для тестирования."""
    CLASS_ID: str = "longsword"
    DAMAGE_DICE: str = "1d8"
    FINESSE: bool = False
    REACH: bool = False
    THROWN: bool = False
    is_ranged: bool = False
    required_proficiency: str = "martial_weapons"

    class RANGE:
        normal = 0
        long = 0

    def get_attack_modifier(self, str_mod: int, dex_mod: int) -> int:
        """Правильно выбирает STR или DEX."""
        if self.is_ranged:
            return dex_mod
        elif self.FINESSE:
            return max(str_mod, dex_mod)
        elif self.THROWN:
            return str_mod
        else:
            return str_mod


@dataclass
class MockFinesseWeapon(MockWeapon):
    """Finesse weapon (rapier, dagger)."""
    CLASS_ID: str = "rapier"
    DAMAGE_DICE: str = "1d8"
    FINESSE: bool = True
    required_proficiency: str = "martial_weapons"


@dataclass
class MockRangedWeapon(MockWeapon):
    """Ranged weapon (shortbow)."""
    CLASS_ID: str = "shortbow"
    DAMAGE_DICE: str = "1d6"
    is_ranged: bool = True
    required_proficiency: str = "simple_weapons"

    class RANGE:
        normal = 80
        long = 160


@dataclass
class MockReachWeapon(MockWeapon):
    """Reach weapon (glaive)."""
    CLASS_ID: str = "glaive"
    DAMAGE_DICE: str = "1d10"
    REACH: bool = True
    required_proficiency: str = "martial_weapons"


class MockEquipmentModule:
    """Mock EquipmentServerModule."""

    def __init__(self):
        self.equipped_weapons: Dict[int, MockWeapon] = {}

    def get_main_weapon(self, client_id: int):
        """Получить экипированное оружие."""
        return self.equipped_weapons.get(client_id)


class MockDnDModule:
    """Mock DnD characters module."""

    def __init__(self):
        self.active_characters: Dict[int, str] = {}
        self.characters: Dict[str, dict] = {}

    def setup_character(self, client_id: int, char_uuid: str, char_data: dict):
        """Setup test character."""
        self.active_characters[client_id] = char_uuid
        self.characters[char_uuid] = char_data


class MockDatabase:
    """Mock database."""

    def __init__(self, dnd_module: MockDnDModule):
        self.dnd_module = dnd_module

    def get_character(self, char_uuid: str) -> dict:
        """Get character by UUID."""
        return self.dnd_module.characters.get(char_uuid, {})


class MockApp:
    """Mock application."""

    def __init__(self):
        self.dnd_module = MockDnDModule()
        self.equipment_module = MockEquipmentModule()
        self.db = MockDatabase(self.dnd_module)
        self.plugin_manager = MockPluginManager(self.dnd_module)


class MockPluginManager:
    """Mock plugin manager."""

    def __init__(self, dnd_module: MockDnDModule):
        self.dnd_module = dnd_module

    def get_plugin(self, plugin_name: str):
        """Get mock plugin."""
        if plugin_name == "nine.dnd":
            return MockPlugin([self.dnd_module])
        elif plugin_name == "nine.inventory":
            return None  # Будет получен через property
        return None


class MockPlugin:
    """Mock plugin."""

    def __init__(self, modules):
        self.modules = modules


class MockEventManager:
    """Mock event manager."""

    def subscribe(self, event_name: str, handler):
        pass

    def unsubscribe(self, event_name: str, handler):
        pass

    def post(self, event_name: str, data: dict):
        pass


class MockContext:
    """Mock plugin context."""

    def __init__(self, app: MockApp):
        self.app = app
        self.logger = logger
        self.event_manager = MockEventManager()


class TurnManagerWeaponTest:
    """Тестирование интеграции TurnManager с системой оружия."""

    def __init__(self):
        self.app = MockApp()
        self.context = MockContext(self.app)

        # Import TurnManager
        from nine.plugins.combat.sv_turn_manager import TurnManager
        self.turn_manager = TurnManager(self.context)

        # Mock equipment_module property
        self.turn_manager._equipment_module = self.app.equipment_module

        logger.info("✅ TurnManager initialized with mock equipment")

    def test_melee_weapon_str(self):
        """Тест: Melee оружие использует STR."""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: Melee Weapon (STR Modifier)")
        logger.info("="*70)

        client_id = 1
        char_uuid = "char-fighter-123"

        # Setup character: STR 16 (+3), DEX 12 (+1), proficiency +2
        char = {
            "uuid": char_uuid,
            "name": "Fighter",
            "strength": 16,
            "dexterity": 12,
            "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons", "martial_weapons"],
        }

        self.app.dnd_module.setup_character(client_id, char_uuid, char)

        # Equip longsword (1d8, martial, not finesse)
        self.app.equipment_module.equipped_weapons[client_id] = MockWeapon()

        # Get combat data
        data = self.turn_manager._get_player_combat_data(client_id)

        logger.info(f"Character stats: STR 16 (+3), DEX 12 (+1), Prof +2")
        logger.info(f"Equipped weapon: Longsword (1d8, martial, not finesse)")
        logger.info(f"Has proficiency: martial_weapons ✓")
        logger.info(f"Expected attack_bonus: STR(+3) + Prof(+2) = +5")
        logger.info(f"Expected damage_dice: 1d8+3")
        logger.info(f"Actual attack_bonus: {data.get('attack_bonus')}")
        logger.info(f"Actual damage_dice: {data.get('damage_dice')}")

        assert data is not None, "Combat data should not be None"
        assert data["attack_bonus"] == 5, f"Expected +5 (STR+Prof), got {data['attack_bonus']}"
        assert data["damage_dice"] == "1d8+3", f"Expected 1d8+3, got {data['damage_dice']}"
        assert data["weapon_range"] == 5.0, f"Expected 5.0 (melee), got {data['weapon_range']}"
        assert data["has_proficiency"] == True, "Fighter should have martial weapon proficiency"

        logger.info("✅ PASS: Melee weapon correctly uses STR + proficiency")

    def test_finesse_weapon_dex(self):
        """Тест: Finesse оружие использует лучший из STR/DEX."""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: Finesse Weapon (DEX Modifier)")
        logger.info("="*70)

        client_id = 2
        char_uuid = "char-rogue-456"

        # Setup character: STR 10 (+0), DEX 18 (+4), proficiency +2
        char = {
            "uuid": char_uuid,
            "name": "Rogue",
            "strength": 10,
            "dexterity": 18,
            "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons", "martial_weapons"],
        }

        self.app.dnd_module.setup_character(client_id, char_uuid, char)

        # Equip rapier (1d8, finesse)
        self.app.equipment_module.equipped_weapons[client_id] = MockFinesseWeapon()

        # Get combat data
        data = self.turn_manager._get_player_combat_data(client_id)

        logger.info(f"Character stats: STR 10 (+0), DEX 18 (+4), Prof +2")
        logger.info(f"Equipped weapon: Rapier (1d8, finesse)")
        logger.info(f"Has proficiency: martial_weapons ✓")
        logger.info(f"Expected attack_bonus: max(STR+0, DEX+4) + Prof(+2) = +6")
        logger.info(f"Expected damage_dice: 1d8+4 (uses DEX for finesse)")
        logger.info(f"Actual attack_bonus: {data.get('attack_bonus')}")
        logger.info(f"Actual damage_dice: {data.get('damage_dice')}")

        assert data is not None, "Combat data should not be None"
        assert data["attack_bonus"] == 6, f"Expected +6 (DEX+Prof), got {data['attack_bonus']}"
        assert data["damage_dice"] == "1d8+4", f"Expected 1d8+4, got {data['damage_dice']}"
        assert data["weapon_range"] == 5.0, f"Expected 5.0 (melee finesse), got {data['weapon_range']}"

        logger.info("✅ PASS: Finesse weapon correctly uses DEX (better than STR)")

    def test_ranged_weapon(self):
        """Тест: Ranged оружие использует DEX."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: Ranged Weapon (DEX Only)")
        logger.info("="*70)

        client_id = 3
        char_uuid = "char-ranger-789"

        # Setup character: STR 14 (+2), DEX 16 (+3), proficiency +2
        char = {
            "uuid": char_uuid,
            "name": "Ranger",
            "strength": 14,
            "dexterity": 16,
            "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons", "martial_weapons"],
        }

        self.app.dnd_module.setup_character(client_id, char_uuid, char)

        # Equip shortbow (1d6, ranged 80/160)
        self.app.equipment_module.equipped_weapons[client_id] = MockRangedWeapon()

        # Get combat data
        data = self.turn_manager._get_player_combat_data(client_id)

        logger.info(f"Character stats: STR 14 (+2), DEX 16 (+3), Prof +2")
        logger.info(f"Equipped weapon: Shortbow (1d6, range 80/160)")
        logger.info(f"Has proficiency: simple_weapons ✓")
        logger.info(f"Expected attack_bonus: DEX(+3) + Prof(+2) = +5 (ignores STR)")
        logger.info(f"Expected damage_dice: 1d6+3")
        logger.info(f"Expected weapon_range: 80.0 (normal)")
        logger.info(f"Actual attack_bonus: {data.get('attack_bonus')}")
        logger.info(f"Actual damage_dice: {data.get('damage_dice')}")
        logger.info(f"Actual weapon_range: {data.get('weapon_range')}")

        assert data is not None, "Combat data should not be None"
        assert data["attack_bonus"] == 5, f"Expected +5 (DEX+Prof), got {data['attack_bonus']}"
        assert data["damage_dice"] == "1d6+3", f"Expected 1d6+3, got {data['damage_dice']}"
        assert data["weapon_range"] == 80.0, f"Expected 80.0 (shortbow range), got {data['weapon_range']}"
        assert data["is_ranged"] == True, "Should be marked as ranged weapon"

        logger.info("✅ PASS: Ranged weapon correctly uses DEX and weapon range")

    def test_reach_weapon(self):
        """Тест: Reach оружие имеет дальность 10 футов."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: Reach Weapon (10 feet)")
        logger.info("="*70)

        client_id = 4
        char_uuid = "char-fighter-reach"

        # Setup character
        char = {
            "uuid": char_uuid,
            "name": "Fighter",
            "strength": 16,
            "dexterity": 10,
            "proficiency_bonus": 2,
            "proficiencies": ["martial_weapons"],
        }

        self.app.dnd_module.setup_character(client_id, char_uuid, char)

        # Equip glaive (1d10, reach)
        self.app.equipment_module.equipped_weapons[client_id] = MockReachWeapon()

        # Get combat data
        data = self.turn_manager._get_player_combat_data(client_id)

        logger.info(f"Equipped weapon: Glaive (1d10, reach)")
        logger.info(f"Expected weapon_range: 10.0 (reach weapons)")
        logger.info(f"Actual weapon_range: {data.get('weapon_range')}")

        assert data is not None, "Combat data should not be None"
        assert data["weapon_range"] == 10.0, f"Expected 10.0 (reach), got {data['weapon_range']}"
        assert data["damage_dice"] == "1d10+3", f"Expected 1d10+3, got {data['damage_dice']}"

        logger.info("✅ PASS: Reach weapon correctly has 10 feet range")

    def test_no_proficiency(self):
        """Тест: Без proficiency не добавляется бонус."""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: No Proficiency (No Prof Bonus)")
        logger.info("="*70)

        client_id = 5
        char_uuid = "char-wizard-sword"

        # Setup character: Wizard without martial weapon proficiency
        char = {
            "uuid": char_uuid,
            "name": "Wizard",
            "strength": 12,
            "dexterity": 14,
            "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons"],  # No martial_weapons!
        }

        self.app.dnd_module.setup_character(client_id, char_uuid, char)

        # Equip longsword (martial - no proficiency!)
        self.app.equipment_module.equipped_weapons[client_id] = MockWeapon()

        # Get combat data
        data = self.turn_manager._get_player_combat_data(client_id)

        logger.info(f"Character: Wizard (no martial weapon proficiency)")
        logger.info(f"Equipped weapon: Longsword (martial)")
        logger.info(f"Expected attack_bonus: STR(+1) only (no prof bonus)")
        logger.info(f"Actual attack_bonus: {data.get('attack_bonus')}")
        logger.info(f"Has proficiency: {data.get('has_proficiency')}")

        assert data is not None, "Combat data should not be None"
        assert data["attack_bonus"] == 1, f"Expected +1 (STR only), got {data['attack_bonus']}"
        assert data["has_proficiency"] == False, "Wizard should not have martial weapon proficiency"

        logger.info("✅ PASS: No proficiency correctly omits proficiency bonus")

    def test_unarmed_strike(self):
        """Тест: Безоружная атака без экипированного оружия."""
        logger.info("\n" + "="*70)
        logger.info("TEST 6: Unarmed Strike (No Weapon Equipped)")
        logger.info("="*70)

        client_id = 6
        char_uuid = "char-monk-unarmed"

        # Setup character
        char = {
            "uuid": char_uuid,
            "name": "Monk",
            "strength": 14,
            "dexterity": 16,
            "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons"],
        }

        self.app.dnd_module.setup_character(client_id, char_uuid, char)

        # No weapon equipped!
        # self.app.equipment_module.equipped_weapons[client_id] = None

        # Get combat data
        data = self.turn_manager._get_player_combat_data(client_id)

        logger.info(f"Character: Monk (no weapon equipped)")
        logger.info(f"Expected: Unarmed strike (1 + STR damage)")
        logger.info(f"STR mod: +2, so damage = 1 + 2 = 3")
        logger.info(f"Expected attack_bonus: STR(+2) + Prof(+2) = +4")
        logger.info(f"Expected damage_dice: 1+2 (unarmed)")
        logger.info(f"Actual attack_bonus: {data.get('attack_bonus')}")
        logger.info(f"Actual damage_dice: {data.get('damage_dice')}")

        assert data is not None, "Combat data should not be None"
        assert data["attack_bonus"] == 4, f"Expected +4 (STR+Prof), got {data['attack_bonus']}"
        assert data["damage_dice"] == "1+2", f"Expected 1+2 (unarmed), got {data['damage_dice']}"
        assert data["weapon_range"] == 5.0, f"Expected 5.0 (unarmed), got {data['weapon_range']}"

        logger.info("✅ PASS: Unarmed strike correctly calculated")

    def run_all_tests(self):
        """Запуск всех тестов."""
        logger.info("\n" + "="*70)
        logger.info("WEAPON INTEGRATION TESTS")
        logger.info("="*70)
        logger.info("Testing TurnManager integration with equipment system...")
        logger.info("")

        tests = [
            self.test_melee_weapon_str,
            self.test_finesse_weapon_dex,
            self.test_ranged_weapon,
            self.test_reach_weapon,
            self.test_no_proficiency,
            self.test_unarmed_strike,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                test()
                passed += 1
            except AssertionError as e:
                logger.error(f"❌ FAIL: {test.__name__}")
                logger.error(f"   {str(e)}")
                failed += 1
            except Exception as e:
                logger.error(f"💥 ERROR: {test.__name__}")
                logger.error(f"   {str(e)}")
                failed += 1

        logger.info("\n" + "="*70)
        logger.info("WEAPON INTEGRATION TEST RESULTS")
        logger.info("="*70)
        logger.info(f"Tests Run: {passed + failed}")
        logger.info(f"✓ Passed: {passed}")
        logger.info(f"✗ Failed: {failed}")
        logger.info("")

        if failed == 0:
            logger.info("✅ ALL TESTS PASSED - weapon integration working correctly!")
            logger.info("")
            logger.info("VERIFIED:")
            logger.info("  ✓ Melee weapons use STR modifier")
            logger.info("  ✓ Finesse weapons use best of STR/DEX")
            logger.info("  ✓ Ranged weapons use DEX modifier")
            logger.info("  ✓ Reach weapons have 10 feet range")
            logger.info("  ✓ Proficiency bonus applied correctly")
            logger.info("  ✓ Unarmed strike works without weapon")
            logger.info("="*70)
        else:
            logger.error("❌ SOME TESTS FAILED - check implementation!")
            sys.exit(1)


if __name__ == "__main__":
    tester = TurnManagerWeaponTest()
    tester.run_all_tests()
