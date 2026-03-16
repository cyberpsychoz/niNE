"""
Mundane (non-combat) items for D&D 5e starting equipment.
Auto-loaded by entities/__init__.py glob.
"""

from nine.plugins.inventory.entities.base import Item


# =============================================================================
# Spellcasting Focuses & Tools
# =============================================================================

class Spellbook(Item):
    CLASS_ID = "spellbook"
    NAME = "Книга заклинаний"
    NAME_EN = "Spellbook"
    DESCRIPTION = "Книга с записанными заклинаниями волшебника."
    CATEGORY = "tool"
    WEIGHT = 3.0
    DROPPABLE = False

    def get_value(self):
        return 5000  # 50 gp


class HolySymbol(Item):
    CLASS_ID = "holy_symbol"
    NAME = "Священный символ"
    NAME_EN = "Holy Symbol"
    DESCRIPTION = "Амулет или эмблема божества, используется как фокус для заклинаний."
    CATEGORY = "tool"
    WEIGHT = 0.0

    def get_value(self):
        return 500  # 5 gp


class ArcaneFocus(Item):
    CLASS_ID = "arcane_focus"
    NAME = "Магическая фокусировка"
    NAME_EN = "Arcane Focus"
    DESCRIPTION = "Кристалл, жезл или посох, используемый как фокус для заклинаний."
    CATEGORY = "tool"
    WEIGHT = 1.0

    def get_value(self):
        return 1000  # 10 gp


class ThievesTools(Item):
    CLASS_ID = "thieves_tools"
    NAME = "Воровские инструменты"
    NAME_EN = "Thieves' Tools"
    DESCRIPTION = "Набор отмычек, маленьких зеркал и щипцов для взлома замков."
    CATEGORY = "tool"
    WEIGHT = 1.0

    def get_value(self):
        return 2500  # 25 gp


class HerbalismKit(Item):
    CLASS_ID = "herbalism_kit"
    NAME = "Набор травника"
    NAME_EN = "Herbalism Kit"
    DESCRIPTION = "Ступка, пестик, мешочки и флаконы для сбора и приготовления трав."
    CATEGORY = "tool"
    WEIGHT = 3.0

    def get_value(self):
        return 500  # 5 gp


class DisguiseKit(Item):
    CLASS_ID = "disguise_kit"
    NAME = "Набор для грима"
    NAME_EN = "Disguise Kit"
    DESCRIPTION = "Косметика, краска для волос и накладные элементы для маскировки."
    CATEGORY = "tool"
    WEIGHT = 3.0

    def get_value(self):
        return 2500  # 25 gp


class ArtisansTools(Item):
    CLASS_ID = "artisans_tools"
    NAME = "Ремесленные инструменты"
    NAME_EN = "Artisan's Tools"
    DESCRIPTION = "Набор инструментов для определённого ремесла."
    CATEGORY = "tool"
    WEIGHT = 5.0

    def get_value(self):
        return 1500  # varies


# =============================================================================
# Musical Instruments & Packs
# =============================================================================

class Lute(Item):
    CLASS_ID = "lute"
    NAME = "Лютня"
    NAME_EN = "Lute"
    DESCRIPTION = "Струнный музыкальный инструмент."
    CATEGORY = "tool"
    WEIGHT = 2.0

    def get_value(self):
        return 3500  # 35 gp


class MusicalInstrument(Item):
    CLASS_ID = "musical_instrument"
    NAME = "Музыкальный инструмент"
    NAME_EN = "Musical Instrument"
    DESCRIPTION = "Музыкальный инструмент на ваш выбор."
    CATEGORY = "tool"
    WEIGHT = 2.0

    def get_value(self):
        return 2000  # varies


class ExplorersPack(Item):
    CLASS_ID = "explorers_pack"
    NAME = "Набор путешественника"
    NAME_EN = "Explorer's Pack"
    DESCRIPTION = "Рюкзак, спальный мешок, котелок, факелы, верёвка и рацион."
    CATEGORY = "misc"
    WEIGHT = 10.0

    def get_value(self):
        return 1000  # 10 gp


# =============================================================================
# Clothing
# =============================================================================

class CommonClothes(Item):
    CLASS_ID = "common_clothes"
    NAME = "Обычная одежда"
    NAME_EN = "Common Clothes"
    DESCRIPTION = "Простая одежда из грубой ткани."
    CATEGORY = "misc"
    WEIGHT = 3.0

    def get_value(self):
        return 50  # 5 sp


class DarkCommonClothes(Item):
    CLASS_ID = "dark_common_clothes"
    NAME = "Тёмная обычная одежда"
    NAME_EN = "Dark Common Clothes"
    DESCRIPTION = "Тёмная одежда с капюшоном, удобная для скрытности."
    CATEGORY = "misc"
    WEIGHT = 3.0

    def get_value(self):
        return 50  # 5 sp


class FineClothes(Item):
    CLASS_ID = "fine_clothes"
    NAME = "Дорогая одежда"
    NAME_EN = "Fine Clothes"
    DESCRIPTION = "Элегантная одежда из дорогих тканей."
    CATEGORY = "misc"
    WEIGHT = 6.0

    def get_value(self):
        return 1500  # 15 gp


class Vestments(Item):
    CLASS_ID = "vestments"
    NAME = "Ризы"
    NAME_EN = "Vestments"
    DESCRIPTION = "Церемониальные одежды служителя храма."
    CATEGORY = "misc"
    WEIGHT = 4.0

    def get_value(self):
        return 100  # 1 gp


class Costume(Item):
    CLASS_ID = "costume"
    NAME = "Костюм"
    NAME_EN = "Costume"
    DESCRIPTION = "Яркий костюм для выступлений."
    CATEGORY = "misc"
    WEIGHT = 4.0

    def get_value(self):
        return 500  # 5 gp


class TravelersClothes(Item):
    CLASS_ID = "travelers_clothes"
    NAME = "Дорожная одежда"
    NAME_EN = "Traveler's Clothes"
    DESCRIPTION = "Прочная одежда для путешествий."
    CATEGORY = "misc"
    WEIGHT = 4.0

    def get_value(self):
        return 200  # 2 gp


# =============================================================================
# Miscellaneous Items
# =============================================================================

class PrayerBook(Item):
    CLASS_ID = "prayer_book"
    NAME = "Молитвенник"
    NAME_EN = "Prayer Book"
    DESCRIPTION = "Книга с молитвами и священными текстами."
    CATEGORY = "misc"
    WEIGHT = 1.0

    def get_value(self):
        return 100  # 1 gp


class Incense(Item):
    CLASS_ID = "incense"
    NAME = "Благовония"
    NAME_EN = "Incense"
    DESCRIPTION = "Ароматические палочки для ритуалов."
    CATEGORY = "misc"
    MAX_STACK = 10
    WEIGHT = 0.1

    def get_value(self):
        return 10


class BeltPouch(Item):
    CLASS_ID = "belt_pouch"
    NAME = "Поясной кошелёк"
    NAME_EN = "Belt Pouch"
    DESCRIPTION = "Маленький кожаный мешочек на поясе."
    CATEGORY = "misc"
    WEIGHT = 1.0

    def get_value(self):
        return 50  # 5 sp


class Crowbar(Item):
    CLASS_ID = "crowbar"
    NAME = "Ломик"
    NAME_EN = "Crowbar"
    DESCRIPTION = "Железный ломик. Даёт преимущество на проверки Силы для взлома."
    CATEGORY = "tool"
    WEIGHT = 5.0

    def get_value(self):
        return 200  # 2 gp


class Shovel(Item):
    CLASS_ID = "shovel"
    NAME = "Лопата"
    NAME_EN = "Shovel"
    DESCRIPTION = "Железная лопата."
    CATEGORY = "tool"
    WEIGHT = 5.0

    def get_value(self):
        return 200  # 2 gp


class IronPot(Item):
    CLASS_ID = "iron_pot"
    NAME = "Железный котелок"
    NAME_EN = "Iron Pot"
    DESCRIPTION = "Чугунный котелок для приготовления пищи."
    CATEGORY = "misc"
    WEIGHT = 10.0

    def get_value(self):
        return 200  # 2 gp


class SignetRing(Item):
    CLASS_ID = "signet_ring"
    NAME = "Перстень с печатью"
    NAME_EN = "Signet Ring"
    DESCRIPTION = "Кольцо с фамильной печатью."
    CATEGORY = "misc"
    WEIGHT = 0.0

    def get_value(self):
        return 500  # 5 gp


class ScrollOfPedigree(Item):
    CLASS_ID = "scroll_of_pedigree"
    NAME = "Свиток родословной"
    NAME_EN = "Scroll of Pedigree"
    DESCRIPTION = "Документ, подтверждающий ваше благородное происхождение."
    CATEGORY = "misc"
    WEIGHT = 0.0

    def get_value(self):
        return 100  # 1 gp


class Ink(Item):
    CLASS_ID = "ink"
    NAME = "Чернила"
    NAME_EN = "Ink"
    DESCRIPTION = "Флакон чёрных чернил."
    CATEGORY = "misc"
    WEIGHT = 0.0

    def get_value(self):
        return 1000  # 10 gp


class Quill(Item):
    CLASS_ID = "quill"
    NAME = "Перо для письма"
    NAME_EN = "Quill"
    DESCRIPTION = "Гусиное перо для письма."
    CATEGORY = "misc"
    WEIGHT = 0.0

    def get_value(self):
        return 2  # 2 cp


class LetterFromColleague(Item):
    CLASS_ID = "letter_from_colleague"
    NAME = "Письмо от коллеги"
    NAME_EN = "Letter from a Colleague"
    DESCRIPTION = "Письмо с вопросом, на который вы ещё не нашли ответа."
    CATEGORY = "misc"
    DROPPABLE = False
    WEIGHT = 0.0

    def get_value(self):
        return 0


class InsigniaOfRank(Item):
    CLASS_ID = "insignia_of_rank"
    NAME = "Знак воинского звания"
    NAME_EN = "Insignia of Rank"
    DESCRIPTION = "Знак отличия, подтверждающий ваше военное звание."
    CATEGORY = "misc"
    WEIGHT = 0.0

    def get_value(self):
        return 100  # 1 gp


class Trophy(Item):
    CLASS_ID = "trophy"
    NAME = "Трофей"
    NAME_EN = "Trophy"
    DESCRIPTION = "Памятный трофей из прошлого — зуб, лоскут знамени или иная реликвия."
    CATEGORY = "misc"
    WEIGHT = 0.5

    def get_value(self):
        return 50


class DiceSet(Item):
    CLASS_ID = "dice_set"
    NAME = "Набор игральных костей"
    NAME_EN = "Dice Set"
    DESCRIPTION = "Набор кубиков для азартных игр."
    CATEGORY = "tool"
    WEIGHT = 0.0

    def get_value(self):
        return 10  # 1 sp


class ConTools(Item):
    CLASS_ID = "con_tools"
    NAME = "Инструменты мошенника"
    NAME_EN = "Con Tools"
    DESCRIPTION = "Набор инструментов для мошенничества: поддельные печати, фальшивые документы."
    CATEGORY = "tool"
    WEIGHT = 1.0

    def get_value(self):
        return 1500  # 15 gp


class FavorOfAdmirer(Item):
    CLASS_ID = "favor_of_admirer"
    NAME = "Подарок поклонника"
    NAME_EN = "Favor of an Admirer"
    DESCRIPTION = "Любовное письмо, локон волос или безделушка от поклонника."
    CATEGORY = "misc"
    DROPPABLE = False
    WEIGHT = 0.0

    def get_value(self):
        return 0


class ScrollCase(Item):
    CLASS_ID = "scroll_case"
    NAME = "Футляр для свитков"
    NAME_EN = "Scroll Case"
    DESCRIPTION = "Цилиндрический кожаный футляр для хранения свитков и записей."
    CATEGORY = "misc"
    WEIGHT = 1.0

    def get_value(self):
        return 100  # 1 gp


class WinterBlanket(Item):
    CLASS_ID = "winter_blanket"
    NAME = "Зимнее одеяло"
    NAME_EN = "Winter Blanket"
    DESCRIPTION = "Тёплое шерстяное одеяло."
    CATEGORY = "misc"
    WEIGHT = 3.0

    def get_value(self):
        return 50  # 5 sp


class HuntingTrap(Item):
    CLASS_ID = "hunting_trap"
    NAME = "Охотничий капкан"
    NAME_EN = "Hunting Trap"
    DESCRIPTION = "Стальной капкан с зубцами. DC 13 Сила чтобы освободиться."
    CATEGORY = "tool"
    WEIGHT = 25.0

    def get_value(self):
        return 500  # 5 gp
