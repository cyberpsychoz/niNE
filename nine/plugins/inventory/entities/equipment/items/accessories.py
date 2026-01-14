"""
Магические аксессуары D&D 5e.

Кольца, амулеты, плащи и другие волшебные предметы.
"""

from nine.plugins.inventory.entities.equipment.accessory import Ring, Amulet, Cloak, Belt, Accessory, AccessoryType
from nine.plugins.inventory.entities.equipment.base_equipment import StatBonus, EquipmentRequirements


# =============================================================================
# Кольца (Rings)
# =============================================================================

class RingOfProtection(Ring):
    """Кольцо защиты — +1 AC и спасброски."""
    CLASS_ID = "ring_of_protection"
    NAME = "Кольцо защиты"
    NAME_EN = "Ring of Protection"
    DESCRIPTION = "Тонкое серебряное кольцо с защитными рунами."
    RARITY = "rare"
    ATTUNEMENT = True
    STAT_BONUS = StatBonus(armor_class=1)
    VALUE = 350000  # ~3500 gp


class RingOfResistance(Ring):
    """Кольцо сопротивления — сопротивление одному типу урона."""
    CLASS_ID = "ring_of_resistance_fire"
    NAME = "Кольцо сопротивления (огонь)"
    NAME_EN = "Ring of Resistance (Fire)"
    DESCRIPTION = "Рубиновое кольцо, защищающее от огня."
    RARITY = "rare"
    ATTUNEMENT = True
    STAT_BONUS = StatBonus(damage_resistance=["fire"])
    VALUE = 600000


class RingOfInvisibility(Ring):
    """Кольцо невидимости — можно стать невидимым."""
    CLASS_ID = "ring_of_invisibility"
    NAME = "Кольцо невидимости"
    NAME_EN = "Ring of Invisibility"
    DESCRIPTION = "Простое золотое кольцо, делающее носителя невидимым."
    RARITY = "legendary"
    ATTUNEMENT = True
    ABILITY_NAME = "Невидимость"
    ABILITY_DESCRIPTION = "Действием вы становитесь невидимым, пока носите кольцо."
    VALUE = 5000000


class RingOfRegeneration(Ring):
    """Кольцо регенерации — восстановление HP."""
    CLASS_ID = "ring_of_regeneration"
    NAME = "Кольцо регенерации"
    NAME_EN = "Ring of Regeneration"
    DESCRIPTION = "Изумрудное кольцо с пульсирующим светом."
    RARITY = "very_rare"
    ATTUNEMENT = True
    ABILITY_NAME = "Регенерация"
    ABILITY_DESCRIPTION = "Восстанавливаете 1d6 HP каждые 10 минут."
    VALUE = 2500000


class RingOfSpellStoring(Ring):
    """Кольцо хранения заклинаний — хранит до 5 уровней заклинаний."""
    CLASS_ID = "ring_of_spell_storing"
    NAME = "Кольцо хранения заклинаний"
    NAME_EN = "Ring of Spell Storing"
    DESCRIPTION = "Кольцо с мерцающими кристаллами."
    RARITY = "rare"
    ATTUNEMENT = True
    ABILITY_NAME = "Хранение заклинаний"
    ABILITY_DESCRIPTION = "Хранит до 5 уровней заклинаний."
    VALUE = 2400000


# =============================================================================
# Амулеты (Amulets)
# =============================================================================

class AmuletOfHealth(Amulet):
    """Амулет здоровья — Телосложение становится 19."""
    CLASS_ID = "amulet_of_health"
    NAME = "Амулет здоровья"
    NAME_EN = "Amulet of Health"
    DESCRIPTION = "Рубиновый медальон на золотой цепи."
    RARITY = "rare"
    ATTUNEMENT = True
    # Особый эффект: устанавливает CON = 19
    VALUE = 800000


class AmuletOfProofAgainstDetection(Amulet):
    """Амулет защиты от обнаружения — скрывает от прорицания."""
    CLASS_ID = "amulet_of_nondetection"
    NAME = "Амулет защиты от обнаружения"
    NAME_EN = "Amulet of Proof Against Detection"
    DESCRIPTION = "Серебряный амулет с глазом, скрывающий носителя."
    RARITY = "uncommon"
    ATTUNEMENT = True
    VALUE = 150000


class PeriaptOfWoundClosure(Amulet):
    """Амулет закрытия ран — стабилизация и усиленное лечение."""
    CLASS_ID = "periapt_of_wound_closure"
    NAME = "Амулет закрытия ран"
    NAME_EN = "Periapt of Wound Closure"
    DESCRIPTION = "Серебряный медальон с каплей крови внутри."
    RARITY = "uncommon"
    ATTUNEMENT = True
    ABILITY_NAME = "Закрытие ран"
    ABILITY_DESCRIPTION = "Автостабилизация. Удвоенное лечение от кубов хитов."
    VALUE = 500000


class MedallionOfThoughts(Amulet):
    """Медальон мыслей — использует Обнаружение мыслей."""
    CLASS_ID = "medallion_of_thoughts"
    NAME = "Медальон мыслей"
    NAME_EN = "Medallion of Thoughts"
    DESCRIPTION = "Медный медальон с изображением глаза."
    RARITY = "uncommon"
    ATTUNEMENT = True
    ABILITY_NAME = "Обнаружение мыслей"
    ABILITY_DESCRIPTION = "Сотворяет заклинание Обнаружение мыслей."
    ABILITY_USES = 3
    ABILITY_RECHARGE = "dawn"
    VALUE = 300000


# =============================================================================
# Плащи (Cloaks)
# =============================================================================

class CloakOfProtection(Cloak):
    """Плащ защиты — +1 AC и спасброски."""
    CLASS_ID = "cloak_of_protection"
    NAME = "Плащ защиты"
    NAME_EN = "Cloak of Protection"
    DESCRIPTION = "Серый плащ с серебряной застёжкой."
    RARITY = "uncommon"
    ATTUNEMENT = True
    STAT_BONUS = StatBonus(armor_class=1)
    VALUE = 350000


class CloakOfDisplacement(Cloak):
    """Плащ смещения — атаки по вам с помехой."""
    CLASS_ID = "cloak_of_displacement"
    NAME = "Плащ смещения"
    NAME_EN = "Cloak of Displacement"
    DESCRIPTION = "Переливающийся плащ, искажающий ваш силуэт."
    RARITY = "rare"
    ATTUNEMENT = True
    ABILITY_NAME = "Смещение"
    ABILITY_DESCRIPTION = "Атаки по вам с помехой, пока не получите урон."
    VALUE = 600000


class CloakOfElvenkind(Cloak):
    """Эльфийский плащ — преимущество на Скрытность."""
    CLASS_ID = "cloak_of_elvenkind"
    NAME = "Эльфийский плащ"
    NAME_EN = "Cloak of Elvenkind"
    DESCRIPTION = "Зелёный плащ, сливающийся с окружением."
    RARITY = "uncommon"
    ATTUNEMENT = True
    ABILITY_NAME = "Эльфийская скрытность"
    ABILITY_DESCRIPTION = "Преимущество на Скрытность. Помеха на Восприятие против вас."
    VALUE = 500000


class CloakOfTheBat(Cloak):
    """Плащ летучей мыши — преимущество на Скрытность, полёт, полиморф."""
    CLASS_ID = "cloak_of_the_bat"
    NAME = "Плащ летучей мыши"
    NAME_EN = "Cloak of the Bat"
    DESCRIPTION = "Чёрный плащ с подкладкой из кожи летучих мышей."
    RARITY = "rare"
    ATTUNEMENT = True
    ABILITY_NAME = "Форма летучей мыши"
    ABILITY_DESCRIPTION = "Полёт 40 фт. в темноте. Превращение в летучую мышь."
    VALUE = 1000000


class CloakOfManyFashions(Cloak):
    """Плащ модника — меняет внешний вид по желанию."""
    CLASS_ID = "cloak_of_many_fashions"
    NAME = "Плащ модника"
    NAME_EN = "Cloak of Many Fashions"
    DESCRIPTION = "Плащ, способный принимать любой вид."
    RARITY = "common"
    MAGICAL = True
    ABILITY_NAME = "Смена стиля"
    ABILITY_DESCRIPTION = "Бонусным действием меняет цвет и стиль."
    VALUE = 10000


# =============================================================================
# Пояса (Belts)
# =============================================================================

class BeltOfGiantStrength(Belt):
    """Пояс великаньей силы — повышает Силу."""
    CLASS_ID = "belt_of_hill_giant_strength"
    NAME = "Пояс силы холмового великана"
    NAME_EN = "Belt of Hill Giant Strength"
    DESCRIPTION = "Широкий кожаный пояс с металлическими вставками."
    RARITY = "rare"
    ATTUNEMENT = True
    # Устанавливает STR = 21
    VALUE = 600000


class BeltOfDwarvenkind(Belt):
    """Пояс дварфов — +2 CON, преимущества дварфов."""
    CLASS_ID = "belt_of_dwarvenkind"
    NAME = "Пояс дварфов"
    NAME_EN = "Belt of Dwarvenkind"
    DESCRIPTION = "Широкий пояс из дварфийской стали."
    RARITY = "rare"
    ATTUNEMENT = True
    STAT_BONUS = StatBonus(constitution=2)
    ABILITY_NAME = "Дварфийская стойкость"
    ABILITY_DESCRIPTION = "Преимущество на спасброски от яда. Тёмное зрение 60 фт."
    VALUE = 600000


# =============================================================================
# Особые аксессуары
# =============================================================================

class BootsOfSpeed(Accessory):
    """Сапоги скорости — удвоенная скорость."""
    CLASS_ID = "boots_of_speed"
    NAME = "Сапоги скорости"
    NAME_EN = "Boots of Speed"
    DESCRIPTION = "Лёгкие сапоги с крылышками на пятках."
    ACCESSORY_TYPE = AccessoryType.BOOTS
    RARITY = "rare"
    ATTUNEMENT = True
    ABILITY_NAME = "Удвоенная скорость"
    ABILITY_DESCRIPTION = "Бонусным действием удваивает скорость на 10 минут."
    ABILITY_USES = 1
    ABILITY_RECHARGE = "long_rest"
    VALUE = 400000


class BootsOfElvenkind(Accessory):
    """Эльфийские сапоги — бесшумные шаги."""
    CLASS_ID = "boots_of_elvenkind"
    NAME = "Эльфийские сапоги"
    NAME_EN = "Boots of Elvenkind"
    DESCRIPTION = "Мягкие сапоги эльфийской работы."
    ACCESSORY_TYPE = AccessoryType.BOOTS
    RARITY = "uncommon"
    ABILITY_NAME = "Бесшумные шаги"
    ABILITY_DESCRIPTION = "Преимущество на Скрытность для бесшумного передвижения."
    VALUE = 250000


class GlovesOfThievery(Accessory):
    """Перчатки воровства — +5 к Ловкости рук и взлому."""
    CLASS_ID = "gloves_of_thievery"
    NAME = "Перчатки воровства"
    NAME_EN = "Gloves of Thievery"
    DESCRIPTION = "Тонкие чёрные перчатки без отпечатков."
    ACCESSORY_TYPE = AccessoryType.GLOVES
    RARITY = "uncommon"
    ABILITY_NAME = "Ловкие пальцы"
    ABILITY_DESCRIPTION = "+5 к проверкам Ловкости рук и использованию воровских инструментов."
    VALUE = 500000


class BracersOfDefense(Accessory):
    """Наручи защиты — +2 AC без брони."""
    CLASS_ID = "bracers_of_defense"
    NAME = "Наручи защиты"
    NAME_EN = "Bracers of Defense"
    DESCRIPTION = "Металлические наручи с защитными символами."
    ACCESSORY_TYPE = AccessoryType.BRACERS
    RARITY = "rare"
    ATTUNEMENT = True
    STAT_BONUS = StatBonus(armor_class=2)
    # Работает только без брони и щита
    VALUE = 600000


class BracersOfArchery(Accessory):
    """Наручи стрельбы — +2 к урону луками."""
    CLASS_ID = "bracers_of_archery"
    NAME = "Наручи стрельбы"
    NAME_EN = "Bracers of Archery"
    DESCRIPTION = "Кожаные наручи с изображением стрел."
    ACCESSORY_TYPE = AccessoryType.BRACERS
    RARITY = "uncommon"
    ATTUNEMENT = True
    STAT_BONUS = StatBonus(damage_bonus=2)
    # Только для луков
    VALUE = 150000


class CircletOfBlasting(Accessory):
    """Диадема взрыва — сотворяет Палящий луч."""
    CLASS_ID = "circlet_of_blasting"
    NAME = "Диадема взрыва"
    NAME_EN = "Circlet of Blasting"
    DESCRIPTION = "Бронзовая диадема с рубином."
    ACCESSORY_TYPE = AccessoryType.CIRCLET
    RARITY = "uncommon"
    ABILITY_NAME = "Палящий луч"
    ABILITY_DESCRIPTION = "Сотворяет Палящий луч (+5 атака, 4d6 огня)."
    ABILITY_USES = 1
    ABILITY_RECHARGE = "dawn"
    VALUE = 150000


# Экспорт
__all__ = [
    # Кольца
    "RingOfProtection",
    "RingOfResistance",
    "RingOfInvisibility",
    "RingOfRegeneration",
    "RingOfSpellStoring",
    # Амулеты
    "AmuletOfHealth",
    "AmuletOfProofAgainstDetection",
    "PeriaptOfWoundClosure",
    "MedallionOfThoughts",
    # Плащи
    "CloakOfProtection",
    "CloakOfDisplacement",
    "CloakOfElvenkind",
    "CloakOfTheBat",
    "CloakOfManyFashions",
    # Пояса
    "BeltOfGiantStrength",
    "BeltOfDwarvenkind",
    # Особые
    "BootsOfSpeed",
    "BootsOfElvenkind",
    "GlovesOfThievery",
    "BracersOfDefense",
    "BracersOfArchery",
    "CircletOfBlasting",
]
