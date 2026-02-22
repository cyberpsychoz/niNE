/**
 * Character Create Component - 8-Step D&D 5e Wizard
 *
 * Steps: 1.Name/Gender  2.Race  3.Class  4.Ability Scores  5.Skills  6.Background  7.Faction  8.Confirm
 */

// ==================== D&D 5e Data (mirrors sh_constants.py) ====================

const DND_RACES = {
    human:    { name: "Человек",    desc: "Универсальные и адаптивные",   bonuses: {strength:1,dexterity:1,constitution:1,intelligence:1,wisdom:1,charisma:1}, speed: 30, features: ["extra_language","extra_skill"] },
    elf:      { name: "Эльф",      desc: "Ловкие и грациозные",           bonuses: {dexterity:2,intelligence:1}, speed: 30, features: ["darkvision","fey_ancestry","trance"] },
    dwarf:    { name: "Дварф",    desc: "Выносливые и стойкие",          bonuses: {constitution:2,wisdom:1},    speed: 25, features: ["darkvision","dwarven_resilience","stonecunning"] },
    halfling: { name: "Полурослик", desc: "Маленькие и проворные",       bonuses: {dexterity:2,charisma:1},     speed: 25, features: ["lucky","brave","halfling_nimbleness"] },
    orc:      { name: "Орк",      desc: "Сильные и выносливые",          bonuses: {strength:2,constitution:1},  speed: 30, features: ["darkvision","aggressive","powerful_build"] },
    tiefling: { name: "Тифлинг", desc: "Инфернальное наследие",          bonuses: {charisma:2,intelligence:1},  speed: 30, features: ["darkvision","hellish_resistance","infernal_legacy"] },
};

const DND_CLASSES = {
    fighter:   { name: "Воин",      desc: "Мастер боя, владеющий разнообразным оружием и тактиками",                hitDie: 10, primary: ["STR","CON"], skills: ["Acrobatics","Animal Handling","Athletics","History","Insight","Intimidation","Perception","Survival"],                              numSkills: 2, features: ["fighting_style","second_wind"] },
    wizard:    { name: "Волшебник", desc: "Учёный маг, черпающий силу из изучения тайной магии",                    hitDie: 6,  primary: ["INT"],       skills: ["Arcana","History","Insight","Investigation","Medicine","Religion"],                                                                  numSkills: 2, features: ["spellcasting","arcane_recovery"] },
    rogue:     { name: "Плут",      desc: "Мастер скрытности и точных ударов",                                     hitDie: 8,  primary: ["DEX"],       skills: ["Acrobatics","Athletics","Deception","Insight","Intimidation","Investigation","Perception","Performance","Persuasion","Sleight of Hand","Stealth"], numSkills: 4, features: ["expertise","sneak_attack","thieves_cant"] },
    cleric:    { name: "Жрец",      desc: "Божественный посланник, несущий волю богов",                             hitDie: 8,  primary: ["WIS"],       skills: ["History","Insight","Medicine","Persuasion","Religion"],                                                                              numSkills: 2, features: ["spellcasting","divine_domain"] },
    ranger:    { name: "Следопыт",  desc: "Воин дикой природы, охотник и следопыт",                                hitDie: 10, primary: ["DEX","WIS"], skills: ["Animal Handling","Athletics","Insight","Investigation","Nature","Perception","Stealth","Survival"],                                   numSkills: 3, features: ["favored_enemy","natural_explorer"] },
    paladin:   { name: "Паладин",   desc: "Святой воин, связанный священной клятвой",                               hitDie: 10, primary: ["STR","CHA"], skills: ["Athletics","Insight","Intimidation","Medicine","Persuasion","Religion"],                                                             numSkills: 2, features: ["divine_sense","lay_on_hands"] },
    barbarian: { name: "Варвар",    desc: "Свирепый воин первобытной мощи",                                        hitDie: 12, primary: ["STR","CON"], skills: ["Animal Handling","Athletics","Intimidation","Nature","Perception","Survival"],                                                       numSkills: 2, features: ["rage","unarmored_defense"] },
    bard:      { name: "Бард",      desc: "Мастер песен, историй и магии слов",                                    hitDie: 8,  primary: ["CHA"],       skills: ["any"],                                                                                                                              numSkills: 3, features: ["spellcasting","bardic_inspiration"] },
    druid:     { name: "Друид",     desc: "Жрец природы, хранитель равновесия",                                    hitDie: 8,  primary: ["WIS"],       skills: ["Arcana","Animal Handling","Insight","Medicine","Nature","Perception","Religion","Survival"],                                          numSkills: 2, features: ["druidic","spellcasting"] },
    monk:      { name: "Монах",     desc: "Мастер боевых искусств и внутренней силы",                              hitDie: 8,  primary: ["DEX","WIS"], skills: ["Acrobatics","Athletics","History","Insight","Religion","Stealth"],                                                                   numSkills: 2, features: ["unarmored_defense","martial_arts"] },
    sorcerer:  { name: "Чародей",   desc: "Маг с врождённой магической силой",                                     hitDie: 6,  primary: ["CHA"],       skills: ["Arcana","Deception","Insight","Intimidation","Persuasion","Religion"],                                                               numSkills: 2, features: ["spellcasting","sorcerous_origin"] },
    warlock:   { name: "Колдун",    desc: "Маг, заключивший договор с могущественной сущностью",                    hitDie: 8,  primary: ["CHA"],       skills: ["Arcana","Deception","History","Intimidation","Investigation","Nature","Religion"],                                                    numSkills: 2, features: ["otherworldly_patron","pact_magic"] },
};

const DND_BACKGROUNDS = {
    acolyte:     { name: "Послушник",      desc: "Вы провели жизнь, служа храму",                      skills: ["Insight","Religion"] },
    criminal:    { name: "Преступник",     desc: "У вас криминальное прошлое",                          skills: ["Deception","Stealth"] },
    folk_hero:   { name: "Народный герой", desc: "Вы совершили подвиг, спасший простых людей",          skills: ["Animal Handling","Survival"] },
    noble:       { name: "Дворянин",       desc: "Вы родились в привилегированной семье",               skills: ["History","Persuasion"] },
    sage:        { name: "Мудрец",         desc: "Вы посвятили жизнь изучению знаний",                  skills: ["Arcana","History"] },
    soldier:     { name: "Солдат",         desc: "Вы служили в армии",                                  skills: ["Athletics","Intimidation"] },
    charlatan:   { name: "Шарлатан",       desc: "Вы мастер обмана и мошенничества",                    skills: ["Deception","Sleight of Hand"] },
    entertainer: { name: "Артист",         desc: "Вы выступаете перед публикой",                        skills: ["Acrobatics","Performance"] },
    hermit:      { name: "Отшельник",      desc: "Вы жили в уединении",                                skills: ["Medicine","Religion"] },
    outlander:   { name: "Чужеземец",      desc: "Вы выросли вдали от цивилизации",                    skills: ["Athletics","Survival"] },
};

const DND_SKILLS = {
    "Athletics":       { ability: "strength", label: "Атлетика" },
    "Acrobatics":      { ability: "dexterity", label: "Акробатика" },
    "Sleight of Hand": { ability: "dexterity", label: "Ловкость рук" },
    "Stealth":         { ability: "dexterity", label: "Скрытность" },
    "Arcana":          { ability: "intelligence", label: "Магия" },
    "History":         { ability: "intelligence", label: "История" },
    "Investigation":   { ability: "intelligence", label: "Расследование" },
    "Nature":          { ability: "intelligence", label: "Природа" },
    "Religion":        { ability: "intelligence", label: "Религия" },
    "Animal Handling": { ability: "wisdom", label: "Уход за животными" },
    "Insight":         { ability: "wisdom", label: "Проницательность" },
    "Medicine":        { ability: "wisdom", label: "Медицина" },
    "Perception":      { ability: "wisdom", label: "Внимание" },
    "Survival":        { ability: "wisdom", label: "Выживание" },
    "Deception":       { ability: "charisma", label: "Обман" },
    "Intimidation":    { ability: "charisma", label: "Запугивание" },
    "Performance":     { ability: "charisma", label: "Выступление" },
    "Persuasion":      { ability: "charisma", label: "Убеждение" },
};

const DND_ABILITIES = [
    { id: "strength",     name: "Сила",          abbr: "СИЛ" },
    { id: "dexterity",    name: "Ловкость",      abbr: "ЛОВ" },
    { id: "constitution", name: "Телосложение",   abbr: "ТЕЛ" },
    { id: "intelligence", name: "Интеллект",      abbr: "ИНТ" },
    { id: "wisdom",       name: "Мудрость",       abbr: "МДР" },
    { id: "charisma",     name: "Харизма",        abbr: "ХАР" },
];

const POINT_BUY_COST = { 8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:7, 15:9 };
const POINT_BUY_TOTAL = 27;

const DND_FACTIONS = {
    alliance: { name: "Альянс",      desc: "Союз людей, эльфов и дварфов. Стремятся к порядку и справедливости.", color: "#0066CC" },
    horde:    { name: "Орда",        desc: "Союз орков и других воинственных рас. Ценят силу и честь.",           color: "#CC0000" },
    neutral:  { name: "Нейтральные", desc: "Свободные искатели приключений, не связанные политикой.",             color: "#999999" },
    undead:   { name: "Нежить",      desc: "Проклятые существа из тёмных земель. Отвергнуты живыми.",             color: "#6600CC" },
};

const DND_FEATURES = {
    extra_language:       { name: "Доп. язык",                desc: "Вы знаете один дополнительный язык по вашему выбору." },
    extra_skill:          { name: "Доп. навык",               desc: "Вы получаете владение одним дополнительным навыком по вашему выбору." },
    darkvision:           { name: "Тёмное зрение",            desc: "Вы видите в тусклом свете на 60 футов как при ярком свете, в оттенках серого." },
    fey_ancestry:         { name: "Наследие фей",             desc: "Вы совершаете с преимуществом спасброски от очарования, и магия не может усыпить вас." },
    trance:               { name: "Транс",                    desc: "Эльфам не нужен сон. Вместо этого они медитируют 4 часа в день, что равноценно 8 часам сна человека." },
    dwarven_resilience:   { name: "Дварфийская стойкость",    desc: "Вы совершаете с преимуществом спасброски от яда и имеете сопротивление к урону ядом." },
    stonecunning:         { name: "Знание камня",             desc: "При проверках Истории, связанных с каменной кладкой, добавляйте удвоенный бонус мастерства." },
    lucky:                { name: "Везучий",                  desc: "Когда вы выбрасываете 1 на броске атаки, проверке характеристики или спасброске, вы можете перебросить и должны использовать новый результат." },
    brave:                { name: "Храбрый",                  desc: "Вы совершаете с преимуществом спасброски от испуга." },
    halfling_nimbleness:  { name: "Проворство полуросликов",  desc: "Вы можете проходить через пространство существа, которое больше вас на один размер." },
    aggressive:           { name: "Агрессивный",              desc: "Бонусным действием вы можете переместиться на расстояние до вашей скорости к видимому враждебному существу." },
    powerful_build:       { name: "Мощное телосложение",      desc: "Вы считаетесь на один размер больше для определения грузоподъёмности." },
    hellish_resistance:   { name: "Адское сопротивление",     desc: "Вы имеете сопротивление к урону огнём." },
    infernal_legacy:      { name: "Инфернальное наследие",    desc: "Вы знаете заговор Чудотворство. На 3-м уровне — Адское возмездие 1/день. На 5-м — Тьма 1/день." },
    fighting_style:       { name: "Боевой стиль",             desc: "Выберите боевой стиль: Оборона (+1 КЗ), Дуэлянт (+2 урон одноручным), Стрельба (+2 дальняя атака), Сражение большим оружием (перебрось 1-2 урона)." },
    second_wind:          { name: "Второе дыхание",           desc: "Бонусным действием восстановите 1к10 + уровень воина ОЗ. Один раз за короткий или длинный отдых." },
    spellcasting:         { name: "Использование заклинаний", desc: "Вы можете использовать заклинания с помощью ячеек заклинаний. Ячейки восстанавливаются после длинного отдыха." },
    arcane_recovery:      { name: "Магическое восстановление", desc: "Один раз в день во время короткого отдыха восстановите ячейки заклинаний с суммарным уровнем до половины уровня волшебника (с округлением вверх)." },
    expertise:            { name: "Компетентность",           desc: "Выберите 2 навыка с владением (или воровские инструменты). Ваш бонус мастерства удваивается для них." },
    sneak_attack:         { name: "Скрытая атака",            desc: "Один раз за ход нанесите дополнительный урон 1к6, если у вас есть преимущество или союзник рядом с целью." },
    thieves_cant:         { name: "Воровской жаргон",         desc: "Вы знаете тайный язык воров — смесь диалекта, жестов и шифров." },
    divine_domain:        { name: "Божественный домен",       desc: "Выберите домен, связанный с вашим божеством. Он даёт дополнительные заклинания и способности." },
    favored_enemy:        { name: "Избранный враг",           desc: "Выберите тип врага. Вы получаете преимущество на проверки Выживания и Интеллекта против них." },
    natural_explorer:     { name: "Странник",                 desc: "Выберите тип местности. Вы получаете преимущества при путешествии и выживании в этой среде." },
    divine_sense:         { name: "Божественное чувство",     desc: "Действием вы обнаруживаете небожителей, исчадий и нежить в пределах 60 футов." },
    lay_on_hands:         { name: "Наложение рук",            desc: "У вас есть запас исцеления в размере уровень паладина x 5 ОЗ. Касанием исцеляйте или снимайте болезнь/яд (5 очков)." },
    rage:                 { name: "Ярость",                   desc: "Бонусным действием впадите в ярость на 1 минуту: +2 урон оружием Силы, сопротивление физическому урону, преимущество на проверки Силы." },
    unarmored_defense:    { name: "Защита без доспехов",      desc: "Без доспехов КЗ = 10 + мод. ЛОВ + мод. ТЕЛ (варвар) или мод. МДР (монах)." },
    martial_arts:         { name: "Боевые искусства",         desc: "Используйте ЛОВ вместо СИЛ для атак. Безоружный урон 1к4. После атаки оружием монаха — бонусный безоружный удар." },
    druidic:              { name: "Друидический",             desc: "Вы знаете тайный язык друидов. Вы можете оставлять скрытые послания, которые замечают только другие друиды." },
    otherworldly_patron:  { name: "Потусторонний покровитель", desc: "Выберите покровителя: Архифея, Исчадие или Великий Древний. Определяет ваши дополнительные способности." },
    pact_magic:           { name: "Магия договора",           desc: "Ваши ячейки заклинаний восстанавливаются после короткого отдыха, а не только после длинного." },
    bardic_inspiration:   { name: "Бардовское вдохновение",   desc: "Бонусным действием дайте союзнику к6 для добавления к проверке, атаке или спасброску. Использований = мод. Харизмы." },
    sorcerous_origin:     { name: "Происхождение чародея",    desc: "Выберите источник вашей магии: Драконье происхождение или Дикая магия." },
};

// ==================== Helpers ====================

function calcModifier(score) { return Math.floor((score - 10) / 2); }
function modStr(mod) { return (mod >= 0 ? '+' : '') + mod; }

function getAllSkillNames() {
    return Object.keys(DND_SKILLS).sort();
}

// ==================== Component ====================

const STEP_LABELS = ["Имя", "Раса", "Класс", "Хар-ки", "Навыки", "Предыстория", "Фракция", "Подтверждение"];

class CharacterCreate {
    constructor(params = {}) {
        this.params = params;
        this.element = null;
        this.currentStep = 0; // 0-indexed

        this.characterData = {
            character_name: "", gender: "male", race: "human", class_name: "fighter",
            background: "", faction: "neutral",
            strength: 10, dexterity: 10, constitution: 10,
            intelligence: 10, wisdom: 10, charisma: 10,
            skills: {},
        };

        this._tooltip = null;

        console.log('[CharacterCreate] Created');
    }

    async render() {
        const response = await fetch('templates/character-create.html');
        const html = await response.text();

        const app = document.getElementById('app');
        app.innerHTML = html;

        this.element = document.getElementById('character-create-screen');

        this._pythonHandler = this._handlePythonMessage.bind(this);
        window.addEventListener('python-message', this._pythonHandler);

        this.renderStep();

        console.log('[CharacterCreate] Rendered');
    }

    _handlePythonMessage(event) {
        const { type, data } = event.detail;
        if (type === 'character_create_failed') {
            this._showValidation('Ошибка: ' + (data.reason || 'Неизвестная ошибка'));
        }
    }

    // ========== Navigation ==========

    renderStep() {
        this._renderStepDots();
        this._renderContent();
        this._attachNavListeners();
    }

    _renderStepDots() {
        const container = document.getElementById('wizard-steps');
        if (!container) return;
        container.innerHTML = STEP_LABELS.map((label, i) => {
            let cls = 'wizard-step-dot';
            if (i === this.currentStep) cls += ' active';
            else if (i < this.currentStep) cls += ' completed';
            return `<div class="${cls}" title="${label}">${i + 1}</div>`;
        }).join('');
    }

    _renderContent() {
        const content = document.getElementById('wizard-content');
        if (!content) return;

        switch (this.currentStep) {
            case 0: this._renderNameGender(content); break;
            case 1: this._renderRace(content); break;
            case 2: this._renderClass(content); break;
            case 3: this._renderAbilityScores(content); break;
            case 4: this._renderSkills(content); break;
            case 5: this._renderBackground(content); break;
            case 6: this._renderFaction(content); break;
            case 7: this._renderConfirm(content); break;
        }
    }

    _attachNavListeners() {
        const backBtn = document.getElementById('btn-wizard-back');
        const cancelBtn = document.getElementById('btn-wizard-cancel');
        const nextBtn = document.getElementById('btn-wizard-next');

        // Back button
        if (backBtn) {
            backBtn.style.visibility = this.currentStep === 0 ? 'hidden' : 'visible';
            backBtn.onclick = () => this.prevStep();
        }

        // Cancel button
        if (cancelBtn) {
            cancelBtn.onclick = () => {
                console.log('[CharacterCreate] Cancel');
                PythonAPI.call('request_character_list');
            };
        }

        // Next / Create button
        if (nextBtn) {
            if (this.currentStep === STEP_LABELS.length - 1) {
                nextBtn.textContent = 'СОЗДАТЬ';
                nextBtn.onclick = () => this.createCharacter();
            } else {
                nextBtn.textContent = 'ДАЛЕЕ';
                nextBtn.onclick = () => this.nextStep();
            }
        }
    }

    nextStep() {
        if (!this._validateStep()) return;
        if (this.currentStep < STEP_LABELS.length - 1) {
            this.currentStep++;
            this.renderStep();
        }
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.renderStep();
        }
    }

    _validateStep() {
        switch (this.currentStep) {
            case 0: // Name
                if (!this.characterData.character_name.trim()) {
                    this._showValidation('Введите имя персонажа.');
                    return false;
                }
                if (this.characterData.character_name.trim().length < 2) {
                    this._showValidation('Имя должно быть не менее 2 символов.');
                    return false;
                }
                return true;
            case 3: // Ability scores - check points
                return this._getPointsSpent() <= POINT_BUY_TOTAL;
            case 4: { // Skills - check count
                const cls = DND_CLASSES[this.characterData.class_name];
                const needed = cls ? cls.numSkills : 2;
                const selected = Object.keys(this.characterData.skills).filter(k => this.characterData.skills[k] && !this._isBackgroundSkill(k));
                if (selected.length < needed) {
                    this._showValidation(`Выберите ${needed} навыков (${selected.length}/${needed}).`);
                    return false;
                }
                return true;
            }
            case 5: // Background
                if (!this.characterData.background) {
                    this._showValidation('Выберите предысторию.');
                    return false;
                }
                return true;
            default:
                return true;
        }
    }

    _showValidation(msg) {
        // Flash a brief validation message on the content area
        const content = document.getElementById('wizard-content');
        let el = document.getElementById('wizard-validation');
        if (el) { el.textContent = msg; return; }
        el = document.createElement('div');
        el.id = 'wizard-validation';
        el.style.cssText = 'color:#e05050;font-size:12px;text-align:center;padding:6px;margin-top:8px;';
        el.textContent = msg;
        content.appendChild(el);
        setTimeout(() => { if (el.parentNode) el.remove(); }, 3000);
    }

    // ========== Step 1: Name & Gender ==========

    _renderNameGender(container) {
        container.innerHTML = `
            <div class="wizard-container">
                <div class="form-group">
                    <label class="form-label">Имя персонажа:</label>
                    <input type="text" id="input-char-name" class="bg1-input" placeholder="Введите имя" maxlength="32"
                        value="${this._esc(this.characterData.character_name)}" />
                </div>
                <div class="form-group">
                    <label class="form-label">Пол:</label>
                    <div class="gender-toggle">
                        <button class="gender-btn ${this.characterData.gender === 'male' ? 'selected' : ''}" data-gender="male">Муж</button>
                        <button class="gender-btn ${this.characterData.gender === 'female' ? 'selected' : ''}" data-gender="female">Жен</button>
                    </div>
                </div>
            </div>
        `;

        const nameInput = document.getElementById('input-char-name');
        nameInput.addEventListener('input', () => { this.characterData.character_name = nameInput.value; });
        nameInput.focus();

        container.querySelectorAll('.gender-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.characterData.gender = btn.dataset.gender;
                container.querySelectorAll('.gender-btn').forEach(b => b.classList.toggle('selected', b.dataset.gender === this.characterData.gender));
            });
        });
    }

    // ========== Step 2: Race ==========

    _renderRace(container) {
        const raceKeys = Object.keys(DND_RACES);
        const selected = this.characterData.race;
        const raceData = DND_RACES[selected];

        container.innerHTML = `
            <div class="wizard-container">
                <div class="selection-grid grid-3">
                    ${raceKeys.map(k => `<button class="selection-btn ${k === selected ? 'selected' : ''}" data-race="${k}">${DND_RACES[k].name}</button>`).join('')}
                </div>
                <div class="info-panel" id="race-info">
                    ${this._raceInfoHTML(selected)}
                </div>
            </div>
        `;

        container.querySelectorAll('.selection-btn[data-race]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.characterData.race = btn.dataset.race;
                container.querySelectorAll('.selection-btn[data-race]').forEach(b => b.classList.toggle('selected', b.dataset.race === this.characterData.race));
                document.getElementById('race-info').innerHTML = this._raceInfoHTML(this.characterData.race);
                this._attachFeatureTooltips(container);
            });
        });

        this._attachFeatureTooltips(container);
    }

    _raceInfoHTML(raceId) {
        const r = DND_RACES[raceId];
        if (!r) return '';
        const bonuses = Object.entries(r.bonuses).map(([k, v]) => `${k.substring(0,3).toUpperCase()} +${v}`).join(', ');
        const feats = r.features.map(f => {
            const info = DND_FEATURES[f] || { name: f, desc: '' };
            return `<span class="feature-tag" data-feature="${f}" title="${this._esc(info.desc)}">${info.name}</span>`;
        }).join('');
        return `
            <div class="info-panel-title">${r.name}</div>
            <div class="info-panel-desc">${r.desc}</div>
            <div class="info-panel-detail">Бонусы характеристик: <span>${bonuses}</span></div>
            <div class="info-panel-detail">Скорость: <span>${r.speed} ft</span></div>
            <div class="feature-tags">${feats}</div>
        `;
    }

    // ========== Step 3: Class ==========

    _renderClass(container) {
        const classKeys = Object.keys(DND_CLASSES);
        const selected = this.characterData.class_name;

        container.innerHTML = `
            <div class="wizard-container">
                <div class="selection-grid grid-4">
                    ${classKeys.map(k => `<button class="selection-btn ${k === selected ? 'selected' : ''}" data-class="${k}">${DND_CLASSES[k].name}</button>`).join('')}
                </div>
                <div class="info-panel" id="class-info">
                    ${this._classInfoHTML(selected)}
                </div>
            </div>
        `;

        container.querySelectorAll('.selection-btn[data-class]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.characterData.class_name = btn.dataset.class;
                container.querySelectorAll('.selection-btn[data-class]').forEach(b => b.classList.toggle('selected', b.dataset.class === this.characterData.class_name));
                document.getElementById('class-info').innerHTML = this._classInfoHTML(this.characterData.class_name);
                this._attachFeatureTooltips(container);
            });
        });

        this._attachFeatureTooltips(container);
    }

    _classInfoHTML(classId) {
        const c = DND_CLASSES[classId];
        if (!c) return '';
        const feats = c.features.map(f => {
            const info = DND_FEATURES[f] || { name: f, desc: '' };
            return `<span class="feature-tag" data-feature="${f}" title="${this._esc(info.desc)}">${info.name}</span>`;
        }).join('');
        const skillList = c.skills[0] === 'any' ? 'Любой' : c.skills.map(s => DND_SKILLS[s]?.label || s).join(', ');
        return `
            <div class="info-panel-title">${c.name}</div>
            <div class="info-panel-desc">${c.desc}</div>
            <div class="info-panel-detail">Кость хитов: <span>d${c.hitDie}</span></div>
            <div class="info-panel-detail">Основные: <span>${c.primary.join(', ')}</span></div>
            <div class="info-panel-detail">Навыки (выберите ${c.numSkills}): <span>${skillList}</span></div>
            <div class="feature-tags">${feats}</div>
        `;
    }

    // ========== Step 4: Ability Scores (Point Buy) ==========

    _renderAbilityScores(container) {
        const race = DND_RACES[this.characterData.race] || {};
        const bonuses = race.bonuses || {};

        container.innerHTML = `
            <div class="wizard-container">
                <div class="points-remaining" id="points-display"></div>
                <div class="ability-scores" id="ability-scores"></div>
            </div>
        `;

        this._refreshAbilityScores();
    }

    _refreshAbilityScores() {
        const race = DND_RACES[this.characterData.race] || {};
        const bonuses = race.bonuses || {};
        const spent = this._getPointsSpent();
        const remaining = POINT_BUY_TOTAL - spent;

        // Points display
        const pd = document.getElementById('points-display');
        if (pd) {
            let cls = '';
            if (remaining === 0) cls = ' depleted';
            else if (remaining <= 5) cls = ' warning';
            pd.className = 'points-remaining' + cls;
            pd.innerHTML = `<span class="points-value">${remaining}</span><span class="points-label">очков осталось (из ${POINT_BUY_TOTAL})</span>`;
        }

        // Ability rows
        const sc = document.getElementById('ability-scores');
        if (!sc) return;
        sc.innerHTML = DND_ABILITIES.map(ab => {
            const base = this.characterData[ab.id];
            const racial = bonuses[ab.id] || 0;
            const total = base + racial;
            const mod = calcModifier(total);
            const cost = POINT_BUY_COST[base] || 0;
            const canInc = base < 15 && remaining > 0 && (POINT_BUY_COST[base + 1] - cost) <= remaining;
            const canDec = base > 8;
            return `
                <div class="ability-row">
                    <div class="ability-name"><span class="ability-abbr">${ab.abbr}</span> ${ab.name}</div>
                    <div class="ability-controls">
                        <button class="ability-btn" data-ability="${ab.id}" data-dir="-1" ${canDec ? '' : 'disabled'}>-</button>
                        <div class="ability-value">${base}</div>
                        <button class="ability-btn" data-ability="${ab.id}" data-dir="1" ${canInc ? '' : 'disabled'}>+</button>
                    </div>
                    <div class="ability-racial">${racial ? '+' + racial : ''}</div>
                    <div class="ability-value" style="min-width:20px;font-size:13px;">${total}</div>
                    <div class="ability-modifier">(${modStr(mod)})</div>
                    <div class="ability-cost">цена: ${cost}</div>
                </div>
            `;
        }).join('');

        // Attach click handlers
        sc.querySelectorAll('.ability-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const ab = btn.dataset.ability;
                const dir = parseInt(btn.dataset.dir);
                const cur = this.characterData[ab];
                const next = cur + dir;
                if (next >= 8 && next <= 15) {
                    if (dir > 0) {
                        const addCost = POINT_BUY_COST[next] - POINT_BUY_COST[cur];
                        if (addCost <= (POINT_BUY_TOTAL - this._getPointsSpent())) {
                            this.characterData[ab] = next;
                            this._refreshAbilityScores();
                        }
                    } else {
                        this.characterData[ab] = next;
                        this._refreshAbilityScores();
                    }
                }
            });
        });
    }

    _getPointsSpent() {
        let total = 0;
        for (const ab of DND_ABILITIES) {
            total += POINT_BUY_COST[this.characterData[ab.id]] || 0;
        }
        return total;
    }

    // ========== Step 5: Skills ==========

    _renderSkills(container) {
        const cls = DND_CLASSES[this.characterData.class_name];
        const numSkills = cls ? cls.numSkills : 2;
        const isAny = cls && cls.skills[0] === 'any';
        const availableSkills = isAny ? getAllSkillNames() : (cls ? cls.skills : []);
        const bg = DND_BACKGROUNDS[this.characterData.background];
        const bgSkills = bg ? bg.skills : [];

        container.innerHTML = `
            <div class="wizard-container">
                <div class="skills-header">
                    <div style="font-size:12px;color:var(--color-text-primary);">Выберите навыки класса</div>
                    <div class="skills-count">Выбрано: <span id="skills-selected-count">0</span> / ${numSkills}</div>
                </div>
                <div class="skills-list" id="skills-list"></div>
            </div>
        `;

        this._refreshSkills(availableSkills, numSkills, bgSkills);
    }

    _refreshSkills(availableSkills, numSkills, bgSkills) {
        const allSkills = getAllSkillNames();
        const race = DND_RACES[this.characterData.race] || {};
        const bonuses = race.bonuses || {};

        const list = document.getElementById('skills-list');
        if (!list) return;

        const selectedCount = Object.keys(this.characterData.skills).filter(k => this.characterData.skills[k] && !this._isBackgroundSkill(k)).length;
        const countEl = document.getElementById('skills-selected-count');
        if (countEl) countEl.textContent = selectedCount;

        list.innerHTML = allSkills.map(skillName => {
            const sk = DND_SKILLS[skillName];
            const ability = sk.ability;
            const abbrUpper = ability.substring(0, 3).toUpperCase();
            const base = this.characterData[ability];
            const racial = bonuses[ability] || 0;
            const mod = calcModifier(base + racial);
            const isBg = bgSkills.includes(skillName);
            const isSelected = !!this.characterData.skills[skillName];
            const isAvailable = availableSkills.includes(skillName);
            const isFull = selectedCount >= numSkills && !isSelected && !isBg;
            const disabled = (!isAvailable && !isBg) || (isFull && !isSelected && !isBg);

            let cls = 'skill-row';
            if (isBg) cls += ' from-background selected';
            else if (isSelected) cls += ' selected';
            if (disabled && !isBg) cls += ' disabled';

            return `
                <div class="${cls}" data-skill="${skillName}" data-bg="${isBg ? '1' : '0'}" data-available="${isAvailable ? '1' : '0'}">
                    <div class="skill-check">${(isSelected || isBg) ? '&#10003;' : ''}</div>
                    <div class="skill-name">${DND_SKILLS[skillName].label || skillName}${isBg ? ' (предыстория)' : ''}</div>
                    <div class="skill-ability">${abbrUpper}</div>
                    <div class="skill-modifier">${modStr(mod)}</div>
                </div>
            `;
        }).join('');

        // Click handlers
        list.querySelectorAll('.skill-row').forEach(row => {
            row.addEventListener('click', () => {
                const skill = row.dataset.skill;
                if (row.dataset.bg === '1') return; // background skills locked
                if (row.dataset.available === '0') return; // not available for class

                const currentSelected = Object.keys(this.characterData.skills).filter(k => this.characterData.skills[k] && !this._isBackgroundSkill(k)).length;
                const isOn = !!this.characterData.skills[skill];

                if (isOn) {
                    delete this.characterData.skills[skill];
                } else if (currentSelected < numSkills) {
                    this.characterData.skills[skill] = true;
                }

                this._refreshSkills(availableSkills, numSkills, bgSkills);
            });
        });
    }

    _isBackgroundSkill(skillName) {
        const bg = DND_BACKGROUNDS[this.characterData.background];
        return bg ? bg.skills.includes(skillName) : false;
    }

    // ========== Step 6: Background ==========

    _renderBackground(container) {
        const bgKeys = Object.keys(DND_BACKGROUNDS);
        const selected = this.characterData.background;

        container.innerHTML = `
            <div class="wizard-container">
                <div class="selection-grid grid-2">
                    ${bgKeys.map(k => `<button class="selection-btn ${k === selected ? 'selected' : ''}" data-bg="${k}">${DND_BACKGROUNDS[k].name}</button>`).join('')}
                </div>
                <div class="info-panel" id="bg-info">
                    ${selected ? this._bgInfoHTML(selected) : '<div class="info-panel-desc">Выберите предысторию для подробностей.</div>'}
                </div>
            </div>
        `;

        container.querySelectorAll('.selection-btn[data-bg]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.characterData.background = btn.dataset.bg;
                // Update background skills in characterData
                const bg = DND_BACKGROUNDS[this.characterData.background];
                if (bg) {
                    bg.skills.forEach(s => { this.characterData.skills[s] = true; });
                }
                container.querySelectorAll('.selection-btn[data-bg]').forEach(b => b.classList.toggle('selected', b.dataset.bg === this.characterData.background));
                document.getElementById('bg-info').innerHTML = this._bgInfoHTML(this.characterData.background);
            });
        });
    }

    _bgInfoHTML(bgId) {
        const b = DND_BACKGROUNDS[bgId];
        if (!b) return '';
        return `
            <div class="info-panel-title">${b.name}</div>
            <div class="info-panel-desc">${b.desc}</div>
            <div class="info-panel-detail">Владение навыками: <span>${b.skills.map(s => DND_SKILLS[s]?.label || s).join(', ')}</span></div>
        `;
    }

    // ========== Step 7: Faction ==========

    _renderFaction(container) {
        const keys = Object.keys(DND_FACTIONS);
        const selected = this.characterData.faction;

        container.innerHTML = `
            <div class="wizard-container">
                <div class="faction-grid">
                    ${keys.map(k => {
                        const f = DND_FACTIONS[k];
                        return `
                            <div class="faction-card ${k === selected ? 'selected' : ''}" data-faction="${k}" style="border-color:${k === selected ? f.color : ''}">
                                <div class="faction-name" style="color:${f.color}">${f.name}</div>
                                <div class="faction-desc">${f.desc}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;

        container.querySelectorAll('.faction-card').forEach(card => {
            card.addEventListener('click', () => {
                this.characterData.faction = card.dataset.faction;
                const f = DND_FACTIONS[this.characterData.faction];
                container.querySelectorAll('.faction-card').forEach(c => {
                    const isSelected = c.dataset.faction === this.characterData.faction;
                    c.classList.toggle('selected', isSelected);
                    c.style.borderColor = isSelected ? DND_FACTIONS[c.dataset.faction].color : '';
                });
            });
        });
    }

    // ========== Step 8: Confirm ==========

    _renderConfirm(container) {
        const d = this.characterData;
        const race = DND_RACES[d.race] || {};
        const cls = DND_CLASSES[d.class_name] || {};
        const bg = DND_BACKGROUNDS[d.background] || {};
        const fac = DND_FACTIONS[d.faction] || {};
        const bonuses = race.bonuses || {};

        const statsHTML = DND_ABILITIES.map(ab => {
            const base = d[ab.id];
            const racial = bonuses[ab.id] || 0;
            const total = base + racial;
            const mod = calcModifier(total);
            return `<div class="summary-row"><span class="label">${ab.abbr}</span><span class="value">${total} (${modStr(mod)})${racial ? ' [+' + racial + ' раса]' : ''}</span></div>`;
        }).join('');

        const skillsList = Object.keys(d.skills).filter(k => d.skills[k]).sort().map(k => DND_SKILLS[k]?.label || k).join(', ') || 'Нет';

        container.innerHTML = `
            <div class="wizard-container">
                <div class="summary-panel">
                    <div class="summary-section">
                        <div class="summary-section-title">Персонаж</div>
                        <div class="summary-row"><span class="label">Имя</span><span class="value">${this._esc(d.character_name)}</span></div>
                        <div class="summary-row"><span class="label">Пол</span><span class="value">${d.gender === 'male' ? 'Муж' : 'Жен'}</span></div>
                        <div class="summary-row"><span class="label">Раса</span><span class="value">${race.name || d.race}</span></div>
                        <div class="summary-row"><span class="label">Класс</span><span class="value">${cls.name || d.class_name}</span></div>
                    </div>
                    <div class="summary-section">
                        <div class="summary-section-title">Характеристики</div>
                        ${statsHTML}
                    </div>
                    <div class="summary-section">
                        <div class="summary-section-title">Детали</div>
                        <div class="summary-row"><span class="label">Предыстория</span><span class="value">${bg.name || d.background}</span></div>
                        <div class="summary-row"><span class="label">Фракция</span><span class="value" style="color:${fac.color || ''}">${fac.name || d.faction}</span></div>
                        <div class="summary-row"><span class="label">Кость хитов</span><span class="value">d${cls.hitDie || '?'}</span></div>
                        <div class="summary-row"><span class="label">HP</span><span class="value">${(cls.hitDie || 8) + calcModifier((d.constitution) + (bonuses.constitution || 0))}</span></div>
                    </div>
                    <div class="summary-section">
                        <div class="summary-section-title">Навыки</div>
                        <div style="font-size:11px;color:var(--color-text-primary);line-height:1.5;">${skillsList}</div>
                    </div>
                </div>
            </div>
        `;
    }

    // ========== Feature tooltips ==========

    _attachFeatureTooltips(container) {
        container.querySelectorAll('.feature-tag').forEach(tag => {
            tag.addEventListener('mouseenter', (e) => this._showTooltip(e, tag.dataset.feature));
            tag.addEventListener('mouseleave', () => this._hideTooltip());
        });
    }

    _showTooltip(e, featureId) {
        this._hideTooltip();
        const info = DND_FEATURES[featureId];
        if (!info) return;

        const tip = document.createElement('div');
        tip.className = 'feature-tooltip';
        tip.innerHTML = `<div class="feature-tooltip-title">${info.name}</div><div class="feature-tooltip-desc">${info.desc}</div>`;
        document.body.appendChild(tip);

        const rect = e.target.getBoundingClientRect();
        tip.style.left = Math.min(rect.left, window.innerWidth - 320) + 'px';
        tip.style.top = (rect.bottom + 6) + 'px';
        this._tooltip = tip;
    }

    _hideTooltip() {
        if (this._tooltip) {
            this._tooltip.remove();
            this._tooltip = null;
        }
    }

    // ========== Create ==========

    createCharacter() {
        const d = this.characterData;

        if (!d.character_name.trim()) {
            this._showValidation('Требуется имя персонажа.');
            return;
        }

        console.log('[CharacterCreate] Creating character:', d);
        PythonAPI.createCharacter(d);
    }

    // ========== Utility ==========

    _esc(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    destroy() {
        window.removeEventListener('python-message', this._pythonHandler);
        this._hideTooltip();

        if (this.element) {
            this.element.remove();
            this.element = null;
        }

        console.log('[CharacterCreate] Destroyed');
    }
}

// Register with router
window.router.registerScreen('character-create', CharacterCreate);
