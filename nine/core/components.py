"""
Компоненты для Entity.
"""

from panda3d.bullet import BulletRigidBodyNode, BulletBoxShape, BulletSphereShape
from panda3d.core import Vec3

from nine.core.entity import Component


class PhysicsComponent(Component):
    """
    Компонент физики для Entity.
    Создаёт BulletRigidBodyNode и управляет им.
    """

    def __init__(self, physics_world, mass: float = 1.0, shape_type: str = "box",
                 shape_size: tuple = (0.2, 0.2, 0.2)):
        """
        Args:
            physics_world: BulletWorld для физики
            mass: Масса объекта (0 = статический)
            shape_type: Тип формы коллизии ("box" или "sphere")
            shape_size: Размеры формы (для box: (x, y, z), для sphere: (radius,))
        """
        super().__init__()
        self.physics_world = physics_world
        self.mass = mass
        self.shape_type = shape_type
        self.shape_size = shape_size

        self.rigid_body: BulletRigidBodyNode = None
        self.rigid_body_np = None

    def on_spawn(self):
        """Создаёт физическое тело при спавне entity."""
        if not self.entity or not self.entity._node:
            return

        # Создаём форму коллизии
        if self.shape_type == "sphere":
            radius = self.shape_size[0] if self.shape_size else 0.2
            shape = BulletSphereShape(radius)
        else:  # box
            half_extents = Vec3(
                self.shape_size[0] / 2,
                self.shape_size[1] / 2,
                self.shape_size[2] / 2
            ) if len(self.shape_size) >= 3 else Vec3(0.1, 0.1, 0.1)
            shape = BulletBoxShape(half_extents)

        # Создаём rigid body
        self.rigid_body = BulletRigidBodyNode(f"physics_{self.entity.unique_id[:8]}")
        self.rigid_body.addShape(shape)
        self.rigid_body.setMass(self.mass)

        # Добавляем трение и демпфирование для реалистичности
        self.rigid_body.setFriction(0.8)
        self.rigid_body.setLinearDamping(0.3)
        self.rigid_body.setAngularDamping(0.5)

        # Создаём NodePath и присоединяем к родителю entity
        parent = self.entity._node.getParent()
        self.rigid_body_np = parent.attachNewNode(self.rigid_body)

        # Синхронизируем позицию с entity
        pos = self.entity._node.getPos()
        self.rigid_body_np.setPos(pos)

        # Перепривязываем визуальную модель к физическому телу
        self.entity._node.reparentTo(self.rigid_body_np)
        self.entity._node.setPos(0, 0, 0)

        # Добавляем в физический мир
        self.physics_world.attachRigidBody(self.rigid_body)

    def on_remove(self):
        """Удаляет физическое тело из мира."""
        if self.rigid_body:
            self.physics_world.removeRigidBody(self.rigid_body)
            self.rigid_body = None

        if self.rigid_body_np:
            self.rigid_body_np.removeNode()
            self.rigid_body_np = None

    def update(self, dt: float):
        """Синхронизирует позицию entity с физическим телом."""
        # Позиция уже синхронизирована через reparentTo
        pass

    def get_position(self) -> tuple:
        """Возвращает текущую позицию физического тела."""
        if self.rigid_body_np:
            pos = self.rigid_body_np.getPos()
            return (pos.x, pos.y, pos.z)
        return (0, 0, 0)

    def set_position(self, pos: tuple):
        """Устанавливает позицию физического тела."""
        if self.rigid_body_np:
            self.rigid_body_np.setPos(*pos)

    def apply_impulse(self, impulse: tuple, point: tuple = None):
        """Применяет импульс к физическому телу."""
        if self.rigid_body:
            imp_vec = Vec3(*impulse)
            if point:
                point_vec = Vec3(*point)
                self.rigid_body.applyImpulse(imp_vec, point_vec)
            else:
                self.rigid_body.applyCentralImpulse(imp_vec)

    def is_on_ground(self) -> bool:
        """Проверяет, находится ли объект на земле."""
        if not self.rigid_body_np:
            return False
        # Простая проверка - скорость по Z близка к нулю
        vel = self.rigid_body.getLinearVelocity()
        return abs(vel.z) < 0.1
