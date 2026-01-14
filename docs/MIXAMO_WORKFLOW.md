# Создание моделей с анимациями через Mixamo + Blender

## Обзор процесса

1. Скачать модель и анимации с Mixamo
2. Импортировать в Blender
3. Объединить анимации в один файл
4. Экспортировать в .glb/.gltf
5. Конвертировать в .bam для Panda3D

## Шаг 1: Mixamo

### Регистрация
1. Перейти на [mixamo.com](https://www.mixamo.com/)
2. Войти через Adobe ID (бесплатно)

### Выбор персонажа
1. Вкладка **Characters**
2. Выбрать любого персонажа (например, "Y Bot" или "X Bot" - они лёгкие)
3. Нажать **Download**
4. Настройки:
   - Format: **FBX Binary (.fbx)**
   - Pose: **T-pose**
5. Сохранить как `character.fbx`

### Скачивание анимаций
Для каждой нужной анимации:

1. Вкладка **Animations**
2. Найти анимацию (поиск):
   - `idle` - стояние
   - `walking` - ходьба
   - `running` - бег
   - `walking backward` - ходьба назад
   - `strafe left/right` - движение вбок
   - `jump` - прыжок

3. Настроить параметры (справа):
   - **In Place**: ВКЛ (галочка) - персонаж остаётся на месте
   - Overdrive: 0
   - Arm Space: по вкусу

4. Нажать **Download**:
   - Format: **FBX Binary (.fbx)**
   - Skin: **Without Skin** (анимация без модели)
   - Frames per Second: **30**
   - Keyframe Reduction: **none**

5. Сохранить с понятным именем: `anim_idle.fbx`, `anim_run.fbx`, и т.д.

## Шаг 2: Blender - Импорт

### Импорт персонажа
1. Открыть Blender, удалить куб (X)
2. **File → Import → FBX (.fbx)**
3. Выбрать `character.fbx`
4. Настройки импорта (справа):
   - Scale: 1.0
   - Apply Transform: ВКЛ

### Проверка
- Должен появиться персонаж в T-pose
- В Outliner должна быть Armature (скелет)

## Шаг 3: Blender - Объединение анимаций

### Импорт первой анимации
1. **File → Import → FBX (.fbx)**
2. Выбрать `anim_idle.fbx`
3. В Outliner появится новая Armature с анимацией

### Копирование анимации на персонажа
1. Выделить **новую** Armature (с анимацией)
2. Перейти в **Dope Sheet** (внизу, переключить Editor Type)
3. Режим: **Action Editor**
4. Увидишь Action (например "mixamo.com")
5. Нажать **F** рядом с именем (Fake User) чтобы сохранить
6. Переименовать Action: `idle`

7. Удалить импортированную Armature:
   - Выделить её в Outliner
   - X → Delete Hierarchy

### Повторить для всех анимаций
Для каждого `anim_*.fbx`:
1. Import FBX
2. В Action Editor: сохранить (F) и переименовать Action
3. Удалить лишнюю Armature

### Назначение анимаций персонажу
1. Выделить Armature персонажа
2. Action Editor → выбрать нужный Action из списка
3. Можно переключаться между анимациями

## Шаг 4: Настройка перед экспортом

### Применить трансформации
1. Выделить Armature
2. **Ctrl+A → All Transforms**

### Проверить ориентацию
Персонаж должен смотреть в **-Y** (в Blender это "вперёд")

Если смотрит не туда:
1. Object Mode
2. **R → Z → 180** (повернуть)
3. **Ctrl+A → Rotation**

### Проверить анимации
1. Выделить Armature
2. Переключиться в **Pose Mode**
3. Внизу: Timeline → нажать Play
4. В Action Editor переключать анимации

## Шаг 5: Экспорт

### Вариант A: glTF/GLB (рекомендуется)

1. Выделить Armature и Mesh (Shift+Click)
2. **File → Export → glTF 2.0 (.glb/.gltf)**
3. Настройки:
   - Format: **glTF Binary (.glb)**
   - Include: **Selected Objects**
   - Transform: **+Y Up** (Panda3D использует Z-up, но конвертер исправит)
   - Animation:
     - ВКЛ Export Animations
     - ВКЛ Group by NLA Track или Export All Actions
4. Сохранить как `player.glb`

### Вариант B: FBX

1. **File → Export → FBX (.fbx)**
2. Настройки:
   - Scale: 1.0
   - Apply Transform: ВКЛ
   - Include: Selected Objects
   - Bake Animation: ВКЛ
   - All Actions: ВКЛ
3. Сохранить как `player.fbx`

## Шаг 6: Конвертация в Panda3D

### Установка blend2bam (рекомендуется)

```bash
pip install panda3d-blend2bam panda3d-gltf
```

### Конвертация GLB → BAM

```bash
# Из GLB
gltf2bam player.glb base.bam

# Или напрямую из Blender файла
blend2bam player.blend base.bam
```

### Конвертация FBX → EGG → BAM

Если используешь FBX:

```bash
# Нужен Autodesk FBX SDK или использовать Blender как промежуточный шаг
# Лучше экспортировать в GLB и использовать gltf2bam
```

## Шаг 7: Проверка в игре

### Быстрый тест

```python
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor

class Test(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # Загрузка модели
        self.actor = Actor("nine/assets/models/base.bam")
        self.actor.setScale(0.01)  # Mixamo модели большие
        self.actor.reparentTo(self.render)

        # Проверка анимаций
        print("Анимации:", self.actor.getAnimNames())

        # Запуск анимации
        self.actor.loop("idle")  # или как назвал

        # Камера
        self.camera.setPos(0, -5, 1)
        self.camera.lookAt(0, 0, 1)

app = Test()
app.run()
```

## Структура файлов

```
nine/assets/models/
├── base.bam          # Основная модель
├── player.glb          # Исходник (для редактирования)
└── source/             # Исходные файлы
    ├── character.fbx
    ├── anim_idle.fbx
    ├── anim_run.fbx
    └── ...
```

## Использование в коде

После конвертации обнови `client.py`:

```python
def load_actor(self, player_id, color, is_local_player=False):
    actor = Actor("nine/assets/models/base.bam")
    actor.setScale(0.01)  # Подобрать под размер
    actor.setColor(color)
    actor.reparentTo(self.render)
    actor.loop("idle")
    # ...
```

И `world.py` для правильных имён анимаций:

```python
anim_state = "idle"
if self.character_controller.is_moving:
    anim_state = "run"  # или "running" - как назвал в Blender
```

## Советы

### Именование анимаций
Называй Actions в Blender так же, как будешь использовать в коде:
- `idle`
- `run`
- `walk`
- `back`
- `strafe_left`
- `strafe_right`

### Размер модели
Mixamo модели обычно ~180 единиц высотой (сантиметры).
В Panda3D нужно `setScale(0.01)` чтобы 180 см стали 1.8 единицы.

### In Place анимации
Всегда скачивай с **In Place** - движение управляется кодом, не анимацией.

### Проблемы и решения

| Проблема | Решение |
|----------|---------|
| Модель лежит на боку | В Blender: R → X → -90, затем Ctrl+A → Rotation |
| Анимации не видны | Проверь что экспортировал All Actions |
| Модель слишком большая | Уменьши scale в коде или в Blender |
| Анимация дёргается | Проверь Keyframe Reduction: none при скачивании |

## Быстрый чеклист

- [ ] Скачал персонажа в T-pose (FBX)
- [ ] Скачал анимации Without Skin, In Place, 30 FPS
- [ ] Импортировал всё в Blender
- [ ] Переименовал Actions понятно
- [ ] Применил трансформации (Ctrl+A)
- [ ] Экспортировал в GLB
- [ ] Конвертировал в BAM через gltf2bam
- [ ] Проверил в игре
