#!/usr/bin/env python3
"""
Просмотрщик анимаций для отладки моделей.
Запуск: python tools/anim_viewer.py [model] [--anims source]

Примеры:
  python tools/anim_viewer.py                                    # player.bam со своими анимациями
  python tools/anim_viewer.py new_char.bam                       # new_char.bam со своими анимациями
  python tools/anim_viewer.py new_char.bam --anims player.bam    # new_char.bam с анимациями от player.bam

Управление:
  1-9: Переключение анимаций
  Space: Остановить анимацию
  +/-: Изменить скорость воспроизведения
  R: Повернуть модель на 45°
  Стрелки: Вращение камеры
  Mouse wheel: Приближение/отдаление
"""

import sys
import os

# Перейти в корень проекта
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)

from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, loadPrcFileData, getModelPath, Filename

loadPrcFileData('', 'window-title Animation Viewer')
loadPrcFileData('', 'audio-library-name null')

# Добавить корень проекта в путь поиска моделей
getModelPath().appendDirectory(Filename.fromOsSpecific(project_root))

class AnimViewer(ShowBase):
    def __init__(self, model_path="nine/assets/models/player.bam", anims_source=None):
        ShowBase.__init__(self)

        self.model_path = model_path
        self.anims_source = anims_source
        self.play_rate = 1.0
        self.current_anim_idx = 0

        # Отключить управление мышью по умолчанию
        self.disableMouse()

        # Загрузка модели
        if anims_source:
            # Загружаем модель БЕЗ анимаций, анимации возьмём из другого файла
            self.actor = Actor(model_path)
            self._load_external_anims(anims_source)
        else:
            # Стандартный режим - модель со своими анимациями
            self.actor = Actor(model_path)

        self.actor.setScale(1.0)
        self.actor.reparentTo(self.render)

        # Показать информацию о риге модели
        self._print_rig_info()

        # Вычислить размер модели для правильного масштабирования камеры
        bounds = self.actor.getTightBounds()
        if bounds:
            min_pt, max_pt = bounds
            model_height = max_pt.z - min_pt.z
            model_center_z = (max_pt.z + min_pt.z) / 2
            print(f"Размер модели: высота={model_height:.2f}, центр Z={model_center_z:.2f}")
        else:
            model_height = 2.0
            model_center_z = 1.0

        # Получить список анимаций
        self.anims = self.actor.getAnimNames()
        print(f"\nМодель: {model_path}")
        print(f"Найдено {len(self.anims)} анимаций:")
        for i, anim in enumerate(self.anims):
            ctrl = self.actor.getAnimControl(anim)
            frames = ctrl.getNumFrames() if ctrl else 0
            print(f"  [{i+1}] {anim}: {frames} кадров")

        # Настройка камеры - смотреть на центр модели
        self.cam_distance = max(model_height * 3, 5)
        self.cam_heading = 180  # Смотреть спереди
        self.cam_pitch = 15
        self.look_at_z = model_center_z
        self.update_camera()

        # Добавить освещение
        from panda3d.core import AmbientLight, DirectionalLight

        ambient = AmbientLight("ambient")
        ambient.setColor((0.4, 0.4, 0.4, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        directional = DirectionalLight("directional")
        directional.setColor((0.8, 0.8, 0.8, 1))
        directional_np = self.render.attachNewNode(directional)
        directional_np.setHpr(45, -45, 0)
        self.render.setLight(directional_np)

        # Фон
        self.setBackgroundColor(0.2, 0.2, 0.3)

        # UI текст
        title = f"Model: {model_path}"
        if anims_source:
            title += f"\nAnims: {anims_source}"
        self.title_text = OnscreenText(
            text=title,
            pos=(0, 0.9), scale=0.05, fg=(1, 1, 1, 1),
            align=TextNode.ACenter
        )

        self.anim_text = OnscreenText(
            text="Press 1-9 to play animation",
            pos=(0, 0.8), scale=0.05, fg=(1, 1, 0, 1),
            align=TextNode.ACenter
        )

        self.info_text = OnscreenText(
            text="",
            pos=(-1.3, 0.9), scale=0.04, fg=(0.8, 0.8, 0.8, 1),
            align=TextNode.ALeft
        )

        self.controls_text = OnscreenText(
            text="[1-9] Анимации | [Space] Стоп | [+/-] Скорость | [R] Поворот | [Arrows] Камера",
            pos=(0, -0.9), scale=0.04, fg=(0.6, 0.6, 0.6, 1),
            align=TextNode.ACenter
        )

        # Управление
        for i in range(1, 10):
            self.accept(str(i), self.play_anim, [i-1])

        self.accept("space", self.stop_anim)
        self.accept("+", self.change_rate, [0.25])
        self.accept("=", self.change_rate, [0.25])
        self.accept("-", self.change_rate, [-0.25])
        self.accept("r", self.rotate_model)

        self.accept("arrow_left", self.rotate_camera, [-5, 0])
        self.accept("arrow_right", self.rotate_camera, [5, 0])
        self.accept("arrow_up", self.rotate_camera, [0, 5])
        self.accept("arrow_down", self.rotate_camera, [0, -5])
        self.accept("wheel_up", self.zoom, [-0.5])
        self.accept("wheel_down", self.zoom, [0.5])

        # Обновление UI
        self.taskMgr.add(self.update_ui, "update_ui")

        # Запустить первую анимацию
        if self.anims:
            self.play_anim(0)

    def _load_external_anims(self, anims_source):
        """Загружает анимации из другого .bam файла и применяет к текущей модели."""
        # Сначала загрузим source как Actor чтобы получить список анимаций
        temp_actor = Actor(anims_source)
        anim_names = temp_actor.getAnimNames()

        if not anim_names:
            print(f"ПРЕДУПРЕЖДЕНИЕ: В {anims_source} не найдено анимаций!")
            return

        print(f"\nЗагрузка анимаций из: {anims_source}")
        print(f"Найдено {len(anim_names)} анимаций: {anim_names}")

        # Загружаем каждую анимацию из source файла
        anims_dict = {name: anims_source for name in anim_names}
        self.actor.loadAnims(anims_dict)

        # Проверим, привязались ли анимации
        loaded = self.actor.getAnimNames()
        print(f"Привязано к модели: {len(loaded)} анимаций")

        # Проверка совместимости ригов
        if loaded:
            print("\n=== ПРОВЕРКА СОВМЕСТИМОСТИ РИГОВ ===")
            self._check_rig_compatibility(temp_actor)

        temp_actor.cleanup()

    def _print_rig_info(self):
        """Выводит информацию о скелете модели."""
        joints = self.actor.getJoints()
        if joints:
            print(f"\nСкелет модели: {len(joints)} костей")
            # Показать первые 10 костей
            for i, joint in enumerate(joints[:10]):
                print(f"  - {joint.getName()}")
            if len(joints) > 10:
                print(f"  ... и ещё {len(joints) - 10} костей")
        else:
            print("\nВНИМАНИЕ: Модель не имеет скелета (не rigged)")

    def _check_rig_compatibility(self, source_actor):
        """Проверяет совместимость скелетов модели и источника анимаций."""
        model_joints = set(j.getName() for j in self.actor.getJoints())
        source_joints = set(j.getName() for j in source_actor.getJoints())

        if not model_joints:
            print("ОШИБКА: Целевая модель не имеет скелета!")
            return

        if not source_joints:
            print("ОШИБКА: Источник анимаций не имеет скелета!")
            return

        # Найти общие и отсутствующие кости
        common = model_joints & source_joints
        missing_in_model = source_joints - model_joints
        extra_in_model = model_joints - source_joints

        print(f"Общих костей: {len(common)}")

        if missing_in_model:
            print(f"\nКости из анимации, отсутствующие в модели ({len(missing_in_model)}):")
            for name in sorted(missing_in_model)[:5]:
                print(f"  ! {name}")
            if len(missing_in_model) > 5:
                print(f"  ... и ещё {len(missing_in_model) - 5}")

        if extra_in_model:
            print(f"\nДополнительные кости в модели ({len(extra_in_model)}):")
            for name in sorted(extra_in_model)[:5]:
                print(f"  + {name}")
            if len(extra_in_model) > 5:
                print(f"  ... и ещё {len(extra_in_model) - 5}")

        # Вердикт
        compatibility = len(common) / len(source_joints) * 100 if source_joints else 0
        print(f"\nСовместимость: {compatibility:.0f}%")
        if compatibility >= 90:
            print("ОТЛИЧНО: Риги практически идентичны")
        elif compatibility >= 70:
            print("ХОРОШО: Большинство костей совпадают")
        elif compatibility >= 50:
            print("СРЕДНЕ: Часть анимации может работать некорректно")
        else:
            print("ПЛОХО: Риги сильно отличаются, анимация может не работать")

    def play_anim(self, idx):
        if idx < len(self.anims):
            self.current_anim_idx = idx
            anim_name = self.anims[idx]
            self.actor.stop()
            self.actor.loop(anim_name)
            self.actor.setPlayRate(self.play_rate, anim_name)
            self.anim_text.setText(f"Playing: {anim_name}")
            print(f"Проигрывается: {anim_name}")

    def stop_anim(self):
        self.actor.stop()
        self.anim_text.setText("Stopped")

    def change_rate(self, delta):
        self.play_rate = max(0.1, min(3.0, self.play_rate + delta))
        if self.current_anim_idx < len(self.anims):
            anim_name = self.anims[self.current_anim_idx]
            self.actor.setPlayRate(self.play_rate, anim_name)
        print(f"Скорость: {self.play_rate:.2f}x")

    def rotate_model(self):
        self.actor.setH(self.actor.getH() + 45)

    def rotate_camera(self, dh, dp):
        self.cam_heading += dh
        self.cam_pitch = max(-89, min(89, self.cam_pitch + dp))
        self.update_camera()

    def zoom(self, delta):
        self.cam_distance = max(1, min(20, self.cam_distance + delta))
        self.update_camera()

    def update_camera(self):
        from math import sin, cos, radians
        h_rad = radians(self.cam_heading)
        p_rad = radians(self.cam_pitch)

        x = self.cam_distance * cos(p_rad) * sin(h_rad)
        y = self.cam_distance * cos(p_rad) * cos(h_rad)
        z = self.cam_distance * sin(p_rad) + self.look_at_z

        self.camera.setPos(x, y, z)
        self.camera.lookAt(0, 0, self.look_at_z)

    def update_ui(self, task):
        current_anim = self.actor.getCurrentAnim()
        if current_anim:
            frame = self.actor.getCurrentFrame(current_anim)
            ctrl = self.actor.getAnimControl(current_anim)
            total = ctrl.getNumFrames() if ctrl else 0
            self.info_text.setText(
                f"Anim: {current_anim}\n"
                f"Frame: {frame:.0f}/{total}\n"
                f"Rate: {self.play_rate:.2f}x\n"
                f"Model H: {self.actor.getH():.0f}°"
            )
        else:
            self.info_text.setText("No animation")
        return task.cont


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Animation Viewer - проверка совместимости моделей и анимаций",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s                                      # player.bam со своими анимациями
  %(prog)s new_char.bam                         # new_char.bam со своими анимациями
  %(prog)s new_char.bam --anims player.bam      # new_char.bam + анимации от player.bam
  %(prog)s new_char.bam -a player.bam           # то же самое, короткая форма

Для моделей с Mixamo риги обычно совместимы (стандартный humanoid rig).
"""
    )
    parser.add_argument("model", nargs="?", default="nine/assets/models/player.bam",
                        help="Путь к модели (.bam или .egg)")
    parser.add_argument("-a", "--anims", dest="anims_source", default=None,
                        help="Файл-источник анимаций (если отличается от модели)")
    args = parser.parse_args()

    app = AnimViewer(args.model, args.anims_source)
    app.run()
