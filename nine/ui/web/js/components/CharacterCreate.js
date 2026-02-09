/**
 * Character Create Component - 8-Step D&D 5e Wizard
 *
 * Steps: 1.Name/Gender  2.Race  3.Class  4.Ability Scores  5.Skills  6.Background  7.Faction  8.Confirm
 */

// ==================== D&D 5e Data (mirrors sh_constants.py) ====================

const DND_RACES = {
    human:    { name: "Human",    desc: "Versatile and adaptive",       bonuses: {strength:1,dexterity:1,constitution:1,intelligence:1,wisdom:1,charisma:1}, speed: 30, features: ["extra_language","extra_skill"] },
    elf:      { name: "Elf",      desc: "Agile and graceful",           bonuses: {dexterity:2,intelligence:1}, speed: 30, features: ["darkvision","fey_ancestry","trance"] },
    dwarf:    { name: "Dwarf",    desc: "Tough and resilient",          bonuses: {constitution:2,wisdom:1},    speed: 25, features: ["darkvision","dwarven_resilience","stonecunning"] },
    halfling: { name: "Halfling", desc: "Small and nimble",             bonuses: {dexterity:2,charisma:1},     speed: 25, features: ["lucky","brave","halfling_nimbleness"] },
    orc:      { name: "Orc",      desc: "Strong and enduring",          bonuses: {strength:2,constitution:1},  speed: 30, features: ["darkvision","aggressive","powerful_build"] },
    tiefling: { name: "Tiefling", desc: "Infernal heritage",            bonuses: {charisma:2,intelligence:1},  speed: 30, features: ["darkvision","hellish_resistance","infernal_legacy"] },
};

const DND_CLASSES = {
    fighter:   { name: "Fighter",   desc: "Master of combat, using diverse weapons and tactics",                    hitDie: 10, primary: ["STR","CON"], skills: ["Acrobatics","Animal Handling","Athletics","History","Insight","Intimidation","Perception","Survival"],                              numSkills: 2, features: ["fighting_style","second_wind"] },
    wizard:    { name: "Wizard",    desc: "Scholarly mage drawing power from arcane study",                         hitDie: 6,  primary: ["INT"],       skills: ["Arcana","History","Insight","Investigation","Medicine","Religion"],                                                                  numSkills: 2, features: ["spellcasting","arcane_recovery"] },
    rogue:     { name: "Rogue",     desc: "Master of stealth and precision strikes",                                hitDie: 8,  primary: ["DEX"],       skills: ["Acrobatics","Athletics","Deception","Insight","Intimidation","Investigation","Perception","Performance","Persuasion","Sleight of Hand","Stealth"], numSkills: 4, features: ["expertise","sneak_attack","thieves_cant"] },
    cleric:    { name: "Cleric",    desc: "Divine messenger carrying the will of the gods",                         hitDie: 8,  primary: ["WIS"],       skills: ["History","Insight","Medicine","Persuasion","Religion"],                                                                              numSkills: 2, features: ["spellcasting","divine_domain"] },
    ranger:    { name: "Ranger",    desc: "Wilderness warrior, hunter and tracker",                                 hitDie: 10, primary: ["DEX","WIS"], skills: ["Animal Handling","Athletics","Insight","Investigation","Nature","Perception","Stealth","Survival"],                                   numSkills: 3, features: ["favored_enemy","natural_explorer"] },
    paladin:   { name: "Paladin",   desc: "Holy warrior bound by a sacred oath",                                    hitDie: 10, primary: ["STR","CHA"], skills: ["Athletics","Insight","Intimidation","Medicine","Persuasion","Religion"],                                                             numSkills: 2, features: ["divine_sense","lay_on_hands"] },
    barbarian: { name: "Barbarian", desc: "Fierce warrior of primal power",                                         hitDie: 12, primary: ["STR","CON"], skills: ["Animal Handling","Athletics","Intimidation","Nature","Perception","Survival"],                                                       numSkills: 2, features: ["rage","unarmored_defense"] },
    bard:      { name: "Bard",      desc: "Master of songs, stories, and word magic",                               hitDie: 8,  primary: ["CHA"],       skills: ["any"],                                                                                                                              numSkills: 3, features: ["spellcasting","bardic_inspiration"] },
    druid:     { name: "Druid",     desc: "Priest of nature, guardian of balance",                                  hitDie: 8,  primary: ["WIS"],       skills: ["Arcana","Animal Handling","Insight","Medicine","Nature","Perception","Religion","Survival"],                                          numSkills: 2, features: ["druidic","spellcasting"] },
    monk:      { name: "Monk",      desc: "Master of martial arts and inner power",                                 hitDie: 8,  primary: ["DEX","WIS"], skills: ["Acrobatics","Athletics","History","Insight","Religion","Stealth"],                                                                   numSkills: 2, features: ["unarmored_defense","martial_arts"] },
    sorcerer:  { name: "Sorcerer",  desc: "Mage with innate magical power",                                        hitDie: 6,  primary: ["CHA"],       skills: ["Arcana","Deception","Insight","Intimidation","Persuasion","Religion"],                                                               numSkills: 2, features: ["spellcasting","sorcerous_origin"] },
    warlock:   { name: "Warlock",   desc: "Mage who made a pact with a powerful entity",                            hitDie: 8,  primary: ["CHA"],       skills: ["Arcana","Deception","History","Intimidation","Investigation","Nature","Religion"],                                                    numSkills: 2, features: ["otherworldly_patron","pact_magic"] },
};

const DND_BACKGROUNDS = {
    acolyte:     { name: "Acolyte",     desc: "You spent your life serving a temple",                   skills: ["Insight","Religion"] },
    criminal:    { name: "Criminal",    desc: "You have a criminal past",                               skills: ["Deception","Stealth"] },
    folk_hero:   { name: "Folk Hero",   desc: "You performed a deed that saved common people",          skills: ["Animal Handling","Survival"] },
    noble:       { name: "Noble",       desc: "You were born into a privileged family",                 skills: ["History","Persuasion"] },
    sage:        { name: "Sage",        desc: "You dedicated your life to studying knowledge",          skills: ["Arcana","History"] },
    soldier:     { name: "Soldier",     desc: "You served in the military",                             skills: ["Athletics","Intimidation"] },
    charlatan:   { name: "Charlatan",   desc: "You are a master of deception and fraud",                skills: ["Deception","Sleight of Hand"] },
    entertainer: { name: "Entertainer", desc: "You perform before audiences",                           skills: ["Acrobatics","Performance"] },
    hermit:      { name: "Hermit",      desc: "You lived in seclusion",                                 skills: ["Medicine","Religion"] },
    outlander:   { name: "Outlander",   desc: "You grew up far from civilization",                      skills: ["Athletics","Survival"] },
};

const DND_SKILLS = {
    "Athletics":       { ability: "strength" },
    "Acrobatics":      { ability: "dexterity" },
    "Sleight of Hand": { ability: "dexterity" },
    "Stealth":         { ability: "dexterity" },
    "Arcana":          { ability: "intelligence" },
    "History":         { ability: "intelligence" },
    "Investigation":   { ability: "intelligence" },
    "Nature":          { ability: "intelligence" },
    "Religion":        { ability: "intelligence" },
    "Animal Handling": { ability: "wisdom" },
    "Insight":         { ability: "wisdom" },
    "Medicine":        { ability: "wisdom" },
    "Perception":      { ability: "wisdom" },
    "Survival":        { ability: "wisdom" },
    "Deception":       { ability: "charisma" },
    "Intimidation":    { ability: "charisma" },
    "Performance":     { ability: "charisma" },
    "Persuasion":      { ability: "charisma" },
};

const DND_ABILITIES = [
    { id: "strength",     name: "Strength",     abbr: "STR" },
    { id: "dexterity",    name: "Dexterity",    abbr: "DEX" },
    { id: "constitution", name: "Constitution",  abbr: "CON" },
    { id: "intelligence", name: "Intelligence",  abbr: "INT" },
    { id: "wisdom",       name: "Wisdom",        abbr: "WIS" },
    { id: "charisma",     name: "Charisma",      abbr: "CHA" },
];

const POINT_BUY_COST = { 8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:7, 15:9 };
const POINT_BUY_TOTAL = 27;

const DND_FACTIONS = {
    alliance: { name: "Alliance", desc: "Union of humans, elves and dwarves. Strive for order and justice.", color: "#0066CC" },
    horde:    { name: "Horde",    desc: "Union of orcs and other warlike races. Value strength and honor.",   color: "#CC0000" },
    neutral:  { name: "Neutral",  desc: "Free adventurers, unbound by politics.",                            color: "#999999" },
    undead:   { name: "Undead",   desc: "Cursed beings from the dark lands. Rejected by the living.",        color: "#6600CC" },
};

const DND_FEATURES = {
    extra_language:       { name: "Extra Language",         desc: "You know one additional language of your choice." },
    extra_skill:          { name: "Extra Skill",            desc: "You gain proficiency in one additional skill of your choice." },
    darkvision:           { name: "Darkvision",             desc: "You can see in dim light within 60 feet as if it were bright light, in shades of grey." },
    fey_ancestry:         { name: "Fey Ancestry",           desc: "You have advantage on saves against being charmed, and magic can't put you to sleep." },
    trance:               { name: "Trance",                 desc: "Elves don't need sleep. Instead, they meditate 4 hours/day, equivalent to 8 hours of human sleep." },
    dwarven_resilience:   { name: "Dwarven Resilience",     desc: "You have advantage on saves against poison and resistance to poison damage." },
    stonecunning:         { name: "Stonecunning",           desc: "On History checks related to stonework, add double proficiency bonus." },
    lucky:                { name: "Lucky",                  desc: "When you roll a 1 on an attack, ability check, or saving throw, you can reroll and must use the new result." },
    brave:                { name: "Brave",                  desc: "You have advantage on saves against being frightened." },
    halfling_nimbleness:  { name: "Halfling Nimbleness",    desc: "You can move through the space of any creature that is a size larger than you." },
    aggressive:           { name: "Aggressive",             desc: "As a bonus action, you can move up to your speed toward a visible hostile creature." },
    powerful_build:       { name: "Powerful Build",         desc: "You count as one size larger for carrying capacity." },
    hellish_resistance:   { name: "Hellish Resistance",     desc: "You have resistance to fire damage." },
    infernal_legacy:      { name: "Infernal Legacy",        desc: "You know the Thaumaturgy cantrip. At 3rd level, Hellish Rebuke 1/day. At 5th, Darkness 1/day." },
    fighting_style:       { name: "Fighting Style",         desc: "Choose a fighting style: Defense (+1 AC), Dueling (+2 damage one-handed), Archery (+2 ranged attack), Great Weapon Fighting (reroll 1-2 damage)." },
    second_wind:          { name: "Second Wind",            desc: "As a bonus action, regain 1d10 + fighter level HP. Once per short or long rest." },
    spellcasting:         { name: "Spellcasting",           desc: "You can cast spells using spell slots. Slots recover after a long rest." },
    arcane_recovery:      { name: "Arcane Recovery",        desc: "Once per day during a short rest, recover spell slots with total levels up to half your wizard level (rounded up)." },
    expertise:            { name: "Expertise",              desc: "Choose 2 proficient skills (or thieves' tools). Your proficiency bonus doubles for them." },
    sneak_attack:         { name: "Sneak Attack",           desc: "Once per turn, deal extra 1d6 damage if you have advantage or an ally near the target." },
    thieves_cant:         { name: "Thieves' Cant",          desc: "You know a secret language of thieves - a mix of dialect, gestures, and ciphers." },
    divine_domain:        { name: "Divine Domain",          desc: "Choose a domain related to your deity. It grants additional spells and abilities." },
    favored_enemy:        { name: "Favored Enemy",          desc: "Choose an enemy type. You gain advantage on Survival and Intelligence checks against them." },
    natural_explorer:     { name: "Natural Explorer",       desc: "Choose a terrain type. You gain advantages when traveling and surviving in that environment." },
    divine_sense:         { name: "Divine Sense",           desc: "As an action, detect celestials, fiends, and undead within 60 feet." },
    lay_on_hands:         { name: "Lay on Hands",           desc: "You have a healing pool of paladin level x 5 HP. Touch to heal or cure disease/poison (5 points)." },
    rage:                 { name: "Rage",                   desc: "As a bonus action, rage for 1 minute: +2 damage with strength weapons, resistance to physical damage, advantage on Strength checks." },
    unarmored_defense:    { name: "Unarmored Defense",      desc: "Without armor, AC = 10 + DEX mod + CON mod (barbarian) or WIS mod (monk)." },
    martial_arts:         { name: "Martial Arts",           desc: "Use DEX instead of STR for attacks. Unarmed damage 1d4. After monk weapon attack, bonus unarmed strike." },
    druidic:              { name: "Druidic",                desc: "You know the secret language of druids. You can leave hidden messages only other druids notice." },
    otherworldly_patron:  { name: "Otherworldly Patron",    desc: "Choose a patron: Archfey, Fiend, or Great Old One. Determines your additional abilities." },
    pact_magic:           { name: "Pact Magic",             desc: "Your spell slots recover after a short rest, not just a long rest." },
    bardic_inspiration:   { name: "Bardic Inspiration",     desc: "As a bonus action, give an ally a d6 to add to a check, attack, or save. Uses = CHA modifier." },
    sorcerous_origin:     { name: "Sorcerous Origin",       desc: "Choose the source of your magic: Draconic Bloodline or Wild Magic." },
};

// ==================== Helpers ====================

function calcModifier(score) { return Math.floor((score - 10) / 2); }
function modStr(mod) { return (mod >= 0 ? '+' : '') + mod; }

function getAllSkillNames() {
    return Object.keys(DND_SKILLS).sort();
}

// ==================== Component ====================

const STEP_LABELS = ["Name", "Race", "Class", "Stats", "Skills", "Background", "Faction", "Confirm"];

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
            alert('Character creation failed: ' + (data.reason || 'Unknown error'));
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
                nextBtn.textContent = 'CREATE';
                nextBtn.onclick = () => this.createCharacter();
            } else {
                nextBtn.textContent = 'NEXT';
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
                    this._showValidation('Please enter a character name.');
                    return false;
                }
                if (this.characterData.character_name.trim().length < 2) {
                    this._showValidation('Name must be at least 2 characters.');
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
                    this._showValidation(`Select ${needed} skills (${selected.length}/${needed}).`);
                    return false;
                }
                return true;
            }
            case 5: // Background
                if (!this.characterData.background) {
                    this._showValidation('Please select a background.');
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
                    <label class="form-label">Character Name:</label>
                    <input type="text" id="input-char-name" class="bg1-input" placeholder="Enter name" maxlength="32"
                        value="${this._esc(this.characterData.character_name)}" />
                </div>
                <div class="form-group">
                    <label class="form-label">Gender:</label>
                    <div class="gender-toggle">
                        <button class="gender-btn ${this.characterData.gender === 'male' ? 'selected' : ''}" data-gender="male">Male</button>
                        <button class="gender-btn ${this.characterData.gender === 'female' ? 'selected' : ''}" data-gender="female">Female</button>
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
            <div class="info-panel-detail">Ability Bonuses: <span>${bonuses}</span></div>
            <div class="info-panel-detail">Speed: <span>${r.speed} ft</span></div>
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
        const skillList = c.skills[0] === 'any' ? 'Any' : c.skills.join(', ');
        return `
            <div class="info-panel-title">${c.name}</div>
            <div class="info-panel-desc">${c.desc}</div>
            <div class="info-panel-detail">Hit Die: <span>d${c.hitDie}</span></div>
            <div class="info-panel-detail">Primary: <span>${c.primary.join(', ')}</span></div>
            <div class="info-panel-detail">Skills (pick ${c.numSkills}): <span>${skillList}</span></div>
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
            pd.innerHTML = `<span class="points-value">${remaining}</span><span class="points-label">points remaining (of ${POINT_BUY_TOTAL})</span>`;
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
                    <div class="ability-cost">cost: ${cost}</div>
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
                    <div style="font-size:12px;color:var(--color-text-primary);">Select class skills</div>
                    <div class="skills-count">Selected: <span id="skills-selected-count">0</span> / ${numSkills}</div>
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
                    <div class="skill-name">${skillName}${isBg ? ' (BG)' : ''}</div>
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
                    ${selected ? this._bgInfoHTML(selected) : '<div class="info-panel-desc">Select a background to see details.</div>'}
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
            <div class="info-panel-detail">Skill Proficiencies: <span>${b.skills.join(', ')}</span></div>
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
            return `<div class="summary-row"><span class="label">${ab.abbr}</span><span class="value">${total} (${modStr(mod)})${racial ? ' [+' + racial + ' racial]' : ''}</span></div>`;
        }).join('');

        const skillsList = Object.keys(d.skills).filter(k => d.skills[k]).sort().join(', ') || 'None';

        container.innerHTML = `
            <div class="wizard-container">
                <div class="summary-panel">
                    <div class="summary-section">
                        <div class="summary-section-title">Character</div>
                        <div class="summary-row"><span class="label">Name</span><span class="value">${this._esc(d.character_name)}</span></div>
                        <div class="summary-row"><span class="label">Gender</span><span class="value">${d.gender === 'male' ? 'Male' : 'Female'}</span></div>
                        <div class="summary-row"><span class="label">Race</span><span class="value">${race.name || d.race}</span></div>
                        <div class="summary-row"><span class="label">Class</span><span class="value">${cls.name || d.class_name}</span></div>
                    </div>
                    <div class="summary-section">
                        <div class="summary-section-title">Ability Scores</div>
                        ${statsHTML}
                    </div>
                    <div class="summary-section">
                        <div class="summary-section-title">Details</div>
                        <div class="summary-row"><span class="label">Background</span><span class="value">${bg.name || d.background}</span></div>
                        <div class="summary-row"><span class="label">Faction</span><span class="value" style="color:${fac.color || ''}">${fac.name || d.faction}</span></div>
                        <div class="summary-row"><span class="label">Hit Die</span><span class="value">d${cls.hitDie || '?'}</span></div>
                        <div class="summary-row"><span class="label">HP</span><span class="value">${(cls.hitDie || 8) + calcModifier((d.constitution) + (bonuses.constitution || 0))}</span></div>
                    </div>
                    <div class="summary-section">
                        <div class="summary-section-title">Skills</div>
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
            this._showValidation('Character name is required.');
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
