# niNE
Это упрощенный 3D фреймворк для ролевых игр, вдохновленный SS14 и Garry's Mod. Он позволяет игрокам легко создавать серверы и расширять функциональность с помощью Python-плагинов с поддержкой дополнительных ресурсов.

![Версия Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Лицензия](https://img.shields.io/badge/license-MIT-green.svg)
![Panda3D](https://img.shields.io/badge/engine-Panda3D-orange.svg)

## Особенности

- **3D среда для ролевых игр**: Базовый 3D мир, в котором игроки могут подключаться и взаимодействовать
- **Простой хостинг серверов**: Запускайте серверы одним кликом или развертывайте отдельно
- **Расширенная система плагинов**: Поддержка плагинов как в виде файлов, так и папок с ресурсами
- **Сетевой мультиплеер**: Построен на asyncio и сокетах Python
- **Чат**: Внутриигровое текстовое общение

## Технологии

- **3D движок**: Panda3D
- **Сетевое взаимодействие**: asyncio с TCP сокетами и TLS-шифрованием
- **База данных**: SQLite (для сохранения состояния игроков, с реляционной схемой)
- **Аутентификация**: Базовая аутентификация по паролю
- **Сериализация**: JSON
- **Система плагинов**: Динамическая загрузка с событийной архитектурой

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

## Структура проекта

```
niNE/
├── requirements.txt        # Зависимости проекта
├── server.py               # Главная точка входа сервера
├── client.py               # Главная точка входа клиента
├── certs/                  # SSL-сертификаты для TLS-соединения
├── nine.db                 # Файл базы данных SQLite
├── nine/                   # Ядро фреймворка
│   ├── core/
│   │   ├── database.py     # Менеджер базы данных (SQLite)
│   │   └── ...
│   └── ...
└── ...
```

## Работа с базой данных (для разработчиков плагинов)

Сервер `niNE` включает `DatabaseManager`, который обеспечивает простое сохранение и загрузку данных игроков в SQLite.

### API для плагинов

Плагины могут получить доступ к менеджеру базы данных через объект `app.db`. `DatabaseManager` предоставляет следующие методы для работы с реляционной схемой:

- `db.set_player_attribute(player_uuid, attribute, value)`: Устанавливает атрибут для игрока. Основные атрибуты (`name`, `pos`) сохраняются в отдельные колонки. Остальные - в JSON-поле `attributes`.
  ```python
  # Установить HP игрока
  db.set_player_attribute('some_player_uuid', 'health', 100)
  
  # Изменить позицию игрока
  db.set_player_attribute('some_player_uuid', 'pos', [10.0, 5.0, 0.0])
  
  # Изменить имя игрока
  db.set_player_attribute('some_player_uuid', 'name', 'NewPlayerName')
  ```

- `db.get_player_attribute(player_uuid, attribute)`: Получает значение атрибута.
  ```python
  # Получить HP игрока
  health = db.get_player_attribute('some_player_uuid', 'health') # 100
  
  # Получить позицию игрока
  pos = db.get_player_attribute('some_player_uuid', 'pos') # [10.0, 5.0, 0.0]
  ```

- `db.get_player_all_attributes(player_uuid)`: Получает все основные атрибуты игрока (имя, позиция) и атрибуты из JSON-поля в виде словаря.
  ```python
  # Получить все данные игрока
  all_data = db.get_player_all_attributes('some_player_uuid')
  # all_data будет {'name': 'NewPlayerName', 'pos': [10.0, 5.0, 0.0], 'health': 100, ...}
  ```
  
- `db.player_exists(player_uuid)`: Проверяет существование игрока.
- `db.create_player(player_uuid, name, password)`: Создает нового игрока.
- `db.verify_player_password(player_uuid, password)`: Проверяет пароль игрока.
  
## Лицензия

Этот проект лицензирован под MIT License - подробности см. в файле [LICENSE](LICENSE).