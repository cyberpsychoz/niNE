"""
D&D 5e Constants.
Константы для системы персонажей D&D.
"""

# =============================================================================
# РАСЫ (Races)
# =============================================================================

RACES = {
    "human": {
        "name": "Человек",
        "name_en": "Human",
        "description": "Универсальные и адаптивные",
        "ability_bonuses": {"strength": 1, "dexterity": 1, "constitution": 1,
                          "intelligence": 1, "wisdom": 1, "charisma": 1},
        "speed": 30,
        "features": ["extra_language", "extra_skill"],
        "models": {"male": "human_male", "female": "human_female"},
    },
    "elf": {
        "name": "Эльф",
        "name_en": "Elf",
        "description": "Ловкие и грациозные",
        "ability_bonuses": {"dexterity": 2, "intelligence": 1},
        "speed": 30,
        "features": ["darkvision", "fey_ancestry", "trance"],
        "models": {"male": "elf_male", "female": "elf_female"},
    },
    "dwarf": {
        "name": "Дварф",
        "name_en": "Dwarf",
        "description": "Крепкие и стойкие",
        "ability_bonuses": {"constitution": 2, "wisdom": 1},
        "speed": 25,
        "features": ["darkvision", "dwarven_resilience", "stonecunning"],
        "models": {"male": "dwarf_male", "female": "dwarf_female"},
    },
    "halfling": {
        "name": "Полурослик",
        "name_en": "Halfling",
        "description": "Малорослые и проворные",
        "ability_bonuses": {"dexterity": 2, "charisma": 1},
        "speed": 25,
        "features": ["lucky", "brave", "halfling_nimbleness"],
        "models": {"male": "halfling_male", "female": "halfling_female"},
    },
    "orc": {
        "name": "Орк",
        "name_en": "Orc",
        "description": "Сильные и выносливые",
        "ability_bonuses": {"strength": 2, "constitution": 1},
        "speed": 30,
        "features": ["darkvision", "aggressive", "powerful_build"],
        "models": {"male": "orc_male", "female": "orc_female"},
    },
    "tiefling": {
        "name": "Тифлинг",
        "name_en": "Tiefling",
        "description": "Наследие преисподней",
        "ability_bonuses": {"charisma": 2, "intelligence": 1},
        "speed": 30,
        "features": ["darkvision", "hellish_resistance", "infernal_legacy"],
        "models": {"male": "tiefling_male", "female": "tiefling_female"},
    },
}

# =============================================================================
# КЛАССЫ (Classes)
# =============================================================================

CLASSES = {
    "fighter": {
        "name": "Воин",
        "name_en": "Fighter",
        "description": "Мастер боя, использующий разнообразное оружие и тактики",
        "hit_die": 10,
        "primary_stats": ["strength", "constitution"],
        "saving_throws": ["strength", "constitution"],
        "armor_proficiencies": ["light", "medium", "heavy", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Acrobatics", "Animal Handling", "Athletics", "History",
                         "Insight", "Intimidation", "Perception", "Survival"],
        "num_skills": 2,
        "features_1": ["fighting_style", "second_wind"],
        "starting_equipment": ["chain_mail", "longsword", "shield"],
    },
    "wizard": {
        "name": "Волшебник",
        "name_en": "Wizard",
        "description": "Учёный-маг, черпающий силу из изучения арканы",
        "hit_die": 6,
        "primary_stats": ["intelligence"],
        "saving_throws": ["intelligence", "wisdom"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["daggers", "darts", "slings", "quarterstaffs", "light_crossbows"],
        "skill_choices": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"],
        "num_skills": 2,
        "features_1": ["spellcasting", "arcane_recovery"],
        "starting_equipment": ["quarterstaff", "spellbook"],
        "spellcaster": True,
        "spellcasting_ability": "intelligence",
    },
    "rogue": {
        "name": "Плут",
        "name_en": "Rogue",
        "description": "Мастер скрытности и точных ударов",
        "hit_die": 8,
        "primary_stats": ["dexterity"],
        "saving_throws": ["dexterity", "intelligence"],
        "armor_proficiencies": ["light"],
        "weapon_proficiencies": ["simple", "hand_crossbows", "longswords", "rapiers", "shortswords"],
        "skill_choices": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation",
                         "Investigation", "Perception", "Performance", "Persuasion",
                         "Sleight of Hand", "Stealth"],
        "num_skills": 4,
        "features_1": ["expertise", "sneak_attack", "thieves_cant"],
        "starting_equipment": ["rapier", "shortbow", "leather_armor", "thieves_tools"],
    },
    "cleric": {
        "name": "Жрец",
        "name_en": "Cleric",
        "description": "Посланник богов, несущий их волю",
        "hit_die": 8,
        "primary_stats": ["wisdom"],
        "saving_throws": ["wisdom", "charisma"],
        "armor_proficiencies": ["light", "medium", "shields"],
        "weapon_proficiencies": ["simple"],
        "skill_choices": ["History", "Insight", "Medicine", "Persuasion", "Religion"],
        "num_skills": 2,
        "features_1": ["spellcasting", "divine_domain"],
        "starting_equipment": ["mace", "scale_mail", "shield", "holy_symbol"],
        "spellcaster": True,
        "spellcasting_ability": "wisdom",
    },
    "ranger": {
        "name": "Следопыт",
        "name_en": "Ranger",
        "description": "Воин дикой природы, охотник и следопыт",
        "hit_die": 10,
        "primary_stats": ["dexterity", "wisdom"],
        "saving_throws": ["strength", "dexterity"],
        "armor_proficiencies": ["light", "medium", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Animal Handling", "Athletics", "Insight", "Investigation",
                         "Nature", "Perception", "Stealth", "Survival"],
        "num_skills": 3,
        "features_1": ["favored_enemy", "natural_explorer"],
        "starting_equipment": ["scale_mail", "longbow", "shortswords"],
    },
    "paladin": {
        "name": "Паладин",
        "name_en": "Paladin",
        "description": "Святой воин, связанный священной клятвой",
        "hit_die": 10,
        "primary_stats": ["strength", "charisma"],
        "saving_throws": ["wisdom", "charisma"],
        "armor_proficiencies": ["light", "medium", "heavy", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Athletics", "Insight", "Intimidation", "Medicine",
                         "Persuasion", "Religion"],
        "num_skills": 2,
        "features_1": ["divine_sense", "lay_on_hands"],
        "starting_equipment": ["chain_mail", "longsword", "shield", "holy_symbol"],
    },
    "barbarian": {
        "name": "Варвар",
        "name_en": "Barbarian",
        "description": "Яростный воин первобытной силы",
        "hit_die": 12,
        "primary_stats": ["strength", "constitution"],
        "saving_throws": ["strength", "constitution"],
        "armor_proficiencies": ["light", "medium", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Animal Handling", "Athletics", "Intimidation",
                         "Nature", "Perception", "Survival"],
        "num_skills": 2,
        "features_1": ["rage", "unarmored_defense"],
        "starting_equipment": ["greataxe", "handaxes", "explorers_pack"],
    },
    "monk": {
        "name": "Монах",
        "name_en": "Monk",
        "description": "Мастер боевых искусств и внутренней силы",
        "hit_die": 8,
        "primary_stats": ["dexterity", "wisdom"],
        "saving_throws": ["strength", "dexterity"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["simple", "shortswords"],
        "skill_choices": ["Acrobatics", "Athletics", "History", "Insight",
                         "Religion", "Stealth"],
        "num_skills": 2,
        "features_1": ["unarmored_defense", "martial_arts"],
        "starting_equipment": ["shortsword", "darts"],
    },
    "druid": {
        "name": "Друид",
        "name_en": "Druid",
        "description": "Жрец природы, хранитель баланса",
        "hit_die": 8,
        "primary_stats": ["wisdom"],
        "saving_throws": ["intelligence", "wisdom"],
        "armor_proficiencies": ["light", "medium", "shields"],  # non-metal only
        "weapon_proficiencies": ["clubs", "daggers", "darts", "javelins", "maces",
                                 "quarterstaffs", "scimitars", "sickles", "slings", "spears"],
        "skill_choices": ["Arcana", "Animal Handling", "Insight", "Medicine",
                         "Nature", "Perception", "Religion", "Survival"],
        "num_skills": 2,
        "features_1": ["druidic", "spellcasting"],
        "starting_equipment": ["leather_armor", "wooden_shield", "scimitar"],
        "spellcaster": True,
        "spellcasting_ability": "wisdom",
    },
    "warlock": {
        "name": "Колдун",
        "name_en": "Warlock",
        "description": "Маг, заключивший договор с могущественной сущностью",
        "hit_die": 8,
        "primary_stats": ["charisma"],
        "saving_throws": ["wisdom", "charisma"],
        "armor_proficiencies": ["light"],
        "weapon_proficiencies": ["simple"],
        "skill_choices": ["Arcana", "Deception", "History", "Intimidation",
                         "Investigation", "Nature", "Religion"],
        "num_skills": 2,
        "features_1": ["otherworldly_patron", "pact_magic"],
        "starting_equipment": ["light_crossbow", "leather_armor", "arcane_focus"],
        "spellcaster": True,
        "spellcasting_ability": "charisma",
    },
    "bard": {
        "name": "Бард",
        "name_en": "Bard",
        "description": "Мастер песен, историй и магии слов",
        "hit_die": 8,
        "primary_stats": ["charisma"],
        "saving_throws": ["dexterity", "charisma"],
        "armor_proficiencies": ["light"],
        "weapon_proficiencies": ["simple", "hand_crossbows", "longswords", "rapiers", "shortswords"],
        "skill_choices": ["any"],  # Bards can choose any 3 skills
        "num_skills": 3,
        "features_1": ["spellcasting", "bardic_inspiration"],
        "starting_equipment": ["rapier", "leather_armor", "lute"],
        "spellcaster": True,
        "spellcasting_ability": "charisma",
    },
    "sorcerer": {
        "name": "Чародей",
        "name_en": "Sorcerer",
        "description": "Маг с врождённой магической силой",
        "hit_die": 6,
        "primary_stats": ["charisma"],
        "saving_throws": ["constitution", "charisma"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["daggers", "darts", "slings", "quarterstaffs", "light_crossbows"],
        "skill_choices": ["Arcana", "Deception", "Insight", "Intimidation",
                         "Persuasion", "Religion"],
        "num_skills": 2,
        "features_1": ["spellcasting", "sorcerous_origin"],
        "starting_equipment": ["light_crossbow", "arcane_focus"],
        "spellcaster": True,
        "spellcasting_ability": "charisma",
    },
}

# =============================================================================
# ПРЕДЫСТОРИИ (Backgrounds)
# =============================================================================

BACKGROUNDS = {
    "acolyte": {
        "name": "Служитель",
        "name_en": "Acolyte",
        "description": "Вы провели жизнь в служении храму",
        "skill_proficiencies": ["Insight", "Religion"],
        "languages": 2,
        "feature": "shelter_of_the_faithful",
        "equipment": ["holy_symbol", "prayer_book", "incense", "vestments", "common_clothes"],
        "gold": 15,
    },
    "criminal": {
        "name": "Преступник",
        "name_en": "Criminal",
        "description": "Вы имеете криминальное прошлое",
        "skill_proficiencies": ["Deception", "Stealth"],
        "tool_proficiencies": ["gaming_set", "thieves_tools"],
        "feature": "criminal_contact",
        "equipment": ["crowbar", "dark_common_clothes", "belt_pouch"],
        "gold": 15,
    },
    "folk_hero": {
        "name": "Народный герой",
        "name_en": "Folk Hero",
        "description": "Вы совершили подвиг, спасший простых людей",
        "skill_proficiencies": ["Animal Handling", "Survival"],
        "tool_proficiencies": ["artisans_tools", "vehicles_land"],
        "feature": "rustic_hospitality",
        "equipment": ["artisans_tools", "shovel", "iron_pot", "common_clothes"],
        "gold": 10,
    },
    "noble": {
        "name": "Аристократ",
        "name_en": "Noble",
        "description": "Вы родились в привилегированной семье",
        "skill_proficiencies": ["History", "Persuasion"],
        "tool_proficiencies": ["gaming_set"],
        "languages": 1,
        "feature": "position_of_privilege",
        "equipment": ["fine_clothes", "signet_ring", "scroll_of_pedigree"],
        "gold": 25,
    },
    "sage": {
        "name": "Мудрец",
        "name_en": "Sage",
        "description": "Вы посвятили жизнь изучению знаний",
        "skill_proficiencies": ["Arcana", "History"],
        "languages": 2,
        "feature": "researcher",
        "equipment": ["ink", "quill", "small_knife", "letter_from_colleague", "common_clothes"],
        "gold": 10,
    },
    "soldier": {
        "name": "Солдат",
        "name_en": "Soldier",
        "description": "Вы служили в армии и знаете военное дело",
        "skill_proficiencies": ["Athletics", "Intimidation"],
        "tool_proficiencies": ["gaming_set", "vehicles_land"],
        "feature": "military_rank",
        "equipment": ["insignia_of_rank", "trophy", "dice_set", "common_clothes"],
        "gold": 10,
    },
    "charlatan": {
        "name": "Шарлатан",
        "name_en": "Charlatan",
        "description": "Вы мастер обмана и мошенничества",
        "skill_proficiencies": ["Deception", "Sleight of Hand"],
        "tool_proficiencies": ["disguise_kit", "forgery_kit"],
        "feature": "false_identity",
        "equipment": ["fine_clothes", "disguise_kit", "con_tools"],
        "gold": 15,
    },
    "entertainer": {
        "name": "Артист",
        "name_en": "Entertainer",
        "description": "Вы выступаете перед публикой",
        "skill_proficiencies": ["Acrobatics", "Performance"],
        "tool_proficiencies": ["disguise_kit", "musical_instrument"],
        "feature": "by_popular_demand",
        "equipment": ["musical_instrument", "favor_of_admirer", "costume"],
        "gold": 15,
    },
    "hermit": {
        "name": "Отшельник",
        "name_en": "Hermit",
        "description": "Вы жили в уединении",
        "skill_proficiencies": ["Medicine", "Religion"],
        "tool_proficiencies": ["herbalism_kit"],
        "languages": 1,
        "feature": "discovery",
        "equipment": ["scroll_case", "winter_blanket", "common_clothes", "herbalism_kit"],
        "gold": 5,
    },
    "outlander": {
        "name": "Чужеземец",
        "name_en": "Outlander",
        "description": "Вы выросли вдали от цивилизации",
        "skill_proficiencies": ["Athletics", "Survival"],
        "tool_proficiencies": ["musical_instrument"],
        "languages": 1,
        "feature": "wanderer",
        "equipment": ["staff", "hunting_trap", "trophy", "travelers_clothes"],
        "gold": 10,
    },
}

# =============================================================================
# НАВЫКИ (Skills)
# =============================================================================

SKILLS = {
    # STR
    "Athletics": {"ability": "strength", "name": "Атлетика"},
    # DEX
    "Acrobatics": {"ability": "dexterity", "name": "Акробатика"},
    "Sleight of Hand": {"ability": "dexterity", "name": "Ловкость рук"},
    "Stealth": {"ability": "dexterity", "name": "Скрытность"},
    # INT
    "Arcana": {"ability": "intelligence", "name": "Магия"},
    "History": {"ability": "intelligence", "name": "История"},
    "Investigation": {"ability": "intelligence", "name": "Расследование"},
    "Nature": {"ability": "intelligence", "name": "Природа"},
    "Religion": {"ability": "intelligence", "name": "Религия"},
    # WIS
    "Animal Handling": {"ability": "wisdom", "name": "Уход за животными"},
    "Insight": {"ability": "wisdom", "name": "Проницательность"},
    "Medicine": {"ability": "wisdom", "name": "Медицина"},
    "Perception": {"ability": "wisdom", "name": "Внимательность"},
    "Survival": {"ability": "wisdom", "name": "Выживание"},
    # CHA
    "Deception": {"ability": "charisma", "name": "Обман"},
    "Intimidation": {"ability": "charisma", "name": "Запугивание"},
    "Performance": {"ability": "charisma", "name": "Выступление"},
    "Persuasion": {"ability": "charisma", "name": "Убеждение"},
}

# =============================================================================
# ХАРАКТЕРИСТИКИ (Abilities)
# =============================================================================

ABILITIES = {
    "strength": {"name": "Сила", "name_en": "Strength", "abbr": "STR"},
    "dexterity": {"name": "Ловкость", "name_en": "Dexterity", "abbr": "DEX"},
    "constitution": {"name": "Телосложение", "name_en": "Constitution", "abbr": "CON"},
    "intelligence": {"name": "Интеллект", "name_en": "Intelligence", "abbr": "INT"},
    "wisdom": {"name": "Мудрость", "name_en": "Wisdom", "abbr": "WIS"},
    "charisma": {"name": "Харизма", "name_en": "Charisma", "abbr": "CHA"},
}

# =============================================================================
# МЕТОДЫ ГЕНЕРАЦИИ ХАРАКТЕРИСТИК (Stat Generation)
# =============================================================================

STAT_GENERATION = {
    "point_buy": {
        "name": "Покупка очков",
        "description": "27 очков для распределения",
        "points": 27,
        "min_value": 8,
        "max_value": 15,
        "cost_table": {
            8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9
        },
    },
    "standard_array": {
        "name": "Стандартный набор",
        "description": "Фиксированный набор значений",
        "values": [15, 14, 13, 12, 10, 8],
    },
    "roll_4d6": {
        "name": "Броски кубов",
        "description": "4d6, убрать наименьший",
        "dice": 4,
        "sides": 6,
        "drop_lowest": 1,
    },
}

# =============================================================================
# РАСЧЁТ МОДИФИКАТОРОВ
# =============================================================================

def calculate_modifier(ability_score: int) -> int:
    """Расчёт модификатора характеристики D&D."""
    return (ability_score - 10) // 2


def calculate_proficiency_bonus(level: int) -> int:
    """Расчёт бонуса владения по уровню."""
    return 2 + (level - 1) // 4


def calculate_hp_at_level_1(class_id: str, constitution_modifier: int) -> int:
    """Расчёт HP на 1 уровне."""
    class_data = CLASSES.get(class_id, {})
    hit_die = class_data.get("hit_die", 8)
    return hit_die + constitution_modifier


def calculate_base_ac(dexterity_modifier: int) -> int:
    """Базовый AC без брони."""
    return 10 + dexterity_modifier


# =============================================================================
# ЛИМИТЫ
# =============================================================================

MAX_CHARACTERS_PER_ACCOUNT = 2
MAX_CHARACTER_NAME_LENGTH = 32
MIN_CHARACTER_NAME_LENGTH = 2

# =============================================================================
# ПОЛА
# =============================================================================

GENDERS = {
    "male": {"name": "Мужской", "name_en": "Male"},
    "female": {"name": "Женский", "name_en": "Female"},
}

# =============================================================================
# СПОСОБНОСТИ И ОСОБЕННОСТИ (Features) - Русские названия и описания
# =============================================================================

FEATURES = {
    # === РАСОВЫЕ ОСОБЕННОСТИ ===
    # Человек
    "extra_language": {
        "name": "Дополнительный язык",
        "description": "Вы знаете один дополнительный язык на ваш выбор."
    },
    "extra_skill": {
        "name": "Дополнительный навык",
        "description": "Вы получаете владение одним дополнительным навыком на ваш выбор."
    },
    # Эльф
    "darkvision": {
        "name": "Тёмное зрение",
        "description": "Вы видите в темноте на расстоянии 60 футов в оттенках серого."
    },
    "fey_ancestry": {
        "name": "Наследие фей",
        "description": "Вы имеете преимущество на спасброски против очарования, и вас нельзя магически усыпить."
    },
    "trance": {
        "name": "Транс",
        "description": "Эльфам не нужен сон. Вместо этого они медитируют 4 часа в день, что равносильно 8 часам сна человека."
    },
    # Дварф
    "dwarven_resilience": {
        "name": "Дварфийская устойчивость",
        "description": "Вы имеете преимущество на спасброски против яда и сопротивление урону ядом."
    },
    "stonecunning": {
        "name": "Знание камня",
        "description": "При проверке Истории, связанной с происхождением каменной кладки, вы считаетесь владеющим навыком История и добавляете удвоенный бонус мастерства."
    },
    # Полурослик
    "lucky": {
        "name": "Везучий",
        "description": "Когда при броске атаки, проверке характеристики или спасброске у вас выпадает 1, вы можете перебросить кость и должны использовать новый результат."
    },
    "brave": {
        "name": "Храбрый",
        "description": "Вы имеете преимущество на спасброски против испуга."
    },
    "halfling_nimbleness": {
        "name": "Проворство полурослика",
        "description": "Вы можете проходить сквозь пространство, занятое существом, размер которого больше вашего."
    },
    # Орк
    "aggressive": {
        "name": "Агрессия",
        "description": "Бонусным действием вы можете переместиться на расстояние до своей скорости к видимому враждебному существу."
    },
    "powerful_build": {
        "name": "Мощное телосложение",
        "description": "Вы считаетесь существом на один размер больше при определении грузоподъёмности."
    },
    # Тифлинг
    "hellish_resistance": {
        "name": "Сопротивление адскому пламени",
        "description": "Вы имеете сопротивление урону огнём."
    },
    "infernal_legacy": {
        "name": "Инфернальное наследие",
        "description": "Вы знаете заговор Чудотворство. С 3-го уровня можете накладывать Адское возмездие раз в день. С 5-го — Тьму раз в день."
    },

    # === КЛАССОВЫЕ ОСОБЕННОСТИ ===
    # Воин
    "fighting_style": {
        "name": "Боевой стиль",
        "description": "Вы выбираете стиль боя: Защита (+1 КБ), Дуэлянт (+2 урона одноручным), Стрельба (+2 к атаке дальним), Сражение большим оружием (переброс 1-2 урона) или другие."
    },
    "second_wind": {
        "name": "Второе дыхание",
        "description": "Бонусным действием вы можете восстановить 1d10 + уровень воина HP. Раз в короткий или длинный отдых."
    },
    # Волшебник
    "spellcasting": {
        "name": "Использование заклинаний",
        "description": "Вы можете накладывать заклинания, используя слоты заклинаний. Количество слотов восстанавливается после длинного отдыха."
    },
    "arcane_recovery": {
        "name": "Магическое восстановление",
        "description": "Раз в день во время короткого отдыха вы можете восстановить слоты заклинаний с суммой уровней до половины уровня волшебника (округлённой вверх)."
    },
    # Плут
    "expertise": {
        "name": "Экспертиза",
        "description": "Выберите 2 навыка, которыми владеете (или воровские инструменты). Ваш бонус мастерства для них удваивается."
    },
    "sneak_attack": {
        "name": "Скрытая атака",
        "description": "Раз в ход вы наносите дополнительный урон 1d6 существу, по которому попадаете, если у вас есть преимущество или рядом с целью находится ваш союзник."
    },
    "thieves_cant": {
        "name": "Воровской жаргон",
        "description": "Вы знаете тайный язык воров — смесь диалекта, жестов и шифров для скрытой передачи сообщений."
    },
    # Жрец
    "divine_domain": {
        "name": "Божественный домен",
        "description": "Выберите домен, связанный с вашим божеством. Домен даёт вам дополнительные заклинания и способности."
    },
    # Следопыт
    "favored_enemy": {
        "name": "Избранный враг",
        "description": "Выберите тип врага (аберрации, звери, драконы и т.д.). Вы получаете преимущество на проверки Выживания и Интеллекта против них."
    },
    "natural_explorer": {
        "name": "Исследователь природы",
        "description": "Выберите тип местности (лес, горы, болото и т.д.). Вы получаете преимущества при путешествии и выживании в этой среде."
    },
    # Паладин
    "divine_sense": {
        "name": "Божественное чувство",
        "description": "Действием вы можете определить местоположение небожителей, исчадий и нежити в пределах 60 футов."
    },
    "lay_on_hands": {
        "name": "Наложение рук",
        "description": "У вас есть запас исцеления равный уровню паладина × 5 HP. Касанием вы можете тратить очки для лечения или снятия болезни/яда (5 очков)."
    },
    # Варвар
    "rage": {
        "name": "Ярость",
        "description": "Бонусным действием вы впадаете в ярость на 1 минуту: +2 к урону силовым оружием, сопротивление физическому урону, преимущество на проверки Силы."
    },
    "unarmored_defense": {
        "name": "Защита без доспехов",
        "description": "Без брони ваш КБ = 10 + модификатор Ловкости + модификатор Телосложения (варвар) или Мудрости (монах)."
    },
    # Монах
    "martial_arts": {
        "name": "Боевые искусства",
        "description": "Вы можете использовать Ловкость вместо Силы для атак. Урон безоружной атаки 1d4. После атаки монашеским оружием — бонусная безоружная атака."
    },
    # Друид
    "druidic": {
        "name": "Друидический язык",
        "description": "Вы знаете тайный язык друидов. Можете оставлять скрытые послания, которые заметят только другие друиды."
    },
    # Колдун
    "otherworldly_patron": {
        "name": "Потусторонний покровитель",
        "description": "Выберите сущность-покровителя: Архифея, Исчадие или Великий Древний. Покровитель определяет ваши дополнительные способности."
    },
    "pact_magic": {
        "name": "Магия договора",
        "description": "Ваши слоты заклинаний восстанавливаются после короткого отдыха, а не только после длинного."
    },
    # Бард
    "bardic_inspiration": {
        "name": "Вдохновение барда",
        "description": "Бонусным действием вы даёте союзнику кость d6, которую он может добавить к проверке, атаке или спасброску. Использований = модификатор Харизмы."
    },
    # Чародей
    "sorcerous_origin": {
        "name": "Происхождение чародея",
        "description": "Выберите источник вашей магии: Драконья родословная или Дикая магия. Это определяет ваши уникальные способности."
    },

    # === ОСОБЕННОСТИ ПРЕДЫСТОРИЙ ===
    "shelter_of_the_faithful": {
        "name": "Приют верующего",
        "description": "Вы можете получить бесплатное лечение и уход в храмах вашей веры. Служители помогут вам, но не станут рисковать жизнью."
    },
    "criminal_contact": {
        "name": "Криминальные связи",
        "description": "У вас есть надёжный контакт в преступном мире, который может предоставить информацию и временное убежище."
    },
    "rustic_hospitality": {
        "name": "Деревенское гостеприимство",
        "description": "Простой народ укроет вас, даст кров и пищу, защитит от закона — но не станет рисковать жизнью."
    },
    "position_of_privilege": {
        "name": "Положение привилегии",
        "description": "Благодаря благородному происхождению люди относятся к вам благосклонно. Вас принимают в высшем обществе."
    },
    "researcher": {
        "name": "Исследователь",
        "description": "Если вы не знаете какую-то информацию, вы часто знаете, где её найти — в библиотеке, университете или у другого мудреца."
    },
    "military_rank": {
        "name": "Воинское звание",
        "description": "Солдаты из вашей бывшей армии узнают ваше звание и окажут помощь. Вы имеете доступ к военным лагерям и крепостям."
    },
    "false_identity": {
        "name": "Вторая личность",
        "description": "Вы создали вторую личность с документами, связями и маскировкой. Можете переключаться между личностями."
    },
    "by_popular_demand": {
        "name": "По многочисленным просьбам",
        "description": "В любом населённом пункте вы найдёте место для выступления с бесплатным жильём и едой среднего качества."
    },
    "discovery": {
        "name": "Открытие",
        "description": "В своём уединении вы сделали важное открытие — природы вселенной, богов или чего-то ещё. Работайте с Мастером над деталями."
    },
    "wanderer": {
        "name": "Странник",
        "description": "Вы отлично помните карты и местность. Можете найти пищу и воду для себя и пяти других людей каждый день."
    },
}


def get_feature_info(feature_id: str) -> dict:
    """Получить информацию о способности по ID."""
    return FEATURES.get(feature_id, {"name": feature_id, "description": "Описание недоступно"})


# =============================================================================
# СПИСОК ВСЕХ МОДЕЛЕЙ
# =============================================================================

def get_all_models() -> list:
    """Получить список всех доступных моделей персонажей."""
    models = []
    for race_id, race_data in RACES.items():
        for gender, model_name in race_data["models"].items():
            models.append(model_name)
    return models


def get_model_for_race_gender(race: str, gender: str) -> str:
    """Получить название модели для расы и пола."""
    race_data = RACES.get(race, RACES["human"])
    return race_data["models"].get(gender, race_data["models"]["male"])
