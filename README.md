# niNE — D&D Gamemode Branch

> **Ветка:** `dnd-gamemode-v0.1.0-alpha`
>
> Эта ветка содержит разработку **D&D режима** — игрового режима, основанного на настольной ролевой игре D&D 5e. Основной проект niNE продолжает развиваться независимо в ветке `main`.

![Версия Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Лицензия](https://img.shields.io/badge/license-MIT-green.svg)
![Panda3D](https://img.shields.io/badge/engine-Panda3D-orange.svg)
![Branch](https://img.shields.io/badge/branch-dnd--gamemode-purple.svg)

![logos](nine/assets/materials/textures/backgrounds/1.jpg)

## D&D Режим — Планируемые особенности

- **Система персонажей D&D 5e**: Полноценное создание персонажа с расами, классами, характеристиками
- **6 рас**: Human, Elf, Dwarf, Halfling, Orc, Tiefling (по 2 модели на расу: male/female)
- **12 классов D&D**: Fighter, Wizard, Rogue, Cleric и другие
- **Пошаговая боевая система**: Инициатива, действия, реакции
- **Система бросков кубов**: d20, d6, d8 с модификаторами
- **DM Mode**: Инструменты для Игрового Мастера
- **Система фракций**: 4 фракции с точками спавна и отношениями

## Базовые особенности niNE

- **3D среда для ролевых игр**: Базовый 3D мир, в котором игроки могут подключаться и взаимодействовать
- **Простой хостинг серверов**: Запускайте серверы одним кликом или развертывайте отдельно
- **Расширенная система плагинов**: Поддержка плагинов как в виде файлов, так и папок с ресурсами
- **Сетевой мультиплеер**: Построен на asyncio и сокетах Python
- **Чат**: Внутриигровое текстовое общение

![logos](nine/assets/materials/ingame.png)
![logos](nine/assets/materials/preview_2.png)
![logos](nine/assets/materials/preview_3.png)

Для получения подробной технической информации, сведений об архитектуре и API для разработчиков, пожалуйста, обратитесь к нашей [**Технической документации (DOCS.md)**](docs/DOCS.md).

Информация для контрибуторов - [**смотреть тут.**](docs/DEVELOPMENT.md).

## Документация по плагинам

niNE имеет мощную модульную систему плагинов, вдохновленную Garry's Mod:

- 📚 [**Полная документация по плагинам**](docs/PLUGINS.md) - архитектура, API, примеры
- 🎓 [**Туториал для начинающих**](docs/PLUGIN_TUTORIAL.md) - создайте свой первый плагин за 20 минут
- 📋 [**Справочник Event API**](docs/EVENT_API.md) - полный список событий и их использование
- 🚀 [**Шаблон плагина**](plugin_template/) - готовый шаблон для быстрого старта

### Быстрый старт с плагинами

```bash
# Скопируйте шаблон
cp -r plugin_template plugins/my_plugin

# Отредактируйте sh_plugin.py с вашими настройками
# Запустите сервер - плагин загрузится автоматически!
```

## Установка

### Предварительные требования


- Python 3.12 или выше

```bash
pip install -r requirements.txt
```

### Быстрый старт

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/niNE.git
cd niNE
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. **Сгенерируйте SSL-сертификаты**: Для безопасного соединения между клиентом и сервером вам потребуются SSL-сертификаты. В режиме разработки вы можете использовать самоподписанные:
```bash
mkdir certs
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=US/ST=CA/L=SanFrancisco/O=MyProject/OU=Dev/CN=localhost"
```

4. Запустите сервер:
```bash
python server.py
```

5. Запустите клиент:
```bash
python client.py
```

## Лицензия

Этот проект лицензирован под MIT License - подробности см. в файле [LICENSE](LICENSE).