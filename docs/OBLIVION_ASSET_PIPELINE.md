# Oblivion Asset Pipeline

## Рабочий пайплайн (проверенный)

```
ISO → Data Files → BSA (bethesda-structs) → NIF → Blender (niftools) → GLB → gltf2bam → BAM
```

## Шаг 1: Распаковка BSA

```python
from bethesda_structs.archive.bsa import BSAArchive
bsa = BSAArchive.parse_file('Data/Oblivion - Meshes.bsa')
for item in bsa.iter_files():
    fp = str(item.filepath)
    if 'characters' in fp.lower():
        # write item.data to extracted/fp
```

## Шаг 2: Структура body parts

```
extracted/meshes/characters/
├── _male/
│   ├── skeleton.nif          # мастер-скелет (34 кости)
│   ├── upperbody.nif         # торс + руки (skinned, 18 костей, 885 вершин)
│   ├── lowerbody.nif         # ноги (skinned, 8 костей, 760 вершин)
│   ├── hand.nif              # кисти + пальцы (skinned, 36 костей, 1646 вершин)
│   ├── foot.nif              # ступни (skinned, 6 костей, 440 вершин)
│   ├── female*.nif           # женские варианты
│   └── *.kf                  # 323 анимации
├── imperial/                 # расовые головы
│   ├── headhuman.nif         # голова (1275 вершин)
│   ├── mouthhuman.nif, eyelefthuman.nif, teeth*.nif
│   └── male/hair01.nif
├── darkelf/, highelf/, woodelf/, orc/, argonian/, khajiit/
└── hair/                     # общие причёски
```

## Шаг 3: Сборка в Blender (io_scene_niftools)

```python
import bpy

EXTRACTED = "/path/to/extracted/meshes"

# Просто импортируем все части — они встают на место автоматически
bpy.ops.import_scene.nif(filepath=f'{EXTRACTED}/characters/_male/upperbody.nif')
bpy.ops.import_scene.nif(filepath=f'{EXTRACTED}/characters/_male/lowerbody.nif')
bpy.ops.import_scene.nif(filepath=f'{EXTRACTED}/characters/_male/hand.nif')
bpy.ops.import_scene.nif(filepath=f'{EXTRACTED}/characters/_male/foot.nif')
bpy.ops.import_scene.nif(filepath=f'{EXTRACTED}/characters/imperial/headhuman.nif')

# Экспорт
bpy.ops.export_scene.gltf(
    filepath='output.glb',
    export_format='GLB',
    export_skins=True,
    export_animations=False,
    export_morph=False,
    export_draco_mesh_compression_enable=False,
)
```

## Шаг 4: GLB → BAM

```bash
gltf2bam output.glb output.bam
```

## Ключевые отличия от Morrowind

| | Morrowind | Oblivion |
|---|---|---|
| NIF версия | v4.0.0.2 | v20.0.0.5 (0x14000004) |
| Body parts | ~12 файлов, 1 сторона | 4 файла, обе стороны |
| Скелет | Отдельный xbase_anim.nif + empties | Встроен в каждый NIF |
| Сборка | Нужен matrix_parent_inverse + зеркалирование | Просто импортируешь |
| Blender плагин | io_scene_mw (Greatness7) | io_scene_niftools (с патчами для 5.0) |
| Текстуры | В BSA | В отдельном BSA (1.1GB) |

## Патчи niftools для Blender 5.0

Три файла пропатчены:
- `vertex/__init__.py` — `use_auto_smooth` + `normals_split_custom_set_from_vertices` guarded
- `armature/__init__.py` — `np_vertices @ np_diff` empty array guard
- `material/__init__.py` — `shadow_method` guarded

## Текстуры

`Oblivion - Textures - Compressed.bsa` (~1.1GB) отсутствует в AnkerGames репаке.
NIF ссылается на: `textures\characters\imperial\male\UpperBodyMale.dds`

## Анимации

323 KF файла в `_male/`. niftools KF импорт не работает в Blender 5.0 (`Action.fcurves` removed).
Альтернатива: конвертация через пайплайн или pyffi.
