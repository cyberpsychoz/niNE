"""
Стандартное оружие D&D 5e из Player's Handbook.
"""

from nine.plugins.inventory.entities.equipment.weapon import (
    SimpleMeleeWeapon, SimpleRangedWeapon,
    MartialMeleeWeapon, MartialRangedWeapon,
    DamageType, WeaponRange
)


# =============================================================================
# Простое рукопашное оружие (Simple Melee Weapons)
# =============================================================================

class Club(SimpleMeleeWeapon):
    """Дубинка — 1d4 дробящий, лёгкое."""
    CLASS_ID = "club"
    NAME = "Дубинка"
    NAME_EN = "Club"
    DAMAGE_DICE = "1d4"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    LIGHT = True
    WEIGHT = 2.0
    VALUE = 10  # 1 sp


class Dagger(SimpleMeleeWeapon):
    """Кинжал — 1d4 колющий, фехтовальное, лёгкое, метательное."""
    CLASS_ID = "dagger"
    NAME = "Кинжал"
    NAME_EN = "Dagger"
    DAMAGE_DICE = "1d4"
    DAMAGE_TYPE = DamageType.PIERCING
    FINESSE = True
    LIGHT = True
    THROWN = True
    RANGE = WeaponRange(normal=20, long=60)
    WEIGHT = 1.0
    VALUE = 200  # 2 gp


class Greatclub(SimpleMeleeWeapon):
    """Палица — 1d8 дробящий, двуручное."""
    CLASS_ID = "greatclub"
    NAME = "Палица"
    NAME_EN = "Greatclub"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    TWO_HANDED = True
    WEIGHT = 10.0
    VALUE = 20  # 2 sp


class Handaxe(SimpleMeleeWeapon):
    """Ручной топор — 1d6 рубящий, лёгкое, метательное."""
    CLASS_ID = "handaxe"
    NAME = "Ручной топор"
    NAME_EN = "Handaxe"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.SLASHING
    LIGHT = True
    THROWN = True
    RANGE = WeaponRange(normal=20, long=60)
    WEIGHT = 2.0
    VALUE = 500  # 5 gp


class Javelin(SimpleMeleeWeapon):
    """Метательное копьё — 1d6 колющий, метательное."""
    CLASS_ID = "javelin"
    NAME = "Метательное копьё"
    NAME_EN = "Javelin"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.PIERCING
    THROWN = True
    RANGE = WeaponRange(normal=30, long=120)
    WEIGHT = 2.0
    VALUE = 50  # 5 sp


class LightHammer(SimpleMeleeWeapon):
    """Лёгкий молот — 1d4 дробящий, лёгкое, метательное."""
    CLASS_ID = "light_hammer"
    NAME = "Лёгкий молот"
    NAME_EN = "Light Hammer"
    DAMAGE_DICE = "1d4"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    LIGHT = True
    THROWN = True
    RANGE = WeaponRange(normal=20, long=60)
    WEIGHT = 2.0
    VALUE = 200  # 2 gp


class Mace(SimpleMeleeWeapon):
    """Булава — 1d6 дробящий."""
    CLASS_ID = "mace"
    NAME = "Булава"
    NAME_EN = "Mace"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    WEIGHT = 4.0
    VALUE = 500  # 5 gp


class Quarterstaff(SimpleMeleeWeapon):
    """Боевой посох — 1d6 дробящий, универсальное (1d8)."""
    CLASS_ID = "quarterstaff"
    NAME = "Боевой посох"
    NAME_EN = "Quarterstaff"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    VERSATILE = "1d8"
    WEIGHT = 4.0
    VALUE = 20  # 2 sp


class Sickle(SimpleMeleeWeapon):
    """Серп — 1d4 рубящий, лёгкое."""
    CLASS_ID = "sickle"
    NAME = "Серп"
    NAME_EN = "Sickle"
    DAMAGE_DICE = "1d4"
    DAMAGE_TYPE = DamageType.SLASHING
    LIGHT = True
    WEIGHT = 2.0
    VALUE = 100  # 1 gp


class Spear(SimpleMeleeWeapon):
    """Копьё — 1d6 колющий, метательное, универсальное (1d8)."""
    CLASS_ID = "spear"
    NAME = "Копьё"
    NAME_EN = "Spear"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.PIERCING
    THROWN = True
    VERSATILE = "1d8"
    RANGE = WeaponRange(normal=20, long=60)
    WEIGHT = 3.0
    VALUE = 100  # 1 gp


# =============================================================================
# Простое дальнобойное оружие (Simple Ranged Weapons)
# =============================================================================

class LightCrossbow(SimpleRangedWeapon):
    """Лёгкий арбалет — 1d8 колющий, перезарядка."""
    CLASS_ID = "light_crossbow"
    NAME = "Лёгкий арбалет"
    NAME_EN = "Light Crossbow"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.PIERCING
    LOADING = True
    TWO_HANDED = True
    RANGE = WeaponRange(normal=80, long=320)
    WEIGHT = 5.0
    VALUE = 2500  # 25 gp


class Shortbow(SimpleRangedWeapon):
    """Короткий лук — 1d6 колющий, двуручное."""
    CLASS_ID = "shortbow"
    NAME = "Короткий лук"
    NAME_EN = "Shortbow"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.PIERCING
    TWO_HANDED = True
    RANGE = WeaponRange(normal=80, long=320)
    WEIGHT = 2.0
    VALUE = 2500  # 25 gp


class Sling(SimpleRangedWeapon):
    """Праща — 1d4 дробящий."""
    CLASS_ID = "sling"
    NAME = "Праща"
    NAME_EN = "Sling"
    DAMAGE_DICE = "1d4"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    RANGE = WeaponRange(normal=30, long=120)
    WEIGHT = 0.0
    VALUE = 10  # 1 sp


class Dart(SimpleRangedWeapon):
    """Дротик — 1d4 колющий, фехтовальное, метательное."""
    CLASS_ID = "dart"
    NAME = "Дротик"
    NAME_EN = "Dart"
    DAMAGE_DICE = "1d4"
    DAMAGE_TYPE = DamageType.PIERCING
    FINESSE = True
    THROWN = True
    RANGE = WeaponRange(normal=20, long=60)
    WEIGHT = 0.25
    VALUE = 5  # 5 cp
    MAX_STACK = 20


# =============================================================================
# Воинское рукопашное оружие (Martial Melee Weapons)
# =============================================================================

class Battleaxe(MartialMeleeWeapon):
    """Боевой топор — 1d8 рубящий, универсальное (1d10)."""
    CLASS_ID = "battleaxe"
    NAME = "Боевой топор"
    NAME_EN = "Battleaxe"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.SLASHING
    VERSATILE = "1d10"
    WEIGHT = 4.0
    VALUE = 1000  # 10 gp


class Flail(MartialMeleeWeapon):
    """Цеп — 1d8 дробящий."""
    CLASS_ID = "flail"
    NAME = "Цеп"
    NAME_EN = "Flail"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    WEIGHT = 2.0
    VALUE = 1000  # 10 gp


class Glaive(MartialMeleeWeapon):
    """Глефа — 1d10 рубящий, тяжёлое, досягаемость, двуручное."""
    CLASS_ID = "glaive"
    NAME = "Глефа"
    NAME_EN = "Glaive"
    DAMAGE_DICE = "1d10"
    DAMAGE_TYPE = DamageType.SLASHING
    HEAVY = True
    REACH = True
    TWO_HANDED = True
    WEIGHT = 6.0
    VALUE = 2000  # 20 gp


class Greataxe(MartialMeleeWeapon):
    """Секира — 1d12 рубящий, тяжёлое, двуручное."""
    CLASS_ID = "greataxe"
    NAME = "Секира"
    NAME_EN = "Greataxe"
    DAMAGE_DICE = "1d12"
    DAMAGE_TYPE = DamageType.SLASHING
    HEAVY = True
    TWO_HANDED = True
    WEIGHT = 7.0
    VALUE = 3000  # 30 gp


class Greatsword(MartialMeleeWeapon):
    """Двуручный меч — 2d6 рубящий, тяжёлое, двуручное."""
    CLASS_ID = "greatsword"
    NAME = "Двуручный меч"
    NAME_EN = "Greatsword"
    DAMAGE_DICE = "2d6"
    DAMAGE_TYPE = DamageType.SLASHING
    HEAVY = True
    TWO_HANDED = True
    WEIGHT = 6.0
    VALUE = 5000  # 50 gp


class Halberd(MartialMeleeWeapon):
    """Алебарда — 1d10 рубящий, тяжёлое, досягаемость, двуручное."""
    CLASS_ID = "halberd"
    NAME = "Алебарда"
    NAME_EN = "Halberd"
    DAMAGE_DICE = "1d10"
    DAMAGE_TYPE = DamageType.SLASHING
    HEAVY = True
    REACH = True
    TWO_HANDED = True
    WEIGHT = 6.0
    VALUE = 2000  # 20 gp


class Lance(MartialMeleeWeapon):
    """Копьё кавалериста — 1d12 колющий, досягаемость, особое."""
    CLASS_ID = "lance"
    NAME = "Копьё кавалериста"
    NAME_EN = "Lance"
    DESCRIPTION = "Помеха при атаке целей ближе 5 футов. Требует две руки, если вы не верхом."
    DAMAGE_DICE = "1d12"
    DAMAGE_TYPE = DamageType.PIERCING
    REACH = True
    SPECIAL = True
    WEIGHT = 6.0
    VALUE = 1000  # 10 gp


class Longsword(MartialMeleeWeapon):
    """Длинный меч — 1d8 рубящий, универсальное (1d10)."""
    CLASS_ID = "longsword"
    NAME = "Длинный меч"
    NAME_EN = "Longsword"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.SLASHING
    VERSATILE = "1d10"
    WEIGHT = 3.0
    VALUE = 1500  # 15 gp


class Maul(MartialMeleeWeapon):
    """Молот — 2d6 дробящий, тяжёлое, двуручное."""
    CLASS_ID = "maul"
    NAME = "Молот"
    NAME_EN = "Maul"
    DAMAGE_DICE = "2d6"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    HEAVY = True
    TWO_HANDED = True
    WEIGHT = 10.0
    VALUE = 1000  # 10 gp


class Morningstar(MartialMeleeWeapon):
    """Моргенштерн — 1d8 колющий."""
    CLASS_ID = "morningstar"
    NAME = "Моргенштерн"
    NAME_EN = "Morningstar"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.PIERCING
    WEIGHT = 4.0
    VALUE = 1500  # 15 gp


class Pike(MartialMeleeWeapon):
    """Пика — 1d10 колющий, тяжёлое, досягаемость, двуручное."""
    CLASS_ID = "pike"
    NAME = "Пика"
    NAME_EN = "Pike"
    DAMAGE_DICE = "1d10"
    DAMAGE_TYPE = DamageType.PIERCING
    HEAVY = True
    REACH = True
    TWO_HANDED = True
    WEIGHT = 18.0
    VALUE = 500  # 5 gp


class Rapier(MartialMeleeWeapon):
    """Рапира — 1d8 колющий, фехтовальное."""
    CLASS_ID = "rapier"
    NAME = "Рапира"
    NAME_EN = "Rapier"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.PIERCING
    FINESSE = True
    WEIGHT = 2.0
    VALUE = 2500  # 25 gp


class Scimitar(MartialMeleeWeapon):
    """Скимитар — 1d6 рубящий, фехтовальное, лёгкое."""
    CLASS_ID = "scimitar"
    NAME = "Скимитар"
    NAME_EN = "Scimitar"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.SLASHING
    FINESSE = True
    LIGHT = True
    WEIGHT = 3.0
    VALUE = 2500  # 25 gp


class Shortsword(MartialMeleeWeapon):
    """Короткий меч — 1d6 колющий, фехтовальное, лёгкое."""
    CLASS_ID = "shortsword"
    NAME = "Короткий меч"
    NAME_EN = "Shortsword"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.PIERCING
    FINESSE = True
    LIGHT = True
    WEIGHT = 2.0
    VALUE = 1000  # 10 gp


class Trident(MartialMeleeWeapon):
    """Трезубец — 1d6 колющий, метательное, универсальное (1d8)."""
    CLASS_ID = "trident"
    NAME = "Трезубец"
    NAME_EN = "Trident"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.PIERCING
    THROWN = True
    VERSATILE = "1d8"
    RANGE = WeaponRange(normal=20, long=60)
    WEIGHT = 4.0
    VALUE = 500  # 5 gp


class Warpick(MartialMeleeWeapon):
    """Боевой клевец — 1d8 колющий."""
    CLASS_ID = "warpick"
    NAME = "Боевой клевец"
    NAME_EN = "War Pick"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.PIERCING
    WEIGHT = 2.0
    VALUE = 500  # 5 gp


class Warhammer(MartialMeleeWeapon):
    """Боевой молот — 1d8 дробящий, универсальное (1d10)."""
    CLASS_ID = "warhammer"
    NAME = "Боевой молот"
    NAME_EN = "Warhammer"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    VERSATILE = "1d10"
    WEIGHT = 2.0
    VALUE = 1500  # 15 gp


class Whip(MartialMeleeWeapon):
    """Кнут — 1d4 рубящий, фехтовальное, досягаемость."""
    CLASS_ID = "whip"
    NAME = "Кнут"
    NAME_EN = "Whip"
    DAMAGE_DICE = "1d4"
    DAMAGE_TYPE = DamageType.SLASHING
    FINESSE = True
    REACH = True
    WEIGHT = 3.0
    VALUE = 200  # 2 gp


# =============================================================================
# Воинское дальнобойное оружие (Martial Ranged Weapons)
# =============================================================================

class Blowgun(MartialRangedWeapon):
    """Духовая трубка — 1 колющий, перезарядка."""
    CLASS_ID = "blowgun"
    NAME = "Духовая трубка"
    NAME_EN = "Blowgun"
    DAMAGE_DICE = "1"
    DAMAGE_TYPE = DamageType.PIERCING
    LOADING = True
    RANGE = WeaponRange(normal=25, long=100)
    WEIGHT = 1.0
    VALUE = 1000  # 10 gp


class HandCrossbow(MartialRangedWeapon):
    """Ручной арбалет — 1d6 колющий, лёгкое, перезарядка."""
    CLASS_ID = "hand_crossbow"
    NAME = "Ручной арбалет"
    NAME_EN = "Hand Crossbow"
    DAMAGE_DICE = "1d6"
    DAMAGE_TYPE = DamageType.PIERCING
    LIGHT = True
    LOADING = True
    RANGE = WeaponRange(normal=30, long=120)
    WEIGHT = 3.0
    VALUE = 7500  # 75 gp


class HeavyCrossbow(MartialRangedWeapon):
    """Тяжёлый арбалет — 1d10 колющий, тяжёлое, перезарядка, двуручное."""
    CLASS_ID = "heavy_crossbow"
    NAME = "Тяжёлый арбалет"
    NAME_EN = "Heavy Crossbow"
    DAMAGE_DICE = "1d10"
    DAMAGE_TYPE = DamageType.PIERCING
    HEAVY = True
    LOADING = True
    TWO_HANDED = True
    RANGE = WeaponRange(normal=100, long=400)
    WEIGHT = 18.0
    VALUE = 5000  # 50 gp


class Longbow(MartialRangedWeapon):
    """Длинный лук — 1d8 колющий, тяжёлое, двуручное."""
    CLASS_ID = "longbow"
    NAME = "Длинный лук"
    NAME_EN = "Longbow"
    DAMAGE_DICE = "1d8"
    DAMAGE_TYPE = DamageType.PIERCING
    HEAVY = True
    TWO_HANDED = True
    RANGE = WeaponRange(normal=150, long=600)
    WEIGHT = 2.0
    VALUE = 5000  # 50 gp


class Net(MartialRangedWeapon):
    """Сеть — особое, метательное."""
    CLASS_ID = "net"
    NAME = "Сеть"
    NAME_EN = "Net"
    DESCRIPTION = "Опутывает существо Большого или меньшего размера. DC 10 СИЛ или рубящий урон 5."
    DAMAGE_DICE = "0"
    DAMAGE_TYPE = DamageType.BLUDGEONING
    THROWN = True
    SPECIAL = True
    RANGE = WeaponRange(normal=5, long=15)
    WEIGHT = 3.0
    VALUE = 100  # 1 gp


# Экспорт
__all__ = [
    # Простое рукопашное
    "Club", "Dagger", "Greatclub", "Handaxe", "Javelin",
    "LightHammer", "Mace", "Quarterstaff", "Sickle", "Spear",
    # Простое дальнобойное
    "LightCrossbow", "Shortbow", "Sling", "Dart",
    # Воинское рукопашное
    "Battleaxe", "Flail", "Glaive", "Greataxe", "Greatsword",
    "Halberd", "Lance", "Longsword", "Maul", "Morningstar",
    "Pike", "Rapier", "Scimitar", "Shortsword", "Trident",
    "Warpick", "Warhammer", "Whip",
    # Воинское дальнобойное
    "Blowgun", "HandCrossbow", "HeavyCrossbow", "Longbow", "Net",
]
