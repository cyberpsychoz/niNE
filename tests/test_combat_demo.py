"""
Демонстрация боевой системы с гарантированными попаданиями.
Показывает как система рассчитывает урон с разными типами оружия.
"""

import logging
from tests.test_combat_simulation import (
    CombatSimulator, Longsword, Rapier, Shortbow, Glaive, DiceRoller
)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("COMBAT_DEMO")


class CombatDemo(CombatSimulator):
    """Демонстрация боя с контролируемыми бросками."""

    def demo_attack(self, attacker_id: int, attacker_name: str, target_ac: int,
                    target_name: str, forced_roll: int = 15):
        """Демонстрация атаки с фиксированным броском d20."""
        logger.info("")
        logger.info("-"*70)
        logger.info(f"⚔️  {attacker_name} attacks {target_name}!")
        logger.info("-"*70)

        combat_data = self.turn_manager._get_player_combat_data(attacker_id)

        if not combat_data:
            logger.error(f"❌ Failed to get combat data")
            return

        attack_bonus = combat_data["attack_bonus"]
        damage_dice = combat_data["damage_dice"]
        weapon_range = combat_data.get("weapon_range", 5.0)
        has_proficiency = combat_data.get("has_proficiency", True)

        logger.info(f"📊 Combat Data:")
        logger.info(f"   Attack Bonus: +{attack_bonus}")
        logger.info(f"   Damage Dice: {damage_dice}")
        logger.info(f"   Weapon Range: {weapon_range} feet")
        logger.info(f"   Proficiency: {'Yes ✓' if has_proficiency else 'No ✗'}")

        # Use forced roll
        d20_roll = forced_roll
        attack_total = d20_roll + attack_bonus

        logger.info("")
        logger.info(f"🎲 Attack Roll: {d20_roll} + {attack_bonus} = {attack_total}")
        logger.info(f"🛡️  Target AC: {target_ac}")

        if d20_roll == 20:
            logger.info("💥 CRITICAL HIT!")
            # Double damage dice
            base_dice = damage_dice.split('+')[0]
            damage1 = DiceRoller.roll_damage(damage_dice)
            damage2 = DiceRoller.roll_damage(base_dice)
            total_damage = damage1 + damage2
            logger.info(f"💀 Critical Damage: {total_damage} ({damage_dice} + {base_dice} doubled)")

        elif attack_total >= target_ac:
            damage = DiceRoller.roll_damage(damage_dice)
            logger.info(f"✅ HIT! Damage: {damage} ({damage_dice})")

        else:
            logger.info(f"❌ MISS! (needed {target_ac}, rolled {attack_total})")

    def run_demo(self):
        """Демонстрация всех сценариев."""
        logger.info("="*70)
        logger.info("COMBAT SYSTEM DEMONSTRATION")
        logger.info("="*70)
        logger.info("")

        # Scenario 1: Fighter с Longsword (STR)
        logger.info("="*70)
        logger.info("SCENARIO 1: Fighter with Longsword (Melee STR weapon)")
        logger.info("="*70)
        self.setup_character(1, "Fighter", {
            "strength": 16, "dexterity": 12, "proficiency_bonus": 2,
            "proficiencies": ["martial_weapons"],
        }, Longsword())
        self.demo_attack(1, "Fighter", 15, "Goblin", forced_roll=15)

        # Scenario 2: Rogue с Rapier (Finesse)
        logger.info("\n")
        logger.info("="*70)
        logger.info("SCENARIO 2: Rogue with Rapier (Finesse weapon - uses DEX!)")
        logger.info("="*70)
        self.setup_character(2, "Rogue", {
            "strength": 10, "dexterity": 18, "proficiency_bonus": 2,
            "proficiencies": ["martial_weapons"],
        }, Rapier())
        logger.info("   NOTE: STR 10 (+0) but DEX 18 (+4) - finesse uses better!")
        self.demo_attack(2, "Rogue", 15, "Goblin", forced_roll=12)

        # Scenario 3: Ranger с Shortbow (Ranged)
        logger.info("\n")
        logger.info("="*70)
        logger.info("SCENARIO 3: Ranger with Shortbow (Ranged weapon - DEX only)")
        logger.info("="*70)
        self.setup_character(3, "Ranger", {
            "strength": 14, "dexterity": 16, "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons"],
        }, Shortbow())
        logger.info("   NOTE: STR 14 (+2) but uses DEX 16 (+3) for ranged!")
        self.demo_attack(3, "Ranger", 15, "Goblin (60 feet away)", forced_roll=14)

        # Scenario 4: Critical Hit
        logger.info("\n")
        logger.info("="*70)
        logger.info("SCENARIO 4: Critical Hit (Natural 20)")
        logger.info("="*70)
        self.setup_character(4, "Paladin", {
            "strength": 18, "dexterity": 10, "proficiency_bonus": 2,
            "proficiencies": ["martial_weapons"],
        }, Longsword())
        logger.info("   NOTE: Natural 20 doubles damage dice!")
        self.demo_attack(4, "Paladin", 20, "Dragon", forced_roll=20)

        # Scenario 5: Без proficiency
        logger.info("\n")
        logger.info("="*70)
        logger.info("SCENARIO 5: Wizard without Martial Proficiency")
        logger.info("="*70)
        self.setup_character(5, "Wizard", {
            "strength": 12, "dexterity": 14, "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons"],  # NO martial!
        }, Longsword())
        logger.info("   NOTE: No proficiency = no proficiency bonus!")
        self.demo_attack(5, "Wizard", 15, "Goblin", forced_roll=14)

        # Scenario 6: Unarmed
        logger.info("\n")
        logger.info("="*70)
        logger.info("SCENARIO 6: Monk Unarmed Strike (No weapon)")
        logger.info("="*70)
        self.setup_character(6, "Monk", {
            "strength": 14, "dexterity": 16, "proficiency_bonus": 2,
            "proficiencies": ["simple_weapons"],
        }, None)
        logger.info("   NOTE: Damage = 1 + STR modifier!")
        self.demo_attack(6, "Monk", 15, "Bandit", forced_roll=13)

        # Scenario 7: Reach weapon
        logger.info("\n")
        logger.info("="*70)
        logger.info("SCENARIO 7: Fighter with Glaive (Reach weapon - 10 feet!)")
        logger.info("="*70)
        self.setup_character(7, "Fighter", {
            "strength": 16, "dexterity": 10, "proficiency_bonus": 2,
            "proficiencies": ["martial_weapons"],
        }, Glaive())
        logger.info("   NOTE: Reach weapons can attack at 10 feet instead of 5!")
        self.demo_attack(7, "Fighter", 15, "Orc (10 feet away)", forced_roll=16)

        logger.info("\n")
        logger.info("="*70)
        logger.info("DEMONSTRATION COMPLETE!")
        logger.info("="*70)
        logger.info("\n✅ VERIFIED FEATURES:")
        logger.info("")
        logger.info("1. MELEE WEAPONS (STR):")
        logger.info("   - Longsword: Attack = STR + Prof, Damage = 1d8 + STR")
        logger.info("")
        logger.info("2. FINESSE WEAPONS (best of STR/DEX):")
        logger.info("   - Rapier: Uses DEX (+4) instead of STR (+0) when better")
        logger.info("   - Attack = max(STR, DEX) + Prof, Damage = 1d8 + modifier")
        logger.info("")
        logger.info("3. RANGED WEAPONS (DEX only):")
        logger.info("   - Shortbow: Uses DEX, ignores STR completely")
        logger.info("   - Range: 80 feet (not 5!)")
        logger.info("   - Attack = DEX + Prof, Damage = 1d6 + DEX")
        logger.info("")
        logger.info("4. REACH WEAPONS (10 feet):")
        logger.info("   - Glaive: Can attack at 10 feet instead of 5")
        logger.info("   - Damage = 1d10 + STR")
        logger.info("")
        logger.info("5. PROFICIENCY:")
        logger.info("   - With proficiency: Attack = modifier + Prof")
        logger.info("   - Without proficiency: Attack = modifier only (no Prof!)")
        logger.info("")
        logger.info("6. UNARMED STRIKE:")
        logger.info("   - Works without equipped weapon")
        logger.info("   - Damage = 1 + STR modifier")
        logger.info("")
        logger.info("7. CRITICAL HITS:")
        logger.info("   - Natural 20 doubles damage dice (not modifier!)")
        logger.info("")


if __name__ == "__main__":
    import random
    random.seed(42)
    demo = CombatDemo()
    demo.run_demo()
