# Руководство по работе с .egg моделями в Panda3D

## Обзор формата EGG

EGG - это текстовый формат Panda3D для хранения 3D моделей, анимаций, текстур и материалов. Его главное преимущество - **можно редактировать текстовым редактором**.

## Структура EGG файла

```
<CoordinateSystem> { Z-Up }  // или Y-Up

<Texture> texture_name {
  "path/to/texture.png"
  <Scalar> wrap { repeat }
}

<Material> material_name {
  <Scalar> diffr { 0.8 }
  <Scalar> diffg { 0.8 }
  <Scalar> diffb { 0.8 }
}

<Group> model_name {
  <VertexPool> vpool {
    <Vertex> 0 { 0 0 0 }
    <Vertex> 1 { 1 0 0 }
    ...
  }

  <Polygon> {
    <VertexRef> { 0 1 2 <Ref> { vpool } }
  }
}

// Скелетные анимации
<Table> {
  <Bundle> animation_name {
    <Table> "<skeleton>" {
      <Table> bone_name {
        <Xfm$Anim_S$> { ... }  // Данные анимации
      }
    }
  }
}
```

## Анимации в EGG

### Как хранятся анимации

Анимации хранятся в секциях `<Bundle>`. Каждый Bundle - отдельная анимация:

```
<Table> {
  <Bundle> walk {
    <Table> "<skeleton>" {
      <Table> root_bone {
        <Xfm$Anim_S$> xform {
          <S$Anim> fps { 24 }
          <S$Anim> order { srpht }
          <V$Anim> t { <V> { 0 0 0 } <V> { 0.1 0 0 } ... }
          <V$Anim> r { <V> { 0 0 0 } <V> { 5 0 0 } ... }
        }
      }
    }
  }
}
```

### Проверка анимаций в модели

```python
from direct.actor.Actor import Actor
actor = Actor("model.egg")
print("Доступные анимации:", actor.getAnimNames())

for anim in actor.getAnimNames():
    ctrl = actor.getAnimControl(anim)
    print(f"  {anim}: {ctrl.getNumFrames()} кадров")
```

### Текущие анимации в player.egg

Модель `nine/assets/models/player.egg` содержит:
- `idleDefault` - стояние (119 кадров)
- `idleDefaultDown` - стояние с опущенной головой
- `idleDefaultUp` - стояние с поднятой головой
- `run` - бег вперёд (59 кадров)
- `backrun` - бег назад
- `strafeL` / `strafeR` - бег вбок
- `defaultrun` / `defaultbackrun` - альтернативные варианты бега

## Редактирование анимаций текстом

### 1. Изменение скорости анимации

Найдите секцию `<S$Anim> fps` и измените значение:
```
<S$Anim> fps { 30 }  // Было 24, стало 30
```

### 2. Переименование анимации

Измените имя Bundle:
```
// Было:
<Bundle> idleDefault {

// Стало:
<Bundle> idle {
```

### 3. Удаление анимации

Удалите весь блок `<Bundle> animation_name { ... }`.

### 4. Копирование анимации

Скопируйте весь блок Bundle и измените имя:
```
<Bundle> walk_fast {
  // скопированное содержимое из walk
}
```
Затем измените значения кадров для ускорения.

## Инструменты для работы с EGG

### Утилиты Panda3D (командная строка)

```bash
# Просмотр модели
pview model.egg

# Конвертация форматов
egg2bam model.egg model.bam          # EGG -> BAM (бинарный, быстрее загружается)
bam2egg model.bam model.egg          # BAM -> EGG
egg-trans -o output.egg input.egg    # Нормализация EGG файла

# Объединение модели и анимаций
egg-optchar -d output_dir -o model.egg model.egg anim1.egg anim2.egg

# Информация о модели
egg-list-textures model.egg          # Список текстур
```

### Просмотр анимаций

```python
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor

class AnimViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.actor = Actor("nine/assets/models/player.egg")
        self.actor.setScale(0.3)
        self.actor.reparentTo(self.render)

        # Вывести все анимации
        print("Анимации:", self.actor.getAnimNames())

        # Запустить конкретную анимацию
        self.actor.loop("run")

        # Управление
        self.accept("1", lambda: self.actor.loop("idleDefault"))
        self.accept("2", lambda: self.actor.loop("run"))
        self.accept("3", lambda: self.actor.loop("backrun"))
        self.accept("space", lambda: self.actor.stop())

app = AnimViewer()
app.run()
```

## Экспорт из Blender

### Установка плагина YABEE

1. Скачать [YABEE](https://github.com/09th/YABEE) или использовать встроенный blend2bam
2. В Blender: Edit → Preferences → Add-ons → Install → выбрать zip

### Настройки экспорта

- **Animation**: Export all actions as separate animations
- **Coordinate System**: Z-Up (стандарт для Panda3D)
- **Применить трансформации**: Обязательно!

### Проблема ориентации модели

Если модель смотрит не в ту сторону:

**Вариант 1: В Blender перед экспортом**
- Выделить модель
- R → Z → 180 (повернуть на 180° по Z)
- Ctrl+A → Apply Rotation

**Вариант 2: В коде**
```python
actor.setH(180)  # Повернуть на 180°
```

**Вариант 3: В EGG файле**
Найти корневую группу и добавить трансформацию:
```
<Group> model_root {
  <Transform> {
    <Matrix4> {
      -1 0 0 0
      0 -1 0 0
      0 0 1 0
      0 0 0 1
    }
  }
  // остальное содержимое
}
```

## Отладка проблем с анимациями

### Анимация не проигрывается

1. Проверить что анимация существует:
```python
print(actor.getAnimNames())  # Должна быть в списке
```

2. Проверить что есть кадры:
```python
ctrl = actor.getAnimControl("run")
print(ctrl.getNumFrames())  # Должно быть > 0
```

3. Проверить что анимация запущена:
```python
print(actor.getCurrentAnim())  # Должно вернуть имя
print(actor.getCurrentFrame("run"))  # Номер кадра
```

### Анимация "дёргается" или странно выглядит

1. **Разные скелеты**: Убедитесь что все анимации используют одинаковый скелет
2. **Проблема с bind pose**: Экспортируйте модель в T-pose или A-pose
3. **Нет интерполяции**: Добавьте blend при смене анимации:
```python
actor.loop("run")
# или с плавным переходом:
# actor.loop("run", blendInto=("idle", 0.2))
```

### Модель "ломается" при анимации

Проблема скорее всего в весах вершин (vertex weights):
- В Blender: проверить Weight Paint
- Каждая вершина должна быть привязана к костям

## Создание простой анимации в EGG

Пример простой анимации покачивания:

```
<Table> {
  <Bundle> sway {
    <Table> "<skeleton>" {
      <Table> root {
        <Xfm$Anim_S$> xform {
          <Scalar> fps { 24 }
          <Scalar> order { srpht }
          // Поворот по Z: 0° -> 5° -> 0° -> -5° -> 0°
          <S$Anim> h {
            0 5 0 -5 0
          }
        }
      }
    }
  }
}
```

## Оптимизация

### Конвертация в BAM

BAM - бинарный формат, загружается быстрее:
```bash
egg2bam -o model.bam model.egg
```

В коде:
```python
actor = Actor("model.bam")  # Работает так же
```

### Разделение модели и анимаций

Для экономии памяти можно хранить анимации отдельно:
```python
actor = Actor("model.egg", {
    "walk": "anims/walk.egg",
    "run": "anims/run.egg"
})
```

## Полезные ссылки

- [Panda3D Manual: Actors and Characters](https://docs.panda3d.org/1.10/python/programming/models-and-actors/index)
- [EGG Syntax](https://docs.panda3d.org/1.10/python/pipeline/egg-files/egg-syntax)
- [YABEE Exporter](https://github.com/09th/YABEE)
- [blend2bam](https://github.com/Moguri/blend2bam) - альтернативный экспортёр
