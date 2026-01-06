# niNE
Это упрощенный 3D фреймворк для ролевых игр, вдохновленный SS14 и Garry's Mod. Он позволяет игрокам легко создавать серверы и расширять функциональность с помощью Python-плагинов с поддержкой дополнительных ресурсов.

![Версия Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Лицензия](https://img.shields.io/badge/license-MIT-green.svg)
![Panda3D](https://img.shields.io/badge/engine-Panda3D-orange.svg)

![logos](nine/assets/materials/preview_1.png)

## Особенности

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