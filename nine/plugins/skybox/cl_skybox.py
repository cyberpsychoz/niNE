"""
Клиентский модуль скайбокса.
Создаёт скайбокс на основе конфигурации от сервера.
"""

from math import pi, sin, cos

from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexFormat,
    GeomVertexData, GeomVertexWriter, TransparencyAttrib, SamplerState
)
from direct.task import Task

from nine.core.plugins import PluginModule


class SkyboxClientModule(PluginModule):

    def on_load(self):
        self.skydome = None
        self._update_task_name = "update-skydome-plugin"

        # Подписка на конфигурацию мира
        self.event_manager.subscribe("world_config", self.on_world_config)

        self.logger.info("Клиентский модуль скайбокса загружен")

    def on_unload(self):
        self.event_manager.unsubscribe("world_config", self.on_world_config)
        self._destroy_skybox()
        self.logger.info("Клиентский модуль скайбокса выгружен")

    def on_world_config(self, data: dict):
        """Обрабатывает конфигурацию мира от сервера."""
        skybox_config = data.get("skybox", {})
        if skybox_config:
            self._create_skybox(skybox_config)

    def _destroy_skybox(self):
        """Удаляет текущий скайбокс."""
        if self.app.taskMgr.hasTaskNamed(self._update_task_name):
            self.app.taskMgr.remove(self._update_task_name)
        if self.skydome:
            self.skydome.removeNode()
            self.skydome = None

    def _create_skybox(self, config: dict):
        """Создаёт скайбокс на основе конфигурации."""
        self._destroy_skybox()

        texture_path = config.get("texture", "")
        if not texture_path:
            self.logger.warning("Текстура скайбокса не указана")
            return

        sky_texture = self.app.loader.loadTexture(texture_path)
        if not sky_texture:
            self.logger.warning(f"Не удалось загрузить текстуру: {texture_path}")
            return

        # Настройки качества текстуры
        sky_texture.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        sky_texture.setMagfilter(SamplerState.FT_linear)
        sky_texture.setAnisotropicDegree(4)

        # Параметры геометрии из конфига
        segments = config.get("segments", 64)
        rings = config.get("rings", 32)
        radius = config.get("radius", 1000)
        uv_scale = config.get("uv_scale", {})
        v_offset = uv_scale.get("v_offset", 0.15)
        v_scale = uv_scale.get("v_scale", 0.9)

        # Генерация сферы
        vformat = GeomVertexFormat.getV3t2()
        vdata = GeomVertexData('skydome', vformat, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        texcoord = GeomVertexWriter(vdata, 'texcoord')

        for ring in range(rings + 1):
            v = ring / rings
            phi = pi * v

            for seg in range(segments + 1):
                u = seg / segments
                theta = 2 * pi * u

                x = -radius * sin(phi) * cos(theta)
                y = -radius * sin(phi) * sin(theta)
                z = radius * cos(phi)

                vertex.addData3(x, y, z)
                v_scaled = v_offset + (1.0 - v) * v_scale
                texcoord.addData2(u, v_scaled)

        tris = GeomTriangles(Geom.UHStatic)
        for ring in range(rings):
            for seg in range(segments):
                curr = ring * (segments + 1) + seg
                next_ring = (ring + 1) * (segments + 1) + seg

                tris.addVertices(curr, next_ring, curr + 1)
                tris.addVertices(curr + 1, next_ring, next_ring + 1)

        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode('skydome')
        node.addGeom(geom)

        self.skydome = self.app.render.attachNewNode(node)
        self.skydome.setTexture(sky_texture)

        # Настройки рендеринга
        self.skydome.setTwoSided(True)
        self.skydome.setLightOff()
        self.skydome.setFogOff()
        self.skydome.setTransparency(TransparencyAttrib.MNone)
        self.skydome.setBin("background", 0)
        self.skydome.setDepthWrite(False)
        self.skydome.setDepthTest(False)

        # Задача для следования за камерой
        self.app.taskMgr.add(self._update_skybox_task, self._update_task_name)

        self.logger.info(f"Скайбокс создан: {texture_path}")

    def _update_skybox_task(self, task):
        """Держит скайбокс по центру камеры."""
        if self.skydome:
            self.skydome.setPos(self.app.camera.getPos(self.app.render))
        return Task.cont
